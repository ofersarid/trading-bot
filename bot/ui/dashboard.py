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
        Binding("1", "decrease_track", "Track -"),
        Binding("2", "increase_track", "Track +"),
        Binding("3", "decrease_trade", "Trade -"),
        Binding("4", "increase_trade", "Trade +"),
        Binding("5", "cycle_momentum_down", "Mom -"),
        Binding("6", "cycle_momentum_up", "Mom +"),
        Binding("a", "toggle_ai", "AI Mode"),
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
    ):
        super().__init__()
        self.config = config or DEFAULT_CONFIG
        self.starting_balance = starting_balance
        self.coins = coins or ["BTC", "ETH", "SOL"]
        
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
        
        # Analysis mode (for future AI integration)
        self.analysis_mode = "RULE-BASED"  # "RULE-BASED" or "AI (Claude)"
        self.ai_model = "None (Momentum Rules)"  # Will be "claude-sonnet-4-20250514" etc.
        self.tokens_used = 0
        self.ai_calls = 0
        
        # Paper trader
        self.trader = PaperTrader(
            starting_balance=starting_balance,
            fees=HYPERLIQUID_FEES,
        )
        
        # Analysis modules (separate analysis logic from UI)
        self.market_analyzer = MarketAnalyzer(self.config)
        self.opportunity_analyzer = OpportunityAnalyzer(self.config)
        
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
            log_callback=self.log_ai,
        )
        
        # State
        self.paused = False
        self.ws_connected = False
        self.emergency_exit_in_progress = False
        self.start_time = datetime.now()
        
    def compose(self) -> ComposeResult:
        """Create the dashboard layout using extracted components."""
        # Custom title bar
        yield Static("PAPER TRADING SIMULATOR", id="title-bar", classes="title-bar")
        
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
        self.log_ai("Dashboard initialized. Connecting to Hyperliquid...")
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
        self.ws_connected = True
        self.emergency_exit_in_progress = False
        self.log_ai(f"[{COLOR_UP}]✓ Connected to Hyperliquid WebSocket[/{COLOR_UP}]")
        self.log_ai(f"[dim]📡 Subscribed to: prices, trades, orderbooks for {', '.join(self.coins)}[/dim]")
        self.log_ai("[yellow]⏳ Waiting for market data...[/yellow]")
    
    async def _handle_ws_disconnect(self, reason: str) -> None:
        """
        Handle WebSocket disconnection - CRITICAL SAFETY HANDLER.
        
        This is called IMMEDIATELY when connection is lost.
        We must exit all positions to protect capital.
        """
        self.ws_connected = False
        
        # Log the disconnect with high visibility
        self.log_ai(f"[{COLOR_DOWN}]🚨 WEBSOCKET DISCONNECTED: {reason}[/{COLOR_DOWN}]")
        
        # CRITICAL: Emergency exit all positions
        if self.trader.positions and not self.emergency_exit_in_progress:
            self.emergency_exit_in_progress = True
            self.log_ai(f"[{COLOR_DOWN}]⚠️ EMERGENCY: Exiting all positions due to disconnect![/{COLOR_DOWN}]")
            
            await self._emergency_exit_all_positions(reason)
    
    async def _emergency_exit_all_positions(self, reason: str) -> None:
        """
        Emergency exit all open positions.
        
        CRITICAL: This protects capital when we lose market data connection.
        We cannot make informed trading decisions without live data.
        """
        positions_to_close = list(self.trader.positions.keys())
        
        for coin in positions_to_close:
            try:
                # Use last known price (not ideal, but better than nothing)
                price = self.prices.get(coin)
                if not price:
                    self.log_ai(f"[{COLOR_DOWN}]⚠️ No price for {coin} - cannot close safely![/{COLOR_DOWN}]")
                    continue
                
                position = self.trader.positions.get(coin)
                if position:
                    result = self.trader.close_position(coin, price)
                    
                    pnl_color = COLOR_UP if result.trade and result.trade.pnl >= 0 else COLOR_DOWN
                    self.log_ai(f"[{pnl_color}]🚨 EMERGENCY CLOSE: {result.message}[/{pnl_color}]")
                    
                    if result.trade:
                        self.update_history_display(result.trade)
                    
                    logger.warning(f"EMERGENCY EXIT: {coin} closed at ${price} due to: {reason}")
                    
            except Exception as e:
                self.log_ai(f"[{COLOR_DOWN}]❌ FAILED to close {coin}: {e}[/{COLOR_DOWN}]")
                logger.error(f"EMERGENCY EXIT FAILED for {coin}: {e}")
        
        self.update_positions_display()
        self.update_status_bar()
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
        
        msg = state_msg.get(state, f"Unknown state: {state}")
        self.log_ai(f"WS State: {msg}")
        
        # If fatal error, show notification
        if state == ConnectionState.FATAL_ERROR:
            self.notify(
                "CRITICAL: WebSocket connection failed! Positions have been closed.",
                severity="error"
            )
    
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
        else:
            self.log_ai(f"[{COLOR_DOWN}]✗ {result.message}[/{COLOR_DOWN}]")
        
        with self.batch_update():
            self.update_positions_display()
            self.update_status_bar()
        
        # Set up exit monitoring
        self.set_timer(1, lambda: self.check_exit_conditions(coin))
    
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
            with self.batch_update():
                self.update_positions_display()
                self.update_history_display(result.trade)
                self.update_status_bar()
        elif pnl_pct <= self.config.stop_loss_pct:
            self.log_ai(f"[{COLOR_DOWN}]🛑 Stop loss triggered for {coin} ({pnl_pct:.2f}%)[/{COLOR_DOWN}]")
            result = self.trader.close_position(coin, price)
            self.log_ai(f"[{COLOR_DOWN}]✗ {result.message}[/{COLOR_DOWN}]")
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
        panel.update_display(self.prices, self.price_history, self.momentum_timeframe)
    
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
    
    def update_ai_title(self) -> None:
        """Update AI panel title with mode and connection info."""
        try:
            panel = self.query_one(AIPanel)
            metrics = self.ws_manager.metrics
            panel.update_title(
                analysis_mode=self.analysis_mode,
                ai_model=self.ai_model,
                tokens_used=self.tokens_used,
                ai_calls=self.ai_calls,
                disconnects=metrics.total_disconnects,
                reconnects=metrics.reconnect_count,
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
        self.log_ai("[yellow]🔄 Simulator reset[/yellow]")
        with self.batch_update():
            self.update_positions_display()
            self.update_history_display()
            self.update_status_bar()
    
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
            # AI mode not yet implemented
            self.log_ai("[yellow]⚠️ AI Mode (Claude) not yet integrated![/yellow]")
            self.log_ai("[dim]  Coming soon: Claude claude-sonnet-4-20250514 for intelligent trade decisions[/dim]")
            self.log_ai("[dim]  Will analyze: market structure, order flow, sentiment[/dim]")
            self.notify("AI Mode coming soon! Currently using rule-based analysis.", severity="warning")
        else:
            self.analysis_mode = "RULE-BASED"
            self.ai_model = "None (Momentum Rules)"
            self.log_ai(f"[{COLOR_UP}]✓ Switched to RULE-BASED analysis[/{COLOR_UP}]")
        self.update_ai_title()
    
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
        
        # Stop WebSocket manager
        await self.ws_manager.stop()
        
        logger.info("Dashboard shutdown complete")
        self.exit()
    


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Paper Trading Dashboard")
    parser.add_argument("--balance", "-b", type=float, default=10000,
                        help="Starting balance (default: 10000)")
    parser.add_argument("--coins", "-c", nargs="+", default=["BTC", "ETH", "SOL"],
                        help="Coins to watch (default: BTC ETH SOL)")
    
    args = parser.parse_args()
    
    app = TradingDashboard(
        starting_balance=args.balance,
        coins=[c.upper() for c in args.coins],
    )
    app.run()


if __name__ == "__main__":
    main()
