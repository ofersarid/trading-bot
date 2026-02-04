"""
Strategy Panel component.

Displays current strategy configuration with:
- Strategy name (selectable)
- Signal threshold
"""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.reactive import reactive
from textual.widgets import Static

from bot.strategies import Strategy, get_strategy, list_strategies


class StrategyPanel(Container):
    """
    Panel showing current strategy configuration.

    Displays:
    - Strategy name (press 's' to cycle)
    - Signal threshold
    """

    strategy_name: reactive[str] = reactive("equal_weight")

    def __init__(self, strategy: Strategy, **kwargs) -> None:
        super().__init__(**kwargs)
        self._strategy = strategy
        self.strategy_name = self._get_strategy_key(strategy.name)

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
