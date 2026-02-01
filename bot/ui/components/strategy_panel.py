"""
Strategy Panel component.

Displays current strategy configuration with:
- Strategy name (selectable)
- Signal threshold
- Visual weight histogram for each indicator
"""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.reactive import reactive
from textual.widgets import Static

from bot.signals.base import SignalType
from bot.strategies import Strategy, get_strategy, list_strategies

# All signal types in display order
ALL_SIGNAL_TYPES = [
    SignalType.MOMENTUM,
    SignalType.RSI,
    SignalType.MACD,
    SignalType.VOLUME_PROFILE,
]

# Short labels for display
SIGNAL_LABELS = {
    SignalType.MOMENTUM: "MOM",
    SignalType.RSI: "RSI",
    SignalType.MACD: "MACD",
    SignalType.VOLUME_PROFILE: "VP",
}


class WeightBar(Static):
    """A single weight bar showing indicator weight visually."""

    weight: reactive[float] = reactive(0.0)

    def __init__(self, signal_type: SignalType, weight: float = 0.0, **kwargs) -> None:
        super().__init__(**kwargs)
        self.signal_type = signal_type
        self.weight = weight

    def render(self) -> str:
        """Render the weight as a visual bar."""
        label = SIGNAL_LABELS.get(self.signal_type, "???")
        # Create bar: 5 characters wide, filled proportionally
        bar_width = 5
        filled = int(self.weight * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)
        # Show weight value below
        weight_str = f"{self.weight:.1f}" if self.weight > 0 else "---"
        return f"{label}\n{bar}\n{weight_str}"

    def watch_weight(self, _weight: float) -> None:
        """Update display when weight changes."""
        self.refresh()


class StrategyPanel(Container):
    """
    Panel showing current strategy configuration.

    Displays:
    - Strategy name (press 's' to cycle)
    - Signal threshold
    - Weight histogram for each signal type
    """

    strategy_name: reactive[str] = reactive("momentum_based")

    def __init__(self, strategy: Strategy, **kwargs) -> None:
        super().__init__(**kwargs)
        self._strategy = strategy
        self.strategy_name = self._get_strategy_key(strategy.name)
        self._weight_bars: dict[SignalType, WeightBar] = {}

    def _get_strategy_key(self, name: str) -> str:
        """Convert strategy display name to key."""
        return name.lower().replace(" ", "_").replace("-", "_")

    def compose(self) -> ComposeResult:
        """Create the panel layout."""
        # Header row with strategy name and threshold
        with Horizontal(classes="strategy-header"):
            yield Static(
                f"Strategy: {self._strategy.name}",
                id="strategy-name",
                classes="strategy-name",
            )
            yield Static(
                f"Threshold: {self._strategy.signal_threshold:.2f}",
                id="strategy-threshold",
                classes="strategy-threshold",
            )
            yield Static(
                "[s] change",
                classes="strategy-hint",
            )

        # Weight bars row
        with Horizontal(classes="weight-bars"):
            for signal_type in ALL_SIGNAL_TYPES:
                weight = self._strategy.signal_weights.get(signal_type, 0.0)
                bar = WeightBar(
                    signal_type,
                    weight=weight,
                    id=f"weight-{signal_type.value.lower()}",
                    classes="weight-bar",
                )
                self._weight_bars[signal_type] = bar
                yield bar

    def update_strategy(self, strategy: Strategy) -> None:
        """Update the panel with a new strategy."""
        self._strategy = strategy
        self.strategy_name = self._get_strategy_key(strategy.name)

        # Update header
        try:
            name_widget = self.query_one("#strategy-name", Static)
            name_widget.update(f"Strategy: {strategy.name}")

            threshold_widget = self.query_one("#strategy-threshold", Static)
            threshold_widget.update(f"Threshold: {strategy.signal_threshold:.2f}")
        except Exception:
            pass

        # Update weight bars
        for signal_type, bar in self._weight_bars.items():
            bar.weight = strategy.signal_weights.get(signal_type, 0.0)

    def get_next_strategy(self) -> Strategy:
        """Get the next strategy in the rotation."""
        strategies = [name for name, _ in list_strategies()]
        current_idx = (
            strategies.index(self.strategy_name) if self.strategy_name in strategies else 0
        )
        next_idx = (current_idx + 1) % len(strategies)
        return get_strategy(strategies[next_idx])

    @property
    def current_strategy(self) -> Strategy:
        """Get the current strategy."""
        return self._strategy
