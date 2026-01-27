"""
Volume Profile Indicator Functions.

Pure functions for analyzing Volume Profile data.
These are Layer 1 indicators - stateless functions that compute
analysis values from profile data.

Functions:
- get_poc: Point of Control (highest volume level)
- get_value_area: Price range containing 70% of volume
- get_hvn_levels: High Volume Nodes
- get_lvn_levels: Low Volume Nodes
- get_delta_at_price: Delta at specific price
- get_total_delta: Overall delta
"""

from .models import VolumeProfile


def get_poc(profile: VolumeProfile) -> float | None:
    """
    Point of Control - price level with highest volume.

    The POC represents the "fair value" where most trading occurred.
    It often acts as a magnet for price.

    Args:
        profile: VolumeProfile to analyze

    Returns:
        Price level with maximum total_volume, or None if profile is empty
    """
    if not profile.levels:
        return None

    return max(profile.levels, key=lambda p: profile.levels[p].total_volume)


def get_value_area(
    profile: VolumeProfile,
    percentage: float = 0.70,
) -> tuple[float, float] | None:
    """
    Value Area - price range containing specified percentage of volume.

    The Value Area represents where most trading activity occurred.
    Typically set to 70% (one standard deviation in normal distribution).

    Algorithm:
    1. Start at POC
    2. Expand alternately above and below
    3. Add level with higher volume until target % reached

    Args:
        profile: VolumeProfile to analyze
        percentage: Target volume percentage (default 0.70 = 70%)

    Returns:
        (value_area_low, value_area_high) or None if profile is empty
    """
    if not profile.levels:
        return None

    total_volume = profile.total_volume
    if total_volume == 0:
        return None

    target_volume = total_volume * percentage

    # Get sorted price levels
    sorted_prices = sorted(profile.levels.keys())
    if len(sorted_prices) == 0:
        return None

    # Find POC index
    poc = get_poc(profile)
    if poc is None:
        return None

    poc_idx = sorted_prices.index(poc)

    # Initialize value area with POC
    va_low_idx = poc_idx
    va_high_idx = poc_idx
    accumulated_volume = profile.levels[poc].total_volume

    # Expand until we reach target volume
    while accumulated_volume < target_volume:
        # Get volumes above and below current VA
        volume_above = 0.0
        volume_below = 0.0

        if va_high_idx + 1 < len(sorted_prices):
            volume_above = profile.levels[sorted_prices[va_high_idx + 1]].total_volume

        if va_low_idx - 1 >= 0:
            volume_below = profile.levels[sorted_prices[va_low_idx - 1]].total_volume

        # If no more levels to add, we're done
        if volume_above == 0 and volume_below == 0:
            break

        # Add the side with more volume
        if volume_above >= volume_below:
            va_high_idx += 1
            accumulated_volume += volume_above
        else:
            va_low_idx -= 1
            accumulated_volume += volume_below

    return (sorted_prices[va_low_idx], sorted_prices[va_high_idx])


def get_hvn_levels(
    profile: VolumeProfile,
    threshold_pct: float = 0.8,
    min_levels: int = 1,
) -> list[float]:
    """
    High Volume Nodes - price levels with above-threshold volume.

    HVNs are areas of price acceptance where significant trading occurred.
    They often act as support/resistance zones.

    Args:
        profile: VolumeProfile to analyze
        threshold_pct: Percentile threshold (0.8 = top 20% by volume)
        min_levels: Minimum number of HVN levels to return

    Returns:
        List of price levels that are HVNs, sorted by volume (highest first)
    """
    if not profile.levels:
        return []

    # Sort levels by volume
    sorted_levels = sorted(
        profile.levels.items(),
        key=lambda x: x[1].total_volume,
        reverse=True,
    )

    # Calculate threshold
    volumes = [level.total_volume for _, level in sorted_levels]
    if not volumes:
        return []

    # Get top percentile
    cutoff_idx = max(min_levels, int(len(volumes) * (1 - threshold_pct)))
    hvn_levels = [price for price, _ in sorted_levels[:cutoff_idx]]

    return hvn_levels


