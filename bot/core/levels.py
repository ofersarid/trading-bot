"""
Structure-Aware TP/SL Calculator.

Calculates Take Profit and Stop Loss levels based on market structure
(support/resistance from Volume Profile) rather than pure ATR.

Key Concepts:
- Support: Price levels where buying pressure historically halts declines
  (VAL, HVNs below price, POC if below)
- Resistance: Price levels where selling pressure historically halts advances
  (VAH, HVNs above price, POC if above)

For LONG positions:
- Stop Loss: Below nearest support
- Take Profit: At nearest resistance

For SHORT positions:
- Stop Loss: Above nearest resistance
- Take Profit: At nearest support

ATR serves as a sanity check - if structural levels are too far,
we cap at reasonable ATR multiples.
"""

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class StructureLevels:
    """
    Aggregated structure levels for TP/SL calculation.

    Combines Volume Profile levels (POC, VAH, VAL) with optional
    High Volume Nodes for more precise support/resistance identification.
    """

    poc: float | None = None  # Point of Control - acts as magnet
    vah: float | None = None  # Value Area High - resistance/support
    val: float | None = None  # Value Area Low - support/resistance
    hvn_levels: list[float] = field(default_factory=list)  # High Volume Nodes

    def get_all_levels(self) -> list[float]:
        """Get all structure levels as a sorted list."""
        levels = []
        if self.poc is not None:
            levels.append(self.poc)
        if self.vah is not None:
            levels.append(self.vah)
        if self.val is not None:
            levels.append(self.val)
        levels.extend(self.hvn_levels)
        return sorted(set(levels))

    def has_levels(self) -> bool:
        """Check if any structure levels are available."""
        return any([self.poc, self.vah, self.val, self.hvn_levels])


@dataclass
class StructureTPSL:
    """
    Result of structure-aware TP/SL calculation.

    Contains the calculated levels along with metadata about
    what structure levels were used.
    """

    stop_loss: float
    take_profit: float
    stop_reason: str  # What structure level the SL is based on
    tp_reason: str  # What structure level the TP is based on
    used_atr_fallback: bool = False  # True if ATR was used due to no structure


def find_nearest_support(
    current_price: float,
    levels: StructureLevels,
    min_distance_pct: float = 0.1,
) -> tuple[float | None, str]:
    """
    Find the nearest support level below current price.

    Support levels are prices where buying pressure historically
    prevents further decline. In order of typical strength:
    1. VAL (Value Area Low) - strong support if price is above VA
    2. POC (Point of Control) - magnet level, support if price is above
    3. HVNs (High Volume Nodes) - areas of price acceptance

    Args:
        current_price: Current market price
        levels: Structure levels to search
        min_distance_pct: Minimum distance from price to consider (0.1 = 0.1%)

    Returns:
        (support_price, reason) or (None, "") if no support found
    """
    min_distance = current_price * (min_distance_pct / 100)
    candidates: list[tuple[float, str, int]] = []  # (price, reason, priority)

    # VAL is strong support if we're above the value area
    if levels.val is not None and levels.val < current_price - min_distance:
        # Higher priority if we're above VAH (price is above entire VA)
        priority = 1 if levels.vah and current_price > levels.vah else 2
        candidates.append((levels.val, "VAL (Value Area Low)", priority))

    # POC is support if price is above it
    if levels.poc is not None and levels.poc < current_price - min_distance:
        candidates.append((levels.poc, "POC (Point of Control)", 3))

    # HVNs below price act as support
    for hvn in levels.hvn_levels:
        if hvn < current_price - min_distance:
            candidates.append((hvn, f"HVN @ ${hvn:,.0f}", 4))

    if not candidates:
        return None, ""

    # Sort by priority first, then by distance (closest first)
    candidates.sort(key=lambda x: (x[2], current_price - x[0]))

    # Return closest by priority
    return candidates[0][0], candidates[0][1]


def find_nearest_resistance(
    current_price: float,
    levels: StructureLevels,
    min_distance_pct: float = 0.1,
) -> tuple[float | None, str]:
    """
    Find the nearest resistance level above current price.

    Resistance levels are prices where selling pressure historically
    prevents further advance. In order of typical strength:
    1. VAH (Value Area High) - strong resistance if price is below VA
    2. POC (Point of Control) - magnet level, resistance if price is below
    3. HVNs (High Volume Nodes) - areas of price acceptance

    Args:
        current_price: Current market price
        levels: Structure levels to search
        min_distance_pct: Minimum distance from price to consider (0.1 = 0.1%)

    Returns:
        (resistance_price, reason) or (None, "") if no resistance found
    """
    min_distance = current_price * (min_distance_pct / 100)
    candidates: list[tuple[float, str, int]] = []  # (price, reason, priority)

    # VAH is strong resistance if we're below the value area
    if levels.vah is not None and levels.vah > current_price + min_distance:
        # Higher priority if we're below VAL (price is below entire VA)
        priority = 1 if levels.val and current_price < levels.val else 2
        candidates.append((levels.vah, "VAH (Value Area High)", priority))

    # POC is resistance if price is below it
    if levels.poc is not None and levels.poc > current_price + min_distance:
        candidates.append((levels.poc, "POC (Point of Control)", 3))

    # HVNs above price act as resistance
    for hvn in levels.hvn_levels:
        if hvn > current_price + min_distance:
            candidates.append((hvn, f"HVN @ ${hvn:,.0f}", 4))

    if not candidates:
        return None, ""

    # Sort by priority first, then by distance (closest first)
    candidates.sort(key=lambda x: (x[2], x[0] - current_price))

    # Return closest by priority
    return candidates[0][0], candidates[0][1]


