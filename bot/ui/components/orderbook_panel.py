"""
Order book panel component.

Displays per-instrument vertical pressure gauges.
Red fills from top (selling), green fills from bottom (buying).
"""

from textual.containers import Container, Horizontal
from textual.widgets import Static
from textual.app import ComposeResult

from bot.core.models import CoinPressure


# Theme colors
COLOR_UP = "#44ffaa"
COLOR_DOWN = "#ff7777"

BAR_HEIGHT = 10
BAR_WIDTH = 1


class CoinGauge(Static):
    """A single coin's vertical pressure gauge."""
    
    DEFAULT_CSS = """
    CoinGauge {
        width: 1fr;
        height: 1fr;
        content-align: center middle;
        text-align: center;
    }
    """
    
    def __init__(self, coin: str, **kwargs):
        super().__init__("", **kwargs)
        self.coin = coin
        self._pressure: CoinPressure | None = None
    
    def update_pressure(self, pressure: CoinPressure) -> None:
        """Update the gauge with new pressure data."""
        self._pressure = pressure
        self.update(self._render_gauge())
    
    def _render_gauge(self) -> str:
        """Render the vertical gauge as a string."""
        if not self._pressure:
            return f"[bold cyan]{self.coin}[/bold cyan]\n\n[dim]Loading...[/dim]"
        
        p = self._pressure
        lines = []
        
        # Coin name
        lines.append(f"[bold cyan]{p.coin}[/bold cyan]")
        lines.append("")  # spacer
        
        # Vertical bar (no labels)
        for row in range(BAR_HEIGHT):
            bar_str, color = self._get_gauge_row(row)
            lines.append(f"[{color}]{bar_str}[/{color}]")
        
        lines.append("")  # spacer
        
        # Winner indicator + percentages on same conceptual block
        diff = p.buy_pressure - p.sell_pressure
        if diff > 10:
            lines.append(f"[{COLOR_UP}]●[/{COLOR_UP}]")
        elif diff < -10:
            lines.append(f"[{COLOR_DOWN}]●[/{COLOR_DOWN}]")
        else:
            lines.append("[dim]●[/dim]")
        
        lines.append(f"[dim]{p.sell_pressure:.0f}/{p.buy_pressure:.0f}[/dim]")
        lines.append("")  # spacer
        
        # Price
        if p.price >= 1000:
            price_str = f"${p.price/1000:.1f}k"
        elif p.price >= 1:
            price_str = f"${p.price:.2f}"
        else:
            price_str = f"${p.price:.4f}"
        lines.append(f"[white]{price_str}[/white]")
        
        # Momentum
        if p.momentum:
            mom_color = COLOR_UP if p.momentum > 0 else COLOR_DOWN
            lines.append(f"[{mom_color}]{p.momentum:+.2f}%[/{mom_color}]")
        else:
            lines.append("[dim]─[/dim]")
        
        return "\n".join(lines)
    
    def _get_gauge_row(self, row: int) -> tuple[str, str]:
        """Get bar characters and color for a gauge row."""
        bar = "█" * BAR_WIDTH
        empty = "░" * BAR_WIDTH
        
        if not self._pressure:
            return empty, "dim"
        
        p = self._pressure
        half = BAR_HEIGHT // 2
        
        sell_rows = max(1, int((p.sell_pressure / 100) * half))
        buy_rows = max(1, int((p.buy_pressure / 100) * half))
        
        if row < half:
            # Top half: sells fill down
            if (row + 1) <= sell_rows:
                return bar, COLOR_DOWN
            return empty, "dim"
        else:
            # Bottom half: buys fill up
            if (BAR_HEIGHT - row) <= buy_rows:
                return bar, COLOR_UP
            return empty, "dim"


class OrderBookPanel(Container):
    """Panel displaying per-instrument vertical pressure gauges."""
    
    DEFAULT_CSS = """
    OrderBookPanel {
        height: 100%;
    }
    
    #gauge-container {
        width: 100%;
        height: 1fr;
        align: center middle;
    }
    """
    
    def __init__(self, coins: list[str], **kwargs):
        super().__init__(**kwargs)
        self.coins = coins
        self._gauges: dict[str, CoinGauge] = {}
    
    def compose(self) -> ComposeResult:
        yield Static("⚔️  MARKET PRESSURE", classes="panel-title")
        with Horizontal(id="gauge-container"):
            for coin in self.coins:
                gauge = CoinGauge(coin, id=f"gauge-{coin}")
                self._gauges[coin] = gauge
                yield gauge
    
    def update_display(
        self,
        orderbook: dict[str, dict],
        prices: dict[str, float],
        momentum: dict[str, float],
    ) -> None:
        """Update all pressure gauges."""
        for coin in self.coins:
            book = orderbook.get(coin, {"bids": [], "asks": []})
            price = prices.get(coin, 0.0)
            mom = momentum.get(coin, 0.0)
            
            pressure = CoinPressure.calculate(
                coin=coin,
                book=book,
                price=price,
                momentum=mom,
            )
            
            if coin in self._gauges:
                self._gauges[coin].update_pressure(pressure)
