"""
Indicator sub-column component.

Displays values and signal for a single indicator type within a market column.
"""

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static


class IndicatorSubColumn(Container):
    """Sub-column showing one indicator's values and signal."""

    TITLES: dict[str, str] = {
        "session_vp": "SESS VP",
        "prev_day_vp": "PREV VP",
        "momentum": "MOM",
        "rsi": "RSI",
        "macd": "MACD",
    }

    TOOLTIPS: dict[str, str] = {
        "session_vp": (
            "Session Volume Profile - Current trading day\n\n"
            "SIGNAL TRIGGERS:\n"
            "🔵 LONG:\n"
            "  • Failed Auction: Price rejects below VAL, closes back inside\n"
            "  • Breakout: 3+ candles close above VAH (acceptance)\n"
            "  • POC Bounce: Price touches POC level and closes above it\n"
            "🔴 SHORT:\n"
            "  • Failed Auction: Price rejects above VAH, closes back inside\n"
            "  • Breakout: 3+ candles close below VAL (acceptance)\n"
            "  • POC Bounce: Price touches POC level and closes below it\n\n"
            "Key Levels:\n"
            "  • POC: Price with highest volume (price magnet)\n"
            "  • VAH/VAL: 70% volume range (acceptance/rejection zones)\n"
            "  • LVN: Low volume nodes (weak support/resistance)"
        ),
        "prev_day_vp": (
            "Previous Day Volume Profile - Support/Resistance Levels\n\n"
            "SIGNAL TRIGGERS:\n"
            "🔵 LONG:\n"
            "  • Opening Drive: Gap open above VAH, continues higher\n"
            "  • VAL Rejection: Price rejects from previous VAL (support)\n"
            "  • POC Test (Bullish): Price tests POC from below, bounces up\n"
            "  • VA Reclaim: Re-entering VA from below (acceptance)\n"
            "🔴 SHORT:\n"
            "  • Opening Drive: Gap open below VAL, continues lower\n"
            "  • VAH Rejection: Price rejects from previous VAH (resistance)\n"
            "  • POC Test (Bearish): Price tests POC from above, rejects down\n"
            "  • VA Reclaim: Re-entering VA from above (rejection)\n\n"
            "Key Levels:\n"
            "  • POC: Price magnet (highest volume level from yesterday)\n"
            "  • VAH: Resistance if trading below it\n"
            "  • VAL: Support if trading above it"
        ),
        "momentum": (
            "EMA Crossover Momentum (9/21 periods)\n\n"
            "SIGNAL TRIGGERS:\n"
            "🔵 LONG: Fast EMA (9) crosses above Slow EMA (21)\n"
            "🔴 SHORT: Fast EMA (9) crosses below Slow EMA (21)\n"
            "⚪ WAIT: No crossover detected\n\n"
            "Shows: 1-minute momentum change percentage"
        ),
        "rsi": (
            "Relative Strength Index (14 periods)\n\n"
            "SIGNAL TRIGGERS:\n"
            "🔵 LONG: RSI < 30 (oversold) + divergence with price\n"
            "🔴 SHORT: RSI > 70 (overbought) + divergence with price\n"
            "⚪ WAIT: RSI 30-70 (neutral)\n\n"
            "Divergence signals weighted higher than extremes"
        ),
        "macd": (
            "MACD (12/26/9 periods)\n\n"
            "SIGNAL TRIGGERS:\n"
            "🔵 LONG: MACD line crosses above signal line\n"
            "🔴 SHORT: MACD line crosses below signal line\n"
            "⚪ WAIT: No crossover\n\n"
            "Shows: MACD line and signal line values"
        ),
    }

    def __init__(self, coin: str, indicator_type: str, strategy=None, **kwargs) -> None:
        """
        Initialize the indicator sub-column.

        Args:
            coin: Coin symbol (BTC, ETH, SOL)
            indicator_type: Type of indicator (session_vp, prev_day_vp, momentum, rsi, macd)
            strategy: Strategy object for displaying weights
        """
        super().__init__(**kwargs)
        self.coin = coin
        self.indicator_type = indicator_type
        self.strategy = strategy
        self._values_widget: Static | None = None
        self._progress_widget: Static | None = None
        self._long_progress: float = 0.0  # 0-1 for LONG signal building
        self._short_progress: float = 0.0  # 0-1 for SHORT signal building

    def compose(self) -> ComposeResult:
        title = self.TITLES.get(self.indicator_type, self.indicator_type.upper())
        tooltip = self.TOOLTIPS.get(self.indicator_type, "")

        # Add weight if strategy is provided
        if self.strategy:
            from bot.signals.base import SignalType

            weight_map = {
                "session_vp": SignalType.VOLUME_PROFILE,
                "prev_day_vp": SignalType.VOLUME_PROFILE,
                "momentum": SignalType.MOMENTUM,
                "rsi": SignalType.RSI,
                "macd": SignalType.MACD,
            }
            signal_type = weight_map.get(self.indicator_type)
            if signal_type:
                weight = self.strategy.signal_weights.get(signal_type, 0.0)
                weight_str = f"{weight:.1f}" if weight > 0 else "---"
                title = f"{title} {weight_str}"

        title_widget = Static(title, classes="subcolumn-title")
        title_widget.tooltip = tooltip
        yield title_widget

        self._values_widget = Static("--", classes="subcolumn-values")
        yield self._values_widget
        # Progress meter - will be sized dynamically on mount
        self._progress_widget = Static("", classes="subcolumn-progress")
        yield self._progress_widget

    def on_mount(self) -> None:
        """Render initial progress bar after mount when size is known."""
        self._render_progress_bar()

    def on_resize(self) -> None:
        """Re-render progress bar when resized."""
        self._render_progress_bar()

    def update_values(self, values_text: str) -> None:
        """
        Update the indicator values display.

        Args:
            values_text: Formatted text showing indicator values (e.g., "POC 99200\\nVAH 99800")
        """
        if self._values_widget:
            self._values_widget.update(values_text)

    def update_signal(self, signal_text: str) -> None:
        """Update signal - deprecated, kept for compatibility."""
        pass  # Signal now shown via progress meter

    def update_signal_progress(
        self, long_strength: float = 0.0, short_strength: float = 0.0
    ) -> None:
        """
        Update the signal progress meter (cooking indicator).

        Single meter: SHORT builds left (red), LONG builds right (green).
        Only one direction can be active at a time.

        Args:
            long_strength: LONG signal strength 0-1
            short_strength: SHORT signal strength 0-1
        """
        self._long_progress = max(0, min(1, long_strength))
        self._short_progress = max(0, min(1, short_strength))
        self._render_progress_bar()

    def _render_progress_bar(self) -> None:
        """Render visual progress meter - single bar from center, filling available width."""
        if not self._progress_widget:
            return

        # Get available width (fallback to 24 if not mounted yet)
        try:
            available_width = self._progress_widget.size.width
            if available_width < 10:
                available_width = 24  # Fallback
        except Exception:
            available_width = 24

        # Calculate bar width: total - "S " (2) - "│" (1) - " L" (2) = 5 chars for labels
        bar_total = available_width - 5
        half_width = max(3, bar_total // 2)  # At least 3 chars per side

        short_bars = int(self._short_progress * half_width)
        long_bars = int(self._long_progress * half_width)

        # Build left side (SHORT) - red filled, dim empty
        short_empty = "[dim]" + "░" * (half_width - short_bars) + "[/dim]"
        short_filled = "[red]" + "█" * short_bars + "[/red]"
        left_side = f"{short_empty}{short_filled}"

        # Build right side (LONG) - green filled, dim empty
        long_filled = "[green]" + "█" * long_bars + "[/green]"
        long_empty = "[dim]" + "░" * (half_width - long_bars) + "[/dim]"
        right_side = f"{long_filled}{long_empty}"

        # Combine: S ░░░░░░████│████░░░░░░ L
        self._progress_widget.update(f"[red]S[/red] {left_side}│{right_side} [green]L[/green]")
