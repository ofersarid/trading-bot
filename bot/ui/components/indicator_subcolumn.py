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

    def __init__(self, coin: str, indicator_type: str, **kwargs) -> None:
        """
        Initialize the indicator sub-column.

        Args:
            coin: Coin symbol (BTC, ETH, SOL)
            indicator_type: Type of indicator (session_vp, prev_day_vp, momentum, rsi, macd)
        """
        super().__init__(**kwargs)
        self.coin = coin
        self.indicator_type = indicator_type
        self._values_widget: Static | None = None
        self._signal_widget: Static | None = None

    def compose(self) -> ComposeResult:
        title = self.TITLES.get(self.indicator_type, self.indicator_type.upper())

        yield Static(title, classes="subcolumn-title")
        self._values_widget = Static("--", classes="subcolumn-values")
        yield self._values_widget
        self._signal_widget = Static("--", classes="subcolumn-signal")
        yield self._signal_widget

    def update_values(self, values_text: str) -> None:
        """
        Update the indicator values display.

        Args:
            values_text: Formatted text showing indicator values (e.g., "POC 99200\\nVAH 99800")
        """
        if self._values_widget:
            self._values_widget.update(values_text)

    def update_signal(self, signal_text: str) -> None:
        """
        Update the individual signal display.

        Args:
            signal_text: Signal text (e.g., "LONG 0.85" or "--")
        """
        if self._signal_widget:
            self._signal_widget.update(signal_text)
