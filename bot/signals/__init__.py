"""
Signals Module - Pattern detectors that use indicators to generate trading signals.

Layer 2 of the 3-layer backtesting architecture.
Signal detectors are deterministic and stateful, tracking patterns over time.
"""

from .aggregator import SignalAggregator
from .base import Signal, SignalDetector, SignalType
from .macd import MACDSignalDetector
from .momentum import MomentumSignalDetector
from .rsi import RSISignalDetector
from .validator import SignalValidator, ValidatorConfig

__all__ = [
    "Signal",
    "SignalType",
    "SignalDetector",
    "MomentumSignalDetector",
    "RSISignalDetector",
    "MACDSignalDetector",
    "SignalAggregator",
    "SignalValidator",
    "ValidatorConfig",
]
