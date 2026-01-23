"""
ATR Indicator - Average True Range.

Measures market volatility by calculating the average of true ranges
over a specified period. Used for position sizing and stop-loss placement.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


class CandleLike(Protocol):
    """Protocol for candle-like objects with OHLC data."""

    high: float
    low: float
    close: float


@dataclass
class ATRCandle:
    """Minimal candle structure for ATR calculation."""

    high: float
    low: float
    close: float


def true_range(current: CandleLike, previous_close: float | None = None) -> float:
    """
    Calculate True Range for a single candle.

    True Range is the greatest of:
    1. Current High - Current Low
    2. |Current High - Previous Close|
    3. |Current Low - Previous Close|

    Args:
        current: Current candle with high, low, close
        previous_close: Previous candle's close price (None for first candle)

    Returns:
        True Range value
    """
    high_low = current.high - current.low

    if previous_close is None:
        return high_low

    high_prev_close = abs(current.high - previous_close)
    low_prev_close = abs(current.low - previous_close)

    return max(high_low, high_prev_close, low_prev_close)


def atr(candles: Sequence[CandleLike], period: int = 14) -> float | None:
    """
    Calculate Average True Range.

    Uses Wilder's smoothing method (same as RSI) for the average.

    Args:
        candles: List of candles with high, low, close (most recent last)
        period: Lookback period (default 14)

    Returns:
        ATR value or None if insufficient data
    """
    if len(candles) < period + 1 or period <= 0:
        return None

    # Calculate true ranges
    true_ranges: list[float] = []

    # First candle has no previous close
    true_ranges.append(true_range(candles[0]))

    # Remaining candles use previous close
    for i in range(1, len(candles)):
        tr = true_range(candles[i], candles[i - 1].close)
        true_ranges.append(tr)

    # Initial ATR is SMA of first 'period' true ranges
    initial_atr = sum(true_ranges[:period]) / period

    # Apply Wilder's smoothing for remaining values
    current_atr = initial_atr
    for tr in true_ranges[period:]:
        current_atr = (current_atr * (period - 1) + tr) / period

    return current_atr


def atr_series(candles: list[CandleLike], period: int = 14) -> list[float]:
    """
    Calculate ATR series for all available data points.

    Args:
        candles: List of candles with high, low, close (most recent last)
        period: Lookback period (default 14)

    Returns:
        List of ATR values
    """
    if len(candles) < period + 1 or period <= 0:
        return []

    # Calculate all true ranges
    true_ranges: list[float] = [true_range(candles[0])]

    for i in range(1, len(candles)):
        tr = true_range(candles[i], candles[i - 1].close)
        true_ranges.append(tr)

    # Calculate ATR series using Wilder's smoothing
    result: list[float] = []

    # Initial ATR
    initial_atr = sum(true_ranges[:period]) / period
    result.append(initial_atr)

    # Smoothed ATR for remaining
    current_atr = initial_atr
    for tr in true_ranges[period:]:
        current_atr = (current_atr * (period - 1) + tr) / period
        result.append(current_atr)

    return result


def atr_percent(candles: list[CandleLike], period: int = 14) -> float | None:
    """
    Calculate ATR as a percentage of the current price.

    Useful for comparing volatility across different price levels.

    Args:
        candles: List of candles with high, low, close (most recent last)
        period: Lookback period (default 14)

    Returns:
        ATR as percentage of current close, or None if insufficient data
    """
    atr_value = atr(candles, period)
    if atr_value is None:
        return None

    current_close = candles[-1].close
    if current_close == 0:
        return None

    return (atr_value / current_close) * 100
