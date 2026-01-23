"""
RSI Indicator - Relative Strength Index calculation.

Measures the speed and magnitude of recent price changes
to evaluate overbought or oversold conditions.
"""


def rsi(prices: list[float], period: int = 14) -> float | None:
    """
    Calculate Relative Strength Index.

    RSI = 100 - (100 / (1 + RS))
    RS = Average Gain / Average Loss over the period

    Args:
        prices: List of prices (most recent last), needs period + 1 prices minimum
        period: Lookback period (default 14)

    Returns:
        RSI value (0-100) or None if insufficient data
    """
    # Need at least period + 1 prices to calculate period changes
    if len(prices) < period + 1 or period <= 0:
        return None

    # Calculate price changes
    changes = [prices[i] - prices[i - 1] for i in range(1, len(prices))]

    # Use only the most recent 'period' changes for initial calculation
    recent_changes = changes[-(period):]

    gains = [change if change > 0 else 0 for change in recent_changes]
    losses = [-change if change < 0 else 0 for change in recent_changes]

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    # Handle edge case where there are no losses
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0

    rs = avg_gain / avg_loss
    rsi_value = 100 - (100 / (1 + rs))

    return rsi_value


def rsi_series(prices: list[float], period: int = 14) -> list[float]:
    """
    Calculate RSI series for all valid points.

    Returns RSI values starting from index (period) in the price list.

    Args:
        prices: List of prices (most recent last)
        period: Lookback period (default 14)

    Returns:
        List of RSI values, one for each point where calculation is possible
    """
    if len(prices) < period + 1 or period <= 0:
        return []

    result: list[float] = []

    # Calculate RSI for each valid window
    for i in range(period, len(prices)):
        window_prices = prices[: i + 1]
        rsi_val = rsi(window_prices, period)
        if rsi_val is not None:
            result.append(rsi_val)

    return result


def rsi_smoothed(prices: list[float], period: int = 14) -> float | None:
    """
    Calculate RSI using Wilder's smoothing method.

    This is the traditional RSI calculation that uses exponential smoothing
    for the average gain and average loss after the initial SMA.

    Args:
        prices: List of prices (most recent last)
        period: Lookback period (default 14)

    Returns:
        RSI value (0-100) or None if insufficient data
    """
    # Need at least period + 1 prices for initial SMA, then more for smoothing
    if len(prices) < period + 1 or period <= 0:
        return None

    # Calculate all price changes
    changes = [prices[i] - prices[i - 1] for i in range(1, len(prices))]

    # Initial SMA for first 'period' changes
    initial_gains = [c if c > 0 else 0 for c in changes[:period]]
    initial_losses = [-c if c < 0 else 0 for c in changes[:period]]

    avg_gain = sum(initial_gains) / period
    avg_loss = sum(initial_losses) / period

    # Apply Wilder's smoothing for remaining changes
    for change in changes[period:]:
        gain = change if change > 0 else 0
        loss = -change if change < 0 else 0

        # Wilder's smoothing: (prev_avg * (period-1) + current) / period
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))
