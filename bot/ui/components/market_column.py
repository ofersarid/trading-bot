"""
Market column component.

Container for a single market (BTC/ETH/SOL) with indicator sub-columns
and combined signal display.
"""

from collections.abc import Generator

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Static

from .combined_signal_row import CombinedSignalRow
from .indicator_subcolumn import IndicatorSubColumn


class MarketColumn(Container):
    """Column for a single market with indicator sub-columns."""

    INDICATORS: list[str] = ["session_vp", "prev_day_vp", "momentum", "rsi", "macd"]

    has_data: reactive[bool] = reactive(True)
    price: reactive[float | None] = reactive(None)

    def __init__(self, coin: str, **kwargs) -> None:
        """
        Initialize the market column.

        Args:
            coin: Coin symbol (BTC, ETH, SOL)
        """
        super().__init__(**kwargs)
        self.coin = coin

    def compose(self) -> ComposeResult:
        yield Static(
            self._format_header(), id=f"{self.coin.lower()}-header", classes="market-header"
        )

        if not self.has_data:
            # Show missing data warning
            with Vertical(classes="missing-data-container"):
                yield Static("⚠ MISSING DATA", classes="missing-data-warning")
                yield Static(
                    f"No historical data found for {self.coin}",
                    classes="missing-data-detail",
                )
                yield Static(
                    "Expected: {coin}_*.csv or {coin}_*.parquet",
                    classes="missing-data-hint",
                )
        else:
            # Normal indicator sub-columns in horizontal row
            with Horizontal(classes="indicators-row"):
                for ind in self.INDICATORS:
                    yield IndicatorSubColumn(
                        self.coin,
                        ind,
                        id=f"{self.coin.lower()}-{ind}",
                        classes="indicator-subcolumn",
                    )

            # Combined signal row at bottom
            yield CombinedSignalRow(
                self.coin,
                id=f"{self.coin.lower()}-combined-row",
                classes="combined-row",
            )

    def _format_header(self) -> str:
        """Format header text with coin symbol and price."""
        if self.price is not None:
            return f"{self.coin}  ${self.price:,.0f}"
        return self.coin

    def _compose_content(
        self,
    ) -> Generator[Static | Vertical | Horizontal | CombinedSignalRow, None, None]:
        """Generate content widgets based on data availability."""
        if not self.has_data:
            # Show missing data warning
            with Vertical(classes="missing-data-container"):
                yield Static("⚠ MISSING DATA", classes="missing-data-warning")
                yield Static(
                    f"No historical data found for {self.coin}",
                    classes="missing-data-detail",
                )
                yield Static(
                    "Expected: {coin}_*.csv or {coin}_*.parquet",
                    classes="missing-data-hint",
                )
        else:
            # Normal indicator sub-columns in horizontal row
            with Horizontal(classes="indicators-row"):
                for ind in self.INDICATORS:
                    yield IndicatorSubColumn(
                        self.coin,
                        ind,
                        id=f"{self.coin.lower()}-{ind}",
                        classes="indicator-subcolumn",
                    )

            # Combined signal row at bottom
            yield CombinedSignalRow(
                self.coin,
                id=f"{self.coin.lower()}-combined-row",
                classes="combined-row",
            )

    def watch_price(self, _price: float | None) -> None:
        """Update header when price changes."""
        try:
            header = self.query_one(f"#{self.coin.lower()}-header", Static)
            header.update(self._format_header())
        except Exception:
            pass

    def watch_has_data(self, _has_data: bool) -> None:
        """Re-compose when data availability changes."""
        self.refresh(recompose=True)

    def get_indicator_subcolumn(self, indicator_type: str) -> IndicatorSubColumn | None:
        """
        Get a specific indicator sub-column.

        Args:
            indicator_type: Type of indicator (session_vp, prev_day_vp, etc.)

        Returns:
            IndicatorSubColumn instance or None if not found
        """
        selector = f"#{self.coin.lower()}-{indicator_type}"
        try:
            result: IndicatorSubColumn = self.query_one(selector, IndicatorSubColumn)
            return result
        except Exception:
            return None

    def get_combined_row(self) -> CombinedSignalRow | None:
        """
        Get the combined signal row.

        Returns:
            CombinedSignalRow instance or None if not found
        """
        try:
            result: CombinedSignalRow = self.query_one(
                f"#{self.coin.lower()}-combined-row", CombinedSignalRow
            )
            return result
        except Exception:
            return None
