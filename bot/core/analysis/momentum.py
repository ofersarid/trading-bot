"""
Momentum calculation utilities.

Provides functions for calculating price momentum over configurable timeframes.
"""

from collections import deque
from datetime import datetime


def calculate_momentum(
    current_price: float,
    price_history: deque[dict],
    lookback_seconds: int,
) -> float | None:
    """
    Calculate price momentum over a lookback period.
    
    Args:
        current_price: The current price of the asset
        price_history: Deque of price points with 'price' and 'time' keys
        lookback_seconds: Number of seconds to look back for comparison
    
    Returns:
        Momentum as a percentage, or None if insufficient history
    """
    if not price_history or len(price_history) < 2:
        return None
    
    if not current_price:
        return None
    
    now = datetime.now()
    lookback_price = None
    
    for point in price_history:
        age = (now - point["time"]).total_seconds()
        if age >= lookback_seconds:
            lookback_price = point["price"]
            break
    
    if lookback_price is None:
        return None
    
    return ((current_price - lookback_price) / lookback_price) * 100


def get_lookback_price(
    price_history: deque[dict],
    lookback_seconds: int,
) -> tuple[float | None, float]:
    """
    Get the price from N seconds ago and the actual age.
    
    Args:
        price_history: Deque of price points with 'price' and 'time' keys
        lookback_seconds: Target number of seconds to look back
    
    Returns:
        Tuple of (price or None, actual age in seconds)
    """
    if not price_history:
        return None, 0.0
    
    now = datetime.now()
    
    for point in price_history:
        age = (now - point["time"]).total_seconds()
        if age >= lookback_seconds:
            return point["price"], age
    
    return None, 0.0
