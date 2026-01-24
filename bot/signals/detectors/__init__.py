"""
Signal Detectors - Implementations of trading signal detection algorithms.

Each detector analyzes candle data and produces Signal objects when
patterns are detected.
"""

from .macd import MACDConfig, MACDSignalDetector
from .momentum import MomentumConfig, MomentumSignalDetector
from .rsi import RSIConfig, RSISignalDetector

__all__ = [
    "MACDConfig",
    "MACDSignalDetector",
    "MomentumConfig",
    "MomentumSignalDetector",
    "RSIConfig",
    "RSISignalDetector",
]
