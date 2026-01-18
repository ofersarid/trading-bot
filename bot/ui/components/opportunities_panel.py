"""
Opportunities panel component.

Displays pending trading opportunities with condition validation status.
"""

from textual.containers import Container, ScrollableContainer
from textual.widgets import Static
from textual.app import ComposeResult

from bot.core.models import PendingOpportunity


# Theme colors (Rich markup)
COLOR_UP = "#44ffaa"
COLOR_DOWN = "#ff7777"


class OpportunitiesPanel(Container):
    """Panel displaying pending trading opportunities."""
    
    def compose(self) -> ComposeResult:
        yield Static("🎯 OPPORTUNITIES IN PROGRESS", classes="panel-title")
        with ScrollableContainer(id="opportunities-scroll", classes="panel-content"):
            yield Static("", id="opportunities-content")
    
    def update_display(self, opportunities: dict[str, PendingOpportunity]) -> None:
        """
        Update the opportunities display.
        
        Args:
            opportunities: Dictionary of pending opportunities by coin
        """
        lines = []
        
        if not opportunities:
            lines.append("[dim]No opportunities being analyzed...[/dim]")
        else:
            for coin, opp in opportunities.items():
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
