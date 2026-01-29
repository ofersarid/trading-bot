"""
Markets panel component.

Displays all trading markets in a DataTable with:
- Coin symbol and tick direction
- Price
- Market pressure bar (from orderbook)
- Signal detector outputs (MOM, RSI, MACD, VP)
- Weighted scores vs threshold
- Position info (if any)
"""

from dataclasses import dataclass, field

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import DataTable, Static

from bot.signals.base import Signal
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

    # Signal detector outputs (new architecture)
    signals: list[Signal] = field(default_factory=list)
    long_score: float = 0.0
    short_score: float = 0.0
    signal_threshold: float = 0.7


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

        # Add columns - new signal-based layout
        table.add_column("COIN", key="coin", width=8)
        table.add_column("PRICE", key="price", width=14)
        table.add_column("SIGNALS", key="signals", width=28)
        table.add_column("SCORE", key="score", width=20)
        table.add_column("PRESSURE", key="pressure", width=26)
        table.add_column("POSITION", key="position", width=32)

        # Add initial rows for each coin
        for coin in self.coins:
            table.add_row(
                Text(coin, style="bold cyan"),
                Text("Loading...", style="dim"),
                Text("—", style="dim"),
                Text("—", style="dim"),
                Text("────────────│────────────", style="dim"),
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

    def update_signals(
        self,
        coin: str,
        signals: list[Signal],
        long_score: float,
        short_score: float,
        threshold: float,
    ) -> None:
        """
        Update signal detector outputs for a market.

        Args:
            coin: Coin symbol
            signals: List of recent signals from detectors
            long_score: Weighted LONG score
            short_score: Weighted SHORT score
            threshold: Signal threshold from strategy
        """
        if coin in self._data:
            self._data[coin].signals = signals
            self._data[coin].long_score = long_score
            self._data[coin].short_score = short_score
            self._data[coin].signal_threshold = threshold
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

            # Update each cell - new signal-based layout
            table.update_cell(coin, "coin", self._format_coin(data))
            table.update_cell(coin, "price", self._format_price(data))
            table.update_cell(coin, "signals", self._format_signals(data))
            table.update_cell(coin, "score", self._format_score(data))
            table.update_cell(coin, "pressure", self._format_pressure(data))
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

    def _format_signals(self, data: MarketData) -> Text:
        """
        Format signals column showing detector outputs.

        Format: MOM▲0.85 RSI▲0.60 MACD─ VP▲0.55
        - ▲ Green = LONG signal
        - ▼ Red = SHORT signal
        - ─ Gray = No signal / not active
        """
        if not data.signals:
            return Text("─", style="dim")

        # Group signals by type (keep most recent of each)
        from bot.signals.base import SignalType

        by_type: dict[SignalType, Signal] = {}
        for signal in data.signals:
            if (
                signal.signal_type not in by_type
                or signal.timestamp > by_type[signal.signal_type].timestamp
            ):
                by_type[signal.signal_type] = signal

        # Format each signal type
        parts: list[str] = []
        signal_abbrevs = {
            SignalType.MOMENTUM: "MOM",
            SignalType.RSI: "RSI",
            SignalType.MACD: "MACD",
            SignalType.VOLUME_PROFILE: "VP",
        }

        for sig_type, abbrev in signal_abbrevs.items():
            if sig_type in by_type:
                signal = by_type[sig_type]
                if signal.direction == "LONG":
                    arrow = f"[{COLOR_UP}]▲[/{COLOR_UP}]"
                else:
                    arrow = f"[{COLOR_DOWN}]▼[/{COLOR_DOWN}]"
                parts.append(f"{abbrev}{arrow}{signal.strength:.2f}")

        if not parts:
            return Text("─", style="dim")

        return Text.from_markup(" ".join(parts))

    def _format_score(self, data: MarketData) -> Text:
        """
        Format score column showing weighted scores vs threshold.

        Format:
        L:1.15 ████████░░ 0.7
        S:0.40 ████░░░░░░
        """
        # Determine which score is higher
        long_score = data.long_score
        short_score = data.short_score
        threshold = data.signal_threshold

        # Build visual bar (10 chars wide)
        bar_width = 10

        # Normalize scores relative to 2x threshold for bar display
        max_display = threshold * 2
        long_filled = min(bar_width, int((long_score / max_display) * bar_width))
        short_filled = min(bar_width, int((short_score / max_display) * bar_width))

        # Build bars with threshold marker
        threshold_pos = int((threshold / max_display) * bar_width)

        def build_bar(filled: int, is_long: bool) -> str:
            color = COLOR_UP if is_long else COLOR_DOWN
            bar_chars: list[str] = []
            for i in range(bar_width):
                if i == threshold_pos:
                    bar_chars.append("[white]│[/white]")
                elif i < filled:
                    bar_chars.append(f"[{color}]█[/{color}]")
                else:
                    bar_chars.append("[dim]░[/dim]")
            return "".join(bar_chars)

        long_bar = build_bar(long_filled, is_long=True)
        short_bar = build_bar(short_filled, is_long=False)

        # Highlight the winning direction
        if long_score >= threshold and long_score > short_score:
            long_prefix = f"[{COLOR_UP}]L:{long_score:.2f}[/{COLOR_UP}]"
        else:
            long_prefix = f"L:{long_score:.2f}"

        if short_score >= threshold and short_score > long_score:
            short_prefix = f"[{COLOR_DOWN}]S:{short_score:.2f}[/{COLOR_DOWN}]"
        else:
            short_prefix = f"S:{short_score:.2f}"

        return Text.from_markup(f"{long_prefix} {long_bar}\n{short_prefix} {short_bar}")

    def _format_pressure(self, data: MarketData) -> Text:
        """
        Format pressure bar column using real orderbook data.

        Shows buy/sell pressure from actual orderbook imbalance,
        not AI-interpreted values.
        """
        # Use real orderbook pressure data
        buy_pct = data.buy_pressure
        sell_pct = data.sell_pressure

        # Normalize to bar width
        total_pressure = buy_pct + sell_pct
        if total_pressure > 0:
            buy_filled = int((buy_pct / total_pressure) * PRESSURE_BAR_WIDTH)
            sell_filled = int((sell_pct / total_pressure) * PRESSURE_BAR_WIDTH)
        else:
            buy_filled = 0
            sell_filled = 0

        # Build buy side (green filled, dim empty)
        buy_filled_str = f"[{COLOR_UP}]{'█' * buy_filled}[/{COLOR_UP}]"
        buy_empty_str = f"[dim]{'░' * (PRESSURE_BAR_WIDTH - buy_filled)}[/dim]"
        buy_bar = buy_filled_str + buy_empty_str

        # Build sell side (dim empty, red filled)
        sell_empty_str = f"[dim]{'░' * (PRESSURE_BAR_WIDTH - sell_filled)}[/dim]"
        sell_filled_str = f"[{COLOR_DOWN}]{'█' * sell_filled}[/{COLOR_DOWN}]"
        sell_bar = sell_empty_str + sell_filled_str

        bar = f"{buy_bar}│{sell_bar}"

        return Text.from_markup(bar)

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
