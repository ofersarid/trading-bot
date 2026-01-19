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
        tokens_used: int = 0,
        ai_calls: int = 0,
        disconnects: int = 0,
        reconnects: int = 0,
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
        """
        try:
            title = self.query_one("#ai-title", Static)

            # Connection stats
            conn_info = ""
            if disconnects > 0:
                conn_info = f" [dim]│[/dim] [yellow]Reconn: {reconnects}[/yellow] [dim]│[/dim] [red]Disc: {disconnects}[/red]"

            if analysis_mode == "RULE-BASED":
                title.update(
                    f"🧠 ANALYSIS [dim]│[/dim] [yellow]📐 {analysis_mode}[/yellow] [dim]│[/dim] "
                    f"Model: [cyan]{ai_model}[/cyan]{conn_info}"
                )
            elif "Local" in analysis_mode:
                # Local AI mode (Ollama)
                title.update(
                    f"🧠 AI REASONING [dim]│[/dim] [#44ffaa]🤖 LOCAL AI[/#44ffaa] [dim]│[/dim] "
                    f"Model: [cyan]{ai_model}[/cyan] [dim]│[/dim] "
                    f"Tokens: [magenta]{tokens_used:,}[/magenta] [dim]│[/dim] "
                    f"Calls: [blue]{ai_calls}[/blue]{conn_info}"
                )
            else:
                title.update(
                    f"🧠 AI REASONING [dim]│[/dim] [#44ffaa]🤖 {analysis_mode}[/#44ffaa] [dim]│[/dim] "
                    f"Model: [cyan]{ai_model}[/cyan] [dim]│[/dim] "
                    f"Tokens: [magenta]{tokens_used:,}[/magenta] [dim]│[/dim] "
                    f"Calls: [blue]{ai_calls}[/blue]{conn_info}"
                )
        except Exception as e:
            logger.debug(f"AI title not ready: {e}")
