"""
AI reasoning panel component.

Displays AI/analysis reasoning log with auto-scroll.
"""

import logging
from collections import deque
from datetime import datetime

from rich.table import Table
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, ScrollableContainer
from textual.widgets import Static

logger = logging.getLogger("ai_panel")


class AIPanel(Container):
    """Panel displaying AI reasoning and analysis log."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Store tuples of (timestamp, message) for table rendering
        self.messages: deque[tuple[str, str]] = deque(maxlen=100)
        self._title_widget: Static | None = None

    def compose(self) -> ComposeResult:
        yield Static("🧠 AI REASONING", classes="panel-title", id="ai-title")
        with ScrollableContainer(id="ai-scroll", classes="panel-content"):
            yield Static("", id="ai-content")

    def log(self, message: str, with_timestamp: bool = True) -> None:
        """
        Log a message to the AI panel.

        Args:
            message: Message with optional Rich markup
            with_timestamp: Whether to prepend timestamp (default True)
        """
        if with_timestamp:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.messages.append((timestamp, message))
        else:
            self.messages.append(("", message))

        self._refresh_display()

    def log_block(self, lines: list[str]) -> None:
        """
        Log a multi-line block with a single timestamp on the first line.

        Args:
            lines: List of message lines (first gets timestamp, rest are indented)
        """
        if not lines:
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        self.messages.append((timestamp, lines[0]))

        for line in lines[1:]:
            self.messages.append(("", line))

        self._refresh_display()

    def _build_table(self) -> Table:
        """Build a Rich Table from the messages."""
        table = Table(
            show_header=False,
            show_edge=False,
            box=None,
            padding=(0, 1),
            expand=True,
        )
        table.add_column("Time", style="dim", width=8, no_wrap=True)
        table.add_column("Message", ratio=1)

        for timestamp, message in self.messages:
            table.add_row(timestamp, Text.from_markup(message))

        return table

    def _refresh_display(self) -> None:
        """Refresh the panel display."""
        try:
            content = self.query_one("#ai-content", Static)
            content.update(self._build_table())
            # Auto-scroll to bottom
            scroll = self.query_one("#ai-scroll", ScrollableContainer)
            scroll.scroll_end(animate=False)
        except Exception as e:
            logger.debug(f"AI panel not ready: {e}")

    def update_title(
        self,
        analysis_mode: str,
        ai_model: str,
        _tokens_used: int = 0,
        ai_calls: int = 0,
        disconnects: int = 0,
        reconnects: int = 0,
        scalper_age: float | None = None,
    ) -> None:
        """
        Update the AI panel title with mode and stats.

        Args:
            analysis_mode: Current analysis mode ("RULE-BASED" or "AI (Claude)")
            ai_model: Name of the AI model in use
            tokens_used: Total tokens consumed
            ai_calls: Number of AI API calls made
            disconnects: Total WebSocket disconnects
            reconnects: Successful reconnection count
            scalper_age: Seconds since last scalper interpretation (optional)
        """
        try:
            title = self.query_one("#ai-title", Static)

            # Connection stats
            conn_info = ""
            if disconnects > 0:
                conn_info = f" [dim]│[/dim] [yellow]Reconn: {reconnects}[/yellow] [dim]│[/dim] [red]Disc: {disconnects}[/red]"

            # Scalper staleness indicator
            scalper_info = ""
            if scalper_age is not None:
                if scalper_age > 30:
                    scalper_info = f" [dim]│[/dim] [red]Scalper: {scalper_age:.0f}s ago[/red]"
                elif scalper_age > 20:
                    scalper_info = f" [dim]│[/dim] [yellow]Scalper: {scalper_age:.0f}s ago[/yellow]"
                else:
                    scalper_info = (
                        f" [dim]│[/dim] [#44ffaa]Scalper: {scalper_age:.0f}s ago[/#44ffaa]"
                    )

            if analysis_mode == "RULE-BASED":
                title.update(
                    f"🧠 ANALYSIS [dim]│[/dim] [yellow]📐 {analysis_mode}[/yellow] [dim]│[/dim] "
                    f"Model: [cyan]{ai_model}[/cyan]{scalper_info}{conn_info}"
                )
            elif "Local" in analysis_mode:
                # Local AI mode (Ollama)
                title.update(
                    f"🧠 AI REASONING [dim]│[/dim] [#44ffaa]🤖 LOCAL AI[/#44ffaa] [dim]│[/dim] "
                    f"Model: [cyan]{ai_model}[/cyan] [dim]│[/dim] "
                    f"Calls: [blue]{ai_calls}[/blue]{scalper_info}{conn_info}"
                )
            else:
                title.update(
                    f"🧠 AI REASONING [dim]│[/dim] [#44ffaa]🤖 {analysis_mode}[/#44ffaa] [dim]│[/dim] "
                    f"Model: [cyan]{ai_model}[/cyan] [dim]│[/dim] "
                    f"Calls: [blue]{ai_calls}[/blue]{scalper_info}{conn_info}"
                )
        except Exception as e:
            logger.debug(f"AI title not ready: {e}")

    def log_scalper_interpretation(
        self,
        coin: str,
        momentum: int,
        pressure: int,
        prediction: int,
        freshness: str,
        action: str,
        confidence: int,
        reason: str,
        response_time_ms: float,
    ) -> None:
        """
        Log a scalper interpretation with visual formatting.

        Args:
            coin: Coin symbol
            momentum: AI-interpreted momentum (0-100)
            pressure: AI-interpreted pressure (0-100, 50=neutral)
            prediction: Continuation probability (0-100)
            freshness: FRESH/DEVELOPING/EXTENDED/EXHAUSTED
            action: NONE/LONG/SHORT/EXIT
            confidence: Confidence level (1-10)
            reason: Scalper's reasoning
            response_time_ms: AI response time
        """

        # Color helpers
        def metric_color(val: int, neutral: int = 50) -> str:
            if val >= neutral + 10:
                return "#44ffaa"
            elif val <= neutral - 10:
                return "#ff7777"
            return "yellow"

        freshness_colors = {
            "FRESH": "#44ffaa",
            "DEVELOPING": "yellow",
            "EXTENDED": "orange1",
            "EXHAUSTED": "#ff7777",
        }

        action_colors = {
            "LONG": "#44ffaa",
            "SHORT": "#ff7777",
            "EXIT": "orange1",
            "NONE": "dim",
        }

        mom_color = metric_color(momentum)
        press_color = metric_color(pressure)
        pred_color = metric_color(prediction)
        fresh_color = freshness_colors.get(freshness, "white")
        act_color = action_colors.get(action, "white")

        lines = [
            f"[cyan]━━━ 🎯 SCALPER: {coin} ━━━[/cyan]",
            f"[bold]Mom:[/bold] [{mom_color}]{momentum}[/{mom_color}] "
            f"[bold]Press:[/bold] [{press_color}]{pressure}[/{press_color}] "
            f"[bold]Pred:[/bold] [{pred_color}]{prediction}%[/{pred_color}]",
            f"[bold]Setup:[/bold] [{fresh_color}]{freshness}[/{fresh_color}] "
            f"[bold]Action:[/bold] [{act_color}]{action}[/{act_color}] "
            f"[bold]Conf:[/bold] {confidence}/10",
            f"[dim]{reason}[/dim]",
            f"[dim]⚡ {response_time_ms:.0f}ms[/dim]",
        ]

        self.log_block(lines)
