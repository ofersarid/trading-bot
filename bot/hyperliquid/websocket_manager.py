"""
Robust WebSocket Manager for Hyperliquid.

Handles:
- Automatic reconnection with exponential backoff
- Heartbeat monitoring (ping/pong)
- Detailed connection state logging
- Emergency callbacks on disconnect (for position exit)
- Connection health metrics

CRITICAL: This is a trading system. Connection integrity is paramount.
"""

import asyncio
import contextlib
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import websockets
from websockets.exceptions import (
    ConnectionClosed,
    ConnectionClosedError,
    ConnectionClosedOK,
    InvalidStatusCode,
    WebSocketException,
)

# Configure module logger
logger = logging.getLogger("ws_manager")


class ConnectionState(Enum):
    """WebSocket connection states."""

    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    RECONNECTING = "RECONNECTING"
    FATAL_ERROR = "FATAL_ERROR"


@dataclass
class ConnectionMetrics:
    """Track connection health metrics."""

    connect_time: datetime | None = None
    disconnect_time: datetime | None = None
    last_message_time: datetime | None = None
    last_ping_time: datetime | None = None
    last_pong_time: datetime | None = None
    messages_received: int = 0
    reconnect_count: int = 0
    total_disconnects: int = 0
    consecutive_failures: int = 0

    def uptime_seconds(self) -> float:
        """Calculate current connection uptime."""
        if not self.connect_time:
            return 0.0
        return (datetime.now() - self.connect_time).total_seconds()

    def time_since_last_message(self) -> float:
        """Seconds since last message received."""
        if not self.last_message_time:
            return float("inf")
        return (datetime.now() - self.last_message_time).total_seconds()


@dataclass
class WebSocketConfig:
    """Configuration for WebSocket connection."""

    url: str = "wss://api.hyperliquid.xyz/ws"

    # Reconnection settings
    max_reconnect_attempts: int = 50  # Very high for trading - we NEED to stay connected
    initial_reconnect_delay: float = 1.0  # Start with 1 second
    max_reconnect_delay: float = 30.0  # Cap at 30 seconds
    reconnect_delay_multiplier: float = 1.5  # Exponential backoff factor

    # Heartbeat settings
    ping_interval: float = 20.0  # Send ping every 20 seconds
    ping_timeout: float = 10.0  # Wait 10 seconds for pong
    message_timeout: float = 60.0  # Consider connection dead if no messages for 60s

    # Connection settings
    connect_timeout: float = 30.0  # Timeout for initial connection
    close_timeout: float = 5.0  # Timeout for graceful close


