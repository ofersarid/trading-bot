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

Run with:
    python bot/ui/dashboard.py --balance 10000
"""

import asyncio
import json
import os
import sys
from collections import deque
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Footer, Static, Label, DataTable
from textual.reactive import reactive
from textual import work
from textual.binding import Binding

import websockets

from bot.core.config import TradingConfig, DEFAULT_CONFIG
from bot.core.models import OpportunityCondition, PendingOpportunity
from bot.simulation.models import HYPERLIQUID_FEES, Side
from bot.simulation.paper_trader import PaperTrader


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
        Binding("q", "quit", "Quit"),
        Binding("r", "reset", "Reset"),
        Binding("p", "toggle_pause", "Pause"),
        Binding("ctrl+r", "restart", "Restart"),
        Binding("1", "decrease_track", "Track -"),
        Binding("2", "increase_track", "Track +"),
        Binding("3", "decrease_trade", "Trade -"),
        Binding("4", "increase_trade", "Trade +"),
        Binding("a", "toggle_ai", "AI Mode"),
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
    ):
        super().__init__()
        self.config = config or DEFAULT_CONFIG
        self.starting_balance = starting_balance
        self.coins = coins or ["BTC", "ETH", "SOL"]
        
        # Data stores
        self.prices: dict[str, float] = {}
        self.prev_prices: dict[str, float] = {}
        self.orderbook: dict[str, dict] = {}  # {coin: {bids: [], asks: []}}
        self.trades: deque = deque(maxlen=self.config.max_trades_history)
        self.pending_opportunities: dict[str, PendingOpportunity] = {}
        self.ai_messages: deque = deque(maxlen=100)  # Store last 100 AI log messages
        
        # Price history for momentum calculation
        self.price_history: dict[str, deque] = {
            coin: deque(maxlen=self.config.price_history_maxlen) for coin in self.coins
        }
        
        # Market analysis state
        self.last_market_analysis = datetime.now()
        
        # Adjustable thresholds (initialized from config, can be changed at runtime)
        self.track_threshold = self.config.track_threshold_pct
        self.trade_threshold = self.config.trade_threshold_pct
        
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
        
        # State
        self.paused = False
        self.ws_connected = False
        self.start_time = datetime.now()
        
    def compose(self) -> ComposeResult:
        """Create the dashboard layout."""
        # Custom title bar (left-aligned)
        yield Static(
            "PAPER TRADING SIMULATOR",
            id="title-bar",
            classes="title-bar"
        )
        
        # Combined status row: status info (left) + threshold settings (right)
        with Horizontal(id="status-row", classes="status-row"):
            yield Static(
                self._render_status_content(),
                id="status-bar",
                classes="status-bar-left"
            )
            yield Static(
                self._render_threshold_content(),
                id="threshold-bar",
                classes="status-bar-right"
            )
        
        # Main content area: AI sidebar (left) + data panels (right)
        with Horizontal(classes="main-content"):
            # Left sidebar: AI Reasoning (full height)
            with Container(id="ai-panel", classes="panel"):
                yield Static("🧠 AI REASONING", classes="panel-title", id="ai-title")
                with ScrollableContainer(id="ai-scroll", classes="panel-content"):
                    yield Static("", id="ai-content")
            
            # Right side: All data panels stacked vertically
            with Vertical(classes="data-panels"):
                # Top row: Prices, Order Book, Live Trades
                with Horizontal(classes="top-row"):
                    # Prices panel
                    with Container(id="prices-panel", classes="panel"):
                        yield Static("💰 PRICES & MOMENTUM", classes="panel-title")
                        with ScrollableContainer(id="prices-scroll", classes="panel-content"):
                            yield Static("", id="prices-content")
                    
                    # Order book panel
                    with Container(id="orderbook-panel", classes="panel"):
                        yield Static("📈 ORDER BOOK", classes="panel-title")
                        with ScrollableContainer(id="orderbook-scroll", classes="panel-content"):
                            yield Static("", id="orderbook-content")
                    
                    # Live trades panel
                    with Container(id="trades-panel", classes="panel"):
                        yield Static("🔄 LIVE TRADES", classes="panel-title")
                        with ScrollableContainer(id="trades-scroll", classes="panel-content"):
                            yield Static("", id="trades-content")
                
                # Opportunities row
                with Container(id="opportunities-panel", classes="panel opportunities-row"):
                    yield Static("🎯 OPPORTUNITIES IN PROGRESS", classes="panel-title")
                    with ScrollableContainer(id="opportunities-scroll", classes="panel-content"):
                        yield Static("", id="opportunities-content")
                
                # Bottom row: Positions and History
                with Horizontal(classes="bottom-row"):
                    with Container(id="positions-panel", classes="panel"):
                        yield Static("📌 OPEN POSITIONS", classes="panel-title")
                        with ScrollableContainer(id="positions-scroll", classes="panel-content"):
                            yield Static("", id="positions-content")
                    
                    with Container(id="history-panel", classes="panel"):
                        yield Static("📜 TRADE HISTORY", classes="panel-title")
                        with ScrollableContainer(id="history-scroll", classes="panel-content"):
                            yield Static("", id="history-content")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Start data streams when app mounts."""
        self.update_ai_title()
        self.log_ai("Dashboard initialized. Connecting to Hyperliquid...")
        self.log_ai(f"[dim]Analysis Mode: {self.analysis_mode} | Model: {self.ai_model}[/dim]")
        self.run_websocket()
        # Update status bar every second for uptime counter
        self.set_interval(1, self.update_status_bar)
        # Update AI title periodically
        self.set_interval(5, self.update_ai_title)
    
    @work(exclusive=True)
    async def run_websocket(self) -> None:
        """Connect to WebSocket and process data."""
        ws_url = "wss://api.hyperliquid.xyz/ws"
        
        try:
            async with websockets.connect(ws_url) as ws:
                self.ws_connected = True
                self.log_ai(f"[{COLOR_UP}]✓ Connected to Hyperliquid WebSocket[/{COLOR_UP}]")
                
                # Subscribe to all prices
                await ws.send(json.dumps({
                    "method": "subscribe",
                    "subscription": {"type": "allMids"}
                }))
                self.log_ai("📡 Subscribed to price updates")
                
                # Subscribe to trades for watched coins
                for coin in self.coins:
                    await ws.send(json.dumps({
                        "method": "subscribe",
                        "subscription": {"type": "trades", "coin": coin}
                    }))
                self.log_ai(f"📡 Subscribed to trades: {', '.join(self.coins)}")
                
                # Subscribe to order book for all coins
                for coin in self.coins:
                    await ws.send(json.dumps({
                        "method": "subscribe",
                        "subscription": {"type": "l2Book", "coin": coin}
                    }))
                self.log_ai(f"📡 Subscribed to order books: {', '.join(self.coins)}")
                
                self.log_ai("[yellow]⏳ Waiting for market data...[/yellow]")
                
                # Process messages
                async for message in ws:
                    if self.paused:
                        continue
                    
                    data = json.loads(message)
                    await self.process_message(data)
                    
        except Exception as e:
            self.log_ai(f"[{COLOR_DOWN}]✗ WebSocket error: {e}[/{COLOR_DOWN}]")
    
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
            self.log_ai("[dim]Building 60s price history before detecting momentum...[/dim]")
        
        # Periodic market analysis
        now = datetime.now()
        if (now - self.last_market_analysis).total_seconds() >= self.config.market_analysis_interval_seconds:
            self.analyze_market_conditions()
            self.last_market_analysis = now
        
        # Update prices display
        self.update_prices_display()
        
        # Update status bar
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
        now = datetime.now()
        
        # Calculate momentum for each coin
        momentums = {}
        for coin in self.coins:
            history = self.price_history[coin]
            if len(history) < 10:
                continue
            
            current_price = self.prices.get(coin, 0)
            
            # Get price from 60 seconds ago
            lookback_price = None
            for point in history:
                age = (now - point["time"]).total_seconds()
                if age >= 60:
                    lookback_price = point["price"]
                    break
            
            if lookback_price and current_price:
                momentum = ((current_price - lookback_price) / lookback_price) * 100
                momentums[coin] = {
                    "momentum": momentum,
                    "price": current_price,
                    "change": current_price - lookback_price
                }
        
        if not momentums:
            return
        
        # Calculate overall market volatility
        avg_abs_momentum = sum(abs(m["momentum"]) for m in momentums.values()) / len(momentums)
        max_mover = max(momentums.items(), key=lambda x: abs(x[1]["momentum"]))
        
        # Determine market condition based on config thresholds
        cfg = self.config
        if avg_abs_momentum < cfg.market_very_calm_threshold:
            condition = "😴 VERY CALM"
            condition_color = "dim"
            description = "Prices barely moving. Waiting for action..."
        elif avg_abs_momentum < cfg.market_calm_threshold:
            condition = "😐 CALM"
            condition_color = "white"
            description = "Low volatility. Minor price fluctuations."
        elif avg_abs_momentum < cfg.market_active_threshold:
            condition = "📊 ACTIVE"
            condition_color = "yellow"
            description = "Moderate movement. Watching for opportunities..."
        elif avg_abs_momentum < cfg.market_volatile_threshold:
            condition = "⚡ VOLATILE"
            condition_color = "cyan"
            description = "Significant price action! High alert."
        else:
            condition = "🔥 VERY VOLATILE"
            condition_color = "magenta"
            description = "Extreme movement! Trading opportunities likely."
        
        # Log market summary
        self.log_ai(f"[{condition_color}]━━━ MARKET ANALYSIS ━━━[/{condition_color}]")
        self.log_ai(f"[{condition_color}]{condition}[/{condition_color}] - {description}")
        
        # Log each coin's status
        for coin, data in sorted(momentums.items(), key=lambda x: abs(x[1]["momentum"]), reverse=True):
            momentum = data["momentum"]
            price = data["price"]
            change = data["change"]
            
            if momentum > 0.1:
                status = f"[{COLOR_UP}]▲ RISING +{momentum:.3f}%[/{COLOR_UP}]"
            elif momentum < -0.1:
                status = f"[{COLOR_DOWN}]▼ FALLING {momentum:.3f}%[/{COLOR_DOWN}]"
            else:
                status = f"[dim]─ FLAT {momentum:+.3f}%[/dim]"
            
            self.log_ai(f"  {coin}: ${price:,.2f} ({change:+.2f}) {status}")
        
        # Log threshold reminder
        self.log_ai(f"[dim]  Threshold: ±{self.track_threshold:.2f}% to track, ±{self.trade_threshold:.2f}% to trade[/dim]")
        
        # Highlight if any coin is close to threshold
        for coin, data in momentums.items():
            momentum = abs(data["momentum"])
            approaching = self.track_threshold * 0.5  # 50% of track threshold
            if approaching <= momentum < self.track_threshold:
                self.log_ai(f"[yellow]  👀 {coin} approaching threshold ({data['momentum']:+.3f}%)[/yellow]")
            elif momentum >= self.track_threshold and momentum < self.trade_threshold:
                remaining = self.trade_threshold - momentum
                self.log_ai(f"[cyan]  🎯 {coin} TRACKING - needs {remaining:.3f}% more to trade[/cyan]")
    
    async def analyze_opportunity(self, coin: str, price: float, old_price: float) -> None:
        """Analyze price for trading opportunities."""
        now = datetime.now()
        history = self.price_history[coin]
        
        # Get price from 60 seconds ago
        lookback_price = None
        lookback_age = 0
        for point in history:
            age = (now - point["time"]).total_seconds()
            if age >= 60:
                lookback_price = point["price"]
                lookback_age = age
                break
        
        if lookback_price is None:
            # Not enough history yet - log occasionally
            if len(history) % 50 == 1:  # Log every ~50 price updates
                self.log_ai(f"[dim]📊 {coin}: Building price history ({len(history)} points)...[/dim]")
            return
        
        # Calculate momentum
        momentum = (price - lookback_price) / lookback_price
        momentum_pct = momentum * 100
        
        # Log analysis periodically (every ~100 updates per coin)
        if len(history) % 100 == 0:
            direction = "📈" if momentum > 0 else "📉" if momentum < 0 else "➡️"
            color = COLOR_UP if momentum > 0 else COLOR_DOWN if momentum < 0 else "white"
            self.log_ai(
                f"[dim]🔍 {coin}: ${price:,.2f} | "
                f"60s momentum: [{color}]{momentum_pct:+.3f}%[/{color}] {direction} | "
                f"Threshold: ±0.30%[/dim]"
            )
        
        # Create or update pending opportunity
        if abs(momentum_pct) > self.track_threshold:  # Start tracking
            direction = "LONG" if momentum > 0 else "SHORT"
            
            if coin not in self.pending_opportunities:
                # Create new pending opportunity
                opp = PendingOpportunity(
                    coin=coin,
                    direction=direction,
                    current_price=price,
                    conditions=[
                        OpportunityCondition("Momentum", f">{self.trade_threshold:.2f}% move in 60s"),
                        OpportunityCondition("No Position", "Not already in position"),
                        OpportunityCondition("Cooldown", "30s since last trade"),
                        OpportunityCondition("Balance", "Sufficient margin"),
                    ]
                )
                self.pending_opportunities[coin] = opp
                self.log_ai(f"[cyan]🔍 Analyzing {coin}...[/cyan]")
            
            opp = self.pending_opportunities[coin]
            opp.current_price = price
            
            # Check conditions
            # 1. Momentum threshold (dynamic)
            opp.conditions[0].met = abs(momentum_pct) >= self.trade_threshold
            opp.conditions[0].value = f"{momentum_pct:+.2f}% (need ±{self.trade_threshold:.2f}%)"
            
            # 2. No existing position
            opp.conditions[1].met = coin not in self.trader.positions
            opp.conditions[1].value = "✓" if opp.conditions[1].met else "In position"
            
            # 3. Cooldown (simplified - always true for demo)
            opp.conditions[2].met = True
            opp.conditions[2].value = "✓"
            
            # 4. Balance check
            required = price * 0.001 * 0.1  # Small position
            opp.conditions[3].met = self.trader.balance >= required
            opp.conditions[3].value = f"${self.trader.balance:,.0f}"
            
            # Update display
            self.update_opportunities_display()
            
            # If all conditions met, execute!
            if opp.is_valid and coin not in self.trader.positions:
                await self.execute_opportunity(opp)
                del self.pending_opportunities[coin]
        else:
            # Remove if momentum died
            if coin in self.pending_opportunities:
                del self.pending_opportunities[coin]
                self.update_opportunities_display()
    
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
        
        self.update_positions_display()
        self.update_status_bar()
        
        # Set up exit monitoring
        self.call_later(1, self.check_exit_conditions, coin)
    
    def check_exit_conditions(self, coin: str) -> None:
        """Check if we should exit a position."""
        if coin not in self.trader.positions:
            return
        
        price = self.prices.get(coin)
        if not price:
            self.call_later(1, self.check_exit_conditions, coin)
            return
        
        position = self.trader.positions[coin]
        pnl_pct = position.unrealized_pnl_percent(price)
        
        # Take profit or stop loss based on config thresholds
        if pnl_pct >= self.config.take_profit_pct:
            self.log_ai(f"[{COLOR_UP}]🎯 Take profit triggered for {coin} (+{pnl_pct:.2f}%)[/{COLOR_UP}]")
            result = self.trader.close_position(coin, price)
            self.log_ai(f"[{COLOR_UP}]✓ {result.message}[/{COLOR_UP}]")
            self.update_positions_display()
            self.update_history_display(result.trade)
            self.update_status_bar()
        elif pnl_pct <= self.config.stop_loss_pct:
            self.log_ai(f"[{COLOR_DOWN}]🛑 Stop loss triggered for {coin} ({pnl_pct:.2f}%)[/{COLOR_DOWN}]")
            result = self.trader.close_position(coin, price)
            self.log_ai(f"[{COLOR_DOWN}]✗ {result.message}[/{COLOR_DOWN}]")
            self.update_positions_display()
            self.update_history_display(result.trade)
            self.update_status_bar()
        else:
            # Keep checking
            self.call_later(0.5, self.check_exit_conditions, coin)
    
    # ============================================================
    # Display Updates
    # ============================================================
    
    def _calculate_momentum(self, coin: str) -> float | None:
        """Calculate 60-second momentum for a coin. Returns percentage or None if not enough data."""
        history = self.price_history.get(coin)
        if not history or len(history) < 10:
            return None
        
        current_price = self.prices.get(coin)
        if not current_price:
            return None
        
        now = datetime.now()
        lookback_price = None
        for point in history:
            age = (now - point["time"]).total_seconds()
            if age >= 60:
                lookback_price = point["price"]
                break
        
        if lookback_price is None:
            return None
        
        return ((current_price - lookback_price) / lookback_price) * 100
    
    def update_prices_display(self) -> None:
        """Update prices panel."""
        lines = []
        
        # Column widths: COIN=5, PRICE=13 (with $), TICK=6, MOMENTUM=rest
        lines.append(f"[dim]{'COIN':<5}   {'PRICE':>13}    {'TICK':^4}    60s MOMENTUM[/dim]")
        lines.append("[dim]─────────────────────────────────────────────────────[/dim]")
        
        for coin in self.coins:
            price = self.prices.get(coin, 0)
            prev = self.prev_prices.get(coin, price)
            change = price - prev
            
            if change > 0:
                tick_color = COLOR_UP
                tick_arrow = "▲"
            elif change < 0:
                tick_color = COLOR_DOWN
                tick_arrow = "▼"
            else:
                tick_color = "white"
                tick_arrow = "─"
            
            # Momentum indicator (60s)
            momentum = self._calculate_momentum(coin)
            if momentum is not None:
                if momentum > 0.1:
                    mom_color = COLOR_UP
                    mom_bar = "▲" * min(5, int(abs(momentum) / 0.1))
                elif momentum < -0.1:
                    mom_color = COLOR_DOWN
                    mom_bar = "▼" * min(5, int(abs(momentum) / 0.1))
                else:
                    mom_color = "dim"
                    mom_bar = "─"
                momentum_str = f"[{mom_color}]{momentum:+.2f}% {mom_bar:<5}[/{mom_color}]"
            else:
                momentum_str = "[dim]building...[/dim]"
            
            # Format price with $ prefix, total 13 chars
            price_str = f"${price:>12,.2f}"
            
            # Single line: COIN | PRICE | TICK | MOMENTUM
            lines.append(
                f"[bold]{coin:<5}[/bold]   "
                f"{price_str}    "
                f"[{tick_color}]{tick_arrow:^4}[/{tick_color}]    "
                f"{momentum_str}"
            )
            
            self.prev_prices[coin] = price
        
        content = self.query_one("#prices-content", Static)
        content.update("\n".join(lines))
    
    def update_orderbook_display(self, coin: str) -> None:
        """Update order book panel with all coins."""
        lines = []
        
        for i, c in enumerate(self.coins):
            book = self.orderbook.get(c, {"bids": [], "asks": []})
            
            if i > 0:
                lines.append("")  # Separator between coins
            
            # Compact: show top 3 asks and bids per coin
            lines.append(f"[bold cyan]{c}[/bold cyan]")
            
            # Asks (reversed so lowest is at bottom)
            for ask in reversed(book["asks"][:3]):
                px = float(ask.get("px", 0))
                sz = float(ask.get("sz", 0))
                lines.append(f"  [{COLOR_DOWN}]${px:>10,.2f}  {sz:>8.4f}[/{COLOR_DOWN}]")
            
            # Spread line
            lines.append(f"  [dim]────────────────────[/dim]")
            
            # Bids
            for bid in book["bids"][:3]:
                px = float(bid.get("px", 0))
                sz = float(bid.get("sz", 0))
                lines.append(f"  [{COLOR_UP}]${px:>10,.2f}  {sz:>8.4f}[/{COLOR_UP}]")
        
        content = self.query_one("#orderbook-content", Static)
        content.update("\n".join(lines))
    
    def update_trades_display(self) -> None:
        """Update trades panel - show trades from last 60 seconds, grouped by coin."""
        now = datetime.now()
        
        # Group trades by coin
        trades_by_coin: dict[str, list] = {coin: [] for coin in self.coins}
        for trade in list(self.trades):
            age = (now - trade["time"]).total_seconds()
            if age > 60:
                continue
            coin = trade["coin"]
            if coin in trades_by_coin:
                trades_by_coin[coin].append(trade)
        
        # Build display grouped by coin
        lines = []
        for i, coin in enumerate(self.coins):
            coin_trades = trades_by_coin[coin]
            
            if i > 0:
                lines.append("")  # Separator between coins
            
            lines.append(f"[bold cyan]{coin}[/bold cyan]")
            
            if not coin_trades:
                lines.append(f"  [dim]No recent trades[/dim]")
            else:
                # Show most recent trades first (up to 6 per coin)
                for trade in coin_trades[:6]:
                    time_str = trade["time"].strftime("%H:%M:%S")
                    side = trade["side"]
                    color = COLOR_UP if side == "B" else COLOR_DOWN
                    side_text = "BUY " if side == "B" else "SELL"
                    
                    lines.append(
                        f"  [{color}]{side_text}[/{color}] "
                        f"[dim]{time_str}[/dim] "
                        f"{trade['size']:>8.4f} @ ${trade['price']:,.2f}"
                    )
        
        content = self.query_one("#trades-content", Static)
        content.update("\n".join(lines))
    
    def update_opportunities_display(self) -> None:
        """Update opportunities panel."""
        lines = []
        
        if not self.pending_opportunities:
            lines.append("[dim]No opportunities being analyzed...[/dim]")
        else:
            for coin, opp in self.pending_opportunities.items():
                color = COLOR_UP if opp.direction == "LONG" else COLOR_DOWN
                lines.append(
                    f"[{color}]{coin} {opp.direction}[/{color}] @ ${opp.current_price:,.2f} │ "
                    f"{opp.progress_bar} {opp.conditions_met}/{opp.total_conditions}"
                )
                for cond in opp.conditions:
                    status = f"[{COLOR_UP}]✓[/{COLOR_UP}]" if cond.met else f"[{COLOR_DOWN}]✗[/{COLOR_DOWN}]"
                    lines.append(f"  {status} {cond.name}: {cond.value or cond.description}")
        
        content = self.query_one("#opportunities-content", Static)
        content.update("\n".join(lines))
    
    def update_positions_display(self) -> None:
        """Update positions panel."""
        lines = []
        
        if not self.trader.positions:
            lines.append("[dim]No open positions[/dim]")
        else:
            for coin, pos in self.trader.positions.items():
                price = self.prices.get(coin, pos.entry_price)
                pnl = pos.unrealized_pnl(price)
                pnl_pct = pos.unrealized_pnl_percent(price)
                
                side = "LONG" if pos.side == Side.LONG else "SHORT"
                color = COLOR_UP if pnl >= 0 else COLOR_DOWN
                
                lines.append(f"[bold]{coin}[/bold] {side} {pos.size:.6f}")
                lines.append(f"  Entry: ${pos.entry_price:,.2f}")
                lines.append(f"  Current: ${price:,.2f}")
                lines.append(f"  [{color}]P&L: ${pnl:+,.2f} ({pnl_pct:+.2f}%)[/{color}]")
        
        content = self.query_one("#positions-content", Static)
        content.update("\n".join(lines))
    
    def update_history_display(self, trade=None) -> None:
        """Update trade history panel."""
        lines = []
        
        if not self.trader.trade_history:
            lines.append("[dim]No completed trades[/dim]")
        else:
            for t in reversed(self.trader.trade_history[-20:]):  # Show last 20 trades
                emoji = "✅" if t.pnl > 0 else "❌"
                color = COLOR_UP if t.pnl > 0 else COLOR_DOWN
                side = "LONG" if t.side == Side.LONG else "SHORT"
                
                lines.append(
                    f"{emoji} [{color}]{side} {t.coin}: "
                    f"${t.pnl:+,.2f} ({t.pnl_percent:+.2f}%)[/{color}]"
                )
        
        content = self.query_one("#history-content", Static)
        content.update("\n".join(lines))
    
    def update_status_bar(self) -> None:
        """Update the status bar."""
        status = self.query_one("#status-bar", Static)
        status.update(self._render_status_content())
    
    def log_ai(self, message: str) -> None:
        """Log message to AI reasoning panel."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.ai_messages.append(f"[dim]{timestamp}[/dim] {message}")
        
        try:
            content = self.query_one("#ai-content", Static)
            content.update("\n".join(self.ai_messages))
            # Auto-scroll to bottom
            scroll = self.query_one("#ai-scroll", ScrollableContainer)
            scroll.scroll_end(animate=False)
        except Exception:
            pass  # Widget not ready yet
    
    def update_ai_title(self) -> None:
        """Update AI panel title with mode and token info."""
        try:
            title = self.query_one("#ai-title", Static)
            if self.analysis_mode == "RULE-BASED":
                title.update(
                    f"🧠 ANALYSIS [dim]│[/dim] [yellow]📐 {self.analysis_mode}[/yellow] [dim]│[/dim] "
                    f"Model: [cyan]{self.ai_model}[/cyan]"
                )
            else:
                title.update(
                    f"🧠 AI REASONING [dim]│[/dim] [{COLOR_UP}]🤖 {self.analysis_mode}[/{COLOR_UP}] [dim]│[/dim] "
                    f"Model: [cyan]{self.ai_model}[/cyan] [dim]│[/dim] "
                    f"Tokens: [magenta]{self.tokens_used:,}[/magenta] [dim]│[/dim] "
                    f"Calls: [blue]{self.ai_calls}[/blue]"
                )
        except Exception:
            pass  # Panel not ready yet
    
    # ============================================================
    # Actions
    # ============================================================
    
    def action_reset(self) -> None:
        """Reset the simulator."""
        self.trader.reset()
        self.pending_opportunities.clear()
        self.log_ai("[yellow]🔄 Simulator reset[/yellow]")
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
    
    def _render_status_content(self) -> str:
        """Render the status bar content (left side)."""
        equity = self.trader.get_equity(self.prices)
        pnl = equity - self.starting_balance
        pnl_pct = (pnl / self.starting_balance) * 100
        pnl_color = COLOR_UP if pnl >= 0 else COLOR_DOWN
        
        # Calculate uptime
        uptime = datetime.now() - self.start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        return (
            f"⏱️ {uptime_str}  │  "
            f"💰${self.trader.balance:,.2f}  │  "
            f"📈${equity:,.2f}  │  "
            f"[{pnl_color}]P&L: ${pnl:+,.2f} ({pnl_pct:+.2f}%)[/{pnl_color}]  │  "
            f"📊{len(self.trader.trade_history)} trades"
        )
    
    def _render_threshold_content(self) -> str:
        """Render the threshold settings content (right side)."""
        # Visual bar for track threshold (0-0.5%)
        track_pct = min(1.0, self.track_threshold / 0.5)
        track_filled = int(track_pct * 15)
        track_bar = "[yellow]" + "█" * track_filled + "░" * (15 - track_filled) + "[/yellow]"
        
        # Visual bar for trade threshold (0-1.0%)
        trade_pct = min(1.0, self.trade_threshold / 1.0)
        trade_filled = int(trade_pct * 15)
        trade_bar = f"[{COLOR_UP}]" + "█" * trade_filled + "░" * (15 - trade_filled) + f"[/{COLOR_UP}]"
        
        return (
            f"Track: {track_bar} {self.track_threshold:.2f}%  │  "
            f"Trade: {trade_bar} {self.trade_threshold:.2f}%"
        )
    
    def update_threshold_bar(self) -> None:
        """Update the threshold display."""
        try:
            bar = self.query_one("#threshold-bar", Static)
            bar.update(self._render_threshold_content())
        except Exception:
            pass  # Widget not ready
    
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
