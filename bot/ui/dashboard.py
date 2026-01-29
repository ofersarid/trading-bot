#!/usr/bin/env python3
"""
Retro Terminal Dashboard for Paper Trading.

A dark-themed, scrollable UI showing:
- Live prices with changes
- Order book depth
- Real-time trades
- AI reasoning log
- Opportunity pipeline
- Open positions & trade history

CRITICAL SAFETY FEATURES:
- WebSocket connection monitoring with auto-reconnect
- Emergency position exit on disconnect
- Detailed connection logging for debugging

Run with:
    python bot/ui/dashboard.py --balance 10000
"""

import logging
import os
import sys
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from bot.signals.base import SignalDetector

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Footer, Static

from bot.ai import AIDecision, OllamaClient, TradingStrategy
from bot.ai import MarketAnalyzer as AIMarketAnalyzer
from bot.core.analysis import (
    MarketAnalyzer,
    MomentumResult,
    calculate_momentum,
    calculate_momentum_with_acceleration,
)
from bot.core.candle_aggregator import MultiCoinCandleManager
from bot.core.config import DEFAULT_CONFIG, TradingConfig
from bot.core.models import MarketPressure
from bot.hyperliquid.websocket_manager import ConnectionState, WebSocketConfig, WebSocketManager
from bot.indicators.volume_profile import Trade as VPTrade
from bot.indicators.volume_profile import VolumeProfileBuilder
from bot.signals.detectors import (
    MACDSignalDetector,
    MomentumSignalDetector,
    RSISignalDetector,
)
from bot.simulation.historical_source import HistoricalDataSource
from bot.simulation.models import HYPERLIQUID_FEES
from bot.simulation.paper_trader import PaperTrader
from bot.simulation.state_manager import SessionStateManager
from bot.strategies import Strategy, get_strategy
from bot.tuning import FeedbackCollector, PerformanceAnalyzer, TuningReportExporter
from bot.ui.components import (
    AIPanel,
    ChartsPanel,
    GoalData,
    GoalPanel,
    HistoryPanel,
    MarketsPanel,
    SignalBrainAdapter,
    StatusBar,
)

# Configure logging - file only to avoid interfering with TUI
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler("trading_bot.log"),
    ],
)
logger = logging.getLogger("dashboard")


# ============================================================
# Theme Colors (Rich markup hex codes)
# ============================================================
COLOR_UP = "#44ffaa"  # Bright green for positive/buy/profit
COLOR_DOWN = "#ff7777"  # Bright red for negative/sell/loss


