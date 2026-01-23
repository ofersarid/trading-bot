"""
Data models for historical data.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class HistoricalCandle:
    """A single historical OHLCV candle."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    turnover: float

    def to_dict(self) -> dict:
        """Convert to dictionary for CSV export."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "turnover": self.turnover,
        }

    @classmethod
    def from_bybit_response(cls, data: list) -> "HistoricalCandle":
        """
        Create from Bybit kline response.

        Bybit returns: [startTime, open, high, low, close, volume, turnover]
        All as strings.
        """
        return cls(
            timestamp=datetime.fromtimestamp(int(data[0]) / 1000),
            open=float(data[1]),
            high=float(data[2]),
            low=float(data[3]),
            close=float(data[4]),
            volume=float(data[5]),
            turnover=float(data[6]),
        )
