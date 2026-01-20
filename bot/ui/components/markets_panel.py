"""
Markets panel component.

Displays all trading markets in a DataTable with:
- Coin symbol and tick direction
- Price and momentum
- Buy/Sell pressure bar
- AI signal and confidence
- Position info (if any)
"""

from dataclasses import dataclass

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import DataTable, Static

from bot.simulation.paper_trader import Position

# Theme colors (Rich markup)
COLOR_UP = "#44ffaa"
COLOR_DOWN = "#ff7777"

# Pressure bar settings (each side of the center divider)
PRESSURE_BAR_WIDTH = 12

# Row height (2 = content line + padding)
ROW_HEIGHT = 2


@dataclass
class MarketData:
    """All data needed to display a market row."""

    coin: str
    price: float
    prev_price: float
    momentum: float | None
    buy_pressure: float  # 0-100
    sell_pressure: float  # 0-100
    ai_signal: str  # BULLISH/BEARISH/NEUTRAL
    ai_confidence: int  # 1-10
    position: Position | None

    # Scalper AI interpretation values (0-100 scale)
    scalper_momentum: int | None = None  # 0-100 from AI
    scalper_pressure: int | None = None  # 0-100 from AI (50 = neutral)
    scalper_prediction: int | None = None  # 0-100 from AI
    scalper_freshness: str | None = None  # FRESH/DEVELOPING/EXTENDED/EXHAUSTED
    scalper_age_seconds: float = 0.0  # Seconds since last interpretation


