"""
MACD Indicator - Moving Average Convergence Divergence.

Trend-following momentum indicator showing the relationship
between two exponential moving averages of price.
"""

from dataclasses import dataclass

from .moving_averages import ema_series


@dataclass
class MACDResult:
    """Result of MACD calculation."""

    macd_line: float  # Fast EMA - Slow EMA
    signal_line: float  # EMA of MACD line
    histogram: float  # MACD line - Signal line

    @property
    def is_bullish(self) -> bool:
        """True if MACD is above signal line."""
        return self.histogram > 0

    @property
    def is_bearish(self) -> bool:
        """True if MACD is below signal line."""
        return self.histogram < 0


def macd(
    prices: list[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> MACDResult | None:
    """
    Calculate MACD (Moving Average Convergence Divergence).

    MACD Line = Fast EMA - Slow EMA
    Signal Line = EMA of MACD Line
    Histogram = MACD Line - Signal Line

    Args:
        prices: List of prices (most recent last)
        fast: Fast EMA period (default 12)
        slow: Slow EMA period (default 26)
        signal: Signal line EMA period (default 9)

    Returns:
        MACDResult with macd_line, signal_line, and histogram,
        or None if insufficient data
    """
    # Need enough data for slow EMA + signal period
    min_required = slow + signal - 1
    if len(prices) < min_required or fast <= 0 or slow <= 0 or signal <= 0:
        return None

    if fast >= slow:
        return None  # Fast period must be less than slow

    # Calculate EMA series
    fast_ema = ema_series(prices, fast)
    slow_ema = ema_series(prices, slow)

    if not fast_ema or not slow_ema:
        return None

    # Align the series - fast EMA starts earlier, so trim to match slow EMA length
    # fast_ema has len(prices) - fast + 1 elements
    # slow_ema has len(prices) - slow + 1 elements
    offset = slow - fast
    aligned_fast_ema = fast_ema[offset:]

    # Calculate MACD line series
    macd_line_series = [f - s for f, s in zip(aligned_fast_ema, slow_ema, strict=False)]

    if len(macd_line_series) < signal:
        return None

    # Calculate signal line (EMA of MACD line)
    signal_series = ema_series(macd_line_series, signal)

    if not signal_series:
        return None

    # Get current values
    current_macd = macd_line_series[-1]
    current_signal = signal_series[-1]
    current_histogram = current_macd - current_signal

    return MACDResult(
        macd_line=current_macd,
        signal_line=current_signal,
        histogram=current_histogram,
    )


def macd_series(
    prices: list[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> list[MACDResult]:
    """
    Calculate MACD series for all available data points.

    Useful for detecting crossovers by comparing consecutive values.

    Args:
        prices: List of prices (most recent last)
        fast: Fast EMA period (default 12)
        slow: Slow EMA period (default 26)
        signal: Signal line EMA period (default 9)

    Returns:
        List of MACDResult objects
    """
    min_required = slow + signal - 1
    if len(prices) < min_required or fast <= 0 or slow <= 0 or signal <= 0:
        return []

    if fast >= slow:
        return []

    fast_ema = ema_series(prices, fast)
    slow_ema = ema_series(prices, slow)

    if not fast_ema or not slow_ema:
        return []

    offset = slow - fast
    aligned_fast_ema = fast_ema[offset:]

    macd_line_series = [f - s for f, s in zip(aligned_fast_ema, slow_ema, strict=False)]

    if len(macd_line_series) < signal:
        return []

    signal_series = ema_series(macd_line_series, signal)

    if not signal_series:
        return []

    # Align MACD line with signal series
    signal_offset = signal - 1
    aligned_macd = macd_line_series[signal_offset:]

    results = []
    for m, s in zip(aligned_macd, signal_series, strict=False):
        results.append(MACDResult(macd_line=m, signal_line=s, histogram=m - s))

    return results
