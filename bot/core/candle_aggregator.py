"""
Candle Aggregator - Convert price ticks into OHLC candles.

Aggregates streaming price data into candlesticks for charting.
Designed to work with any number of coins dynamically.
"""

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

# Candle interval in seconds (1s for dev, change to 60 for production)
CANDLE_INTERVAL_SECONDS = 1


@dataclass
class Candle:
    """A single OHLC candlestick."""

    timestamp: datetime  # Start of the minute
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    trade_count: int = 0

    @property
    def is_bullish(self) -> bool:
        """Returns True if close > open (green candle)."""
        return self.close >= self.open

    @property
    def body_size(self) -> float:
        """Size of the candle body (absolute)."""
        return abs(self.close - self.open)

    @property
    def wick_upper(self) -> float:
        """Size of the upper wick."""
        return self.high - max(self.open, self.close)

    @property
    def wick_lower(self) -> float:
        """Size of the lower wick."""
        return min(self.open, self.close) - self.low

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "trade_count": self.trade_count,
        }


class CandleAggregator:
    """
    Aggregates price ticks into OHLC candles for a single coin.

    Call add_tick() with each price update. When an interval boundary is crossed,
    the completed candle is returned and a new one begins.

    Interval is controlled by CANDLE_INTERVAL_SECONDS (5s for dev, 60s for prod).
    """

    def __init__(self, coin: str, max_candles: int = 60):
        """
        Initialize the aggregator.

        Args:
            coin: Coin symbol (e.g., "BTC")
            max_candles: Maximum number of completed candles to retain
        """
        self.coin = coin
        self.max_candles = max_candles

        # Current candle being built
        self._current_interval: datetime | None = None
        self._current_open: float = 0.0
        self._current_high: float = 0.0
        self._current_low: float = float("inf")
        self._current_close: float = 0.0
        self._current_volume: float = 0.0
        self._current_trade_count: int = 0

        # Completed candles
        self.candles: deque[Candle] = deque(maxlen=max_candles)

    def _get_interval_start(self, dt: datetime) -> datetime:
        """Get the start of the current interval for a given timestamp."""
        # Truncate to the interval boundary
        interval_second = (dt.second // CANDLE_INTERVAL_SECONDS) * CANDLE_INTERVAL_SECONDS
        return dt.replace(second=interval_second, microsecond=0)

    def add_tick(self, price: float, volume: float = 0.0) -> Candle | None:
        """
        Add a price tick to the aggregator.

        Args:
            price: Current price
            volume: Trade volume (optional)

        Returns:
            Completed Candle if an interval boundary was crossed, else None
        """
        now = datetime.now()
        interval = self._get_interval_start(now)

        completed_candle = None

        # Check if we've crossed into a new interval
        if self._current_interval is None:
            # First tick ever - start new candle
            self._start_candle(interval, price)
        elif interval > self._current_interval:
            # New interval - complete previous candle and start new one
            completed_candle = self._close_candle()
            self._start_candle(interval, price)

        # Update current candle
        self._update_candle(price, volume)

        return completed_candle

    def _start_candle(self, interval: datetime, price: float) -> None:
        """Start a new candle at the given interval."""
        self._current_interval = interval
        self._current_open = price
        self._current_high = price
        self._current_low = price
        self._current_close = price
        self._current_volume = 0.0
        self._current_trade_count = 0

    def _update_candle(self, price: float, volume: float) -> None:
        """Update the current candle with a new tick."""
        self._current_high = max(self._current_high, price)
        self._current_low = min(self._current_low, price)
        self._current_close = price
        self._current_volume += volume
        self._current_trade_count += 1

    def _close_candle(self) -> Candle:
        """Close the current candle and add it to history."""
        # _close_candle is only called when _current_interval is set (after first tick)
        assert self._current_interval is not None
        candle = Candle(
            timestamp=self._current_interval,
            open=self._current_open,
            high=self._current_high,
            low=self._current_low,
            close=self._current_close,
            volume=self._current_volume,
            trade_count=self._current_trade_count,
        )
        self.candles.append(candle)
        return candle

    def get_current_candle(self) -> Candle | None:
        """Get the current (incomplete) candle."""
        if self._current_interval is None:
            return None

        return Candle(
            timestamp=self._current_interval,
            open=self._current_open,
            high=self._current_high,
            low=self._current_low,
            close=self._current_close,
            volume=self._current_volume,
            trade_count=self._current_trade_count,
        )

    def get_all_candles(self, include_current: bool = True) -> list[Candle]:
        """
        Get all candles including optionally the current incomplete one.

        Args:
            include_current: Whether to include the incomplete current candle

        Returns:
            List of candles, oldest first
        """
        result = list(self.candles)
        if include_current:
            current = self.get_current_candle()
            if current:
                result.append(current)
        return result

    def get_ohlc_arrays(self, include_current: bool = True) -> dict[str, list]:
        """
        Get OHLC data as separate arrays for plotting.

        Returns:
            Dict with keys: timestamps, opens, highs, lows, closes, volumes
        """
        candles = self.get_all_candles(include_current)

        return {
            "timestamps": [c.timestamp for c in candles],
            "opens": [c.open for c in candles],
            "highs": [c.high for c in candles],
            "lows": [c.low for c in candles],
            "closes": [c.close for c in candles],
            "volumes": [c.volume for c in candles],
        }

    def clear(self) -> None:
        """Clear all candle data."""
        self._current_interval = None
        self.candles.clear()


class MultiCoinCandleManager:
    """
    Manages CandleAggregators for multiple coins.

    Provides a unified interface for feeding price data and retrieving
    candles across any number of dynamically configured coins.
    """

    def __init__(
        self,
        coins: list[str],
        max_candles: int = 60,
        on_candle_complete: Callable[[str, Candle], None] | None = None,
    ):
        """
        Initialize the manager.

        Args:
            coins: List of coin symbols to track
            max_candles: Maximum candles to retain per coin
            on_candle_complete: Optional callback when a candle completes
        """
        self.coins = coins
        self.max_candles = max_candles
        self.on_candle_complete = on_candle_complete

        self._aggregators: dict[str, CandleAggregator] = {
            coin: CandleAggregator(coin, max_candles) for coin in coins
        }

    def add_tick(self, coin: str, price: float, volume: float = 0.0) -> Candle | None:
        """
        Add a price tick for a coin.

        Args:
            coin: Coin symbol
            price: Current price
            volume: Trade volume (optional)

        Returns:
            Completed Candle if minute boundary crossed, else None
        """
        if coin not in self._aggregators:
            return None

        completed = self._aggregators[coin].add_tick(price, volume)

        if completed and self.on_candle_complete:
            self.on_candle_complete(coin, completed)

        return completed

    def get_aggregator(self, coin: str) -> CandleAggregator | None:
        """Get the aggregator for a specific coin."""
        return self._aggregators.get(coin)

    def get_candles(self, coin: str, include_current: bool = True) -> list[Candle]:
        """Get all candles for a coin."""
        agg = self._aggregators.get(coin)
        if agg:
            return agg.get_all_candles(include_current)
        return []

    def get_ohlc(self, coin: str, include_current: bool = True) -> dict[str, list]:
        """Get OHLC arrays for a coin."""
        agg = self._aggregators.get(coin)
        if agg:
            return agg.get_ohlc_arrays(include_current)
        return {"timestamps": [], "opens": [], "highs": [], "lows": [], "closes": [], "volumes": []}

    def clear_all(self) -> None:
        """Clear all candle data for all coins."""
        for agg in self._aggregators.values():
            agg.clear()