class MarketsPanel(Container):
    """Panel displaying all trading markets in a DataTable."""

    DEFAULT_CSS = """
    MarketsPanel {
        height: 100%;
    }

    MarketsPanel DataTable {
        height: 1fr;
        background: #0a0a0a;
        margin-top: 1;
    }

    MarketsPanel DataTable > .datatable--header {
        background: transparent;
        text-style: bold;
    }

    MarketsPanel DataTable:focus {
        border: none;
    }
    """

    def __init__(self, coins: list[str], **kwargs):
        super().__init__(**kwargs)
        self.coins = coins
        self._data: dict[str, MarketData] = {}
        self._prev_prices: dict[str, float] = {}
        self._initialized = False

    def compose(self) -> ComposeResult:
        yield Static("📊 TRADE DESK", classes="panel-title")
        yield DataTable(id="markets-table", cursor_type="none", header_height=2)

    def on_mount(self) -> None:
        """Set up the table columns and initial rows."""
        table = self.query_one(DataTable)

        # Add columns
        table.add_column("COIN", key="coin", width=8)
        table.add_column("PRICE", key="price", width=14)
        table.add_column("MOMENTUM", key="momentum", width=10)
        table.add_column("MARKET PRESSURE", key="pressure", width=26)
        table.add_column("AI PREDICTION", key="ai", width=26)
        table.add_column("POSITION", key="position", width=32)

        # Add initial rows for each coin
        for coin in self.coins:
            table.add_row(
                Text(coin, style="bold cyan"),
                Text("Loading...", style="dim"),
                Text("—", style="dim"),
                Text("────────────│────────────", style="dim"),
                Text.from_markup("[dim]—[/dim]   [#333333]● ● ● ● ● ● ● ● ● ●[/#333333]"),
                Text("—", style="dim"),
                key=coin,
                height=ROW_HEIGHT,
            )

        self._initialized = True

    def update_price(self, coin: str, price: float, momentum: float | None) -> None:
        """Update price and momentum for a market."""
        prev_price = self._prev_prices.get(coin, price)
        self._prev_prices[coin] = price

        if coin in self._data:
            self._data[coin].prev_price = self._data[coin].price
            self._data[coin].price = price
            self._data[coin].momentum = momentum
        else:
            self._data[coin] = MarketData(
                coin=coin,
                price=price,
                prev_price=prev_price,
                momentum=momentum,
                buy_pressure=50,
                sell_pressure=50,
                ai_signal="NEUTRAL",
                ai_confidence=0,
                position=None,
            )

        self._update_row(coin)

    def update_pressure(self, coin: str, buy_pressure: float, sell_pressure: float) -> None:
        """Update pressure for a market."""
        if coin in self._data:
            self._data[coin].buy_pressure = buy_pressure
            self._data[coin].sell_pressure = sell_pressure
            self._update_row(coin)

    def update_ai(self, coin: str, signal: str, confidence: int) -> None:
        """Update AI signal for a market."""
        if coin in self._data:
            self._data[coin].ai_signal = signal
            self._data[coin].ai_confidence = confidence
            self._update_row(coin)

    def update_position(
        self, coin: str, position: Position | None, price: float | None = None
    ) -> None:
        """Update position for a market."""
        if coin in self._data:
            self._data[coin].position = position
            if price is not None:
                self._data[coin].price = price
            self._update_row(coin)

    def update_scalper(
        self,
        coin: str,
        momentum: int,
        pressure: int,
        prediction: int,
        freshness: str,
        age_seconds: float,
    ) -> None:
        """
        Update scalper AI interpretation values for a market.

        Args:
            coin: Coin symbol
            momentum: AI-interpreted momentum (0-100)
            pressure: AI-interpreted pressure (0-100, 50=neutral)
            prediction: AI-interpreted continuation probability (0-100)
            freshness: FRESH/DEVELOPING/EXTENDED/EXHAUSTED
            age_seconds: Seconds since this interpretation
        """
        if coin in self._data:
            self._data[coin].scalper_momentum = momentum
            self._data[coin].scalper_pressure = pressure
            self._data[coin].scalper_prediction = prediction
            self._data[coin].scalper_freshness = freshness
            self._data[coin].scalper_age_seconds = age_seconds
            self._update_row(coin)

    def _update_row(self, coin: str) -> None:
        """Update a single row in the table."""
        if not self._initialized:
            return

        try:
            table = self.query_one(DataTable)
            data = self._data.get(coin)

            if not data:
                return

            # Update each cell
            table.update_cell(coin, "coin", self._format_coin(data))
            table.update_cell(coin, "price", self._format_price(data))
            table.update_cell(coin, "momentum", self._format_momentum(data))
            table.update_cell(coin, "pressure", self._format_pressure(data))
            table.update_cell(coin, "ai", self._format_ai(data))
            table.update_cell(coin, "position", self._format_position(data))
        except Exception:
            pass

    def _format_coin(self, data: MarketData) -> Text:
        """Format coin column with tick direction."""
        if data.price > data.prev_price:
            tick = f" [{COLOR_UP}]▲[/{COLOR_UP}]"
        elif data.price < data.prev_price:
            tick = f" [{COLOR_DOWN}]▼[/{COLOR_DOWN}]"
        else:
            tick = " [dim]─[/dim]"

        return Text.from_markup(f"[bold cyan]{data.coin}[/bold cyan]{tick}")

    def _format_price(self, data: MarketData) -> Text:
        """Format price column."""
        if data.price >= 1000:
            price_str = f"${data.price:,.2f}"
        elif data.price >= 1:
            price_str = f"${data.price:.2f}"
        else:
            price_str = f"${data.price:.4f}"

        return Text(price_str)

    def _format_momentum(self, data: MarketData) -> Text:
        """Format momentum column - shows scalper AI value only."""
        if data.scalper_momentum is not None:
            mom = data.scalper_momentum
            # Color based on 0-100 scale (50 = neutral)
            if mom >= 60:
                color = COLOR_UP
            elif mom <= 40:
                color = COLOR_DOWN
            else:
                color = "yellow"
            return Text.from_markup(f"[{color}]{mom}/100[/{color}]")

        return Text("—", style="dim")

    def _format_pressure(self, data: MarketData) -> Text:
        """Format pressure bar column - uses scalper AI pressure only."""
        if data.scalper_pressure is not None:
            pressure = data.scalper_pressure
            # Convert 0-100 scale to buy/sell bars
            # >50 = buy pressure, <50 = sell pressure
            if pressure >= 50:
                buy_pct = (pressure - 50) * 2  # 50->0, 100->100
                sell_pct = 0
            else:
                buy_pct = 0
                sell_pct = (50 - pressure) * 2  # 50->0, 0->100

            buy_filled = int((buy_pct / 100) * PRESSURE_BAR_WIDTH)
            sell_filled = int((sell_pct / 100) * PRESSURE_BAR_WIDTH)
        else:
            # No scalper interpretation yet - show empty/neutral bar
            buy_filled = 0
            sell_filled = 0

        # Build buy side (green, fills from left)
        buy_bar = "█" * buy_filled + "░" * (PRESSURE_BAR_WIDTH - buy_filled)

        # Build sell side (red, fills from right)
        sell_bar = "░" * (PRESSURE_BAR_WIDTH - sell_filled) + "█" * sell_filled

        bar = f"[{COLOR_UP}]{buy_bar}[/{COLOR_UP}]│[{COLOR_DOWN}]{sell_bar}[/{COLOR_DOWN}]"

        return Text.from_markup(bar)

    def _format_ai(self, data: MarketData) -> Text:
        """
        Format AI signal column with freshness indicator and confidence dots.

        Format: FRE ●●●●●○○○○○
        - Left: Freshness code (FRE/DEV/EXT/EXH)
        - Right: 10 dots, colored count = prediction value / 10
        - Green dots = bullish (>50%), Red dots = bearish (<50%), Yellow = neutral (50%)
        """
        if data.scalper_prediction is not None and data.scalper_freshness is not None:
            pred = data.scalper_prediction
            fresh = data.scalper_freshness
            age = data.scalper_age_seconds

            # Number of colored dots (1-10 scale from 0-100 prediction)
            colored_count = round(pred / 10)
            colored_count = max(0, min(10, colored_count))  # Clamp to 0-10
            gray_count = 10 - colored_count

            # Dot color based on prediction direction
            if pred > 50:
                dot_color = COLOR_UP  # Bullish = green
            elif pred < 50:
                dot_color = COLOR_DOWN  # Bearish = red
            else:
                dot_color = "yellow"  # Neutral

            # Build dots string with spaces between dots
            colored_dots = f"[{dot_color}]" + " ".join("●" * colored_count) + f"[/{dot_color}]"
            gray_dots = "[#333333]" + " ".join("●" * gray_count) + "[/#333333]"
            # Add separator space between colored and gray sections
            separator = " " if colored_count > 0 and gray_count > 0 else ""

            # Freshness color
            if fresh == "FRESH":
                fresh_color = COLOR_UP
            elif fresh == "DEVELOPING":
                fresh_color = "yellow"
            elif fresh == "EXTENDED":
                fresh_color = "orange1"
            else:  # EXHAUSTED
                fresh_color = COLOR_DOWN

            # Staleness indicator (data getting old)
            if age > 30:
                stale = "[red]![/red]"
            elif age > 20:
                stale = "[yellow]·[/yellow]"
            else:
                stale = ""

            return Text.from_markup(
                f"[{fresh_color}]{fresh[:3]}[/{fresh_color}] {colored_dots}{separator}{gray_dots}{stale}"
            )

        # No scalper interpretation yet - show all gray dots
        return Text.from_markup("[dim]—[/dim]   [#333333]● ● ● ● ● ● ● ● ● ●[/#333333]")

    def _format_position(self, data: MarketData) -> Text:
        """Format position column."""
        if not data.position:
            return Text("—", style="dim")

        pos = data.position
        price = data.price

        # Direction
        if pos.side.value == "long":
            direction = f"[{COLOR_UP}]LONG[/{COLOR_UP}]"
        else:
            direction = f"[{COLOR_DOWN}]SHORT[/{COLOR_DOWN}]"

        # Size
        size_str = f"{pos.size:.4f}"

        # P&L in dollars and percentage
        pnl_dollars = pos.unrealized_pnl(price)
        pnl_pct = pos.unrealized_pnl_percent(price)
        pnl_color = COLOR_UP if pnl_dollars >= 0 else COLOR_DOWN
        pnl_str = f"[{pnl_color}]{pnl_dollars:+.2f}$ ({pnl_pct:+.2f}%)[/{pnl_color}]"

        return Text.from_markup(f"{direction} {size_str} {pnl_str}")
