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

import asyncio
import json
import logging
import os
import sys
from collections import deque
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Footer, Static
from textual.reactive import reactive
from textual import work
from textual.binding import Binding

from bot.core.config import TradingConfig, DEFAULT_CONFIG
from bot.core.models import OpportunityCondition, PendingOpportunity
from bot.core.analysis import (
    calculate_momentum,
    MarketAnalyzer,
    CoinStatus,
    OpportunityAnalyzer,
    OpportunityAction,
)
from bot.hyperliquid.websocket_manager import WebSocketManager, WebSocketConfig, ConnectionState
from bot.simulation.models import HYPERLIQUID_FEES, Side
from bot.simulation.paper_trader import PaperTrader
from bot.simulation.state_manager import SessionStateManager
from bot.tuning import FeedbackCollector, PerformanceAnalyzer, TuningReportExporter
from bot.ai import MarketAnalyzer as AIMarketAnalyzer, OllamaClient
from bot.ui.components import (
    PricesPanel,
    OrderBookPanel,
    TradesPanel,
    AIPanel,
    OpportunitiesPanel,
    PositionsPanel,
    HistoryPanel,
    StatusBar,
)

# Configure logging - file only to avoid interfering with TUI
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
    ]
)
logger = logging.getLogger("dashboard")


# ============================================================
# Theme Colors (Rich markup hex codes)
# ============================================================
COLOR_UP = "#44ffaa"      # Bright green for positive/buy/profit
COLOR_DOWN = "#ff7777"    # Bright red for negative/sell/loss


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
        Binding("ctrl+s", "save_session", "Save", priority=True),
        Binding("1", "decrease_track", "Track -"),
        Binding("2", "increase_track", "Track +"),
        Binding("3", "decrease_trade", "Trade -"),
        Binding("4", "increase_trade", "Trade +"),
        Binding("5", "cycle_momentum_down", "Mom -"),
        Binding("6", "cycle_momentum_up", "Mom +"),
        Binding("a", "toggle_ai", "AI Mode"),
        Binding("t", "tuning_report", "Tuning"),
    ]
    
    # Available momentum timeframes in seconds
    MOMENTUM_TIMEFRAMES = [5, 10, 30, 60]
    
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
    ):
        super().__init__()
        self.config = config or DEFAULT_CONFIG
        self.starting_balance = starting_balance
        self.coins = coins or ["BTC", "ETH", "SOL"]
        self.resume_mode = resume
        self.session_name = session_name or "default"
        
        # Data stores
        self.prices: dict[str, float] = {}
        self.orderbook: dict[str, dict] = {}  # {coin: {bids: [], asks: []}}
        self.trades: deque = deque(maxlen=self.config.max_trades_history)
        self.pending_opportunities: dict[str, PendingOpportunity] = {}
        
        # Price history for momentum calculation
        self.price_history: dict[str, deque] = {
            coin: deque(maxlen=self.config.price_history_maxlen) for coin in self.coins
        }
        
        # Market analysis state
        self.last_market_analysis = datetime.now()
        
        # Adjustable thresholds (initialized from config, can be changed at runtime)
        self.track_threshold = self.config.track_threshold_pct
        self.trade_threshold = self.config.trade_threshold_pct
        
        # Momentum timeframe (default 5 seconds)
        self.momentum_timeframe = 5  # seconds
        
        # Analysis mode - AI uses local Ollama with Mistral
        self.analysis_mode = "RULE-BASED"  # "RULE-BASED" or "AI (Local)"
        self.ai_model = "None (Momentum Rules)"  # Will be "mistral:7b" when AI enabled
        self.tokens_used = 0
        self.ai_calls = 0
        
        # Local AI analyzer (Ollama + Mistral)
        self.ai_client = OllamaClient(model="mistral")
        self.ai_analyzer = AIMarketAnalyzer(client=self.ai_client, enabled=False)
        
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
        
        # Analysis modules (separate analysis logic from UI)
        self.market_analyzer = MarketAnalyzer(self.config)
        self.opportunity_analyzer = OpportunityAnalyzer(self.config)
        
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
        
        # Auto-save interval (save state every 30 seconds)
        self._last_state_save = datetime.now()
        
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
        self._last_state_save = datetime.now()
        
    def compose(self) -> ComposeResult:
        """Create the dashboard layout using extracted components."""
        # Custom title bar with session name
        yield Static(f"PAPER TRADING SIMULATOR  ⟫  {self.session_name}", id="title-bar", classes="title-bar")
        
        # Status bar
        yield StatusBar(id="status-row", classes="status-row")
        
        # Main content area: AI sidebar (left) + data panels (right)
        with Horizontal(classes="main-content"):
            # Left sidebar: AI Reasoning
            yield AIPanel(id="ai-panel", classes="panel")
            
            # Right side: All data panels stacked vertically
            with Vertical(classes="data-panels"):
                # Top row: Prices, Order Book, Live Trades
                with Horizontal(classes="top-row"):
                    yield PricesPanel(self.coins, self.config, id="prices-panel", classes="panel")
                    yield OrderBookPanel(self.coins, id="orderbook-panel", classes="panel")
                    yield TradesPanel(self.coins, id="trades-panel", classes="panel")
                
                # Opportunities row
                yield OpportunitiesPanel(id="opportunities-panel", classes="panel opportunities-row")
                
                # Bottom row: Positions and History
                with Horizontal(classes="bottom-row"):
                    yield PositionsPanel(id="positions-panel", classes="panel")
                    yield HistoryPanel(id="history-panel", classes="panel")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Start data streams when app mounts."""
        self.update_ai_title()
        self.update_threshold_bar()  # Initialize threshold display
        
        # Log session status
        if self._restored_from_state:
            pnl = self.trader.balance - self.starting_balance
            pnl_color = COLOR_UP if pnl >= 0 else COLOR_DOWN
            self.log_ai(f"[{COLOR_UP}]✓ Session '{self.session_name}' restored[/{COLOR_UP}]")
            self.log_ai(f"[dim]  Balance: ${self.trader.balance:,.2f} | P&L: [{pnl_color}]${pnl:+,.2f}[/{pnl_color}][/dim]")
            if self.trader.positions:
                self.log_ai(f"[dim]  Open positions: {', '.join(self.trader.positions.keys())}[/dim]")
        else:
            self.log_ai(f"Dashboard initialized. Session: '{self.session_name}'")
            
        self.log_ai(f"[dim]Analysis Mode: {self.analysis_mode} | Model: {self.ai_model}[/dim]")
        self.log_ai(f"[dim]WebSocket: Auto-reconnect enabled, emergency exit on disconnect[/dim]")
        
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
        # Update connection status every 2 seconds
        self.set_interval(2, self.update_connection_status)
    
    @work(exclusive=True)
    async def run_websocket(self) -> None:
        """Connect to WebSocket using robust manager."""
        logger.info("Starting WebSocket manager...")
        await self.ws_manager.start()
    
    async def _handle_ws_message(self, data: dict) -> None:
        """Handle incoming WebSocket message."""
        if self.paused:
            return
        await self.process_message(data)
    
    async def _handle_ws_connect(self) -> None:
        """Handle WebSocket connection established."""
        import threading
        self.ws_connected = True
        self.emergency_exit_in_progress = False
        
        coins_str = ', '.join(self.coins)
        def update_ui() -> None:
            self.log_ai(f"[{COLOR_UP}]✓ Connected to Hyperliquid WebSocket[/{COLOR_UP}]")
            self.log_ai(f"[dim]📡 Subscribed to: prices, trades, orderbooks for {coins_str}[/dim]")
            self.log_ai("[yellow]⏳ Waiting for market data...[/yellow]")
        
        if self._thread_id == threading.get_ident():
            update_ui()
        else:
            self.call_from_thread(update_ui)
    
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
            self._log_ai_threadsafe(f"[{COLOR_DOWN}]⚠️ EMERGENCY: Exiting all positions due to disconnect![/{COLOR_DOWN}]")
            
            await self._emergency_exit_all_positions(reason)
    
    async def _emergency_exit_all_positions(self, reason: str) -> None:
        """
        Emergency exit all open positions.
        
        CRITICAL: This protects capital when we lose market data connection.
        We cannot make informed trading decisions without live data.
        """
        import threading
        positions_to_close = list(self.trader.positions.keys())
        
        for coin in positions_to_close:
            try:
                # Use last known price (not ideal, but better than nothing)
                price = self.prices.get(coin)
                if not price:
                    self._log_ai_threadsafe(f"[{COLOR_DOWN}]⚠️ No price for {coin} - cannot close safely![/{COLOR_DOWN}]")
                    continue
                
                position = self.trader.positions.get(coin)
                if position:
                    result = self.trader.close_position(coin, price)
                    
                    pnl_color = COLOR_UP if result.trade and result.trade.pnl >= 0 else COLOR_DOWN
                    self._log_ai_threadsafe(f"[{pnl_color}]🚨 EMERGENCY CLOSE: {result.message}[/{pnl_color}]")
                    
                    if result.trade:
                        self._record_trade_feedback(result.trade, "emergency_exit")
                        if self._thread_id == threading.get_ident():
                            self.update_history_display(result.trade)
                        else:
                            self.call_from_thread(self.update_history_display, result.trade)
                    
                    logger.warning(f"EMERGENCY EXIT: {coin} closed at ${price} due to: {reason}")
                    
            except Exception as e:
                self._log_ai_threadsafe(f"[{COLOR_DOWN}]❌ FAILED to close {coin}: {e}[/{COLOR_DOWN}]")
                logger.error(f"EMERGENCY EXIT FAILED for {coin}: {e}")
        
        def update_displays() -> None:
            self.update_positions_display()
            self.update_status_bar()
        
        if self._thread_id == threading.get_ident():
            update_displays()
        else:
            self.call_from_thread(update_displays)
        self.emergency_exit_in_progress = False
    
    def _handle_ws_state_change(self, state: ConnectionState) -> None:
        """Handle WebSocket state changes for UI updates."""
        import threading
        
        def update_ui() -> None:
            state_msg = {
                ConnectionState.DISCONNECTED: f"[{COLOR_DOWN}]⭕ Disconnected[/{COLOR_DOWN}]",
                ConnectionState.CONNECTING: "[yellow]🔄 Connecting...[/yellow]",
                ConnectionState.CONNECTED: f"[{COLOR_UP}]🟢 Connected[/{COLOR_UP}]",
                ConnectionState.RECONNECTING: "[yellow]🟡 Reconnecting...[/yellow]",
                ConnectionState.FATAL_ERROR: f"[{COLOR_DOWN}]🔴 FATAL ERROR[/{COLOR_DOWN}]",
            }
            
            msg = state_msg.get(state, f"Unknown state: {state}")
            self.log_ai(f"WS State: {msg}")
            
            # If fatal error, show notification
            if state == ConnectionState.FATAL_ERROR:
                self.notify(
                    "CRITICAL: WebSocket connection failed! Positions have been closed.",
                    severity="error"
                )
        
        # Check if we're on main thread or worker thread
        if self._thread_id == threading.get_ident():
            update_ui()
        else:
            self.call_from_thread(update_ui)
    
    def update_connection_status(self) -> None:
        """Update connection status display."""
        try:
            status = self.ws_manager.get_status_string()
            # Could update a dedicated connection status widget here
            pass
        except Exception:
            pass
    
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
                old_price = self.prices.get(coin)
                
                # Log first price for this coin
                if coin not in self.prices:
                    self.log_ai(f"[{COLOR_UP}]✓ First price received: {coin} @ ${new_price:,.2f}[/{COLOR_UP}]")
                
                self.prices[coin] = new_price
                
                # Store history
                self.price_history[coin].append({
                    "price": new_price,
                    "time": datetime.now()
                })
                
                # Check for opportunities
                if old_price:
                    await self.analyze_opportunity(coin, new_price, old_price)
        
        # Log when all coins have prices
        if first_update and len(self.prices) >= len(self.coins):
            self.log_ai(f"[{COLOR_UP}]✓ All prices received! Starting opportunity analysis...[/{COLOR_UP}]")
            self.log_ai(f"[dim]Building {self.momentum_timeframe}s price history before detecting momentum...[/dim]")
        
        # Periodic market analysis
        now = datetime.now()
        if (now - self.last_market_analysis).total_seconds() >= self.config.market_analysis_interval_seconds:
            self.analyze_market_conditions()
            self.last_market_analysis = now
        
        # Update displays
        with self.batch_update():
            self.update_prices_display()
            self.update_status_bar()
    
    async def handle_trades(self, data: dict) -> None:
        """Handle trade updates."""
        trades_data = data.get("data", [])
        
        for trade in trades_data:
            coin = trade.get("coin", "?")
            price = float(trade.get("px", 0))
            size = float(trade.get("sz", 0))
            side = trade.get("side", "?")
            
            self.trades.appendleft({
                "time": datetime.now(),
                "coin": coin,
                "side": side,
                "size": size,
                "price": price,
            })
        
        self.update_trades_display()
    
    async def handle_orderbook(self, data: dict) -> None:
        """Handle order book updates."""
        book = data.get("data", {})
        coin = book.get("coin", self.coins[0])
        levels = book.get("levels", [[], []])
        
        depth = self.config.orderbook_depth
        self.orderbook[coin] = {
            "bids": levels[0][:depth] if len(levels) > 0 else [],
            "asks": levels[1][:depth] if len(levels) > 1 else [],
        }
        
        self.update_orderbook_display(coin)
    
    def analyze_market_conditions(self) -> None:
        """Analyze and report overall market conditions."""
        analysis = self.market_analyzer.analyze(
            coins=self.coins,
            prices=self.prices,
            price_history=self.price_history,
            momentum_timeframe=self.momentum_timeframe,
        )
        
        if not analysis:
            return
        
        # Log market summary
        color = analysis.condition_color
        self.log_ai(f"[{color}]━━━ MARKET ANALYSIS ━━━[/{color}]")
        self.log_ai(f"[{color}]{analysis.condition_label}[/{color}] - {analysis.description}")
        
        # Log each coin's status
        for ca in analysis.coin_analyses:
            if ca.status == CoinStatus.RISING:
                status_str = f"[{COLOR_UP}]▲ RISING +{ca.momentum:.3f}%[/{COLOR_UP}]"
            elif ca.status == CoinStatus.FALLING:
                status_str = f"[{COLOR_DOWN}]▼ FALLING {ca.momentum:.3f}%[/{COLOR_DOWN}]"
            else:
                status_str = f"[dim]─ FLAT {ca.momentum:+.3f}%[/dim]"
            
            self.log_ai(f"  {ca.coin}: ${ca.price:,.2f} ({ca.change:+.2f}) {status_str}")
        
        # Log threshold reminder
        self.log_ai(f"[dim]  Threshold: ±{self.track_threshold:.2f}% to track, ±{self.trade_threshold:.2f}% to trade[/dim]")
        
        # Highlight coins approaching thresholds
        for ca in analysis.coin_analyses:
            abs_momentum = abs(ca.momentum)
            approaching = self.track_threshold * 0.5
            if approaching <= abs_momentum < self.track_threshold:
                self.log_ai(f"[yellow]  👀 {ca.coin} approaching threshold ({ca.momentum:+.3f}%)[/yellow]")
            elif abs_momentum >= self.track_threshold and abs_momentum < self.trade_threshold:
                remaining = self.trade_threshold - abs_momentum
                self.log_ai(f"[cyan]  🎯 {ca.coin} TRACKING - needs {remaining:.3f}% more to trade[/cyan]")
        
        # If AI mode is enabled, request AI analysis
        if self.ai_analyzer.enabled and self.prices:
            self.run_ai_market_analysis()
    
    @work(exclusive=False)
    async def run_ai_market_analysis(self) -> None:
        """Run AI-powered market analysis."""
        if not self.prices:
            return
        
        # Prepare data for AI
        prices_data = {}
        momentum_data = {}
        orderbook_data = {}
        
        for coin in self.coins:
            price = self.prices.get(coin)
            if price:
                momentum = self._calculate_momentum(coin)
                prices_data[coin] = {
                    "price": price,
                    "change_1m": momentum if momentum else 0,
                }
                momentum_data[coin] = momentum if momentum else 0
                
                # Get orderbook data if available
                book = self.orderbook.get(coin, {})
                bids = book.get("bids", [])
                asks = book.get("asks", [])
                if bids and asks:
                    bid_volume = sum(float(b.get("sz", 0)) for b in bids[:5])
                    ask_volume = sum(float(a.get("sz", 0)) for a in asks[:5])
                    total = bid_volume + ask_volume
                    bid_ratio = (bid_volume / total * 100) if total > 0 else 50
                    orderbook_data[coin] = {"bid_ratio": bid_ratio}
        
        # Get recent trades
        recent_trades = [
            {"side": t.get("side", "buy")}
            for t in list(self.trades)[:20]
        ]
        
        # Run AI analysis on primary coin (first in list)
        primary_coin = self.coins[0]
        try:
            result = await self.ai_analyzer.analyze_market(
                coin=primary_coin,
                prices=prices_data,
                momentum=momentum_data,
                orderbook=orderbook_data,
                recent_trades=recent_trades,
            )
            
            # Display AI result
            sentiment_color = {
                "BULLISH": COLOR_UP,
                "BEARISH": COLOR_DOWN,
                "NEUTRAL": "yellow",
            }.get(result.sentiment.value, "white")
            
            self.log_ai(f"[cyan]━━━ 🤖 AI ANALYSIS ━━━[/cyan]")
            self.log_ai(f"  Sentiment: [{sentiment_color}]{result.sentiment.value}[/{sentiment_color}]")
            self.log_ai(f"  Confidence: {result.confidence}/10")
            self.log_ai(f"  Signal: [{sentiment_color}]{result.signal.value}[/{sentiment_color}]")
            self.log_ai(f"  [dim]{result.reason}[/dim]")
            self.log_ai(f"  [dim]⚡ Response: {result.response_time_ms:.0f}ms[/dim]")
            
            # Update metrics display
            self.update_ai_title()
            
        except Exception as e:
            self.log_ai(f"[{COLOR_DOWN}]AI analysis error: {e}[/{COLOR_DOWN}]")
    
    async def analyze_opportunity(self, coin: str, price: float, old_price: float) -> None:
        """Analyze price for trading opportunities."""
        history = self.price_history[coin]
        
        # Analyze opportunity using extracted logic
        result = self.opportunity_analyzer.analyze(
            coin=coin,
            current_price=price,
            price_history=history,
            momentum_timeframe=self.momentum_timeframe,
            track_threshold=self.track_threshold,
            trade_threshold=self.trade_threshold,
            is_currently_tracking=coin in self.pending_opportunities,
        )
        
        # Handle no-action cases
        if result.action == OpportunityAction.NO_ACTION:
            if len(history) % self.config.price_history_log_interval == 1:
                self.log_ai(f"[dim]📊 {coin}: Building price history ({len(history)} points)...[/dim]")
            return
        
        # Log analysis periodically
        if len(history) % self.config.momentum_analysis_log_interval == 0 and result.momentum_pct is not None:
            direction_emoji = "📈" if result.momentum_pct > 0 else "📉" if result.momentum_pct < 0 else "➡️"
            color = COLOR_UP if result.momentum_pct > 0 else COLOR_DOWN if result.momentum_pct < 0 else "white"
            self.log_ai(
                f"[dim]🔍 {coin}: ${price:,.2f} | "
                f"{self.momentum_timeframe}s momentum: [{color}]{result.momentum_pct:+.3f}%[/{color}] {direction_emoji} | "
                f"Threshold: ±{self.trade_threshold:.2f}%[/dim]"
            )
        
        # Handle stop tracking
        if result.action == OpportunityAction.STOP_TRACKING:
            if coin in self.pending_opportunities:
                del self.pending_opportunities[coin]
                self.update_opportunities_display()
            return
        
        # Handle tracking (start or continue)
        if result.is_trackable:
            if coin not in self.pending_opportunities:
                # Create new pending opportunity
                opp = self.opportunity_analyzer.create_opportunity(
                    coin=coin,
                    direction=result.direction,
                    price=price,
                    trade_threshold=self.trade_threshold,
                    momentum_timeframe=self.momentum_timeframe,
                )
                self.pending_opportunities[coin] = opp
                self.log_ai(f"[cyan]🔍 Analyzing {coin}...[/cyan]")
            
            opp = self.pending_opportunities[coin]
            opp.current_price = price
            opp.direction = result.direction
            
            # Validate conditions
            is_valid = self.opportunity_analyzer.validate_conditions(
                opp=opp,
                momentum_pct=result.momentum_pct,
                trade_threshold=self.trade_threshold,
                has_position=coin in self.trader.positions,
                balance=self.trader.balance,
                position_size_pct=self.config.position_size_pct,
            )
            
            self.update_opportunities_display()
            
            # If all conditions met, execute!
            if is_valid and coin not in self.trader.positions:
                await self.execute_opportunity(opp)
                del self.pending_opportunities[coin]
    
    async def execute_opportunity(self, opp: PendingOpportunity) -> None:
        """Execute a validated opportunity."""
        coin = opp.coin
        price = opp.current_price
        
        # Calculate position size based on config
        position_value = self.trader.balance * self.config.position_size_pct
        size = position_value / price
        
        self.log_ai(f"[{COLOR_UP}]✓ ALL CONDITIONS MET for {coin}[/{COLOR_UP}]")
        self.log_ai(f"[{COLOR_UP}]→ Executing {opp.direction} {size:.6f} {coin} @ ${price:,.2f}[/{COLOR_UP}]")
        
        # Execute trade
        if opp.direction == "LONG":
            result = self.trader.open_long(coin, size, price)
        else:
            result = self.trader.open_short(coin, size, price)
        
        if result.success:
            self.log_ai(f"[{COLOR_UP}]✓ {result.message}[/{COLOR_UP}]")
            # Store entry momentum for feedback recording
            momentum = self._calculate_momentum(coin)
            if momentum is not None:
                self.entry_momentum[coin] = momentum
        else:
            self.log_ai(f"[{COLOR_DOWN}]✗ {result.message}[/{COLOR_DOWN}]")
        
        with self.batch_update():
            self.update_positions_display()
            self.update_status_bar()
        
        # Set up exit monitoring
        self.set_timer(1, lambda: self.check_exit_conditions(coin))
    
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
    
    def _record_trade_feedback(self, trade, outcome: str) -> None:
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
                # Current parameters
                track_threshold_pct=self.track_threshold,
                trade_threshold_pct=self.trade_threshold,
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
        """Check if we should exit a position."""
        if coin not in self.trader.positions:
            return
        
        price = self.prices.get(coin)
        if not price:
            self.set_timer(1, lambda: self.check_exit_conditions(coin))
            return
        
        position = self.trader.positions[coin]
        pnl_pct = position.unrealized_pnl_percent(price)
        
        # Take profit or stop loss based on config thresholds
        if pnl_pct >= self.config.take_profit_pct:
            self.log_ai(f"[{COLOR_UP}]🎯 Take profit triggered for {coin} (+{pnl_pct:.2f}%)[/{COLOR_UP}]")
            result = self.trader.close_position(coin, price)
            self.log_ai(f"[{COLOR_UP}]✓ {result.message}[/{COLOR_UP}]")
            self._record_trade_feedback(result.trade, "take_profit")
            with self.batch_update():
                self.update_positions_display()
                self.update_history_display(result.trade)
                self.update_status_bar()
        elif pnl_pct <= self.config.stop_loss_pct:
            self.log_ai(f"[{COLOR_DOWN}]🛑 Stop loss triggered for {coin} ({pnl_pct:.2f}%)[/{COLOR_DOWN}]")
            result = self.trader.close_position(coin, price)
            self.log_ai(f"[{COLOR_DOWN}]✗ {result.message}[/{COLOR_DOWN}]")
            self._record_trade_feedback(result.trade, "stop_loss")
            with self.batch_update():
                self.update_positions_display()
                self.update_history_display(result.trade)
                self.update_status_bar()
        else:
            # Keep checking
            self.set_timer(0.5, lambda: self.check_exit_conditions(coin))
    
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
    
    def update_prices_display(self) -> None:
        """Update prices panel."""
        panel = self.query_one(PricesPanel)
        panel.update_display(
            self.prices,
            self.price_history,
            self.momentum_timeframe,
            self.track_threshold,
            self.trade_threshold,
        )
    
    def update_orderbook_display(self, coin: str) -> None:
        """Update order book panel."""
        panel = self.query_one(OrderBookPanel)
        panel.update_display(self.orderbook)
    
    def update_trades_display(self) -> None:
        """Update trades panel."""
        panel = self.query_one(TradesPanel)
        panel.update_display(self.trades)
    
    def update_opportunities_display(self) -> None:
        """Update opportunities panel."""
        panel = self.query_one(OpportunitiesPanel)
        panel.update_display(self.pending_opportunities)
    
    def update_positions_display(self) -> None:
        """Update positions panel."""
        panel = self.query_one(PositionsPanel)
        panel.update_display(self.trader.positions, self.prices)
    
    def update_history_display(self, trade=None) -> None:
        """Update trade history panel."""
        panel = self.query_one(HistoryPanel)
        panel.update_display(self.trader.trade_history)
    
    def update_status_bar(self) -> None:
        """Update the status bar."""
        status_bar = self.query_one(StatusBar)
        
        # Calculate last message age
        last_msg_age = None
        if self.ws_connected and self.ws_manager.metrics.last_message_time:
            last_msg_age = (datetime.now() - self.ws_manager.metrics.last_message_time).total_seconds()
        
        status_bar.update_status(
            ws_connected=self.ws_connected,
            last_message_age=last_msg_age,
            reconnect_count=self.ws_manager.metrics.reconnect_count,
            balance=self.trader.balance,
            equity=self.trader.get_equity(self.prices),
            starting_balance=self.starting_balance,
            trade_count=len(self.trader.trade_history),
        )
    
    def log_ai(self, message: str) -> None:
        """Log message to AI reasoning panel."""
        try:
            panel = self.query_one(AIPanel)
            panel.log(message)
        except Exception as e:
            logger.debug(f"AI panel not ready: {e}")
    
    def _log_ai_threadsafe(self, message: str) -> None:
        """Thread-safe version of log_ai that works from any context."""
        import threading
        if self._thread_id == threading.get_ident():
            # On main thread - call directly
            self.log_ai(message)
        else:
            # On worker thread - use call_from_thread
            self.call_from_thread(self.log_ai, message)
    
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
        self.pending_opportunities.clear()
        
        # Clear saved session state
        self.state_manager.clear_state()
        
        self.log_ai("[yellow]🔄 Simulator reset[/yellow]")
        self.log_ai("[dim]💾 Saved session state cleared[/dim]")
        with self.batch_update():
            self.update_positions_display()
            self.update_history_display()
            self.update_status_bar()
    
    def action_save_session(self) -> None:
        """Manually save the current session state (Ctrl+S)."""
        self._save_session_state()
        pnl = self.trader.balance - self.starting_balance
        self.log_ai(f"[{COLOR_UP}]💾 Session '{self.session_name}' saved[/{COLOR_UP}]")
        self.log_ai(f"[dim]  Balance: ${self.trader.balance:,.2f} | P&L: ${pnl:+,.2f}[/dim]")
        self.notify(f"Session '{self.session_name}' saved!", severity="information")
    
    def action_toggle_pause(self) -> None:
        """Pause/unpause the simulator."""
        self.paused = not self.paused
        status = "PAUSED" if self.paused else "RUNNING"
        self.log_ai(f"[yellow]⏸️ Simulator {status}[/yellow]")
    
    def action_restart(self) -> None:
        """Restart the app with fresh code."""
        self.log_ai("[yellow]🔄 Restarting with fresh code...[/yellow]")
        self.exit()
        # Replace current process with new one (reloads all code)
        os.execv(sys.executable, [sys.executable] + sys.argv)
    
    def action_decrease_track(self) -> None:
        """Decrease tracking threshold."""
        self.track_threshold = max(0.01, self.track_threshold - 0.01)
        self.update_threshold_bar()
        self.log_ai(f"[yellow]📉 Track threshold: {self.track_threshold:.2f}%[/yellow]")
    
    def action_increase_track(self) -> None:
        """Increase tracking threshold."""
        self.track_threshold = min(self.trade_threshold - 0.01, self.track_threshold + 0.01)
        self.update_threshold_bar()
        self.log_ai(f"[yellow]📈 Track threshold: {self.track_threshold:.2f}%[/yellow]")
    
    def action_decrease_trade(self) -> None:
        """Decrease trading threshold."""
        self.trade_threshold = max(self.track_threshold + 0.01, self.trade_threshold - 0.01)
        self.update_threshold_bar()
        self.log_ai(f"[yellow]📉 Trade threshold: {self.trade_threshold:.2f}%[/yellow]")
    
    def action_increase_trade(self) -> None:
        """Increase trading threshold."""
        self.trade_threshold = min(2.0, self.trade_threshold + 0.01)
        self.update_threshold_bar()
        self.log_ai(f"[yellow]📈 Trade threshold: {self.trade_threshold:.2f}%[/yellow]")
    
    def action_cycle_momentum_down(self) -> None:
        """Decrease momentum timeframe."""
        idx = self.MOMENTUM_TIMEFRAMES.index(self.momentum_timeframe)
        if idx > 0:
            self.momentum_timeframe = self.MOMENTUM_TIMEFRAMES[idx - 1]
            self.log_ai(f"[yellow]⏱️ Momentum timeframe: {self.momentum_timeframe}s[/yellow]")
            self.update_threshold_bar()
            self.update_prices_display()
    
    def action_cycle_momentum_up(self) -> None:
        """Increase momentum timeframe."""
        idx = self.MOMENTUM_TIMEFRAMES.index(self.momentum_timeframe)
        if idx < len(self.MOMENTUM_TIMEFRAMES) - 1:
            self.momentum_timeframe = self.MOMENTUM_TIMEFRAMES[idx + 1]
            self.log_ai(f"[yellow]⏱️ Momentum timeframe: {self.momentum_timeframe}s[/yellow]")
            self.update_threshold_bar()
            self.update_prices_display()
    
    def update_threshold_bar(self) -> None:
        """Update the threshold display."""
        try:
            status_bar = self.query_one(StatusBar)
            status_bar.update_thresholds(
                track_threshold=self.track_threshold,
                trade_threshold=self.trade_threshold,
                momentum_timeframe=self.momentum_timeframe,
                momentum_timeframes=self.MOMENTUM_TIMEFRAMES,
            )
        except Exception as e:
            logger.debug(f"Threshold bar not ready: {e}")
    
    def action_toggle_ai(self) -> None:
        """Toggle between rule-based and AI analysis mode."""
        if self.analysis_mode == "RULE-BASED":
            # Enable AI mode with local Ollama
            self.ai_analyzer.enabled = True
            self.analysis_mode = "AI (Local)"
            self.ai_model = "mistral:7b"
            self.log_ai(f"[{COLOR_UP}]🤖 Switched to AI analysis mode[/{COLOR_UP}]")
            self.log_ai(f"[dim]  Model: {self.ai_model} (Local Ollama)[/dim]")
            self.log_ai(f"[dim]  AI will analyze: market sentiment, entry signals[/dim]")
            self.notify("AI Mode enabled! Using local Mistral model.", severity="information")
            # Check AI availability
            self.check_ai_availability()
        else:
            self.ai_analyzer.enabled = False
            self.analysis_mode = "RULE-BASED"
            self.ai_model = "None (Momentum Rules)"
            self.log_ai(f"[{COLOR_UP}]✓ Switched to RULE-BASED analysis[/{COLOR_UP}]")
        self.update_ai_title()
    
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
    
    def action_tuning_report(self) -> None:
        """Generate and display incremental tuning report (only new trades)."""
        # Get last report timestamp from state manager
        last_report = self.state_manager.get_last_report_timestamp()
        
        # Count new trades since last report
        new_trades = self.feedback_collector.get_trades_since(last_report)
        new_trade_count = len(new_trades)
        total_trade_count = len(self.feedback_collector.trades)
        
        if total_trade_count == 0:
            self.log_ai("[yellow]📊 No trades recorded yet for tuning analysis[/yellow]")
            self.log_ai("[dim]  Trades are recorded when positions close (TP/SL/emergency)[/dim]")
            self.notify("No trades recorded yet. Trade first!", severity="warning")
            return
        
        if new_trade_count == 0 and last_report:
            self.log_ai("[yellow]📊 No new trades since last report[/yellow]")
            self.log_ai(f"[dim]  Last report: {last_report.strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
            self.log_ai(f"[dim]  Total trades: {total_trade_count}[/dim]")
            self.notify("No new trades since last report.", severity="warning")
            return
        
        # Quick summary in AI panel
        is_incremental = last_report is not None
        report_type = "INCREMENTAL" if is_incremental else "FULL"
        
        self.log_ai(f"[cyan]━━━ {report_type} TUNING REPORT ━━━[/cyan]")
        if is_incremental:
            self.log_ai(f"[dim]  📈 {new_trade_count} new trades (since {last_report.strftime('%H:%M:%S')})[/dim]")
        else:
            self.log_ai(f"[dim]  📊 Analyzing all {total_trade_count} trades[/dim]")
        
        # Generate incremental report
        try:
            json_path, md_path = self.tuning_exporter.export_both(since=last_report)
            
            # Mark that we generated a report (for next incremental)
            self.state_manager.mark_report_generated()
            
            self.log_ai(f"[{COLOR_UP}]✓ Report generated![/{COLOR_UP}]")
            self.log_ai(f"[dim]  📄 {md_path}[/dim]")
            self.log_ai(f"[dim]  📊 {json_path}[/dim]")
            
            # Show suggestions preview for the new trades
            analysis = self.performance_analyzer.analyze(trades=new_trades if is_incremental else None)
            suggestions = analysis.get("suggestions", [])
            if suggestions:
                self.log_ai(f"[yellow]💡 {len(suggestions)} suggestion(s):[/yellow]")
                for s in suggestions[:3]:  # Show first 3
                    if s.get("parameter"):
                        self.log_ai(f"[dim]  • {s.get('parameter')}: {s.get('direction')} ({s.get('confidence')})[/dim]")
                    elif s.get("message"):
                        self.log_ai(f"[dim]  • {s.get('message')}[/dim]")
            
            self.notify(f"Report saved! {new_trade_count} new trades analyzed.", severity="information")
        except Exception as e:
            self.log_ai(f"[{COLOR_DOWN}]✗ Failed to generate report: {e}[/{COLOR_DOWN}]")
            logger.error(f"Tuning report generation failed: {e}")
    
    async def action_quit(self) -> None:
        """Quit the application with proper cleanup."""
        self.log_ai("[yellow]🛑 Shutting down...[/yellow]")
        
        # Close any open positions before exit
        if self.trader.positions:
            self.log_ai(f"[yellow]⚠️ Closing {len(self.trader.positions)} open positions before exit...[/yellow]")
            for coin in list(self.trader.positions.keys()):
                price = self.prices.get(coin)
                if price:
                    result = self.trader.close_position(coin, price)
                    self.log_ai(f"Closed {coin}: {result.message}")
                    if result.trade:
                        self._record_trade_feedback(result.trade, "manual")
        
        # Save final session state
        self._save_session_state()
        self.log_ai(f"[dim]💾 Session '{self.session_name}' saved. Use --resume --session {self.session_name} to continue.[/dim]")
        
        # Stop WebSocket manager
        await self.ws_manager.stop()
        
        # Close AI client
        await self.ai_analyzer.close()
        
        logger.info("Dashboard shutdown complete")
        self.exit()
    


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Paper Trading Dashboard")
    parser.add_argument("--balance", "-b", type=float, default=10000,
                        help="Starting balance (default: 10000)")
    parser.add_argument("--coins", "-c", nargs="+", default=["BTC", "ETH", "SOL"],
                        help="Coins to watch (default: BTC ETH SOL)")
    parser.add_argument("--resume", "-r", action="store_true",
                        help="Resume from saved session state")
    parser.add_argument("--fresh", "-f", action="store_true",
                        help="Start fresh, ignoring any saved state")
    parser.add_argument("--session", "-s", type=str, default=None,
                        help="Session name to use (required for trading)")
    parser.add_argument("--list-sessions", "-l", action="store_true",
                        help="List all available sessions and exit")
    parser.add_argument("--delete-session", type=str, metavar="NAME",
                        help="Delete a saved session and exit")
    
    args = parser.parse_args()
    
    # Handle --list-sessions
    if args.list_sessions:
        sessions = SessionStateManager.list_sessions()
        if not sessions:
            print("\n📂 No saved sessions found.")
            print("   Sessions are saved to data/sessions/")
            print()
        else:
            print(f"\n📂 Available Sessions ({len(sessions)}):")
            print("-" * 70)
            for s in sessions:
                pnl_symbol = "+" if s['pnl'] >= 0 else ""
                print(f"  📊 {s['name']}")
                print(f"     Balance: ${s['balance']:,.2f} | P&L: {pnl_symbol}${s['pnl']:.2f} ({s['pnl_pct']:+.1f}%)")
                report_status = "✓" if s.get('has_report') else "–"
                print(f"     Trades: {s['total_trades']} | Win Rate: {s['win_rate']:.1f}% | Open: {s['open_positions']} | Report: {report_status}")
                print(f"     Last updated: {s['last_update']}")
                print()
            print("   Use --session <name> --resume to load a session")
            print()
        return
    
    # Handle --delete-session
    if args.delete_session:
        if SessionStateManager.delete_session(args.delete_session):
            print(f"✓ Deleted session '{args.delete_session}'")
        else:
            print(f"✗ Session '{args.delete_session}' not found")
        return
    
    # Session name is required for trading
    if not args.session:
        print("\n❌ Session name required!")
        print("\nUsage:")
        print("  python bot/ui/dashboard.py --session <name> [--balance 10000] [--resume]")
        print("\nExamples:")
        print("  python bot/ui/dashboard.py --session my_strategy")
        print("  python bot/ui/dashboard.py --session aggressive --balance 5000")
        print("  python bot/ui/dashboard.py --session my_strategy --resume")
        print("\nOr use dev.sh:")
        print("  ./dev.sh my_strategy")
        print("  ./dev.sh aggressive 5000")
        print()
        
        # Show available sessions
        sessions = SessionStateManager.list_sessions()
        if sessions:
            print(f"📂 Available Sessions ({len(sessions)}):")
            for s in sessions:
                print(f"  • {s['name']} - ${s['balance']:,.2f} ({s['total_trades']} trades)")
            print()
        return
    
    # Handle state manager for --fresh flag
    if args.fresh:
        state_manager = SessionStateManager(session_name=args.session)
        if state_manager.has_saved_state:
            state_manager.clear_state()
            print(f"Cleared session '{args.session}'. Starting fresh.")
    
    # Show saved state info if available and not resuming
    if not args.resume and not args.fresh:
        state_manager = SessionStateManager(session_name=args.session)
        summary = state_manager.get_session_summary()
        if summary:
            print(f"\n📊 Found saved session '{args.session}':")
            print(f"   Balance: ${summary['balance']:,.2f} (started: ${summary['starting_balance']:,.2f})")
            print(f"   P&L: ${summary['pnl']:+,.2f} ({summary['pnl_pct']:+.2f}%)")
            print(f"   Trades: {summary['total_trades']} ({summary['win_rate']:.1f}% win rate)")
            print(f"   Open positions: {summary['open_positions']}")
            print(f"\n   Use --resume --session {args.session} to continue")
            print(f"   Use --fresh --session {args.session} to reset this session")
            print(f"   Use --session <new_name> to create a new session")
            print()
    
    app = TradingDashboard(
        starting_balance=args.balance,
        coins=[c.upper() for c in args.coins],
        resume=args.resume,
        session_name=args.session,
    )
    app.run()


if __name__ == "__main__":
    main()