# ============================================================
# Main Dashboard App
# ============================================================
class TradingDashboard(App):
    """Retro terminal trading dashboard."""

    CSS_PATH = "styles/theme.css"
    TITLE = "PAPER TRADING SIMULATOR"
    SHOW_TITLE = False  # Hide default header title
    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("r", "reset", "Reset"),
        Binding("p", "toggle_pause", "Pause"),
        Binding("ctrl+r", "restart", "Restart"),
        Binding("s", "cycle_strategy", "Strategy"),
        Binding("t", "tuning_report", "Tuning"),
        Binding("c", "toggle_charts", "Charts"),
    ]

    # Auto-save interval in seconds
    AUTO_SAVE_INTERVAL = 60

    # Available AI trading strategies
    AI_STRATEGIES = [
        TradingStrategy.MOMENTUM_BASED,
        TradingStrategy.MOMENTUM_MACD,
        TradingStrategy.RSI_BASED,
        TradingStrategy.MULTI_SIGNAL,
    ]

    # Reactive state
    balance = reactive(10000.0)
    equity = reactive(10000.0)
    total_pnl = reactive(0.0)

    def __init__(
        self,
        starting_balance: float = 10000,
        coins: list[str] | None = None,
        config: TradingConfig | None = None,
        resume: bool = False,
        session_name: str | None = None,
        historical_file: str | None = None,
        historical_speed: float = 0.5,
    ):
        super().__init__()
        self.config = config or DEFAULT_CONFIG
        self.starting_balance = starting_balance
        self.coins = coins or ["BTC", "ETH", "SOL"]
        self.resume_mode = resume
        self.session_name = session_name or "default"

        # Historical replay mode
        self.historical_file = historical_file
        self.historical_speed = historical_speed
        self.historical_source: HistoricalDataSource | None = None
        self.is_historical_mode = historical_file is not None
        self.historical_complete = False
        self.historical_candles_processed = 0
        self.simulated_time: datetime | None = None

        # Data stores
        self.prices: dict[str, float] = {}
        self.orderbook: dict[str, dict] = {}  # {coin: {bids: [], asks: []}}
        self.trades: deque = deque(maxlen=self.config.max_trades_history)

        # Market pressure tracking
        self.market_pressure: MarketPressure | None = None

        # Price history for momentum calculation
        self.price_history: dict[str, deque] = {
            coin: deque(maxlen=self.config.price_history_maxlen) for coin in self.coins
        }

        # Velocity tracking for acceleration calculation
        self._previous_velocity: dict[str, float] = {}

        # Market analysis state
        self.last_market_analysis = datetime.now()

        # Momentum timeframe for AI analysis
        self.momentum_timeframe = 5  # seconds

        # Analysis mode - AI uses local Ollama with Mistral (default: AI enabled)
        self.analysis_mode = "AI (Local)"
        self.ai_model = "mistral:7b"
        self.tokens_used = 0
        self.ai_calls = 0

        # AI Trading Strategy - defines how the AI trades (via prompt)
        self.ai_strategy = TradingStrategy.MOMENTUM_BASED

        # Local AI analyzer (Ollama + Mistral) - enabled by default
        self.ai_client = OllamaClient(model="mistral")
        self.ai_analyzer = AIMarketAnalyzer(client=self.ai_client, enabled=True)

        # AI decision interval (how often AI makes decisions)
        self.ai_decision_interval = 10  # seconds
        self._last_ai_decision = datetime.now()

        # Candle aggregator for charting (1-minute candles)
        self.candle_manager = MultiCoinCandleManager(
            coins=self.coins,
            max_candles=60,  # Keep 1 hour of candles
            on_candle_complete=self._on_candle_complete,
        )

        # Volume Profile builders per coin (for live VP analysis)
        self.vp_builders: dict[str, VolumeProfileBuilder] = {
            coin: VolumeProfileBuilder(
                tick_size=10.0,  # $10 buckets for BTC-like assets
                session_type="daily",
                coin=coin,
            )
            for coin in self.coins
        }

        # Signal Brain Adapter for real-time signal display
        # Maps the current AI strategy to the appropriate Strategy object
        self._signal_strategy = self._get_strategy_for_trading_strategy(self.ai_strategy)
        self._signal_detectors: list["SignalDetector"] = [
            MomentumSignalDetector(),
            RSISignalDetector(),
            MACDSignalDetector(),
        ]
        self.signal_adapter = SignalBrainAdapter(
            strategy=self._signal_strategy,
            detectors=self._signal_detectors,
        )

        # Session state manager for persistence (supports multiple named sessions)
        self.state_manager = SessionStateManager(session_name=self.session_name)

        # Paper trader - may be restored from saved state
        self.trader = PaperTrader(
            starting_balance=starting_balance,
            fees=HYPERLIQUID_FEES,
        )

        # Try to restore from saved session if resume mode
        self._restored_from_state = False
        if resume and self.state_manager.has_saved_state:
            self._restore_session_state()

        # Market analyzer for condition classification
        self.market_analyzer = MarketAnalyzer(self.config)

        # Feedback loop for parameter tuning
        # Reports are saved in the session's folder
        self.feedback_collector = FeedbackCollector()
        self.performance_analyzer = PerformanceAnalyzer(self.feedback_collector)
        self.tuning_exporter = TuningReportExporter(
            self.feedback_collector,
            self.performance_analyzer,
            output_dir=str(self.state_manager.get_reports_dir()),
        )

        # Track entry momentum for feedback recording
        self.entry_momentum: dict[str, float] = {}  # {coin: momentum_at_entry}

        # Auto-save tracking
        self._last_auto_save = datetime.now()

        # WebSocket manager with robust reconnection
        ws_config = WebSocketConfig(
            url="wss://api.hyperliquid.xyz/ws",
            max_reconnect_attempts=100,  # Very high - we MUST stay connected
            initial_reconnect_delay=1.0,
            max_reconnect_delay=30.0,
            ping_interval=20.0,
            ping_timeout=10.0,
            message_timeout=60.0,
        )
        self.ws_manager = WebSocketManager(
            config=ws_config,
            on_message=self._handle_ws_message,
            on_connect=self._handle_ws_connect,
            on_disconnect=self._handle_ws_disconnect,
            on_state_change=self._handle_ws_state_change,
            log_callback=self._log_ai_threadsafe,
        )

        # State
        self.paused = False
        self.ws_connected = False
        self.emergency_exit_in_progress = False
        self.start_time = datetime.now()

        # Goal tracking state
        # These can be configured via session config or CLI in the future
        self.account_goal: float | None = None  # Target balance
        self.goal_timeframe_days: int | None = None  # Days to reach goal
        self.goal_start_date: datetime = datetime.now()  # When goal tracking started
        self.last_ai_multiplier: float = 1.0  # Last AI position sizing multiplier

        # UI visibility state
        self.charts_visible: bool = True  # Charts panel visibility

    def _get_strategy_for_trading_strategy(self, ts: TradingStrategy) -> Strategy:
        """Map TradingStrategy enum to Strategy object for signal adapter."""
        strategy_map = {
            TradingStrategy.MOMENTUM_BASED: "momentum_based",
            TradingStrategy.MOMENTUM_MACD: "momentum_macd",
            TradingStrategy.RSI_BASED: "rsi_based",
            TradingStrategy.MULTI_SIGNAL: "multi_signal",
        }
        strategy_name = strategy_map.get(ts, "momentum_based")
        return get_strategy(strategy_name)

    def _restore_session_state(self) -> None:
        """Restore session state from disk."""
        state = self.state_manager.load_state()
        if not state:
            return

        # Restore trader state
        positions = self.state_manager.deserialize_positions(state.positions)
        self.trader.load_state(
            balance=state.balance,
            positions=positions,
            total_fees_paid=state.total_fees_paid,
        )

        # Update starting balance to match saved session
        self.starting_balance = state.starting_balance
        self.trader.starting_balance = state.starting_balance

        self._restored_from_state = True
        logger.info(f"Restored session: balance=${state.balance:.2f}, {len(positions)} positions")

    def _save_session_state(self) -> None:
        """Save current session state to disk."""
        self.state_manager.update_from_trader(
            balance=self.trader.balance,
            starting_balance=self.starting_balance,
            total_fees_paid=self.trader.total_fees_paid,
            positions=self.trader.positions,
            trade_count=len(self.trader.trade_history) + len(self.feedback_collector.trades),
            winning_count=self.trader.get_winning_count(),
        )

    def _save_session_logs(self) -> None:
        """Save AI panel logs to a timestamped file."""
        try:
            logs_dir = self.state_manager.session_dir / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = logs_dir / f"session_log_{timestamp}.txt"

            # Get logs from AI panel
            ai_panel = self.query_one(AIPanel)

            with log_file.open("w") as f:
                f.write(f"Session: {self.session_name}\n")
                f.write(f"Saved: {datetime.now().isoformat()}\n")
                f.write(f"Strategy: {self.ai_strategy.value}\n")
                f.write(f"Balance: ${self.trader.balance:,.2f}\n")
                pnl = self.trader.balance - self.starting_balance
                f.write(f"P&L: ${pnl:+,.2f}\n")
                f.write("=" * 60 + "\n\n")

                for timestamp_str, message in ai_panel.messages:
                    # Strip Rich markup for plain text file
                    clean_msg = self._strip_markup(message)
                    if timestamp_str:
                        f.write(f"[{timestamp_str}] {clean_msg}\n")
                    else:
                        f.write(f"           {clean_msg}\n")

            logger.info(f"Saved session logs to {log_file}")
        except Exception as e:
            logger.error(f"Failed to save session logs: {e}")

    def _strip_markup(self, text: str) -> str:
        """Strip Rich markup from text for plain text output."""
        import re

        return re.sub(r"\[/?[^\]]+\]", "", text)

    def _auto_save(self) -> None:
        """Auto-save session state and logs."""
        self._save_session_state()
        self._save_session_logs()
        self._last_auto_save = datetime.now()
        self.log_ai("[dim]💾 Auto-saved session state and logs[/dim]")

    def compose(self) -> ComposeResult:
        """Create the dashboard layout using extracted components."""
        # Custom title bar with session name and mode indicator
        if self.is_historical_mode:
            title = f"PAPER TRADING SIMULATOR  ⟫  {self.session_name}  [📼 HISTORICAL]"
        else:
            title = f"PAPER TRADING SIMULATOR  ⟫  {self.session_name}"
        yield Static(title, id="title-bar", classes="title-bar")

        # Goal progress panel (shows AI position sizing context)
        yield GoalPanel(id="goal-panel")

        # Status bar
        yield StatusBar(id="status-row", classes="status-row")

        # Main content area: AI sidebar (left) + instruments panel (right)
        with Horizontal(classes="main-content"):
            # Left sidebar: AI Reasoning log
            yield AIPanel(id="ai-panel", classes="panel")

            # Right side: Markets table + Charts + History
            with Vertical(classes="data-panels"):
                # Markets panel with DataTable
                yield MarketsPanel(self.coins, id="markets-panel", classes="panel")

                # Candlestick charts for each coin
                yield ChartsPanel(self.coins, id="charts-panel", classes="panel")

                # Global trade history at bottom
                yield HistoryPanel(id="history-panel", classes="panel")

        yield Footer()

    def on_mount(self) -> None:
        """Start data streams when app mounts."""
        self.update_ai_title()
        self.update_strategy_bar()
        self.update_goal_panel()

        # Log session status
        strategy_name = self.ai_strategy.value.replace("_", " ").title()

        if self.is_historical_mode:
            # Historical replay mode
            assert self.historical_file is not None  # Guaranteed by is_historical_mode
            try:
                self.historical_source = HistoricalDataSource(self.historical_file)
                # Override coins to match historical data
                self.coins = [self.historical_source.coin]

                self.log_ai("[cyan]━━━ 📼 HISTORICAL REPLAY MODE ━━━[/cyan]")
                self.log_ai(f"[dim]  File: {self.historical_source.filepath.name}[/dim]")
                self.log_ai(f"[dim]  Coin: {self.historical_source.coin}[/dim]")
                self.log_ai(
                    f"[dim]  Period: {self.historical_source.start_time.strftime('%Y-%m-%d %H:%M')} → "
                    f"{self.historical_source.end_time.strftime('%Y-%m-%d %H:%M')}[/dim]"
                )
                self.log_ai(f"[dim]  Candles: {self.historical_source.candle_count}[/dim]")
                self.log_ai(f"[dim]  Speed: {self.historical_speed}s per candle[/dim]")
                self.log_ai(f"[dim]🤖 AI Mode: {self.ai_model} | Strategy: {strategy_name}[/dim]")
                self.log_ai("")
                self.log_ai("[yellow]▶ Starting replay... Press Q to stop[/yellow]")

                # Start historical replay instead of WebSocket
                self.run_historical_replay()

            except Exception as e:
                self.log_ai(f"[{COLOR_DOWN}]❌ Failed to load historical data: {e}[/{COLOR_DOWN}]")
                return
        else:
            # Live mode
            if self._restored_from_state:
                pnl = self.trader.balance - self.starting_balance
                pnl_color = COLOR_UP if pnl >= 0 else COLOR_DOWN
                self.log_ai(f"[{COLOR_UP}]✓ Session '{self.session_name}' restored[/{COLOR_UP}]")
                self.log_ai(
                    f"[dim]  Balance: ${self.trader.balance:,.2f} | P&L: [{pnl_color}]${pnl:+,.2f}[/{pnl_color}][/dim]"
                )
                if self.trader.positions:
                    self.log_ai(
                        f"[dim]  Open positions: {', '.join(self.trader.positions.keys())}[/dim]"
                    )
            else:
                self.log_ai(f"Dashboard initialized. Session: '{self.session_name}'")

            self.log_ai(f"[dim]🤖 AI Mode: {self.ai_model} | Strategy: {strategy_name}[/dim]")
            self.log_ai(f"[dim]AI makes decisions every {self.ai_decision_interval}s[/dim]")

            # Check AI availability on startup
            self.check_ai_availability()

            # Set up WebSocket subscriptions
            self.ws_manager.add_subscription({"type": "allMids"})
            for coin in self.coins:
                self.ws_manager.add_subscription({"type": "trades", "coin": coin})
                self.ws_manager.add_subscription({"type": "l2Book", "coin": coin})

            self.run_websocket()

        # Update status bar every second for uptime counter
        self.set_interval(1, self.update_status_bar)
        # Update positions P&L every second
        self.set_interval(1, self.update_positions_display)
        # Update AI title periodically
        self.set_interval(5, self.update_ai_title)
        # Update candlestick charts every 5 seconds
        self.set_interval(5, self._refresh_all_charts)
        # Auto-save session state and logs every minute
        self.set_interval(self.AUTO_SAVE_INTERVAL, self._auto_save)

    @work(exclusive=True)
    async def run_websocket(self) -> None:
        """Connect to WebSocket using robust manager."""
        logger.info("Starting WebSocket manager...")
        await self.ws_manager.start()

    @work(exclusive=True)
    async def run_historical_replay(self) -> None:
        """Replay historical data through the price handling system."""
        import asyncio

        if not self.historical_source:
            return

        logger.info(f"Starting historical replay: {self.historical_source}")
        self.ws_connected = True  # Fake connected status for UI

        # Reinitialize data structures for the historical coin
        historical_coin = self.historical_source.coin
        self.price_history = {historical_coin: deque(maxlen=self.config.price_history_maxlen)}

        try:
            for update in self.historical_source.stream():
                if self.historical_complete:
                    break

                # Update simulated time
                self.simulated_time = update.timestamp
                self.historical_candles_processed += 1

                # Create a fake "allMids" message structure
                fake_message = {
                    "channel": "allMids",
                    "data": {
                        "mids": {
                            update.coin: str(update.price),
                        }
                    },
                }

                # Process through existing handler (updates prices)
                await self.process_message(fake_message)

                # AI decisions are triggered automatically via analyze_market_conditions
                # which is called from handle_prices based on ai_decision_interval (10s)

                # Progress log every 50 candles
                if self.historical_candles_processed % 50 == 0:
                    progress_pct = (
                        self.historical_candles_processed / self.historical_source.candle_count
                    ) * 100
                    self.log_ai(
                        f"[dim]📼 Replay: {self.historical_candles_processed}/{self.historical_source.candle_count} "
                        f"({progress_pct:.0f}%) - {update.timestamp.strftime('%Y-%m-%d %H:%M')}[/dim]"
                    )

                # Delay between candles for visualization
                await asyncio.sleep(self.historical_speed)

        except Exception as e:
            self.log_ai(f"[{COLOR_DOWN}]❌ Replay error: {e}[/{COLOR_DOWN}]")
            logger.error(f"Historical replay failed: {e}")

        # Replay complete
        self.historical_complete = True
        self._on_historical_complete()

    def _on_historical_complete(self) -> None:
        """Handle completion of historical replay."""
        self.log_ai("")
        self.log_ai("[cyan]━━━ 📼 REPLAY COMPLETE ━━━[/cyan]")
        self.log_ai(f"[dim]  Candles processed: {self.historical_candles_processed}[/dim]")

        # Close any open positions
        if self.trader.positions:
            self.log_ai("[yellow]  Closing open positions...[/yellow]")
            for coin in list(self.trader.positions.keys()):
                price = self.prices.get(coin)
                if price:
                    result = self.trader.close_position(coin, price)
                    pnl_color = COLOR_UP if result.trade and result.trade.pnl >= 0 else COLOR_DOWN
                    self.log_ai(f"[{pnl_color}]  → {result.message}[/{pnl_color}]")

        # Show final results
        state = self.trader.get_state(self.prices)
        pnl = state.balance - self.starting_balance
        pnl_pct = (pnl / self.starting_balance) * 100
        pnl_color = COLOR_UP if pnl >= 0 else COLOR_DOWN

        self.log_ai("")
        self.log_ai("[bold]📊 FINAL RESULTS[/bold]")
        self.log_ai(f"  Starting Balance: ${self.starting_balance:,.2f}")
        self.log_ai(f"  Final Balance:    ${state.balance:,.2f}")
        self.log_ai(
            f"  P&L:              [{pnl_color}]${pnl:+,.2f} ({pnl_pct:+.2f}%)[/{pnl_color}]"
        )
        self.log_ai(f"  Trades:           {state.total_trades}")
        self.log_ai(f"  Win Rate:         {state.win_rate:.1f}%")
        self.log_ai(f"  Fees Paid:        ${state.total_fees:,.2f}")
        self.log_ai("")
        self.log_ai("[dim]Press Q to exit[/dim]")

        # Update displays
        self.update_positions_display()
        self.update_history_display()
        self.update_status_bar()
        self.update_goal_panel()

    async def _handle_ws_message(self, data: dict) -> None:
        """Handle incoming WebSocket message."""
        if self.paused:
            return
        await self.process_message(data)

    async def _handle_ws_connect(self) -> None:
        """Handle WebSocket connection established."""
        self.ws_connected = True
        self.emergency_exit_in_progress = False

        coins_str = ", ".join(self.coins)

        def log_connection():
            self.log_ai(f"[{COLOR_UP}]✓ Connected to Hyperliquid WebSocket[/{COLOR_UP}]")
            self.log_ai(f"[dim]📡 Subscribed to: prices, trades, orderbooks for {coins_str}[/dim]")
            self.log_ai("[yellow]⏳ Waiting for market data...[/yellow]")

        self._run_on_main_thread(log_connection)

    async def _handle_ws_disconnect(self, reason: str) -> None:
        """
        Handle WebSocket disconnection - CRITICAL SAFETY HANDLER (called from worker thread).

        This is called IMMEDIATELY when connection is lost.
        We must exit all positions to protect capital.
        """
        self.ws_connected = False

        # Log the disconnect with high visibility (thread-safe)
        self._log_ai_threadsafe(f"[{COLOR_DOWN}]🚨 WEBSOCKET DISCONNECTED: {reason}[/{COLOR_DOWN}]")

        # CRITICAL: Emergency exit all positions
        if self.trader.positions and not self.emergency_exit_in_progress:
            self.emergency_exit_in_progress = True
            self._log_ai_threadsafe(
                f"[{COLOR_DOWN}]⚠️ EMERGENCY: Exiting all positions due to disconnect![/{COLOR_DOWN}]"
            )

            await self._emergency_exit_all_positions(reason)

    def _emergency_close_position(self, coin: str, reason: str) -> None:
        """Close a single position during emergency exit."""
        price = self.prices.get(coin)
        if not price:
            self._log_ai_threadsafe(
                f"[{COLOR_DOWN}]⚠️ No price for {coin} - cannot close safely![/{COLOR_DOWN}]"
            )
            return

        position = self.trader.positions.get(coin)
        if not position:
            return

        result = self.trader.close_position(coin, price)
        pnl_color = COLOR_UP if result.trade and result.trade.pnl >= 0 else COLOR_DOWN
        self._log_ai_threadsafe(f"[{pnl_color}]🚨 EMERGENCY CLOSE: {result.message}[/{pnl_color}]")

        if result.trade:
            self._record_trade_feedback(result.trade, "emergency_exit")
            self._run_on_main_thread(self.update_history_display, result.trade)

        logger.warning(f"EMERGENCY EXIT: {coin} closed at ${price} due to: {reason}")

    async def _emergency_exit_all_positions(self, reason: str) -> None:
        """
        Emergency exit all open positions.

        CRITICAL: This protects capital when we lose market data connection.
        We cannot make informed trading decisions without live data.
        """
        for coin in list(self.trader.positions.keys()):
            try:
                self._emergency_close_position(coin, reason)
            except Exception as e:
                self._log_ai_threadsafe(
                    f"[{COLOR_DOWN}]❌ FAILED to close {coin}: {e}[/{COLOR_DOWN}]"
                )
                logger.error(f"EMERGENCY EXIT FAILED for {coin}: {e}")

        def update_displays():
            self.update_positions_display()
            self.update_status_bar()

        self._run_on_main_thread(update_displays)
        self.emergency_exit_in_progress = False

    def _handle_ws_state_change(self, state: ConnectionState) -> None:
        """Handle WebSocket state changes for UI updates."""
        state_msg = {
            ConnectionState.DISCONNECTED: f"[{COLOR_DOWN}]⭕ Disconnected[/{COLOR_DOWN}]",
            ConnectionState.CONNECTING: "[yellow]🔄 Connecting...[/yellow]",
            ConnectionState.CONNECTED: f"[{COLOR_UP}]🟢 Connected[/{COLOR_UP}]",
            ConnectionState.RECONNECTING: "[yellow]🟡 Reconnecting...[/yellow]",
            ConnectionState.FATAL_ERROR: f"[{COLOR_DOWN}]🔴 FATAL ERROR[/{COLOR_DOWN}]",
        }

        def update_ui():
            msg = state_msg.get(state, f"Unknown state: {state}")
            self.log_ai(f"WS State: {msg}")
            if state == ConnectionState.FATAL_ERROR:
                self.notify(
                    "CRITICAL: WebSocket connection failed! Positions have been closed.",
                    severity="error",
                )

        self._run_on_main_thread(update_ui)

    async def process_message(self, data: dict) -> None:
        """Process incoming WebSocket message."""
        channel = data.get("channel")

        if channel == "allMids":
            await self.handle_prices(data)
        elif channel == "trades":
            await self.handle_trades(data)
        elif channel == "l2Book":
            await self.handle_orderbook(data)

    async def handle_prices(self, data: dict) -> None:
        """Handle price updates."""
        mids = data.get("data", {}).get("mids", {})

        # Log first price received
        first_update = len(self.prices) == 0

        for coin in self.coins:
            if coin in mids:
                new_price = float(mids[coin])

                # Log first price for this coin
                if coin not in self.prices:
                    self.log_ai(
                        f"[{COLOR_UP}]✓ First price received: {coin} @ ${new_price:,.2f}[/{COLOR_UP}]"
                    )

                self.prices[coin] = new_price

                # Store history for momentum calculation (legacy)
                # Use simulated_time for historical mode, current time for live
                history_time = self.simulated_time if self.simulated_time else datetime.now()
                self.price_history[coin].append({"price": new_price, "time": history_time})

                # Feed candle aggregator for charting
                # Use simulated_time for historical mode, None for live (uses current time)
                self.candle_manager.add_tick(coin, new_price, timestamp=self.simulated_time)

        # Log when all coins have prices
        if first_update and len(self.prices) >= len(self.coins):
            self.log_ai(f"[{COLOR_UP}]✓ All prices received![/{COLOR_UP}]")
            self.log_ai("[dim]AI will analyze and trade based on strategy...[/dim]")

        # Periodic market analysis
        now = datetime.now()
        if (
            now - self.last_market_analysis
        ).total_seconds() >= self.config.market_analysis_interval_seconds:
            self.analyze_market_conditions()
            self.last_market_analysis = now

        # Update instrument rows
        with self.batch_update():
            for coin in self.coins:
                if coin in self.prices:
                    self._update_market_price(coin)
            self.update_status_bar()

    async def handle_trades(self, data: dict) -> None:
        """Handle trade updates (stored for reference but not displayed)."""
        trades_data = data.get("data", [])

        for trade in trades_data:
            coin = trade.get("coin", "?")
            price = float(trade.get("px", 0))
            size = float(trade.get("sz", 0))
            side = trade.get("side", "?")

            self.trades.appendleft(
                {
                    "time": datetime.now(),
                    "coin": coin,
                    "side": side,
                    "size": size,
                    "price": price,
                }
            )

            # Feed trade to Volume Profile builder
            if coin in self.coins and coin in self.vp_builders:
                vp_trade = VPTrade(
                    timestamp=datetime.now(),
                    price=price,
                    size=size,
                    side=side if side in ("B", "A") else "B",
                    coin=coin,
                )
                self.vp_builders[coin].add_trade(vp_trade)

    async def handle_orderbook(self, data: dict) -> None:
        """Handle order book updates."""
        book = data.get("data", {})
        coin = book.get("coin", self.coins[0])
        levels = book.get("levels", [[], []])

        depth = self.config.orderbook_depth
        bids = levels[0][:depth] if len(levels) > 0 else []
        asks = levels[1][:depth] if len(levels) > 1 else []

        self.orderbook[coin] = {
            "bids": bids,
            "asks": asks,
        }

        # Calculate pressure and update instrument row
        self._update_market_pressure(coin)

    def _on_candle_complete(self, coin: str, _candle) -> None:
        """Called when a 1-minute candle completes."""
        # Update the chart for this coin
        self._update_chart(coin)

        # Process signals through adapter and update markets panel
        self._update_signals_display(coin)

    def _update_signals_display(self, coin: str) -> None:
        """Update the markets panel with signal detector outputs."""
        try:
            # Get candles for signal detection
            candles = self.candle_manager.get_candles(coin, include_current=True)
            if not candles or len(candles) < 20:
                return  # Need enough candles for indicators

            # Process through signal adapter (debounced internally)
            self.signal_adapter.process_candles(coin, candles)

            # Get signal data for display
            signals, long_score, short_score, threshold = (
                self.signal_adapter.get_signal_display_data(coin)
            )

            # Update markets panel
            markets_panel = self.query_one(MarketsPanel)
            markets_panel.update_signals(
                coin=coin,
                signals=signals,
                long_score=long_score,
                short_score=short_score,
                threshold=threshold,
            )
        except Exception:
            pass  # Panel may not be ready yet

    def _update_chart(self, coin: str) -> None:
        """Update the candlestick chart for a coin."""
        try:
            charts_panel = self.query_one(ChartsPanel)
            candles = self.candle_manager.get_candles(coin, include_current=True)
            current_price = self.prices.get(coin)
            charts_panel.update_chart(coin, candles, current_price)
        except Exception:
            pass  # Chart panel may not be ready yet

    def _refresh_all_charts(self) -> None:
        """Refresh all candlestick charts with current data."""
        for coin in self.coins:
            self._update_chart(coin)

    def analyze_market_conditions(self) -> None:
        """Trigger AI trading decisions at configured intervals."""
        if not self.prices:
            return

        # Check if it's time for AI to make a decision
        now = datetime.now()
        if (now - self._last_ai_decision).total_seconds() >= self.ai_decision_interval:
            self._last_ai_decision = now
            self.run_ai_trading_decision()

    def _prepare_ai_analysis_data(
        self,
    ) -> tuple[dict, dict, dict, dict, list, MarketPressure | None]:
        """Prepare market data for AI analysis including acceleration."""
        prices_data = {}
        momentum_data = {}
        acceleration_data = {}
        orderbook_data = {}

        for coin in self.coins:
            price = self.prices.get(coin)
            if price:
                # Use momentum with acceleration for AI analysis
                result = self._get_momentum_with_acceleration(coin)
                if result:
                    momentum_data[coin] = result.velocity
                    acceleration_data[coin] = result.acceleration
                else:
                    momentum_data[coin] = 0
                    acceleration_data[coin] = 0

                prices_data[coin] = {
                    "price": price,
                    "change_1m": momentum_data.get(coin, 0),
                }

                book = self.orderbook.get(coin, {})
                bids = book.get("bids", [])
                asks = book.get("asks", [])
                if bids and asks:
                    bid_volume = sum(float(b.get("sz", 0)) for b in bids[:5])
                    ask_volume = sum(float(a.get("sz", 0)) for a in asks[:5])
                    total = bid_volume + ask_volume
                    bid_ratio = (bid_volume / total * 100) if total > 0 else 50
                    orderbook_data[coin] = {"bid_ratio": bid_ratio}

        recent_trades = [{"side": t.get("side", "buy")} for t in list(self.trades)[:20]]

        # Calculate market pressure
        pressure = MarketPressure.calculate(
            orderbook=self.orderbook,
            recent_trades=recent_trades,
            momentum=momentum_data,
        )
        self.market_pressure = pressure

        return (
            prices_data,
            momentum_data,
            acceleration_data,
            orderbook_data,
            recent_trades,
            pressure,
        )

    def _display_ai_analysis_result(
        self, result, _prices_data: dict, pressure: MarketPressure | None
    ) -> None:
        """Display AI analysis result in the AI panel."""
        sentiment_color = {
            "BULLISH": COLOR_UP,
            "BEARISH": COLOR_DOWN,
            "NEUTRAL": "yellow",
        }.get(result.sentiment.value, "white")

        # Momentum per coin
        momentum_parts = []
        for coin in self.coins:
            if coin in result.momentum_by_coin:
                mom = result.momentum_by_coin[coin]
                mom_color = COLOR_UP if mom > 0 else COLOR_DOWN if mom < 0 else "white"
                momentum_parts.append(f"[{mom_color}]{coin} {mom:+.2f}%[/{mom_color}]")
        momentum_str = " | ".join(momentum_parts) if momentum_parts else "N/A"

        # Pressure display
        if pressure:
            pressure_color = (
                COLOR_UP if pressure.score > 55 else COLOR_DOWN if pressure.score < 45 else "yellow"
            )
            pressure_str = (
                f"[{pressure_color}]{pressure.score:.0f} ({pressure.label})[/{pressure_color}]"
            )
        else:
            pressure_str = f"{result.pressure_score} ({result.pressure_label})"

        # Freshness
        freshness_colors = {
            "FRESH": COLOR_UP,
            "DEVELOPING": "cyan",
            "EXTENDED": "yellow",
            "EXHAUSTED": COLOR_DOWN,
        }
        freshness_color = freshness_colors.get(result.freshness.value, "white")

        self.log_ai_block(
            [
                "[cyan]━━━ 🤖 AI MARKET ANALYSIS ━━━[/cyan]",
                f"[bold]Momentum:[/bold] {momentum_str}",
                f"[bold]Pressure:[/bold] {pressure_str} | [bold]Freshness:[/bold] [{freshness_color}]{result.freshness.value}[/{freshness_color}]",
                f"Sentiment: [{sentiment_color}]{result.sentiment.value}[/{sentiment_color}] | Confidence: {result.confidence}/10 | Signal: [{sentiment_color}]{result.signal.value}[/{sentiment_color}]",
                f"[dim]{result.reason}[/dim]",
                f"[dim]⚡ {result.response_time_ms:.0f}ms[/dim]",
            ]
        )

        self.update_ai_title()

        # Update orderbook panel with latest pressure
        if pressure:
            self.update_orderbook_display_with_pressure(pressure)

    @work(exclusive=False)
    async def run_ai_market_analysis(self) -> None:
        """Run AI-powered market analysis (legacy - kept for compatibility)."""
        if not self.prices:
            return

        prices_data, momentum_data, _acceleration_data, orderbook_data, recent_trades, pressure = (
            self._prepare_ai_analysis_data()
        )
        primary_coin = self.coins[0]

        try:
            result = await self.ai_analyzer.analyze_market(
                coin=primary_coin,
                prices=prices_data,
                momentum=momentum_data,
                orderbook=orderbook_data,
                recent_trades=recent_trades,
                pressure_score=int(pressure.score) if pressure else 50,
                pressure_label=pressure.label if pressure else "Neutral",
                momentum_timeframe=self.momentum_timeframe,
            )
            self._display_ai_analysis_result(result, prices_data, pressure)
        except Exception as e:
            self.log_ai(f"[{COLOR_DOWN}]AI analysis error: {e}[/{COLOR_DOWN}]")

    @work(exclusive=False)
    async def run_ai_trading_decision(self) -> None:
        """
        AI makes a complete trading decision - full control mode.

        Uses the general AI trading prompt with the selected strategy.
        Signal detection is handled by the SignalBrainAdapter for UI display.
        """
        if not self.prices:
            return

        # Use the general AI prompt for all strategies
        _prices_data, momentum_data, acceleration_data, orderbook_data, recent_trades, pressure = (
            self._prepare_ai_analysis_data()
        )

        prices_flat = {coin: self.prices[coin] for coin in self.coins if coin in self.prices}

        try:
            decision = await self.ai_analyzer.make_decision(
                strategy=self.ai_strategy,
                prices=prices_flat,
                momentum=momentum_data,
                acceleration=acceleration_data,
                orderbook=orderbook_data,
                pressure_score=int(pressure.score) if pressure else 50,
                pressure_label=pressure.label if pressure else "Neutral",
                recent_trades=recent_trades,
                positions=self.trader.positions,
                balance=self.trader.balance,
                equity=self.trader.get_equity(self.prices),
                momentum_timeframe=self.momentum_timeframe,
            )

            await self._execute_ai_decision(decision, prices_flat, pressure)

        except Exception as e:
            self.log_ai(f"[{COLOR_DOWN}]AI decision error: {e}[/{COLOR_DOWN}]")
            logger.error(f"AI trading decision failed: {e}")

    async def _execute_ai_decision(self, decision: AIDecision, prices: dict, pressure) -> None:
        """Execute an AI trading decision."""
        # Build momentum display
        momentum_parts = []
        for coin in self.coins:
            mom = self._calculate_momentum(coin) or 0
            mom_color = COLOR_UP if mom > 0 else COLOR_DOWN if mom < 0 else "white"
            momentum_parts.append(f"[{mom_color}]{coin} {mom:+.2f}%[/{mom_color}]")
        momentum_str = " | ".join(momentum_parts)

        # Pressure display
        if pressure:
            pressure_color = (
                COLOR_UP if pressure.score > 55 else COLOR_DOWN if pressure.score < 45 else "yellow"
            )
            pressure_str = (
                f"[{pressure_color}]{pressure.score:.0f} ({pressure.label})[/{pressure_color}]"
            )
        else:
            pressure_str = "N/A"

        # Strategy name
        strategy_name = self.ai_strategy.value.replace("_", " ").title()

        if decision.is_none:
            # AI decided to wait
            self.log_ai_block(
                [
                    f"[cyan]━━━ 🤖 AI DECISION ({strategy_name}) ━━━[/cyan]",
                    f"[bold]Momentum:[/bold] {momentum_str}",
                    f"[bold]Pressure:[/bold] {pressure_str}",
                    f"Action: [yellow]WAIT[/yellow] | Confidence: {decision.confidence}/10",
                    f"[dim]{decision.reason}[/dim]",
                    f"[dim]⚡ {decision.response_time_ms:.0f}ms[/dim]",
                ]
            )

        elif decision.is_entry:
            # AI wants to enter a trade
            coin = decision.coin
            direction = decision.action  # LONG or SHORT

            if coin not in prices:
                self.log_ai(
                    f"[{COLOR_DOWN}]AI requested {direction} {coin} but no price available[/{COLOR_DOWN}]"
                )
                return

            if coin in self.trader.positions:
                self.log_ai(
                    f"[yellow]AI requested {direction} {coin} but already in position[/yellow]"
                )
                return

            price = prices[coin]
            position_value = self.trader.balance * decision.size_pct
            size = position_value / price

            # Display AI decision
            action_color = COLOR_UP if direction == "LONG" else COLOR_DOWN
            self.log_ai_block(
                [
                    f"[cyan]━━━ 🤖 AI DECISION ({strategy_name}) ━━━[/cyan]",
                    f"[bold]Momentum:[/bold] {momentum_str}",
                    f"[bold]Pressure:[/bold] {pressure_str}",
                    f"Action: [{action_color}]{direction} {coin}[/{action_color}] | Size: {decision.size_pct * 100:.0f}% | Confidence: {decision.confidence}/10",
                    f"[dim]{decision.reason}[/dim]",
                    f"[dim]⚡ {decision.response_time_ms:.0f}ms[/dim]",
                ]
            )

            # Execute the trade
            self.log_ai(
                f"[{action_color}]→ Executing {direction} {size:.6f} {coin} @ ${price:,.2f}[/{action_color}]"
            )

            if direction == "LONG":
                result = self.trader.open_long(coin, size, price)
            else:
                result = self.trader.open_short(coin, size, price)

            if result.success:
                self.log_ai(f"[{COLOR_UP}]✓ {result.message}[/{COLOR_UP}]")
                momentum = self._calculate_momentum(coin)
                if momentum is not None:
                    self.entry_momentum[coin] = momentum
            else:
                self.log_ai(f"[{COLOR_DOWN}]✗ {result.message}[/{COLOR_DOWN}]")

            with self.batch_update():
                self.update_positions_display()
                self.update_status_bar()

            # AI will manage exit in next decision cycle (no timer-based exit)

        elif decision.is_exit:
            # AI wants to exit a position
            exit_coin = decision.exit_coin

            if not exit_coin or exit_coin not in self.trader.positions:
                self.log_ai(f"[yellow]AI requested EXIT {exit_coin} but no position found[/yellow]")
                return

            price = prices.get(exit_coin)
            if not price:
                self.log_ai(f"[{COLOR_DOWN}]No price for {exit_coin} to exit[/{COLOR_DOWN}]")
                return

            position = self.trader.positions[exit_coin]
            pnl_pct = position.unrealized_pnl_percent(price)
            pnl_color = COLOR_UP if pnl_pct >= 0 else COLOR_DOWN

            self.log_ai_block(
                [
                    f"[cyan]━━━ 🤖 AI DECISION ({strategy_name}) ━━━[/cyan]",
                    f"[bold]Momentum:[/bold] {momentum_str}",
                    f"[bold]Pressure:[/bold] {pressure_str}",
                    f"Action: [yellow]EXIT {exit_coin}[/yellow] | P&L: [{pnl_color}]{pnl_pct:+.2f}%[/{pnl_color}] | Confidence: {decision.confidence}/10",
                    f"[dim]{decision.reason}[/dim]",
                    f"[dim]⚡ {decision.response_time_ms:.0f}ms[/dim]",
                ]
            )

            result = self.trader.close_position(exit_coin, price)
            if result.success:
                self.log_ai(f"[{pnl_color}]✓ {result.message}[/{pnl_color}]")
                self._record_trade_feedback(result.trade, "ai_exit")
                with self.batch_update():
                    self.update_positions_display()
                    self.update_history_display(result.trade)
                    self.update_status_bar()

        # Update AI signals in instrument rows
        self._update_market_ai_from_decision(decision, prices)
        self.update_ai_title()

        # Mark the chart with AI analysis indicator
        try:
            charts_panel = self.query_one(ChartsPanel)
            # Mark all coins that have prices (the AI analyzed all of them)
            for coin in self.coins:
                if coin in prices:
                    # Get current candles to ensure chart has data
                    candles = self.candle_manager.get_candles(coin, include_current=True)
                    charts_panel.mark_ai_analysis(coin, candles)
        except Exception:
            pass  # Chart panel might not be ready yet

    def _get_market_condition(self) -> str:
        """Get current market condition for feedback recording."""
        analysis = self.market_analyzer.analyze(
            coins=self.coins,
            prices=self.prices,
            price_history=self.price_history,
            momentum_timeframe=self.momentum_timeframe,
        )
        if analysis:
            return analysis.condition_label.lower().replace(" ", "_")
        return "unknown"

    def _record_trade_feedback(
        self,
        trade,
        outcome: Literal["take_profit", "stop_loss", "emergency_exit", "manual", "ai_exit"],
    ) -> None:
        """Record a completed trade to the feedback collector."""
        if not trade:
            return

        coin = trade.coin
        entry_momentum = self.entry_momentum.pop(coin, 0.0)

        # Get BTC and ETH momentum for correlation analysis
        btc_momentum = self._calculate_momentum("BTC") if "BTC" in self.coins else None
        eth_momentum = self._calculate_momentum("ETH") if "ETH" in self.coins else None

        try:
            self.feedback_collector.record_trade(
                coin=coin,
                side=trade.side,
                entry_price=trade.entry_price,
                exit_price=trade.exit_price,
                entry_momentum_pct=entry_momentum,
                size=trade.size,
                outcome=outcome,
                pnl_usd=trade.pnl,
                fees_paid=trade.fees_paid,
                entry_time=trade.entry_time,
                exit_time=trade.exit_time,
                # Current parameters (from config)
                track_threshold_pct=self.config.track_threshold_pct,
                trade_threshold_pct=self.config.trade_threshold_pct,
                momentum_timeframe_seconds=self.momentum_timeframe,
                take_profit_pct=self.config.take_profit_pct,
                stop_loss_pct=self.config.stop_loss_pct,
                position_size_pct=self.config.position_size_pct,
                cooldown_seconds=self.config.cooldown_seconds,
                max_concurrent_positions=self.config.max_concurrent_positions,
                # Market context
                market_condition=self._get_market_condition(),
                btc_momentum=btc_momentum,
                eth_momentum=eth_momentum,
            )
            recorded_count = len(self.feedback_collector.trades)
            self.log_ai(f"[dim]📊 Trade recorded for tuning (#{recorded_count})[/dim]")

            # Save session state after each trade
            self._save_session_state()
        except Exception as e:
            logger.error(f"Failed to record trade feedback: {e}")

    def check_exit_conditions(self, coin: str) -> None:
        """Check if we should exit a position (triggers async AI check if enabled)."""
        if coin not in self.trader.positions:
            return

        price = self.prices.get(coin)
        if not price:
            self.set_timer(1, lambda: self.check_exit_conditions(coin))
            return

        position = self.trader.positions[coin]
        pnl_pct = position.unrealized_pnl_percent(price)

        # Hard stop loss always triggers (safety)
        if pnl_pct <= self.config.stop_loss_pct:
            self.log_ai(
                f"[{COLOR_DOWN}]🛑 Stop loss triggered for {coin} ({pnl_pct:.2f}%)[/{COLOR_DOWN}]"
            )
            result = self.trader.close_position(coin, price)
            self.log_ai(f"[{COLOR_DOWN}]✗ {result.message}[/{COLOR_DOWN}]")
            self._record_trade_feedback(result.trade, "stop_loss")
            with self.batch_update():
                self.update_positions_display()
                self.update_history_display(result.trade)
                self.update_status_bar()
            return

        # Hard take profit triggers (lock in profits)
        if pnl_pct >= self.config.take_profit_pct:
            self.log_ai(
                f"[{COLOR_UP}]🎯 Take profit triggered for {coin} (+{pnl_pct:.2f}%)[/{COLOR_UP}]"
            )
            result = self.trader.close_position(coin, price)
            self.log_ai(f"[{COLOR_UP}]✓ {result.message}[/{COLOR_UP}]")
            self._record_trade_feedback(result.trade, "take_profit")
            with self.batch_update():
                self.update_positions_display()
                self.update_history_display(result.trade)
                self.update_status_bar()
            return

        # AI can suggest early exit before TP/SL
        if self.ai_analyzer.enabled:
            self.run_ai_exit_check(coin)

        # Keep checking
        self.set_timer(2, lambda: self.check_exit_conditions(coin))

    @work(exclusive=False)
    async def run_ai_exit_check(self, coin: str) -> None:
        """Run AI exit analysis for a position."""
        if coin not in self.trader.positions:
            return

        position = self.trader.positions[coin]
        price = self.prices.get(coin)
        if not price:
            return

        pnl_pct = position.unrealized_pnl_percent(price)
        momentum = self._calculate_momentum(coin) or 0.0
        hold_time = int((datetime.now() - position.entry_time).total_seconds())

        # Get market pressure
        pressure = self.market_pressure
        pressure_score = int(pressure.score) if pressure else 50
        pressure_label = pressure.label if pressure else "Neutral"

        # Determine direction string
        direction = "LONG" if position.side.value == "long" else "SHORT"

        should_exit, confidence, reason = await self.ai_analyzer.should_exit(
            coin=coin,
            direction=direction,
            entry_price=position.entry_price,
            current_price=price,
            pnl_percent=pnl_pct,
            hold_time=hold_time,
            momentum=momentum,
            momentum_timeframe=self.momentum_timeframe,
            pressure_score=pressure_score,
            pressure_label=pressure_label,
            take_profit_pct=self.config.take_profit_pct,
            stop_loss_pct=self.config.stop_loss_pct,
        )

        if should_exit and confidence >= 7:
            self.log_ai_block(
                [
                    f"[yellow]🤖 AI EXIT: {direction} {coin}[/yellow]",
                    f"P&L: {pnl_pct:+.2f}% | Confidence: {confidence}/10",
                    f"[dim]{reason}[/dim]",
                ]
            )

            result = self.trader.close_position(coin, price)
            if result.success:
                self.log_ai(f"[yellow]✓ {result.message}[/yellow]")
                self._record_trade_feedback(result.trade, "ai_exit")
                with self.batch_update():
                    self.update_positions_display()
                    self.update_history_display(result.trade)
                    self.update_status_bar()

    # ============================================================
    # Display Updates
    # ============================================================

    def _calculate_momentum(self, coin: str) -> float | None:
        """Calculate momentum for a coin over the configured timeframe."""
        history = self.price_history.get(coin)
        current_price = self.prices.get(coin)
        if not history or not current_price:
            return None
        return calculate_momentum(current_price, history, self.momentum_timeframe)

    def _get_momentum_with_acceleration(self, coin: str) -> MomentumResult | None:
        """Get full momentum result with acceleration for AI analysis."""
        history = self.price_history.get(coin)
        current_price = self.prices.get(coin)
        if not history or not current_price:
            return None

        prev_velocity = self._previous_velocity.get(coin)
        result = calculate_momentum_with_acceleration(
            current_price, history, self.momentum_timeframe, prev_velocity
        )
        if result:
            self._previous_velocity[coin] = result.velocity
        return result

    def _update_market_price(self, coin: str) -> None:
        """Update price and momentum for a market."""
        try:
            panel = self.query_one(MarketsPanel)
            price = self.prices.get(coin, 0)
            momentum = self._calculate_momentum(coin)
            panel.update_price(coin, price, momentum)
        except Exception as e:
            logger.debug(f"Failed to update market price for {coin}: {e}")

    def _update_market_pressure(self, coin: str) -> None:
        """Update pressure bar for a market."""
        try:
            panel = self.query_one(MarketsPanel)
            book = self.orderbook.get(coin, {})
            bids = book.get("bids", [])
            asks = book.get("asks", [])

            # Calculate pressure from orderbook
            if bids and asks:
                bid_volume = sum(float(b.get("sz", 0)) for b in bids[:5])
                ask_volume = sum(float(a.get("sz", 0)) for a in asks[:5])
                total = bid_volume + ask_volume
                if total > 0:
                    buy_pressure = (bid_volume / total) * 100
                    sell_pressure = (ask_volume / total) * 100
                else:
                    buy_pressure = 50
                    sell_pressure = 50
            else:
                buy_pressure = 50
                sell_pressure = 50

            panel.update_pressure(coin, buy_pressure, sell_pressure)
        except Exception as e:
            logger.debug(f"Failed to update market pressure for {coin}: {e}")

    def _update_market_ai(self, coin: str, signal: str, confidence: int) -> None:
        """Update AI signal for a market."""
        try:
            panel = self.query_one(MarketsPanel)
            panel.update_ai(coin, signal, confidence)
        except Exception as e:
            logger.debug(f"Failed to update market AI for {coin}: {e}")

    def _update_market_position(self, coin: str) -> None:
        """Update position info for a market."""
        try:
            panel = self.query_one(MarketsPanel)
            position = self.trader.positions.get(coin)
            price = self.prices.get(coin)
            panel.update_position(coin, position, price)
        except Exception as e:
            logger.debug(f"Failed to update market position for {coin}: {e}")

    def _update_all_market_positions(self) -> None:
        """Update position info for all markets."""
        for coin in self.coins:
            self._update_market_position(coin)

    def _update_market_ai_from_decision(
        self,
        decision: AIDecision,
        _prices: dict[str, float],
    ) -> None:
        """Update AI signals in markets based on AI decision."""
        for coin in self.coins:
            momentum = self._calculate_momentum(coin) or 0
            abs_momentum = abs(momentum)

            # Determine signal and confidence based on momentum strength
            if abs_momentum > 0.2:
                # Very strong momentum
                confidence = 10
            elif abs_momentum > 0.1:
                # Strong momentum
                confidence = 7
            elif abs_momentum > 0.05:
                # Moderate momentum
                confidence = 5
            elif abs_momentum > 0.02:
                # Weak momentum
                confidence = 3
            else:
                # No clear signal
                confidence = 0

            # Determine signal direction
            if momentum > 0.02:
                signal = "BULLISH"
            elif momentum < -0.02:
                signal = "BEARISH"
            else:
                signal = "NEUTRAL"

            # If this coin is the target of the AI decision, boost confidence
            if decision.coin == coin and decision.confidence > confidence:
                confidence = decision.confidence

            self._update_market_ai(coin, signal, confidence)

    def update_positions_display(self) -> None:
        """Update position info for all markets."""
        self._update_all_market_positions()

    def update_history_display(self, _trade=None) -> None:
        """Update trade history panel."""
        panel = self.query_one(HistoryPanel)
        panel.update_display(self.trader.trade_history)

    def update_status_bar(self) -> None:
        """Update the status bar."""
        status_bar = self.query_one(StatusBar)

        # Calculate last message age
        last_msg_age = None
        if self.ws_connected and self.ws_manager.metrics.last_message_time:
            last_msg_age = (
                datetime.now() - self.ws_manager.metrics.last_message_time
            ).total_seconds()

        status_bar.update_status(
            ws_connected=self.ws_connected,
            last_message_age=last_msg_age,
            reconnect_count=self.ws_manager.metrics.reconnect_count,
            balance=self.trader.balance,
            equity=self.trader.get_equity(self.prices),
            starting_balance=self.starting_balance,
            trade_count=len(self.trader.trade_history),
        )

    def update_goal_panel(self) -> None:
        """Update the goal progress panel."""
        try:
            panel = self.query_one(GoalPanel)

            # Calculate days elapsed since goal start
            days_elapsed = (datetime.now() - self.goal_start_date).days

            # Build GoalData from current state
            goal_data = GoalData(
                initial_balance=self.starting_balance,
                current_balance=self.trader.balance,
                target_balance=self.account_goal,
                goal_timeframe_days=self.goal_timeframe_days,
                days_elapsed=days_elapsed,
                ai_multiplier=self.last_ai_multiplier,
            )

            # Calculate computed properties if goal is set
            if goal_data.has_goal and self.account_goal is not None:
                # Goal progress percentage
                total_needed = self.account_goal - self.starting_balance
                if total_needed > 0:
                    achieved = self.trader.balance - self.starting_balance
                    goal_data.goal_progress_pct = (achieved / total_needed) * 100
                else:
                    goal_data.goal_progress_pct = 100.0

                # Time progress percentage
                if self.goal_timeframe_days and self.goal_timeframe_days > 0:
                    goal_data.time_progress_pct = (days_elapsed / self.goal_timeframe_days) * 100

                    # Pace status
                    if goal_data.goal_progress_pct >= 100:
                        goal_data.pace_status = "goal_reached"
                    elif goal_data.time_progress_pct <= 0:
                        goal_data.pace_status = "just_started"
                    else:
                        ratio = goal_data.goal_progress_pct / goal_data.time_progress_pct
                        if ratio >= 1.2:
                            goal_data.pace_status = "ahead"
                        elif ratio >= 0.8:
                            goal_data.pace_status = "on_pace"
                        else:
                            goal_data.pace_status = "behind"

                    # Required daily return
                    days_left = max(0, self.goal_timeframe_days - days_elapsed)
                    if days_left > 0 and self.trader.balance > 0:
                        remaining = self.account_goal - self.trader.balance
                        if remaining > 0:
                            goal_data.required_daily_return_pct = (
                                remaining / self.trader.balance / days_left
                            ) * 100

            panel.update(goal_data)
        except Exception as e:
            logger.debug(f"Goal panel not ready: {e}")

    def log_ai(self, message: str) -> None:
        """Log message to AI reasoning panel."""
        try:
            panel = self.query_one(AIPanel)
            panel.log(message)
        except Exception as e:
            logger.debug(f"AI panel not ready: {e}")

    def log_ai_block(self, lines: list[str]) -> None:
        """Log a multi-line block with single timestamp to AI panel."""
        try:
            panel = self.query_one(AIPanel)
            panel.log_block(lines)
        except Exception as e:
            logger.debug(f"AI panel not ready: {e}")

    def _run_on_main_thread(self, func, *args) -> None:
        """Execute a function on the main thread (thread-safe helper)."""
        import threading

        if self._thread_id == threading.get_ident():
            func(*args)
        else:
            self.call_from_thread(func, *args)

    def _log_ai_threadsafe(self, message: str) -> None:
        """Thread-safe version of log_ai that works from any context."""
        self._run_on_main_thread(self.log_ai, message)

    def update_ai_title(self) -> None:
        """Update AI panel title with mode and connection info."""
        try:
            panel = self.query_one(AIPanel)
            ws_metrics = self.ws_manager.metrics

            # Get AI metrics from analyzer if AI mode is enabled
            if self.ai_analyzer.enabled:
                ai_metrics = self.ai_analyzer.get_metrics()
                self.tokens_used = ai_metrics.total_tokens
                self.ai_calls = ai_metrics.total_calls

            panel.update_title(
                analysis_mode=self.analysis_mode,
                ai_model=self.ai_model,
                tokens_used=self.tokens_used,
                ai_calls=self.ai_calls,
                disconnects=ws_metrics.total_disconnects,
                reconnects=ws_metrics.reconnect_count,
            )
        except Exception as e:
            logger.debug(f"AI panel not ready: {e}")

    # ============================================================
    # Actions
    # ============================================================

    def action_reset(self) -> None:
        """Reset the simulator."""
        self.trader.reset()

        # Clear saved session state
        self.state_manager.clear_state()

        self.log_ai("[yellow]🔄 Simulator reset[/yellow]")
        self.log_ai("[dim]💾 Saved session state cleared[/dim]")
        with self.batch_update():
            self.update_positions_display()
            self.update_history_display()
            self.update_status_bar()
            self.update_goal_panel()

    def action_toggle_pause(self) -> None:
        """Pause/unpause the simulator."""
        self.paused = not self.paused
        status = "PAUSED" if self.paused else "RUNNING"
        self.log_ai(f"[yellow]⏸️ Simulator {status}[/yellow]")

    def action_toggle_charts(self) -> None:
        """Toggle charts panel visibility."""
        self.charts_visible = not self.charts_visible
        try:
            charts_panel = self.query_one(ChartsPanel)
            charts_panel.display = self.charts_visible
            status = "shown" if self.charts_visible else "hidden"
            self.log_ai(f"[dim]📊 Charts panel {status}[/dim]")
        except Exception:
            pass

    def action_restart(self) -> None:
        """Restart the app with fresh code."""
        self.log_ai("[yellow]🔄 Restarting with fresh code...[/yellow]")
        self.exit()
        # Replace current process with new one (reloads all code)
        os.execv(sys.executable, [sys.executable, *sys.argv])

    def update_strategy_bar(self) -> None:
        """Update the strategy display in status bar."""
        try:
            status_bar = self.query_one(StatusBar)
            strategy_name = self.ai_strategy.value.replace("_", " ").title()
            status_bar.update_strategy(
                strategy_name=strategy_name,
                ai_enabled=self.ai_analyzer.enabled,
                decision_interval=self.ai_decision_interval,
            )
        except Exception as e:
            logger.debug(f"Strategy bar not ready: {e}")

    def action_toggle_ai(self) -> None:
        """Toggle between rule-based and AI analysis mode."""
        if self.analysis_mode == "RULE-BASED":
            # Enable AI mode with local Ollama
            self.ai_analyzer.enabled = True
            self.analysis_mode = "AI (Local)"
            self.ai_model = "mistral:7b"
            strategy_name = self.ai_strategy.value.replace("_", " ").title()
            self.log_ai(f"[{COLOR_UP}]🤖 AI MODE ENABLED[/{COLOR_UP}]")
            self.log_ai(f"[dim]  Model: {self.ai_model} | Strategy: {strategy_name}[/dim]")
            self.log_ai(
                f"[dim]  AI has FULL CONTROL - decisions every {self.ai_decision_interval}s[/dim]"
            )
            self.notify(f"AI Mode: {strategy_name}", severity="information")
            # Check AI availability
            self.check_ai_availability()
        else:
            self.ai_analyzer.enabled = False
            self.analysis_mode = "RULE-BASED"
            self.ai_model = "None (Momentum Rules)"
            self.log_ai(f"[{COLOR_UP}]✓ Switched to RULE-BASED analysis[/{COLOR_UP}]")
        self.update_ai_title()
        self.update_strategy_bar()

    def action_cycle_strategy(self) -> None:
        """Cycle through AI trading strategies."""
        if not self.ai_analyzer.enabled:
            self.notify("Enable AI mode first (press A)", severity="warning")
            return

        # Find current index and cycle to next
        try:
            current_idx = self.AI_STRATEGIES.index(self.ai_strategy)
            next_idx = (current_idx + 1) % len(self.AI_STRATEGIES)
        except ValueError:
            next_idx = 0

        self.ai_strategy = self.AI_STRATEGIES[next_idx]
        strategy_name = self.ai_strategy.value.replace("_", " ").title()

        # Update signal adapter with new strategy
        self._signal_strategy = self._get_strategy_for_trading_strategy(self.ai_strategy)
        self.signal_adapter.update_strategy(self._signal_strategy)

        # Get strategy description
        descriptions = {
            TradingStrategy.MOMENTUM_BASED: "Primary: MOMENTUM + VP support",
            TradingStrategy.MOMENTUM_MACD: "Primary: MOMENTUM + MACD confirmation",
            TradingStrategy.RSI_BASED: "Primary: RSI + VP support",
            TradingStrategy.MULTI_SIGNAL: "Balanced: Multiple signals required",
        }
        desc = descriptions.get(self.ai_strategy, "")

        self.log_ai_block(
            [
                "[cyan]━━━ STRATEGY CHANGED ━━━[/cyan]",
                f"New Strategy: [bold]{strategy_name}[/bold]",
                f"[dim]{desc}[/dim]",
            ]
        )
        self.notify(f"Strategy: {strategy_name}", severity="information")
        self.update_strategy_bar()

    @work(exclusive=False)
    async def check_ai_availability(self) -> None:
        """Check if local AI server is available."""
        is_available = await self.ai_analyzer.is_available()
        if is_available:
            self.log_ai(f"[{COLOR_UP}]✓ Ollama server connected[/{COLOR_UP}]")
        else:
            self.log_ai(f"[{COLOR_DOWN}]⚠️ Ollama server not available![/{COLOR_DOWN}]")
            self.log_ai("[dim]  Run 'ollama serve' to start the server[/dim]")
            self.notify("Ollama server not running! Start with 'ollama serve'", severity="warning")

    def _generate_tuning_report(self, last_report, new_trades: list, is_incremental: bool) -> None:
        """Generate and display the tuning report."""
        try:
            json_path, md_path = self.tuning_exporter.export_both(since=last_report)
            self.state_manager.mark_report_generated()

            self.log_ai(f"[{COLOR_UP}]✓ Report generated![/{COLOR_UP}]")
            self.log_ai(f"[dim]  📄 {md_path}[/dim]")
            self.log_ai(f"[dim]  📊 {json_path}[/dim]")

            analysis = self.performance_analyzer.analyze(
                trades=new_trades if is_incremental else None
            )
            suggestions = analysis.get("suggestions", [])
            if suggestions:
                self.log_ai(f"[yellow]💡 {len(suggestions)} suggestion(s):[/yellow]")
                for s in suggestions[:3]:
                    if s.get("parameter"):
                        self.log_ai(
                            f"[dim]  • {s.get('parameter')}: {s.get('direction')} ({s.get('confidence')})[/dim]"
                        )
                    elif s.get("message"):
                        self.log_ai(f"[dim]  • {s.get('message')}[/dim]")

            self.notify(
                f"Report saved! {len(new_trades)} new trades analyzed.", severity="information"
            )
        except Exception as e:
            self.log_ai(f"[{COLOR_DOWN}]✗ Failed to generate report: {e}[/{COLOR_DOWN}]")
            logger.error(f"Tuning report generation failed: {e}")

    def action_tuning_report(self) -> None:
        """Generate and display incremental tuning report (only new trades)."""
        last_report = self.state_manager.get_last_report_timestamp()
        new_trades = self.feedback_collector.get_trades_since(last_report)
        total_trade_count = len(self.feedback_collector.trades)

        if total_trade_count == 0:
            self.log_ai("[yellow]📊 No trades recorded yet for tuning analysis[/yellow]")
            self.log_ai("[dim]  Trades are recorded when positions close (TP/SL/emergency)[/dim]")
            self.notify("No trades recorded yet. Trade first!", severity="warning")
            return

        if not new_trades and last_report:
            self.log_ai("[yellow]📊 No new trades since last report[/yellow]")
            self.log_ai(f"[dim]  Last report: {last_report.strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
            self.log_ai(f"[dim]  Total trades: {total_trade_count}[/dim]")
            self.notify("No new trades since last report.", severity="warning")
            return

        is_incremental = last_report is not None
        report_type = "INCREMENTAL" if is_incremental else "FULL"
        self.log_ai(f"[cyan]━━━ {report_type} TUNING REPORT ━━━[/cyan]")

        if is_incremental and last_report:
            self.log_ai(
                f"[dim]  📈 {len(new_trades)} new trades (since {last_report.strftime('%H:%M:%S')})[/dim]"
            )
        else:
            self.log_ai(f"[dim]  📊 Analyzing all {total_trade_count} trades[/dim]")

        self._generate_tuning_report(last_report, new_trades, is_incremental)

    async def action_quit(self) -> None:
        """Quit the application with proper cleanup."""
        self.log_ai("[yellow]🛑 Shutting down...[/yellow]")

        # Close any open positions before exit
        if self.trader.positions:
            self.log_ai(
                f"[yellow]⚠️ Closing {len(self.trader.positions)} open positions before exit...[/yellow]"
            )
            for coin in list(self.trader.positions.keys()):
                price = self.prices.get(coin)
                if price:
                    result = self.trader.close_position(coin, price)
                    self.log_ai(f"Closed {coin}: {result.message}")
                    if result.trade:
                        self._record_trade_feedback(result.trade, "manual")

        # Save final session state and logs
        self._save_session_state()
        self._save_session_logs()
        self.log_ai(
            f"[dim]💾 Session '{self.session_name}' saved. Use --resume --session {self.session_name} to continue.[/dim]"
        )

        # Stop WebSocket manager
        await self.ws_manager.stop()

        # Close AI client
        await self.ai_analyzer.close()

        logger.info("Dashboard shutdown complete")
        self.exit()


def main():
    """Entry point for the dashboard application."""
    from bot.ui.cli import run_cli

    run_cli()


if __name__ == "__main__":
    main()