class WebSocketManager:
    """
    Robust WebSocket manager with automatic reconnection and health monitoring.

    CRITICAL SAFETY FEATURES:
    - Calls on_disconnect callback immediately when connection is lost
    - This allows the trading system to exit positions before reconnecting
    - Detailed logging of all connection events for debugging
    """

    def __init__(
        self,
        config: WebSocketConfig | None = None,
        on_message: Callable[[dict], Awaitable[None]] | None = None,
        on_connect: Callable[[], Awaitable[None]] | None = None,
        on_disconnect: Callable[[str], Awaitable[None]] | None = None,
        on_state_change: Callable[[ConnectionState], None] | None = None,
        log_callback: Callable[[str], None] | None = None,
    ):
        """
        Initialize WebSocket manager.

        Args:
            config: WebSocket configuration
            on_message: Async callback for each message received
            on_connect: Async callback when connection established
            on_disconnect: CRITICAL - Async callback when connection lost (for emergency exits)
            on_state_change: Callback when connection state changes
            log_callback: Optional callback for UI logging
        """
        self.config = config or WebSocketConfig()
        self.on_message = on_message
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.on_state_change = on_state_change
        self.log_callback = log_callback

        # State
        self._state = ConnectionState.DISCONNECTED
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._subscriptions: list[dict] = []
        self._should_run = False
        self._reconnect_delay = self.config.initial_reconnect_delay

        # Metrics
        self.metrics = ConnectionMetrics()

        # Tasks
        self._receive_task: asyncio.Task | None = None
        self._heartbeat_task: asyncio.Task | None = None

    @property
    def state(self) -> ConnectionState:
        """Current connection state."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """Check if currently connected."""
        return self._state == ConnectionState.CONNECTED

    def _set_state(self, new_state: ConnectionState) -> None:
        """Update connection state and notify callback (no UI logging - dashboard handles display)."""
        if new_state != self._state:
            old_state = self._state
            self._state = new_state
            logger.info(f"[WebSocket] STATE: {old_state.value} → {new_state.value}")
            if self.on_state_change:
                self.on_state_change(new_state)

    def _log(self, message: str, level: str = "info") -> None:
        """Log message to both logger and optional UI callback."""
        log_func = getattr(logger, level)
        log_func(f"[WebSocket] {message}")
        if self.log_callback:
            self.log_callback(message)

    def add_subscription(self, subscription: dict) -> None:
        """Add a subscription to be sent on connect/reconnect."""
        self._subscriptions.append(subscription)

    async def start(self) -> None:
        """Start the WebSocket manager (connect and maintain connection)."""
        self._should_run = True
        self.metrics.consecutive_failures = 0

        while self._should_run:
            try:
                await self._connect_and_run()
            except asyncio.CancelledError:
                self._log("WebSocket manager cancelled", "warning")
                break
            except Exception as e:
                self._log(f"Unexpected error in WebSocket loop: {e}", "error")

            # Handle reconnection
            if self._should_run:
                self.metrics.consecutive_failures += 1

                if self.metrics.consecutive_failures > self.config.max_reconnect_attempts:
                    self._set_state(ConnectionState.FATAL_ERROR)
                    self._log(
                        f"FATAL: Max reconnect attempts ({self.config.max_reconnect_attempts}) exceeded!",
                        "critical",
                    )
                    break

                self._set_state(ConnectionState.RECONNECTING)
                self._log(
                    f"Reconnecting in {self._reconnect_delay:.1f}s "
                    f"(attempt {self.metrics.consecutive_failures}/{self.config.max_reconnect_attempts})",
                    "warning",
                )
                await asyncio.sleep(self._reconnect_delay)

                # Exponential backoff
                self._reconnect_delay = min(
                    self._reconnect_delay * self.config.reconnect_delay_multiplier,
                    self.config.max_reconnect_delay,
                )

    async def stop(self) -> None:
        """Stop the WebSocket manager gracefully."""
        self._should_run = False
        await self._cleanup()
        self._set_state(ConnectionState.DISCONNECTED)

    async def _connect_and_run(self) -> None:
        """Connect to WebSocket and run message loop."""
        self._set_state(ConnectionState.CONNECTING)

        try:
            logger.info(f"[WebSocket] Connecting to {self.config.url}...")

            # Create connection with explicit timeouts
            self._ws = await asyncio.wait_for(
                websockets.connect(
                    self.config.url,
                    ping_interval=None,  # We handle our own pings
                    ping_timeout=None,
                    close_timeout=self.config.close_timeout,
                    max_size=10 * 1024 * 1024,  # 10MB max message size
                ),
                timeout=self.config.connect_timeout,
            )

            # Connection successful
            self.metrics.connect_time = datetime.now()
            self.metrics.reconnect_count += 1 if self.metrics.total_disconnects > 0 else 0
            self.metrics.consecutive_failures = 0
            self._reconnect_delay = self.config.initial_reconnect_delay

            self._set_state(ConnectionState.CONNECTED)
            logger.info(
                f"[WebSocket] Connected! (reconnects: {self.metrics.reconnect_count}, "
                f"total disconnects: {self.metrics.total_disconnects})"
            )

            # Send subscriptions
            await self._send_subscriptions()

            # Notify connection callback
            if self.on_connect:
                await self.on_connect()

            # Start heartbeat monitor
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            # Run message loop
            await self._message_loop()

        except TimeoutError:
            self._log(f"Connection timeout after {self.config.connect_timeout}s", "error")
            raise
        except InvalidStatusCode as e:
            self._log(f"Invalid status code: {e.status_code}", "error")
            raise
        except ConnectionRefusedError:
            self._log("Connection refused by server", "error")
            raise
        except Exception as e:
            self._log(f"Connection error: {type(e).__name__}: {e}", "error")
            raise
        finally:
            await self._handle_disconnect("Connection ended")

    async def _send_subscriptions(self) -> None:
        """Send all registered subscriptions (no UI logging - dashboard summarizes)."""
        if not self._ws:
            return
        for sub in self._subscriptions:
            try:
                msg = {"method": "subscribe", "subscription": sub}
                await self._ws.send(json.dumps(msg))
                logger.info(f"[WebSocket] Subscribed: {sub.get('type', 'unknown')}")
            except Exception as e:
                self._log(f"Failed to subscribe {sub}: {e}", "error")

    async def _message_loop(self) -> None:
        """Process incoming messages."""
        if not self._ws:
            return
        try:
            async for message in self._ws:
                self.metrics.last_message_time = datetime.now()
                self.metrics.messages_received += 1

                try:
                    data = json.loads(message)

                    # Handle pong responses (tracked in metrics, not logged to UI)
                    if data.get("channel") == "pong":
                        self.metrics.last_pong_time = datetime.now()
                        continue

                    # Pass to message handler
                    if self.on_message:
                        await self.on_message(data)

                except json.JSONDecodeError as e:
                    self._log(f"Invalid JSON received: {e}", "warning")
                except Exception as e:
                    self._log(f"Error processing message: {e}", "error")

        except ConnectionClosedOK:
            self._log("Connection closed normally")
        except ConnectionClosedError as e:
            self._log(f"Connection closed with error: code={e.code}, reason={e.reason}", "error")
        except ConnectionClosed as e:
            self._log(f"Connection closed: {e}", "warning")

    async def _heartbeat_loop(self) -> None:
        """Monitor connection health with periodic pings."""
        while self._should_run and self.is_connected:
            try:
                await asyncio.sleep(self.config.ping_interval)

                if not self.is_connected:
                    break

                # Check for stale connection (no messages received)
                time_since_msg = self.metrics.time_since_last_message()
                if time_since_msg > self.config.message_timeout:
                    self._log(
                        f"STALE CONNECTION: No messages for {time_since_msg:.1f}s! Forcing reconnect.",
                        "critical",
                    )
                    if self._ws:
                        await self._ws.close(code=1000, reason="Stale connection")
                    break

                # Send ping
                self.metrics.last_ping_time = datetime.now()
                if self._ws:
                    await self._ws.send(json.dumps({"method": "ping"}))

                # Wait for pong
                await asyncio.sleep(self.config.ping_timeout)

                # Check if pong was received
                if self.metrics.last_pong_time:
                    pong_age = (datetime.now() - self.metrics.last_pong_time).total_seconds()
                    if pong_age > self.config.ping_timeout:
                        self._log(
                            f"PING TIMEOUT: No pong for {pong_age:.1f}s! Connection may be dead.",
                            "warning",
                        )

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._log(f"Heartbeat error: {e}", "error")

    async def _handle_disconnect(self, reason: str) -> None:
        """Handle disconnection - CRITICAL for trading safety."""
        self.metrics.disconnect_time = datetime.now()
        self.metrics.total_disconnects += 1

        uptime = self.metrics.uptime_seconds()
        self._log(
            f"DISCONNECTED after {uptime:.1f}s: {reason} "
            f"(total msgs: {self.metrics.messages_received}, disconnects: {self.metrics.total_disconnects})",
            "warning",
        )

        # CRITICAL: Notify disconnect callback IMMEDIATELY
        # This allows the trading system to exit positions before we try to reconnect
        if self.on_disconnect:
            try:
                await self.on_disconnect(reason)
            except Exception as e:
                self._log(f"Error in disconnect callback: {e}", "critical")

        await self._cleanup()

    async def _cleanup(self) -> None:
        """Clean up resources."""
        # Cancel heartbeat task
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._heartbeat_task

        # Close WebSocket
        if self._ws:
            try:
                await self._ws.close()
            except (ConnectionClosed, WebSocketException) as e:
                logger.debug(f"WebSocket close during cleanup (expected): {e}")
            except Exception as e:
                logger.warning(f"Unexpected error closing WebSocket: {e}")
            self._ws = None

    async def send(self, data: dict) -> bool:
        """Send a message through the WebSocket."""
        if not self.is_connected or not self._ws:
            self._log("Cannot send: not connected", "warning")
            return False

        try:
            await self._ws.send(json.dumps(data))
            return True
        except Exception as e:
            self._log(f"Send error: {e}", "error")
            return False

    def get_status_string(self) -> str:
        """Get a human-readable status string for display."""
        state_emoji = {
            ConnectionState.DISCONNECTED: "⭕",
            ConnectionState.CONNECTING: "🔄",
            ConnectionState.CONNECTED: "🟢",
            ConnectionState.RECONNECTING: "🟡",
            ConnectionState.FATAL_ERROR: "🔴",
        }

        emoji = state_emoji.get(self._state, "❓")
        uptime = self.metrics.uptime_seconds()

        if self._state == ConnectionState.CONNECTED:
            return f"{emoji} Connected ({uptime:.0f}s, {self.metrics.messages_received} msgs)"
        elif self._state == ConnectionState.RECONNECTING:
            return f"{emoji} Reconnecting... (attempt {self.metrics.consecutive_failures})"
        else:
            return f"{emoji} {self._state.value}"
