"""
Goal progress panel component.

Displays account goal tracking that drives AI position sizing decisions:
- Progress toward target balance
- Time elapsed vs remaining
- Pace status (ahead, on_pace, behind)
- AI position multiplier from last decision
"""

from dataclasses import dataclass

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static

# Theme colors (Rich markup)
COLOR_UP = "#44ffaa"
COLOR_DOWN = "#ff7777"
COLOR_WARNING = "#ffaa44"
COLOR_NEUTRAL = "#ffff44"
COLOR_DIM = "#666666"


@dataclass
class GoalData:
    """All data needed to display goal progress."""

    initial_balance: float
    current_balance: float
    target_balance: float | None = None
    goal_timeframe_days: int | None = None
    days_elapsed: int = 0
    goal_progress_pct: float | None = None
    time_progress_pct: float | None = None
    pace_status: str = "no_goal"
    required_daily_return_pct: float | None = None
    ai_multiplier: float = 1.0

    @property
    def has_goal(self) -> bool:
        """Whether a goal is configured."""
        return self.target_balance is not None and self.goal_timeframe_days is not None

    @property
    def days_remaining(self) -> int | None:
        """Days remaining to reach goal."""
        if self.goal_timeframe_days is None:
            return None
        return max(0, self.goal_timeframe_days - self.days_elapsed)

    @property
    def progress_dollars(self) -> float:
        """Dollar progress toward goal."""
        return self.current_balance - self.initial_balance


