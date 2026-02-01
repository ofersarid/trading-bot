"""
Signals Module - Pattern detectors that use indicators to generate trading signals.

Layer 2 of the 3-layer backtesting architecture.
Signal detectors are deterministic and stateful, tracking patterns over time.

Key Components:
- SignalsFactory: Processes raw signals through strategy weights (no AI)
- SignalAggregator: Collects and batches signals from detectors
- Signal: Data class representing a trading signal with optional position info
"""

from .aggregator import SignalAggregator
from .base import Signal, SignalDetector, SignalType
from .detectors import (
    MACDConfig,
    MACDSignalDetector,
    MomentumConfig,
    MomentumSignalDetector,
    PrevDayVPConfig,
    PrevDayVPSignalDetector,
    RSIConfig,
    RSISignalDetector,
    VolumeProfileConfig,
    VolumeProfileSignalDetector,
)
from .factory import FactoryOutput, SignalsFactory
from .validator import SignalValidator, ValidatorConfig

__all__ = [
    # Core types
    "Signal",
    "SignalType",
    "SignalDetector",
    # Factory (signal processing)
    "SignalsFactory",
    "FactoryOutput",
    # Detectors
    "MomentumConfig",
    "MomentumSignalDetector",
    "RSIConfig",
    "RSISignalDetector",
    "MACDConfig",
    "MACDSignalDetector",
    "PrevDayVPConfig",
    "PrevDayVPSignalDetector",
    "VolumeProfileConfig",
    "VolumeProfileSignalDetector",
    # Aggregation and validation
    "SignalAggregator",
    "SignalValidator",
    "ValidatorConfig",
]
