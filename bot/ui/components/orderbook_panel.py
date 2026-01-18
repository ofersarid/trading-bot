"""
Order book panel component.

Displays bid/ask levels for tracked coins.
"""

from textual.containers import Container, ScrollableContainer
from textual.widgets import Static
from textual.app import ComposeResult


# Theme colors (Rich markup)
COLOR_UP = "#44ffaa"
COLOR_DOWN = "#ff7777"


class OrderBookPanel(Container):
    """Panel displaying order book depth for tracked coins."""
    
    def __init__(self, coins: list[str], **kwargs):
        super().__init__(**kwargs)
        self.coins = coins
    
    def compose(self) -> ComposeResult:
        yield Static("📈 ORDER BOOK", classes="panel-title")
        with ScrollableContainer(id="orderbook-scroll", classes="panel-content"):
            yield Static("", id="orderbook-content")
    
    def update_display(self, orderbook: dict[str, dict]) -> None:
        """
        Update the order book display.
        
        Args:
            orderbook: Order book data by coin, each with 'bids' and 'asks' lists
        """
        lines = []
        
        for i, coin in enumerate(self.coins):
            book = orderbook.get(coin, {"bids": [], "asks": []})
            
            if i > 0:
                lines.append("")  # Separator between coins
            
            # Coin header
            lines.append(f"[bold cyan]{coin}[/bold cyan]")
            
            # Asks (reversed so lowest is at bottom, near spread)
            for ask in reversed(book["asks"][:3]):
                px = float(ask.get("px", 0))
                sz = float(ask.get("sz", 0))
                lines.append(f"  [{COLOR_DOWN}]${px:>10,.2f}  {sz:>8.4f}[/{COLOR_DOWN}]")
            
            # Spread line
            lines.append("  [dim]────────────────────[/dim]")
            
            # Bids
            for bid in book["bids"][:3]:
                px = float(bid.get("px", 0))
                sz = float(bid.get("sz", 0))
                lines.append(f"  [{COLOR_UP}]${px:>10,.2f}  {sz:>8.4f}[/{COLOR_UP}]")
        
        content = self.query_one("#orderbook-content", Static)
        content.update("\n".join(lines))
