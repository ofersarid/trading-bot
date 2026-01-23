"""
Technical Indicators Module - Pure math functions for market analysis.

Layer 1 of the 3-layer backtesting architecture.
All functions are stateless and operate on price/candle data.
"""

from .atr import atr
from .macd import MACDResult, macd
from .moving_averages import ema, ema_series, sma
from .rsi import rsi, rsi_series

__all__ = [
    "sma",
    "ema",
    "ema_series",
    "rsi",
    "rsi_series",
    "macd",
    "MACDResult",
    "atr",
]
