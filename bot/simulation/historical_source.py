"""
Historical Data Source for replay simulation.

Reads CSV files from the historical data fetcher and yields price updates
that can be fed into the TradingSimulator.
"""

import csv
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class PriceUpdate:
    """A single price update from historical data."""

    timestamp: datetime
    coin: str
    price: float
    open: float
    high: float
    low: float
    close: float
    volume: float


class HistoricalDataSource:
    """
    Reads historical CSV data and yields price updates.

    Usage:
        source = HistoricalDataSource("data/historical/BTCUSDT_1m_....csv")
        for update in source.stream():
            # Process update.price, update.timestamp, etc.
    """

    def __init__(self, filepath: str | Path):
        """
        Initialize with path to CSV file.

        Args:
            filepath: Path to CSV file from get-data-set-from
        """
        self.filepath = Path(filepath)
        if not self.filepath.exists():
            raise FileNotFoundError(f"Historical data file not found: {filepath}")

        # Extract coin symbol from filename (e.g., "BTCUSDT_1m_..." -> "BTC")
        self.symbol = self._extract_symbol(self.filepath.name)
        self.coin = self._symbol_to_coin(self.symbol)

        # Load data
        self._candles: list[dict] = []
        self._load_data()

    def _extract_symbol(self, filename: str) -> str:
        """Extract symbol from filename like 'BTCUSDT_1m_...'"""
        return filename.split("_")[0]

    def _symbol_to_coin(self, symbol: str) -> str:
        """Convert symbol to coin (BTCUSDT -> BTC, BTCUSD -> BTC)."""
        # Remove common suffixes
        for suffix in ["USDT", "USD", "USDC", "BUSD"]:
            if symbol.endswith(suffix):
                return symbol[: -len(suffix)]
        return symbol

    def _load_data(self) -> None:
        """Load CSV data into memory."""
        with self.filepath.open() as f:
            reader = csv.DictReader(f)
            for row in reader:
                self._candles.append(row)

        if not self._candles:
            raise ValueError(f"No data found in {self.filepath}")

    @property
    def start_time(self) -> datetime:
        """Get the start timestamp of the data."""
        return datetime.fromisoformat(self._candles[0]["timestamp"])

    @property
    def end_time(self) -> datetime:
        """Get the end timestamp of the data."""
        return datetime.fromisoformat(self._candles[-1]["timestamp"])

    @property
    def candle_count(self) -> int:
        """Get the number of candles in the data."""
        return len(self._candles)

    def stream(self) -> Iterator[PriceUpdate]:
        """
        Yield price updates from the historical data.

        Yields:
            PriceUpdate objects in chronological order
        """
        for candle in self._candles:
            yield PriceUpdate(
                timestamp=datetime.fromisoformat(candle["timestamp"]),
                coin=self.coin,
                price=float(candle["close"]),
                open=float(candle["open"]),
                high=float(candle["high"]),
                low=float(candle["low"]),
                close=float(candle["close"]),
                volume=float(candle["volume"]),
            )

    def __repr__(self) -> str:
        return (
            f"HistoricalDataSource({self.coin}, "
            f"{self.candle_count} candles, "
            f"{self.start_time.strftime('%Y-%m-%d %H:%M')} to "
            f"{self.end_time.strftime('%Y-%m-%d %H:%M')})"
        )
