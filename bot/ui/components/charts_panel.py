"""
Charts Panel - Price charts for each trading coin.

Uses Unicode block characters for reliable terminal rendering.
Shows one chart at a time with coin toggle buttons.
"""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Button, Static

from bot.core.candle_aggregator import CANDLE_INTERVAL_SECONDS, Candle


def _get_interval_label() -> str:
    """Get human-readable interval label (e.g., '5s', '1m')."""
    if CANDLE_INTERVAL_SECONDS >= 60:
        return f"{CANDLE_INTERVAL_SECONDS // 60}m"
    return f"{CANDLE_INTERVAL_SECONDS}s"


# Chart dimensions
CHART_WIDTH = 80
CHART_HEIGHT = 12

# Minimum data points before showing chart
MIN_POINTS_TO_DISPLAY = 10

# Unicode block characters for vertical bar chart (8 levels)
BLOCKS = " ▁▂▃▄▅▆▇█"


class PriceLineChart(Static):
    """
    Single coin price chart using Unicode blocks.

    Renders price movements as a clean bar/area chart in the terminal.
    """

    DEFAULT_CSS = """
    PriceLineChart {
        height: 1fr;
        background: #0a0a0a;
        border: solid #333333;
        padding: 1 2;
    }
    """

    def __init__(self, coin: str, **kwargs):
        super().__init__(**kwargs)
        self.coin = coin
        self._prices: list[float] = []
        self._last_price: float | None = None

    def update_candles(self, candles: list[Candle], current_price: float | None = None) -> None:
        """
        Update the chart with new candle data (uses close prices).

        Args:
            candles: List of Candle objects to display
            current_price: Optional current price for title display
        """
        self._prices = [c.close for c in candles]
        self._last_price = current_price
        self._render_chart()

    def _render_chart(self) -> None:
        """Render the price chart using Unicode characters."""
        price_str = f"${self._last_price:,.2f}" if self._last_price else "—"
        num_points = len(self._prices)
        interval_label = _get_interval_label()

        # Show waiting message until we have enough data
        if num_points < MIN_POINTS_TO_DISPLAY:
            remaining = MIN_POINTS_TO_DISPLAY - num_points
            progress = "█" * num_points + "░" * remaining
            self.update(
                f"[bold cyan]{self.coin}[/bold cyan] {interval_label}  {price_str}\n\n"
                f"[dim]Collecting data: [{progress}] {num_points}/{MIN_POINTS_TO_DISPLAY}[/dim]"
            )
            return

        # Determine trend color
        if self._prices[-1] > self._prices[0]:
            color = "#22cc66"  # Green - up
            trend = "▲"
        elif self._prices[-1] < self._prices[0]:
            color = "#ff5555"  # Red - down
            trend = "▼"
        else:
            color = "#888888"  # Gray - flat
            trend = "─"

        # Calculate change
        change = self._prices[-1] - self._prices[0]
        change_pct = (change / self._prices[0]) * 100 if self._prices[0] != 0 else 0

        # Build header
        header = (
            f"[bold cyan]{self.coin}[/bold cyan] {interval_label}  "
            f"[bold]{price_str}[/bold]  "
            f"[{color}]{trend} {change_pct:+.2f}%[/{color}]"
        )

        # Build the chart
        chart_lines = self._build_chart(color)

        # Combine
        output = header + "\n\n" + "\n".join(chart_lines)
        self.update(output)

    def _build_chart(self, color: str) -> list[str]:
        """Build the Unicode block chart."""
        prices = self._prices[-CHART_WIDTH:]  # Limit to chart width

        if not prices:
            return ["[dim]No data[/dim]"]

        min_price = min(prices)
        max_price = max(prices)
        price_range = max_price - min_price

        if price_range == 0:
            # Flat line - show middle
            normalized = [0.5] * len(prices)
        else:
            normalized = [(p - min_price) / price_range for p in prices]

        # Build rows from top to bottom
        lines = []

        for row in range(CHART_HEIGHT - 1, -1, -1):
            row_threshold = row / (CHART_HEIGHT - 1) if CHART_HEIGHT > 1 else 0
            line_chars = []

            for val in normalized:
                if val >= row_threshold:
                    # Calculate sub-block level
                    if row == CHART_HEIGHT - 1:
                        char = "█"
                    else:
                        next_threshold = (row + 1) / (CHART_HEIGHT - 1) if CHART_HEIGHT > 1 else 1
                        if val >= next_threshold:
                            char = "█"
                        else:
                            # Partial block
                            level = int(
                                (val - row_threshold) / (next_threshold - row_threshold) * 8
                            )
                            char = BLOCKS[min(level + 1, 8)]
                    line_chars.append(char)
                else:
                    line_chars.append(" ")

            line = "".join(line_chars)

            # Add price label on first and last row
            if row == CHART_HEIGHT - 1:
                label = f" ${max_price:,.0f}"
            elif row == 0:
                label = f" ${min_price:,.0f}"
            else:
                label = ""

            lines.append(f"[{color}]{line}[/{color}][dim]{label}[/dim]")

        return lines


