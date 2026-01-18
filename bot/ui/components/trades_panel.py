"""
Live trades panel component.

Displays recent market trades grouped by coin.
"""

from collections import deque
from datetime import datetime

from textual.containers import Container, ScrollableContainer
from textual.widgets import Static
from textual.app import ComposeResult


# Theme colors (Rich markup)
COLOR_UP = "#44ffaa"
COLOR_DOWN = "#ff7777"


class TradesPanel(Container):
    """Panel displaying recent market trades."""
    
    def __init__(self, coins: list[str], **kwargs):
        super().__init__(**kwargs)
        self.coins = coins
    
    def compose(self) -> ComposeResult:
        yield Static("🔄 LIVE TRADES", classes="panel-title")
        with ScrollableContainer(id="trades-scroll", classes="panel-content"):
            yield Static("", id="trades-content")
    
    def update_display(self, trades: deque) -> None:
        """
        Update the trades display.
        
        Args:
            trades: Deque of trade dictionaries with time, coin, side, size, price
        """
        now = datetime.now()
        
        # Group trades by coin (only last 60 seconds)
        trades_by_coin: dict[str, list] = {coin: [] for coin in self.coins}
        for trade in list(trades):
            age = (now - trade["time"]).total_seconds()
            if age > 60:
                continue
            coin = trade["coin"]
            if coin in trades_by_coin:
                trades_by_coin[coin].append(trade)
        
        # Build display
        lines = []
        for i, coin in enumerate(self.coins):
            coin_trades = trades_by_coin[coin]
            
            if i > 0:
                lines.append("")  # Separator
            
            lines.append(f"[bold cyan]{coin}[/bold cyan]")
            
            if not coin_trades:
                lines.append("  [dim]No recent trades[/dim]")
            else:
                # Show most recent trades (up to 6 per coin)
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