def calculate_structure_tp_sl(
    direction: Literal["LONG", "SHORT"],
    current_price: float,
    levels: StructureLevels,
    atr: float,
    max_sl_atr_mult: float = 2.0,
    max_tp_atr_mult: float = 4.0,
    min_rr_ratio: float = 1.5,
    sl_buffer_pct: float = 0.1,
) -> StructureTPSL:
    """
    Calculate structure-aware Take Profit and Stop Loss levels.

    Uses Volume Profile structure levels (support/resistance) when available,
    with ATR as a sanity check and fallback.

    For LONG:
    - SL below nearest support (or ATR-based if no support)
    - TP at nearest resistance (or ATR-based if no resistance)

    For SHORT:
    - SL above nearest resistance (or ATR-based if no resistance)
    - TP at nearest support (or ATR-based if no support)

    Args:
        direction: Trade direction ("LONG" or "SHORT")
        current_price: Current market price
        levels: Structure levels for support/resistance
        atr: Current ATR value for sanity checks and fallback
        max_sl_atr_mult: Maximum SL distance as ATR multiple (default 2.0)
        max_tp_atr_mult: Maximum TP distance as ATR multiple (default 4.0)
        min_rr_ratio: Minimum risk/reward ratio to enforce (default 1.5)
        sl_buffer_pct: Buffer to add beyond structure level for SL (default 0.1%)

    Returns:
        StructureTPSL with calculated levels and reasons
    """
    used_atr_fallback = False

    if direction == "LONG":
        # Find support for SL and resistance for TP
        support_price, support_reason = find_nearest_support(current_price, levels)
        resistance_price, resistance_reason = find_nearest_resistance(current_price, levels)

        # Calculate SL
        if support_price is not None:
            # Place SL slightly below support with buffer
            sl_buffer = support_price * (sl_buffer_pct / 100)
            stop_loss = support_price - sl_buffer
            stop_reason = f"Below {support_reason}"

            # Cap at max ATR distance
            max_sl = current_price - (atr * max_sl_atr_mult)
            if stop_loss < max_sl:
                stop_loss = max_sl
                stop_reason = f"ATR-capped (structure too far: {support_reason})"
        else:
            # Fallback to ATR-based SL
            stop_loss = current_price - (atr * 1.5)
            stop_reason = "ATR-based (no structure support found)"
            used_atr_fallback = True

        # Calculate TP
        if resistance_price is not None:
            take_profit = resistance_price
            tp_reason = f"At {resistance_reason}"

            # Cap at max ATR distance
            max_tp = current_price + (atr * max_tp_atr_mult)
            if take_profit > max_tp:
                take_profit = max_tp
                tp_reason = f"ATR-capped (structure too far: {resistance_reason})"
        else:
            # Fallback to ATR-based TP
            take_profit = current_price + (atr * 2.5)
            tp_reason = "ATR-based (no structure resistance found)"
            used_atr_fallback = True

    else:  # SHORT
        # Find resistance for SL and support for TP
        resistance_price, resistance_reason = find_nearest_resistance(current_price, levels)
        support_price, support_reason = find_nearest_support(current_price, levels)

        # Calculate SL
        if resistance_price is not None:
            # Place SL slightly above resistance with buffer
            sl_buffer = resistance_price * (sl_buffer_pct / 100)
            stop_loss = resistance_price + sl_buffer
            stop_reason = f"Above {resistance_reason}"

            # Cap at max ATR distance
            max_sl = current_price + (atr * max_sl_atr_mult)
            if stop_loss > max_sl:
                stop_loss = max_sl
                stop_reason = f"ATR-capped (structure too far: {resistance_reason})"
        else:
            # Fallback to ATR-based SL
            stop_loss = current_price + (atr * 1.5)
            stop_reason = "ATR-based (no structure resistance found)"
            used_atr_fallback = True

        # Calculate TP
        if support_price is not None:
            take_profit = support_price
            tp_reason = f"At {support_reason}"

            # Cap at max ATR distance
            max_tp = current_price - (atr * max_tp_atr_mult)
            if take_profit < max_tp:
                take_profit = max_tp
                tp_reason = f"ATR-capped (structure too far: {support_reason})"
        else:
            # Fallback to ATR-based TP
            take_profit = current_price - (atr * 2.5)
            tp_reason = "ATR-based (no structure support found)"
            used_atr_fallback = True

    # Enforce minimum risk/reward ratio
    risk = abs(current_price - stop_loss)
    reward = abs(take_profit - current_price)

    if risk > 0 and reward / risk < min_rr_ratio:
        # Extend TP to meet minimum R:R
        min_reward = risk * min_rr_ratio
        if direction == "LONG":
            take_profit = current_price + min_reward
            tp_reason = f"{tp_reason} (extended for {min_rr_ratio}:1 R:R)"
        else:
            take_profit = current_price - min_reward
            tp_reason = f"{tp_reason} (extended for {min_rr_ratio}:1 R:R)"

    return StructureTPSL(
        stop_loss=stop_loss,
        take_profit=take_profit,
        stop_reason=stop_reason,
        tp_reason=tp_reason,
        used_atr_fallback=used_atr_fallback,
    )
