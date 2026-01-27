"""
Signal Detectors - Implementations of trading signal detection algorithms.

Each detector analyzes candle data and produces Signal objects when
patterns are detected.
"""

from .macd import MACDConfig, MACDSignalDetector
from .momentum import MomentumConfig, MomentumSignalDetector
from .rsi import RSIConfig, RSISignalDetector
from .volume_profile import VolumeProfileConfig, VolumeProfileSignalDetector

__all__ = [
    "MACDConfig",
    "MACDSignalDetector",
    "MomentumConfig",
    "MomentumSignalDetector",
    "RSIConfig",
    "RSISignalDetector",
    "VolumeProfileConfig",
    "VolumeProfileSignalDetector",
]
