"""
Prices panel component.

Displays live prices with tick direction and momentum indicators.
"""

from collections import deque

from textual.containers import Container, ScrollableContainer
from textual.widgets import Static
from textual.app import ComposeResult

from bot.core.config import TradingConfig
from bot.core.analysis import calculate_momentum


# Theme colors (Rich markup)
COLOR_UP = "#44ffaa"
COLOR_DOWN = "#ff7777"


class PricesPanel(Container):
    """Panel displaying prices and momentum for tracked coins."""
    
    def __init__(
        self,
        coins: list[str],
        config: TradingConfig,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.coins = coins
        self.config = config
        self.prev_prices: dict[str, float] = {}
    
    def compose(self) -> ComposeResult:
        yield Static("💰 PRICES & MOMENTUM", classes="panel-title")
        with ScrollableContainer(id="prices-scroll", classes="panel-content"):
            yield Static("", id="prices-content")
    
    def update_display(
        self,
        prices: dict[str, float],
        price_history: dict[str, deque],
        momentum_timeframe: int,
    ) -> None:
        """
        Update the prices display.
        
        Args:
            prices: Current prices by coin
            price_history: Price history deques by coin
            momentum_timeframe: Lookback period for momentum in seconds
        """
        lines = []
        
        # Header
        lines.append(f"[dim]{'COIN':<5}   {'PRICE':>13}    {'TICK':^4}    {momentum_timeframe}s MOMENTUM[/dim]")
        lines.append("[dim]─────────────────────────────────────────────────────[/dim]")
        
        for coin in self.coins:
            price = prices.get(coin, 0)
            prev = self.prev_prices.get(coin, price)
            change = price - prev
            
            # Tick direction
            if change > 0:
                tick_color = COLOR_UP
                tick_arrow = "▲"
            elif change < 0:
                tick_color = COLOR_DOWN
                tick_arrow = "▼"
            else:
                tick_color = "white"
                tick_arrow = "─"
            
            # Momentum indicator
            history = price_history.get(coin)
            momentum = calculate_momentum(price, history, momentum_timeframe) if history else None
            
            if momentum is not None:
                momentum_str = self._format_momentum(momentum)
            else:
                momentum_str = "[dim]building...[/dim]"
            
            # Format price
            price_str = f"${price:>12,.2f}"
            
            # Build line
            lines.append(
                f"[bold]{coin:<5}[/bold]   "
                f"{price_str}    "
                f"[{tick_color}]{tick_arrow:^4}[/{tick_color}]    "
                f"{momentum_str}"
            )
            
            self.prev_prices[coin] = price
        
        content = self.query_one("#prices-content", Static)
        content.update("\n".join(lines))
    
    def _format_momentum(self, momentum: float) -> str:
        """Format momentum value with color and label."""
        abs_mom = abs(momentum)
        cfg = self.config
        
        if abs_mom < cfg.momentum_flat_threshold:
            label = "flat"
            color = "dim"
        elif abs_mom < cfg.momentum_weak_threshold:
            label = "weak"
            color = COLOR_UP if momentum > 0 else COLOR_DOWN
        elif abs_mom < cfg.momentum_strong_threshold:
            label = "strong"
            color = COLOR_UP if momentum > 0 else COLOR_DOWN
        else:
            label = "aggro"
            color = COLOR_UP if momentum > 0 else COLOR_DOWN
        
        return f"[{color}]{momentum:+.2f}% {label}[/{color}]"
