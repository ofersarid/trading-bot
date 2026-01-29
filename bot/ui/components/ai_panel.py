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
        scalper_age: float | None = None,  # noqa: ARG002 - deprecated, kept for compatibility
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
            scalper_age: DEPRECATED - no longer used
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
                    f"Calls: [blue]{ai_calls}[/blue]{conn_info}"
                )
            else:
                title.update(
                    f"🧠 AI REASONING [dim]│[/dim] [#44ffaa]🤖 {analysis_mode}[/#44ffaa] [dim]│[/dim] "
                    f"Model: [cyan]{ai_model}[/cyan] [dim]│[/dim] "
                    f"Calls: [blue]{ai_calls}[/blue]{conn_info}"
                )
        except Exception as e:
            logger.debug(f"AI title not ready: {e}")

    def log_sizing_decision(
        self,
        coin: str,
        direction: str,
        signal_score: float,
        threshold: float,
        goal_progress_pct: float | None,
        time_progress_pct: float | None,
        pace_status: str,
        position_multiplier: float,
        base_size_pct: float,
        actual_size_pct: float,
        reason: str,
        response_time_ms: float,
    ) -> None:
        """
        Log an AI sizing decision with goal context.

        This is the new signal-based logging format that shows:
        - Signal score vs threshold
        - Goal progress context
        - AI position sizing decision

        Args:
            coin: Coin symbol
            direction: LONG or SHORT
            signal_score: Weighted score from signals
            threshold: Strategy threshold
            goal_progress_pct: Progress toward goal (if set)
            time_progress_pct: Time elapsed percentage (if set)
            pace_status: ahead/on_pace/behind/goal_reached/no_goal
            position_multiplier: AI's sizing multiplier (0.5 - 2.0)
            base_size_pct: Base position size percentage
            actual_size_pct: Final position size after multiplier
            reason: AI's reasoning for the decision
            response_time_ms: AI response time
        """
        # Direction color
        dir_color = "#44ffaa" if direction == "LONG" else "#ff7777"

        # Signal threshold check
        signal_check = "✓" if signal_score >= threshold else "✗"
        signal_color = "#44ffaa" if signal_score >= threshold else "#ff7777"

        # Pace status color and icon
        pace_colors = {
            "goal_reached": "#44ffaa",
            "ahead": "#44ffaa",
            "on_pace": "yellow",
            "behind": "orange1",
            "just_started": "dim",
            "no_goal": "dim",
        }
        pace_color = pace_colors.get(pace_status, "dim")

        # Multiplier color
        if position_multiplier >= 1.5:
            mult_color = "orange1"
            mult_label = "aggressive"
        elif position_multiplier >= 1.2:
            mult_color = "yellow"
            mult_label = "elevated"
        elif position_multiplier >= 0.8:
            mult_color = "white"
            mult_label = "standard"
        else:
            mult_color = "cyan"
            mult_label = "conservative"

        # Build log lines
        lines = [
            "[cyan]━━━ 🤖 AI SIZING DECISION ━━━[/cyan]",
            f"Direction: [{dir_color}]{direction} {coin}[/{dir_color}] (from signals)",
            f"Signal Score: [{signal_color}]{signal_score:.2f}[/{signal_color}] "
            f"(threshold: {threshold:.2f}) [{signal_color}]{signal_check}[/{signal_color}]",
        ]

        # Add goal context if available
        if goal_progress_pct is not None and time_progress_pct is not None:
            lines.append("")
            lines.append("[bold]🎯 GOAL CONTEXT:[/bold]")
            lines.append(
                f"Progress: {goal_progress_pct:.0f}% │ Time: {time_progress_pct:.0f}% │ "
                f"Status: [{pace_color}]{pace_status.upper()}[/{pace_color}]"
            )

        lines.append("")
        lines.append("[bold]POSITION SIZING:[/bold]")
        lines.append(
            f"Multiplier: [{mult_color}]{position_multiplier:.1f}x ({mult_label})[/{mult_color}]"
        )
        lines.append(f"Base: {base_size_pct:.0f}% → Actual: {actual_size_pct:.0f}%")
        lines.append("")
        lines.append(f'[dim]Reason: "{reason}"[/dim]')
        lines.append(f"[dim]⚡ {response_time_ms:.0f}ms[/dim]")

        self.log_block(lines)
