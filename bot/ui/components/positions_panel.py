"""
Positions panel component.

Displays open trading positions with P&L.
"""

from textual.containers import Container, ScrollableContainer
from textual.widgets import Static
from textual.app import ComposeResult

from bot.simulation.models import Side


# Theme colors (Rich markup)
COLOR_UP = "#44ffaa"
COLOR_DOWN = "#ff7777"


class PositionsPanel(Container):
    """Panel displaying open trading positions."""
    
    def compose(self) -> ComposeResult:
        yield Static("📌 OPEN POSITIONS", classes="panel-title")
        with ScrollableContainer(id="positions-scroll", classes="panel-content"):
            yield Static("", id="positions-content")
    
    def update_display(self, positions: dict, prices: dict[str, float]) -> None:
        """
        Update the positions display.
        
        Args:
            positions: Dictionary of Position objects by coin
            prices: Current prices by coin for P&L calculation
        """
        lines = []
        
        if not positions:
            lines.append("[dim]No open positions[/dim]")
        else:
            for coin, pos in positions.items():
                price = prices.get(coin, pos.entry_price)
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