class ChartsPanel(Container):
    """
    Panel containing a candlestick chart with coin toggle buttons.

    Shows one chart at a time. User can switch between coins using buttons.
    """

    DEFAULT_CSS = """
    ChartsPanel {
        height: 100%;
        width: 100%;
    }

    #charts-header {
        height: 3;
        background: #1a1a1a;
        padding: 0 1;
    }

    #charts-header .panel-title {
        text-style: bold;
        width: auto;
        padding-right: 2;
    }

    #coin-toggles {
        height: auto;
        width: 1fr;
    }

    .coin-toggle {
        min-width: 6;
        height: 1;
        margin: 0 1 0 0;
        background: #333333;
        color: #888888;
        border: none;
    }

    .coin-toggle:hover {
        background: #444444;
    }

    .coin-toggle.active {
        background: #0066cc;
        color: white;
        text-style: bold;
    }

    #active-chart {
        height: 1fr;
    }
    """

    def __init__(self, coins: list[str], **kwargs):
        super().__init__(**kwargs)
        self.coins = coins
        self._selected_coin: str = coins[0] if coins else ""
        self._chart: PriceLineChart | None = None
        self._candle_data: dict[str, tuple[list[Candle], float | None]] = {}

    def compose(self) -> ComposeResult:
        interval_label = _get_interval_label()

        with Horizontal(id="charts-header"):
            yield Static(f"📈 PRICE ({interval_label})", classes="panel-title")
            with Horizontal(id="coin-toggles"):
                for coin in self.coins:
                    btn_class = (
                        "coin-toggle active" if coin == self._selected_coin else "coin-toggle"
                    )
                    yield Button(coin, id=f"toggle-{coin.lower()}", classes=btn_class)

        # Single chart for the selected coin
        self._chart = PriceLineChart(self._selected_coin, id="active-chart")
        yield self._chart

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle coin toggle button press."""
        button_id = event.button.id
        if button_id and button_id.startswith("toggle-"):
            coin = button_id.replace("toggle-", "").upper()
            if coin in self.coins:
                self._select_coin(coin)

    def _select_coin(self, coin: str) -> None:
        """Switch to displaying the selected coin's chart."""
        if coin == self._selected_coin:
            return

        self._selected_coin = coin

        # Update button styles
        for c in self.coins:
            btn = self.query_one(f"#toggle-{c.lower()}", Button)
            if c == coin:
                btn.add_class("active")
            else:
                btn.remove_class("active")

        # Update chart with cached data for the new coin
        if self._chart and coin in self._candle_data:
            candles, price = self._candle_data[coin]
            self._chart.coin = coin
            self._chart.update_candles(candles, price)
        elif self._chart:
            self._chart.coin = coin
            self._chart.update_candles([], None)

    def update_chart(
        self,
        coin: str,
        candles: list[Candle],
        current_price: float | None = None,
    ) -> None:
        """
        Update a specific coin's chart data.

        Args:
            coin: Coin symbol
            candles: List of Candle objects
            current_price: Current price for display
        """
        # Cache data for all coins
        self._candle_data[coin] = (candles, current_price)

        # Only update the visible chart if it's the selected coin
        if coin == self._selected_coin and self._chart:
            self._chart.update_candles(candles, current_price)

    def get_chart(self, coin: str) -> PriceLineChart | None:
        """Get the chart widget (returns the single chart if coin matches)."""
        if coin == self._selected_coin:
            return self._chart
        return None


class MiniChart(Static):
    """
    Compact single-line sparkline-style chart for inline display.

    Shows price trend using Unicode block characters.
    Useful for embedding in table cells or tight spaces.
    """

    def __init__(self, width: int = 20, **kwargs):
        super().__init__(**kwargs)
        self.width = width
        self._prices: list[float] = []

    def update_prices(self, prices: list[float]) -> None:
        """Update the mini chart with price data."""
        self._prices = prices[-self.width :] if len(prices) > self.width else prices
        self._render()

    def _render(self) -> None:
        """Render the sparkline."""
        if len(self._prices) < 2:
            self.update("[dim]" + "─" * self.width + "[/dim]")
            return

        # Normalize prices to 0-7 range for block characters
        min_p = min(self._prices)
        max_p = max(self._prices)
        range_p = max_p - min_p if max_p != min_p else 1

        blocks = "▁▂▃▄▅▆▇█"

        sparkline = ""
        for price in self._prices:
            normalized = (price - min_p) / range_p
            block_idx = min(7, int(normalized * 8))
            sparkline += blocks[block_idx]

        # Pad to width
        sparkline = sparkline.ljust(self.width, "─")

        # Color based on trend
        if self._prices[-1] > self._prices[0]:
            color = "#44ffaa"
        elif self._prices[-1] < self._prices[0]:
            color = "#ff7777"
        else:
            color = "white"

        self.update(f"[{color}]{sparkline}[/{color}]")
