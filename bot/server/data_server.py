"""
Data Server for Multi-Terminal Dashboard.

Background process that:
- Connects to Hyperliquid WebSocket
- Processes trades into Volume Profiles
- Aggregates candles and generates signals
- Writes state files for UI terminals to read
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bot.signals.base import SignalDetector

from bot.core.candle_aggregator import MultiCoinCandleManager
from bot.hyperliquid.websocket_manager import ConnectionState, WebSocketConfig, WebSocketManager
from bot.indicators.volume_profile import (
    Trade as VPTrade,
)
from bot.indicators.volume_profile import (
    VolumeProfileBuilder,
    get_poc,
    get_significant_lvn_levels,
    get_value_area,
)
from bot.signals.detectors import (
    MACDSignalDetector,
    MomentumSignalDetector,
    RSISignalDetector,
    VolumeProfileSignalDetector,
)
from bot.strategies import get_strategy
from bot.ui.components import SignalBrainAdapter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.FileHandler("data_server.log"), logging.StreamHandler()],
)
logger = logging.getLogger("data_server")


class DataServer:
    """
    Background server that handles WebSocket and writes state files.

    State files are written to data/live-state/{coin}.json for UI terminals to read.
    """

    STATE_DIR = Path("data/live-state")
    UPDATE_INTERVAL = 0.5  # Write state every 500ms

    def __init__(
        self,
        coins: list[str] | None = None,
        strategy_name: str = "momentum_based",
    ) -> None:
        """
        Initialize the data server.

        Args:
            coins: List of coins to monitor (default: BTC, ETH, SOL)
            strategy_name: Strategy name for signal weighting
        """
        self.coins = coins or ["BTC", "ETH", "SOL"]
        self.strategy = get_strategy(strategy_name)

        # Ensure state directory exists
        self.STATE_DIR.mkdir(parents=True, exist_ok=True)

        # Volume Profile builders per coin
        self._vp_builders: dict[str, VolumeProfileBuilder] = {}
        for coin in self.coins:
            tick_size = 10.0 if coin == "BTC" else 1.0 if coin == "ETH" else 0.1
            self._vp_builders[coin] = VolumeProfileBuilder(
                tick_size=tick_size,
                session_type="daily",
                coin=coin,
            )

        # Candle manager for price data
        self._candle_manager = MultiCoinCandleManager(coins=self.coins)

        # Signal detectors
        self._detectors: list[SignalDetector] = [
            MomentumSignalDetector(),
            RSISignalDetector(),
            MACDSignalDetector(),
            VolumeProfileSignalDetector(),
        ]

        # Signal adapter for weighted scoring
        self._signal_adapter = SignalBrainAdapter(
            strategy=self.strategy,
            detectors=self._detectors,
        )

        # WebSocket manager
        self._ws_manager: WebSocketManager | None = None

        # Current prices per coin
        self._prices: dict[str, float] = {}

        # Running flag
        self._running = False

    async def run(self) -> None:
        """Main loop - connect WebSocket and periodically write state."""
        self._running = True

        logger.info(f"Starting Data Server for coins: {self.coins}")
        logger.info(f"Strategy: {self.strategy.name}")
        logger.info(f"State files will be written to: {self.STATE_DIR.absolute()}")

        # Setup WebSocket with subscriptions
        self._setup_websocket()

        # Run WebSocket and state writer concurrently
        if self._ws_manager:
            await asyncio.gather(
                self._ws_manager.start(),
                self._state_writer_loop(),
            )

    async def _state_writer_loop(self) -> None:
        """Periodically write state files."""
        while self._running:
            for coin in self.coins:
                self._write_state(coin)
            await asyncio.sleep(self.UPDATE_INTERVAL)

    async def stop(self) -> None:
        """Stop the server."""
        self._running = False
        if self._ws_manager:
            await self._ws_manager.stop()
        logger.info("Data Server stopped")

    def _setup_websocket(self) -> None:
        """Setup WebSocket manager with subscriptions."""
        self._ws_manager = WebSocketManager(
            config=WebSocketConfig(),
            on_message=self._handle_ws_message,
            on_connect=self._handle_ws_connect,
            on_disconnect=self._handle_ws_disconnect,
            on_state_change=self._handle_state_change,
        )

        # Add subscriptions (will be sent on connect)
        for coin in self.coins:
            self._ws_manager.add_subscription({"type": "trades", "coin": coin})

        # Subscribe to all mids for price updates
        self._ws_manager.add_subscription({"type": "allMids"})

    async def _handle_ws_message(self, data: dict) -> None:
        """Handle incoming WebSocket message."""
        channel = data.get("channel")

        if channel == "trades":
            await self._handle_trades(data)
        elif channel == "allMids":
            await self._handle_prices(data)

    async def _handle_trades(self, data: dict) -> None:
        """Handle trade data for Volume Profile building."""
        trades_data = data.get("data", [])
        for trade in trades_data:
            coin = trade.get("coin", "")
            if coin not in self._vp_builders:
                continue

            vp_trade = VPTrade(
                timestamp=datetime.now(),
                price=float(trade.get("px", 0)),
                size=float(trade.get("sz", 0)),
                side="B" if trade.get("side") == "B" else "A",
            )
            self._vp_builders[coin].add_trade(vp_trade)

    async def _handle_prices(self, data: dict) -> None:
        """Handle price updates for signal generation."""
        mids = data.get("data", {}).get("mids", {})

        for coin in self.coins:
            if coin in mids:
                price = float(mids[coin])
                self._prices[coin] = price
                self._process_price_update(coin, price)

    def _process_price_update(self, coin: str, price: float) -> None:
        """Process a price update through candle manager and signals."""
        timestamp = datetime.now()

        # Add to candle manager
        self._candle_manager.add_tick(coin, price, timestamp=timestamp)

        # Get candles and process signals
        candles = self._candle_manager.get_candles(coin)
        if candles:
            self._signal_adapter.process_candles(coin, candles)

    def _build_state(self, coin: str) -> dict[str, Any]:
        """Build state dict for a coin."""
        state: dict[str, Any] = {
            "coin": coin,
            "timestamp": datetime.now().isoformat(),
            "price": self._prices.get(coin, 0.0),
            "indicators": {},
            "signals": {
                "active": [],
                "combined": {
                    "direction": "WAIT",
                    "score": 0.0,
                    "threshold": self.strategy.signal_threshold,
                },
            },
        }

        # Volume Profile indicators
        if coin in self._vp_builders:
            profile = self._vp_builders[coin].get_profile()
            if profile and profile.levels:
                poc = get_poc(profile)
                va = get_value_area(profile)
                lvns = get_significant_lvn_levels(profile)

                state["indicators"]["session_vp"] = {
                    "poc": poc,
                    "vah": va[1] if va else None,
                    "val": va[0] if va else None,
                    "lvn": [lvn["price"] for lvn in lvns] if lvns else [],
                }

        # Momentum indicator
        candles = self._candle_manager.get_candles(coin)
        if candles and len(candles) >= 2:
            pct_change = ((candles[-1].close - candles[-2].close) / candles[-2].close) * 100
            state["indicators"]["momentum"] = {"1m_pct": round(pct_change, 4)}

        # Signals
        signals, long_score, short_score, threshold = self._signal_adapter.get_signal_display_data(
            coin
        )

        # Determine direction
        if long_score > short_score and long_score > 0:
            direction = "LONG"
            score = long_score
        elif short_score > long_score and short_score > 0:
            direction = "SHORT"
            score = short_score
        else:
            direction = "WAIT"
            score = max(long_score, short_score)

        state["signals"]["combined"] = {
            "direction": direction,
            "score": round(score, 3),
            "threshold": threshold,
        }

        # Active signals
        for signal in signals:
            state["signals"]["active"].append(
                {
                    "type": signal.signal_type.value,
                    "direction": signal.direction,
                    "strength": round(signal.strength, 3),
                }
            )

        return state

    def _write_state(self, coin: str) -> None:
        """Write state file for a coin."""
        state = self._build_state(coin)
        state_file = self.STATE_DIR / f"{coin}.json"

        try:
            # Write to temp file then rename (atomic write)
            temp_file = state_file.with_suffix(".tmp")
            temp_file.write_text(json.dumps(state, indent=2))
            temp_file.rename(state_file)
        except Exception as e:
            logger.error(f"Error writing state for {coin}: {e}")

    async def _handle_ws_connect(self) -> None:
        """Handle WebSocket connection established."""
        logger.info("WebSocket connected")

    async def _handle_ws_disconnect(self, reason: str) -> None:
        """Handle WebSocket disconnection."""
        logger.warning(f"WebSocket disconnected: {reason}")

    def _handle_state_change(self, state: ConnectionState) -> None:
        """Handle connection state change."""
        logger.info(f"Connection state: {state.value}")


async def run_server(
    coins: list[str] | None = None,
    strategy_name: str = "momentum_based",
) -> None:
    """Run the data server."""
    server = DataServer(coins=coins, strategy_name=strategy_name)

    try:
        await server.run()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await server.stop()


def main() -> None:
    """Entry point for data server."""
    import argparse

    parser = argparse.ArgumentParser(description="Trading Bot Data Server")
    parser.add_argument(
        "--coins",
        "-c",
        nargs="+",
        default=["BTC", "ETH", "SOL"],
        help="Coins to monitor (default: BTC ETH SOL)",
    )
    parser.add_argument(
        "--strategy",
        "-s",
        type=str,
        default="momentum_based",
        help="Strategy name (default: momentum_based)",
    )

    args = parser.parse_args()

    asyncio.run(
        run_server(
            coins=[c.upper() for c in args.coins],
            strategy_name=args.strategy,
        )
    )


if __name__ == "__main__":
    main()
