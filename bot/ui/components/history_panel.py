"""
Trade history panel component.

Displays completed trades with P&L results.
"""

from textual.app import ComposeResult
from textual.containers import Container, ScrollableContainer
from textual.widgets import Static

from bot.simulation.models import Side

# Theme colors (Rich markup)
COLOR_UP = "#44ffaa"
COLOR_DOWN = "#ff7777"


class HistoryPanel(Container):
    """Panel displaying trade history."""

    def compose(self) -> ComposeResult:
        yield Static("📜 TRADE HISTORY", classes="panel-title")
        with ScrollableContainer(id="history-scroll", classes="panel-content"):
            yield Static("", id="history-content")

    def update_display(self, trade_history: list) -> None:
        """
        Update the history display.

        Args:
            trade_history: List of completed Trade objects
        """
        lines = []

        if not trade_history:
            lines.append("[dim]No completed trades[/dim]")
        else:
            # Show last 20 trades, most recent first
            for trade in reversed(trade_history[-20:]):
                emoji = "✅" if trade.pnl > 0 else "❌"
                color = COLOR_UP if trade.pnl > 0 else COLOR_DOWN
                side = "LONG" if trade.side == Side.LONG else "SHORT"

                lines.append(
                    f"{emoji} [{color}]{side} {trade.coin}: "
                    f"${trade.pnl:+,.2f} ({trade.pnl_percent:+.2f}%)[/{color}]"
                )

        content = self.query_one("#history-content", Static)
        content.update("\n".join(lines))
