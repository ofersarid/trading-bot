#!/usr/bin/env python3
"""
Trading Bot Dashboard v2 - Observation Mode.

A simplified dashboard for validating indicators and signals:
- 3 market columns (BTC | ETH | SOL) arranged horizontally
- Each column shows indicator values + individual signals
- Combined weighted signal at bottom of each column
- Scrollable signal log history

Modes:
- Live: WebSocket connection to Hyperliquid
- Historical: Replay CSV/Parquet data from data/historical/
- Client: Read from data server state files (for multi-terminal setup)

Run with:
    python -m bot.ui.dashboard --live --strategy momentum_based
    python -m bot.ui.dashboard --historical data/historical/BTC_20260126 --strategy momentum_based
    python -m bot.ui.dashboard --coin BTC  # Client mode, reads from data server
"""

import asyncio
import contextlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from bot.signals.base import SignalDetector

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Footer, Static

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
from bot.simulation.historical_source import HistoricalDataSource
from bot.strategies import get_strategy
from bot.ui.components import MarketColumn, SignalBrainAdapter, StrategyPanel

# Configure logging - file only to avoid interfering with TUI
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.FileHandler("trading_bot.log")],
)
logger = logging.getLogger("dashboard")


class TradingDashboard(App):
    """Trading Bot 1.0 - Observation Dashboard."""

    CSS_PATH = "styles/dashboard.tcss"
    TITLE = "TRADING-BOT 1.0"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("space", "toggle_pause", "Pause/Resume"),
        Binding("r", "reset", "Reset"),
        Binding("s", "change_strategy", "Strategy"),
    ]

    # Reactive state
    is_paused: reactive[bool] = reactive(False)
    connection_state: reactive[ConnectionState] = reactive(ConnectionState.DISCONNECTED)

    # State file directory for client mode
    STATE_DIR = Path("data/live-state")

    def __init__(
        self,
        mode: Literal["live", "historical", "client"],
        strategy_name: str,
        coins: list[str] | None = None,
        historical_folder: str | None = None,
        replay_speed: float = 0.5,
    ) -> None:
        """
        Initialize the dashboard.

        Args:
            mode: "live" for WebSocket, "historical" for replay, "client" for state file polling
            strategy_name: Name of strategy to use for signal weighting
            coins: List of coins to monitor (default: BTC, ETH, SOL)
            historical_folder: Path to historical data folder (for historical mode)
            replay_speed: Seconds between candles in historical mode
        """
        super().__init__()
        self.mode = mode
        self.strategy = get_strategy(strategy_name)
        self.coins = coins or ["BTC", "ETH", "SOL"]
        self.historical_folder = historical_folder
        self.replay_speed = replay_speed

        # Data availability per coin (for historical mode)
        self._data_available: dict[str, bool] = {coin: True for coin in self.coins}

        # Type declarations for optional components
        self._vp_builders: dict[str, VolumeProfileBuilder] = {}
        self._candle_manager: MultiCoinCandleManager | None = None
        self._signal_adapter: SignalBrainAdapter | None = None
        self._detectors: list[SignalDetector] = []

        # Client mode doesn't need local data processing
        if mode != "client":
            # Volume Profile builders per coin
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
            self._detectors = [
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

        # WebSocket manager (for live mode)
        self._ws_manager: WebSocketManager | None = None

        # Historical data sources (for historical mode)
        self._historical_sources: dict[str, HistoricalDataSource] = {}

    def compose(self) -> ComposeResult:
        """Create the dashboard layout."""
        if self.mode == "client":
            coin = self.coins[0] if self.coins else "???"
            title = f"TRADING-BOT 1.0 | {coin} | CLIENT MODE"
        else:
            mode_str = "LIVE" if self.mode == "live" else "HISTORICAL"
            title = f"TRADING-BOT 1.0 | {mode_str}"

        yield Static(title, id="title-bar")

        # Strategy panel (not shown in client mode)
        if self.mode != "client":
            yield StrategyPanel(self.strategy, id="strategy-panel")

        with Horizontal(classes="main-content"):
            for coin in self.coins:
                # Add single-column class in client mode for full-width layout
                classes = "single-column" if self.mode == "client" else ""
                yield MarketColumn(coin, id=f"{coin.lower()}-column", classes=classes)

        yield Footer()

    async def on_mount(self) -> None:
        """Initialize on mount."""
        if self.mode == "client":
            self._start_state_polling()
        elif self.mode == "historical":
            await self._check_historical_data()
            self._start_historical_replay()
        else:
            self._start_live_connection()

    @work(exclusive=True)
    async def _start_state_polling(self) -> None:
        """Start polling state files from data server (client mode)."""
        self.notify(f"Polling state files from {self.STATE_DIR}")

        while not self.is_paused:
            for coin in self.coins:
                state_file = self.STATE_DIR / f"{coin}.json"
                if state_file.exists():
                    try:
                        state = json.loads(state_file.read_text())
                        self._update_from_state(coin, state)
                    except (json.JSONDecodeError, OSError) as e:
                        logger.debug(f"Error reading state for {coin}: {e}")
                else:
                    # Mark as no data if state file doesn't exist
                    try:
                        column = self.query_one(f"#{coin.lower()}-column", MarketColumn)
                        column.has_data = False
                    except Exception:
                        pass

            await asyncio.sleep(0.5)  # Poll every 500ms

    def _update_from_state(self, coin: str, state: dict[str, Any]) -> None:
        """Update UI from state file data."""
        try:
            column = self.query_one(f"#{coin.lower()}-column", MarketColumn)
            column.has_data = True

            # Update price in header
            if "price" in state:
                column.price = float(state["price"])

            # Update Volume Profile indicator
            vp_data = state.get("indicators", {}).get("session_vp", {})
            if vp_data:
                lines = []
                if vp_data.get("poc"):
                    lines.append(f"POC {vp_data['poc']:,.0f}")
                if vp_data.get("vah"):
                    lines.append(f"VAH {vp_data['vah']:,.0f}")
                if vp_data.get("val"):
                    lines.append(f"VAL {vp_data['val']:,.0f}")
                for lvn_price in vp_data.get("lvn", [])[:2]:
                    lines.append(f"LVN {lvn_price:,.0f}")

                vp_subcolumn = column.get_indicator_subcolumn("session_vp")
                if vp_subcolumn:
                    vp_subcolumn.update_values("\n".join(lines) if lines else "--")

            # Update Momentum indicator
            momentum_data = state.get("indicators", {}).get("momentum", {})
            if momentum_data:
                pct = momentum_data.get("1m_pct", 0)
                momentum_subcolumn = column.get_indicator_subcolumn("momentum")
                if momentum_subcolumn:
                    momentum_subcolumn.update_values(f"1m: {pct:+.2f}%")

            # Update signals
            signals_data = state.get("signals", {})
            combined = signals_data.get("combined", {})
            active = signals_data.get("active", [])

            # Update per-indicator signals
            for sig in active:
                sig_type = sig.get("type", "").lower()
                subcolumn = column.get_indicator_subcolumn(sig_type)
                if subcolumn:
                    direction = sig.get("direction", "?")[:1]
                    strength = sig.get("strength", 0)
                    subcolumn.update_signal(f"{direction} {strength:.2f}")

            # Update combined signal row
            combined_row = column.get_combined_row()
            if combined_row:
                direction = combined.get("direction", "WAIT")
                score = combined.get("score", 0)
                threshold = combined.get("threshold", 0.7)

                # Build contributions from active signals
                contributions: dict[str, float] = {}
                for sig in active:
                    key = sig.get("type", "UNK")[:3].upper()
                    contributions[key] = sig.get("strength", 0)

                combined_row.update_signal(direction, score, threshold, contributions)

        except Exception as e:
            logger.debug(f"Error updating from state for {coin}: {e}")

    async def _check_historical_data(self) -> None:
        """Check which coins have historical data available."""
        if not self.historical_folder:
            return

        folder = Path(self.historical_folder)
        if not folder.exists():
            logger.warning(f"Historical folder not found: {folder}")
            return

        for coin in self.coins:
            # Look for CSV or Parquet files
            csv_files = list(folder.glob(f"{coin}*.csv")) + list(
                folder.glob(f"{coin.upper()}*.csv")
            )
            parquet_files = list(folder.glob(f"{coin}*.parquet")) + list(
                folder.glob(f"{coin.upper()}*.parquet")
            )

            has_data = bool(csv_files or parquet_files)
            self._data_available[coin] = has_data

            # Update the MarketColumn
            try:
                column = self.query_one(f"#{coin.lower()}-column", MarketColumn)
                column.has_data = has_data

                # Load historical source if data exists
                if has_data and csv_files:
                    self._historical_sources[coin] = HistoricalDataSource(csv_files[0])
                    logger.info(f"Loaded historical data for {coin}: {csv_files[0]}")
            except Exception as e:
                logger.error(f"Error checking data for {coin}: {e}")

    @work(exclusive=True)
    async def _start_historical_replay(self) -> None:
        """Start replaying historical data."""
        if not self._historical_sources:
            self.notify("No historical data loaded", severity="error")
            return

        self.notify(f"Starting historical replay at {self.replay_speed}s interval")

        # Get all sources and interleave by timestamp
        sources = list(self._historical_sources.items())
        iterators = {coin: source.stream() for coin, source in sources}
        current_updates = {}

        # Get first update from each source
        for coin, iterator in iterators.items():
            with contextlib.suppress(StopIteration):
                current_updates[coin] = next(iterator)

        while current_updates and not self.is_paused:
            # Find the earliest update
            earliest_coin = min(current_updates, key=lambda c: current_updates[c].timestamp)
            update = current_updates[earliest_coin]

            # Process the update
            await self._process_price_update(earliest_coin, update.close, update.timestamp)

            # Get next update for this coin
            try:
                current_updates[earliest_coin] = next(iterators[earliest_coin])
            except StopIteration:
                del current_updates[earliest_coin]

            # Replay speed delay
            await asyncio.sleep(self.replay_speed)

        self.notify("Historical replay complete")

    def _start_live_connection(self) -> None:
        """Start live WebSocket connection."""
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
        self._ws_manager.add_subscription({"type": "allMids"})

        # Start WebSocket in background
        self._run_websocket()

    @work(exclusive=True)
    async def _run_websocket(self) -> None:
        """Run WebSocket connection (handles connect/reconnect automatically)."""
        if not self._ws_manager:
            return

        try:
            await self._ws_manager.start()
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            self.notify(f"Connection failed: {e}", severity="error")

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

        # Update VP indicators display
        for coin in self.coins:
            if coin in self._vp_builders:
                self._update_vp_display(coin)

    async def _handle_prices(self, data: dict) -> None:
        """Handle price updates for signal generation."""
        mids = data.get("data", {}).get("mids", {})

        for coin in self.coins:
            if coin in mids:
                price = float(mids[coin])
                await self._process_price_update(coin, price, datetime.now())

    async def _process_price_update(
        self,
        coin: str,
        price: float,
        timestamp: datetime,
    ) -> None:
        """Process a price update through candle manager and signals."""
        # Update price display in header
        try:
            column = self.query_one(f"#{coin.lower()}-column", MarketColumn)
            column.price = price
        except Exception:
            pass

        # Add to candle manager (use keyword arg since volume comes before timestamp)
        if self._candle_manager is None or self._signal_adapter is None:
            return

        self._candle_manager.add_tick(coin, price, timestamp=timestamp)

        # Get candles and process signals
        candles = self._candle_manager.get_candles(coin)
        if candles:
            self._signal_adapter.process_candles(coin, candles)

        # Update displays
        self._update_signal_display(coin)
        self._update_indicator_displays(coin, price)

    def _update_vp_display(self, coin: str) -> None:
        """Update Volume Profile indicator display."""
        if coin not in self._vp_builders:
            return

        profile = self._vp_builders[coin].get_profile()
        if not profile or not profile.levels:
            return

        # Get VP values
        poc = get_poc(profile)
        va = get_value_area(profile)
        lvns = get_significant_lvn_levels(profile)

        # Format values text
        lines = []
        if poc:
            lines.append(f"POC {poc:,.0f}")
        if va:
            lines.append(f"VAH {va[1]:,.0f}")
            lines.append(f"VAL {va[0]:,.0f}")
        if lvns:
            for lvn in lvns[:2]:
                lines.append(f"LVN {lvn['price']:,.0f}")

        values_text = "\n".join(lines) if lines else "--"

        # Update the session_vp subcolumn
        try:
            column = self.query_one(f"#{coin.lower()}-column", MarketColumn)
            subcolumn = column.get_indicator_subcolumn("session_vp")
            if subcolumn:
                subcolumn.update_values(values_text)
        except Exception:
            pass

    def _update_indicator_displays(self, coin: str, _price: float) -> None:
        """Update all indicator displays for a coin."""
        try:
            column = self.query_one(f"#{coin.lower()}-column", MarketColumn)

            # Momentum
            momentum_col = column.get_indicator_subcolumn("momentum")
            if momentum_col and self._candle_manager:
                # Get recent price changes from candle manager
                candles = self._candle_manager.get_candles(coin)
                if candles and len(candles) >= 2:
                    pct_change = ((candles[-1].close - candles[-2].close) / candles[-2].close) * 100
                    momentum_col.update_values(f"1m: {pct_change:+.2f}%")

            # RSI placeholder
            rsi_col = column.get_indicator_subcolumn("rsi")
            if rsi_col:
                rsi_col.update_values("RSI: --")

            # MACD placeholder
            macd_col = column.get_indicator_subcolumn("macd")
            if macd_col:
                macd_col.update_values("Line: --\nSig: --")

        except Exception:
            pass

    def _update_signal_display(self, coin: str) -> None:
        """Update signal displays for a coin."""
        if self._signal_adapter is None:
            return

        try:
            # Get signal data from adapter
            signals, long_score, short_score, threshold = (
                self._signal_adapter.get_signal_display_data(coin)
            )

            # Determine direction and score
            if long_score > short_score and long_score > 0:
                direction = "LONG"
                score = long_score
            elif short_score > long_score and short_score > 0:
                direction = "SHORT"
                score = short_score
            else:
                direction = "WAIT"
                score = max(long_score, short_score)

            # Build contributions dict
            contributions: dict[str, float] = {}
            for signal in signals:
                weight = self.strategy.signal_weights.get(signal.signal_type, 0)
                contrib = signal.strength * weight
                key = signal.signal_type.value[:3].upper()
                if key not in contributions:
                    contributions[key] = 0
                contributions[key] += contrib

            # Update individual signal indicators
            column = self.query_one(f"#{coin.lower()}-column", MarketColumn)

            # Update per-indicator signals
            for signal in signals:
                signal_type = signal.signal_type.value.lower()
                subcolumn = column.get_indicator_subcolumn(signal_type)
                if subcolumn:
                    sig_text = f"{signal.direction[:1]} {signal.strength:.2f}"
                    subcolumn.update_signal(sig_text)

            # Update combined signal row
            combined_row = column.get_combined_row()
            if combined_row:
                combined_row.update_signal(direction, score, threshold, contributions)

        except Exception as e:
            logger.debug(f"Error updating signal display for {coin}: {e}")

    async def _handle_ws_connect(self) -> None:
        """Handle WebSocket connection established."""
        self.notify("Connected to Hyperliquid", severity="information")

    async def _handle_ws_disconnect(self, reason: str) -> None:
        """Handle WebSocket disconnection."""
        self.notify(f"Disconnected: {reason}", severity="warning")

    def _handle_state_change(self, state: ConnectionState) -> None:
        """Handle connection state change."""
        self.connection_state = state

    def action_toggle_pause(self) -> None:
        """Toggle pause state."""
        self.is_paused = not self.is_paused
        status = "Paused" if self.is_paused else "Resumed"
        self.notify(status)

    def action_reset(self) -> None:
        """Reset all state."""
        if self.mode == "client":
            self.notify("Reset not available in client mode")
            return

        for builder in self._vp_builders.values():
            builder.reset()
        if self._signal_adapter:
            self._signal_adapter.reset()
        self.notify("State reset")

    def action_change_strategy(self) -> None:
        """Cycle to the next strategy."""
        if self.mode == "client":
            self.notify("Strategy change not available in client mode")
            return

        try:
            # Get the strategy panel and next strategy
            panel = self.query_one("#strategy-panel", StrategyPanel)
            new_strategy = panel.get_next_strategy()

            # Update the dashboard's strategy
            self.strategy = new_strategy

            # Reinitialize the signal adapter with new strategy
            if self._signal_adapter:
                self._signal_adapter = SignalBrainAdapter(
                    strategy=new_strategy,
                    detectors=self._detectors,
                )

            # Update the panel display
            panel.update_strategy(new_strategy)

            self.notify(f"Strategy: {new_strategy.name}")
        except Exception as e:
            logger.error(f"Error changing strategy: {e}")
            self.notify(f"Error: {e}", severity="error")

    async def on_unmount(self) -> None:
        """Cleanup on unmount."""
        if self._ws_manager:
            await self._ws_manager.stop()


def main() -> None:
    """Entry point for dashboard."""
    import argparse

    parser = argparse.ArgumentParser(description="Trading Bot Dashboard v2")
    parser.add_argument("--live", action="store_true", help="Live mode (WebSocket)")
    parser.add_argument("--historical", type=str, help="Historical mode (folder path)")
    parser.add_argument(
        "--coin", type=str, help="Client mode - single coin (reads from data server)"
    )
    parser.add_argument("--strategy", type=str, default="momentum_based", help="Strategy name")
    parser.add_argument(
        "--coins", type=str, nargs="+", default=["BTC", "ETH", "SOL"], help="Coins to monitor"
    )
    parser.add_argument("--speed", type=float, default=0.5, help="Replay speed (seconds)")

    args = parser.parse_args()

    mode: Literal["live", "historical", "client"]
    coins: list[str]
    historical_folder: str | None = None

    if args.coin:
        # Client mode - single coin, reads from data server state files
        mode = "client"
        coins = [args.coin.upper()]
    elif args.historical:
        mode = "historical"
        historical_folder = args.historical
        coins = [c.upper() for c in args.coins]
    elif args.live:
        mode = "live"
        coins = [c.upper() for c in args.coins]
    else:
        # Default to live mode
        mode = "live"
        coins = [c.upper() for c in args.coins]

    app = TradingDashboard(
        mode=mode,
        strategy_name=args.strategy,
        coins=coins,
        historical_folder=historical_folder,
        replay_speed=args.speed,
    )
    app.run()


if __name__ == "__main__":
    main()
