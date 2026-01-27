"""
Technical Indicators Module - Pure math functions for market analysis.

Layer 1 of the 3-layer backtesting architecture.
All functions are stateless and operate on price/candle data.
"""

from .atr import atr
from .macd import MACDResult, macd
from .moving_averages import ema, ema_series, sma
from .rsi import rsi, rsi_series
from .volume_profile import (
    MultiSessionProfileBuilder,
    Trade,
    VolumeAtPrice,
    VolumeProfile,
    VolumeProfileBuilder,
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

__all__ = [
    # Moving Averages
    "sma",
    "ema",
    "ema_series",
    # RSI
    "rsi",
    "rsi_series",
    # MACD
    "macd",
    "MACDResult",
    # ATR
    "atr",
    # Volume Profile - Models
    "Trade",
    "VolumeAtPrice",
    "VolumeProfile",
    # Volume Profile - Builders
    "VolumeProfileBuilder",
    "MultiSessionProfileBuilder",
    # Volume Profile - Functions
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