def get_lvn_levels(
    profile: VolumeProfile,
    threshold_pct: float = 0.2,
    min_levels: int = 1,
) -> list[float]:
    """
    Low Volume Nodes - price levels with below-threshold volume.

    LVNs are areas of price rejection where trading was sparse.
    Price tends to move quickly through these levels.

    Args:
        profile: VolumeProfile to analyze
        threshold_pct: Percentile threshold (0.2 = bottom 20% by volume)
        min_levels: Minimum number of LVN levels to return

    Returns:
        List of price levels that are LVNs, sorted by volume (lowest first)
    """
    if not profile.levels:
        return []

    # Sort levels by volume (ascending)
    sorted_levels = sorted(
        profile.levels.items(),
        key=lambda x: x[1].total_volume,
    )

    # Calculate threshold
    volumes = [level.total_volume for _, level in sorted_levels]
    if not volumes:
        return []

    # Get bottom percentile
    cutoff_idx = max(min_levels, int(len(volumes) * threshold_pct))
    lvn_levels = [price for price, _ in sorted_levels[:cutoff_idx]]

    return lvn_levels


def get_delta_at_price(profile: VolumeProfile, price: float) -> float:
    """
    Get net delta (buy - sell volume) at a specific price level.

    Delta indicates buying/selling pressure:
    - Positive delta = more aggressive buyers
    - Negative delta = more aggressive sellers

    Args:
        profile: VolumeProfile to analyze
        price: Price level to check

    Returns:
        Delta value (buy_volume - sell_volume) at the price level, or 0 if not found
    """
    # Round to tick size bucket
    bucket = round(price / profile.tick_size) * profile.tick_size
    level = profile.levels.get(bucket)

    return level.delta if level else 0.0


def get_total_delta(profile: VolumeProfile) -> float:
    """
    Get total delta for the entire profile.

    Indicates overall buying/selling pressure for the session.

    Args:
        profile: VolumeProfile to analyze

    Returns:
        Total delta (sum of all level deltas)
    """
    return sum(level.delta for level in profile.levels.values())


def get_delta_profile(profile: VolumeProfile) -> dict[float, float]:
    """
    Get delta at each price level.

    Useful for identifying areas of buying/selling imbalance.

    Args:
        profile: VolumeProfile to analyze

    Returns:
        Dictionary mapping price -> delta
    """
    return {price: level.delta for price, level in profile.levels.items()}


def get_delta_extremes(
    profile: VolumeProfile,
    top_n: int = 3,
) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """
    Get price levels with most extreme delta values.

    Args:
        profile: VolumeProfile to analyze
        top_n: Number of extreme levels to return

    Returns:
        (highest_delta_levels, lowest_delta_levels)
        Each is a list of (price, delta) tuples
    """
    if not profile.levels:
        return ([], [])

    # Sort by delta
    sorted_by_delta = sorted(
        [(price, level.delta) for price, level in profile.levels.items()],
        key=lambda x: x[1],
        reverse=True,
    )

    highest = sorted_by_delta[:top_n]
    lowest = sorted_by_delta[-top_n:][::-1]  # Reverse to get most negative first

    return (highest, lowest)


def is_price_in_value_area(
    profile: VolumeProfile,
    price: float,
    percentage: float = 0.70,
) -> bool:
    """
    Check if a price is within the value area.

    Args:
        profile: VolumeProfile to analyze
        price: Price to check
        percentage: Value area percentage

    Returns:
        True if price is within value area
    """
    va = get_value_area(profile, percentage)
    if va is None:
        return False

    va_low, va_high = va
    return va_low <= price <= va_high


def get_profile_stats(profile: VolumeProfile) -> dict:
    """
    Get comprehensive statistics for a volume profile.

    Args:
        profile: VolumeProfile to analyze

    Returns:
        Dictionary with profile statistics
    """
    poc = get_poc(profile)
    va = get_value_area(profile)
    hvn = get_hvn_levels(profile)
    lvn = get_lvn_levels(profile)
    delta_extremes = get_delta_extremes(profile)

    return {
        "poc": poc,
        "value_area": va,
        "value_area_low": va[0] if va else None,
        "value_area_high": va[1] if va else None,
        "total_volume": profile.total_volume,
        "total_delta": get_total_delta(profile),
        "total_delta_pct": profile.total_delta_pct,
        "level_count": profile.level_count,
        "price_range": profile.price_range,
        "hvn_levels": hvn,
        "lvn_levels": lvn,
        "highest_delta_levels": delta_extremes[0],
        "lowest_delta_levels": delta_extremes[1],
        "session_start": profile.session_start,
        "session_end": profile.session_end,
    }
