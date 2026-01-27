"""
Signals Module - Pattern detectors that use indicators to generate trading signals.

Layer 2 of the 3-layer backtesting architecture.
Signal detectors are deterministic and stateful, tracking patterns over time.
"""

from .aggregator import SignalAggregator
from .base import Signal, SignalDetector, SignalType
from .detectors import (
    MACDConfig,
    MACDSignalDetector,
    MomentumConfig,
    MomentumSignalDetector,
    RSIConfig,
    RSISignalDetector,
    VolumeProfileConfig,
    VolumeProfileSignalDetector,
)
from .validator import SignalValidator, ValidatorConfig

__all__ = [
    "Signal",
    "SignalType",
    "SignalDetector",
    "MomentumConfig",
    "MomentumSignalDetector",
    "RSIConfig",
    "RSISignalDetector",
    "MACDConfig",
    "MACDSignalDetector",
    "VolumeProfileConfig",
    "VolumeProfileSignalDetector",
    "SignalAggregator",
    "SignalValidator",
    "ValidatorConfig",
]