class GoalPanel(Container):
    """Panel displaying goal progress and AI position sizing context."""

    DEFAULT_CSS = """
    GoalPanel {
        height: auto;
        padding: 0 1;
        background: #0a0a0a;
        border-bottom: solid #333333;
    }

    GoalPanel .goal-content {
        height: auto;
    }
    """

    # Progress bar width (total characters)
    BAR_WIDTH = 50

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._data: GoalData | None = None

    def compose(self) -> ComposeResult:
        yield Static("", id="goal-content", classes="goal-content")

    def update(self, data: GoalData) -> None:
        """Update the goal panel with new data."""
        self._data = data
        self._refresh_display()

    def _refresh_display(self) -> None:
        """Refresh the panel display."""
        try:
            content = self.query_one("#goal-content", Static)

            if self._data is None or not self._data.has_goal:
                content.update(self._format_no_goal())
            else:
                content.update(self._format_goal())
        except Exception:
            pass

    def _format_no_goal(self) -> Text:
        """Format display when no goal is set."""
        return Text.from_markup(
            f"[{COLOR_DIM}]🎯 No trading goal configured. "
            "Set a goal in session config to enable AI position sizing adjustments.[/{COLOR_DIM}]"
        )

    def _format_goal(self) -> Text:
        """Format the full goal display with progress bar."""
        if self._data is None:
            return Text()

        data = self._data

        # Build the display lines
        lines: list[str] = []

        # Line 1: Goal summary and day info
        lines.append(self._format_header_line(data))

        # Line 2: Progress bar
        lines.append(self._format_progress_bar(data))

        # Line 3: Stats and AI multiplier
        lines.append(self._format_stats_line(data))

        return Text.from_markup("\n".join(lines))

    def _format_header_line(self, data: GoalData) -> str:
        """Format: 🎯 $10,000 → $15,000 (30 days)    Day 16 of 30"""
        goal_str = (
            f"🎯 ${data.initial_balance:,.0f} → ${data.target_balance:,.0f} "
            f"({data.goal_timeframe_days} days)"
        )

        day_str = f"Day {data.days_elapsed} of {data.goal_timeframe_days}"

        # Pad to align right
        padding = max(0, 70 - len(goal_str) - len(day_str))
        return f"{goal_str}{' ' * padding}[dim]{day_str}[/dim]"

    def _format_progress_bar(self, data: GoalData) -> str:
        """
        Format dual progress bar showing goal progress vs time progress.

        Progress fills from left, time marker shows as vertical line.
        """
        goal_pct = data.goal_progress_pct or 0.0
        time_pct = data.time_progress_pct or 0.0

        # Clamp percentages
        goal_pct = max(0.0, min(100.0, goal_pct))
        time_pct = max(0.0, min(100.0, time_pct))

        # Calculate bar positions
        goal_filled = int((goal_pct / 100.0) * self.BAR_WIDTH)
        time_marker_pos = int((time_pct / 100.0) * self.BAR_WIDTH)

        # Choose fill color based on pace status
        fill_color = self._get_pace_color(data.pace_status)

        # Build bar character by character
        bar_chars: list[str] = []
        for i in range(self.BAR_WIDTH):
            if i == time_marker_pos:
                # Time marker (white vertical line)
                bar_chars.append("[white bold]│[/white bold]")
            elif i < goal_filled:
                # Filled portion
                bar_chars.append(f"[{fill_color}]█[/{fill_color}]")
            else:
                # Empty portion
                bar_chars.append(f"[{COLOR_DIM}]░[/{COLOR_DIM}]")

        return "".join(bar_chars)

    def _format_stats_line(self, data: GoalData) -> str:
        """
        Format stats line with progress, time, status, and AI multiplier.

        Format: Progress: 42% ($2,100)  │  Time: 53%  Status: BEHIND 🔶
                Required: +1.82%/day    AI Multiplier: 1.5x (aggressive)
        """
        pace_color = self._get_pace_color(data.pace_status)
        pace_icon = self._get_pace_icon(data.pace_status)
        multiplier_label = self._get_multiplier_label(data.ai_multiplier)
        multiplier_color = self._get_multiplier_color(data.ai_multiplier)

        # First row of stats
        progress_str = f"Progress: {data.goal_progress_pct or 0:.0f}%"
        dollars_str = f"(${data.progress_dollars:+,.0f})"
        time_str = f"Time: {data.time_progress_pct or 0:.0f}%"
        status_str = f"[{pace_color}]{data.pace_status.upper()} {pace_icon}[/{pace_color}]"

        line1 = (
            f"{progress_str} [dim]{dollars_str}[/dim]  [dim]│[/dim]  "
            f"{time_str}  [dim]│[/dim]  Status: {status_str}"
        )

        # Second row of stats
        if data.required_daily_return_pct is not None:
            req_str = f"Required: [cyan]+{data.required_daily_return_pct:.2f}%/day[/cyan]"
        else:
            req_str = f"[{COLOR_DIM}]Required: —[/{COLOR_DIM}]"

        mult_str = f"🤖 [{multiplier_color}]{data.ai_multiplier:.1f}x ({multiplier_label})[/{multiplier_color}]"

        line2 = f"{req_str}        {mult_str}"

        return f"{line1}\n{line2}"

    def _get_pace_color(self, pace_status: str) -> str:
        """Get color for pace status."""
        colors = {
            "goal_reached": COLOR_UP,
            "ahead": COLOR_UP,
            "on_pace": COLOR_NEUTRAL,
            "behind": COLOR_WARNING,
            "just_started": COLOR_DIM,
            "no_goal": COLOR_DIM,
        }
        return colors.get(pace_status, COLOR_DIM)

    def _get_pace_icon(self, pace_status: str) -> str:
        """Get icon for pace status."""
        icons = {
            "goal_reached": "🟢",
            "ahead": "🟢",
            "on_pace": "🟡",
            "behind": "🔶",
            "just_started": "⚪",
            "no_goal": "⚪",
        }
        return icons.get(pace_status, "⚪")

    def _get_multiplier_label(self, multiplier: float) -> str:
        """Get label for AI multiplier."""
        if multiplier >= 1.5:
            return "aggressive"
        elif multiplier >= 1.2:
            return "elevated"
        elif multiplier >= 0.8:
            return "standard"
        else:
            return "conservative"

    def _get_multiplier_color(self, multiplier: float) -> str:
        """Get color for AI multiplier."""
        if multiplier >= 1.5:
            return COLOR_WARNING  # Orange for aggressive
        elif multiplier >= 1.2:
            return COLOR_NEUTRAL  # Yellow for elevated
        elif multiplier >= 0.8:
            return "white"  # White for standard
        else:
            return "cyan"  # Cyan for conservative
