"""
Volume Profile Module.

Provides Volume Profile analysis for trading:
- Data models (Trade, VolumeAtPrice, VolumeProfile)
- Profile builder for aggregating trades
- Indicator functions (POC, Value Area, HVN/LVN, Delta)

This is a Layer 1 indicator in the 3-layer backtesting architecture.
"""

from .builder import MultiSessionProfileBuilder, VolumeProfileBuilder
from .indicator import (
    get_delta_at_price,
    get_delta_extremes,
    get_delta_profile,
    get_hvn_levels,
    get_lvn_levels,
    get_poc,
    get_profile_stats,
    get_total_delta,
    get_value_area,
    is_price_in_value_area,
)
from .models import Trade, VolumeAtPrice, VolumeProfile

__all__ = [
    # Data models
    "Trade",
    "VolumeAtPrice",
    "VolumeProfile",
    # Builders
    "VolumeProfileBuilder",
    "MultiSessionProfileBuilder",
    # Indicator functions
    "get_poc",
    "get_value_area",
    "get_hvn_levels",
    "get_lvn_levels",
    "get_delta_at_price",
    "get_total_delta",
    "get_delta_profile",
    "get_delta_extremes",
    "is_price_in_value_area",
    "get_profile_stats",
]
