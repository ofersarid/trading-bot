"""
Moving Average Indicators - SMA and EMA calculations.

Pure math functions for calculating simple and exponential moving averages.
"""


def sma(prices: list[float], period: int) -> float | None:
    """
    Calculate Simple Moving Average.

    Args:
        prices: List of prices (most recent last)
        period: Number of periods to average

    Returns:
        SMA value or None if insufficient data
    """
    if len(prices) < period or period <= 0:
        return None

    return sum(prices[-period:]) / period


def ema(prices: list[float], period: int) -> float | None:
    """
    Calculate Exponential Moving Average.

    Uses the standard EMA formula with multiplier = 2 / (period + 1).
    The first EMA value is seeded with SMA.

    Args:
        prices: List of prices (most recent last)
        period: Number of periods for EMA calculation

    Returns:
        Current EMA value or None if insufficient data
    """
    if len(prices) < period or period <= 0:
        return None

    series = ema_series(prices, period)
    return series[-1] if series else None


def ema_series(prices: list[float], period: int) -> list[float]:
    """
    Calculate EMA series for all available data points.

    Useful for MACD calculation which needs the full EMA history.

    Args:
        prices: List of prices (most recent last)
        period: Number of periods for EMA calculation

    Returns:
        List of EMA values (same length as prices minus period + 1)
    """
    if len(prices) < period or period <= 0:
        return []

    multiplier = 2 / (period + 1)
    result: list[float] = []

    # Seed with SMA for the first value
    initial_sma = sum(prices[:period]) / period
    result.append(initial_sma)

    # Calculate EMA for remaining prices
    for price in prices[period:]:
        prev_ema = result[-1]
        current_ema = (price - prev_ema) * multiplier + prev_ema
        result.append(current_ema)

    return result
