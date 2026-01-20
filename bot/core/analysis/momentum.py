"""
Momentum calculation utilities.

Provides functions for calculating price momentum over configurable timeframes.
Includes smoothed velocity and acceleration for distinguishing building vs fading moves.
"""

from collections import deque
from dataclasses import dataclass
from datetime import datetime


def calculate_momentum(
    current_price: float,
    price_history: deque[dict],
    lookback_seconds: int,
) -> float | None:
    """
    Calculate smoothed price momentum over a lookback period.

    Uses average price over the lookback window instead of a single point,
    which reduces noise from individual tick variations.

    Args:
        current_price: The current price of the asset
        price_history: Deque of price points with 'price' and 'time' keys
        lookback_seconds: Number of seconds to look back for averaging

    Returns:
        Momentum as a percentage, or None if insufficient history
    """
    if not price_history or len(price_history) < 2:
        return None

    if not current_price:
        return None

    now = datetime.now()
    prices_in_window = []

    for point in price_history:
        age = (now - point["time"]).total_seconds()
        if age <= lookback_seconds:
            prices_in_window.append(point["price"])

    if not prices_in_window:
        return None

    avg_price = sum(prices_in_window) / len(prices_in_window)
    return float((current_price - avg_price) / avg_price) * 100


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


@dataclass
class MomentumResult:
    """
    Momentum calculation result with velocity and acceleration.

    Velocity is the smoothed momentum percentage.
    Acceleration indicates whether momentum is building (positive) or fading (negative).
    """

    velocity: float  # Smoothed momentum %
    acceleration: float  # Rate of change of velocity
    is_building: bool  # True if acceleration >= 0


def calculate_momentum_with_acceleration(
    current_price: float,
    price_history: deque[dict],
    lookback_seconds: int,
    previous_velocity: float | None = None,
) -> MomentumResult | None:
    """
    Calculate momentum with acceleration for trade quality assessment.

    Acceleration helps distinguish between building moves (worth entering)
    and fading moves (avoid chasing).

    Args:
        current_price: The current price of the asset
        price_history: Deque of price points with 'price' and 'time' keys
        lookback_seconds: Number of seconds to look back for averaging
        previous_velocity: The velocity from the previous calculation cycle

    Returns:
        MomentumResult with velocity, acceleration, and is_building flag,
        or None if insufficient history
    """
    velocity = calculate_momentum(current_price, price_history, lookback_seconds)
    if velocity is None:
        return None

    acceleration = 0.0
    if previous_velocity is not None:
        acceleration = velocity - previous_velocity

    return MomentumResult(
        velocity=velocity,
        acceleration=acceleration,
        is_building=acceleration >= 0,
    )
