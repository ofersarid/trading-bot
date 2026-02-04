"""
Base classes for trading strategies.

Defines the core dataclasses that all strategies use:
- StrategyType: Enum of available strategy types
- RiskConfig: Risk management parameters
- Strategy: Complete strategy definition
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot.signals.base import ExitLevelSource, SignalType


class StrategyType(Enum):
    """Available strategy types."""

    MOMENTUM_BASED = "momentum_based"  # Primary: MOMENTUM
    MOMENTUM_MACD = "momentum_macd"  # Primary: MOMENTUM + MACD confirmation
    RSI_BASED = "rsi_based"  # Primary: RSI
    MULTI_SIGNAL = "multi_signal"  # Balanced: Multiple signals required
    EQUAL_WEIGHT = "equal_weight"  # All signals weighted equally at 0.5


# Backwards compatibility alias
TradingStrategy = StrategyType


@dataclass
class RiskConfig:
    """Risk management configuration for a strategy."""

    max_position_pct: float = 10.0  # Max % of balance per trade
    stop_loss_atr_multiplier: float = 1.5  # SL = entry ± ATR * multiplier
    take_profit_atr_multiplier: float = 2.0  # TP = entry ± ATR * multiplier
    trail_activation_pct: float = 0.5  # When to activate trailing (% profit)
    trail_distance_pct: float = 0.3  # Trail distance as % of price

    def __post_init__(self) -> None:
        """Validate risk parameters."""
        if not 0 < self.max_position_pct <= 100:
            raise ValueError("max_position_pct must be between 0 and 100")
        if self.stop_loss_atr_multiplier <= 0:
            raise ValueError("stop_loss_atr_multiplier must be positive")
        if self.take_profit_atr_multiplier <= 0:
            raise ValueError("take_profit_atr_multiplier must be positive")


@dataclass
class Strategy:
    """
    A trading strategy configuration.

    Defines signal weights and risk parameters for trading decisions.
    The strategy is ONLY configuration - no prompts or AI logic.
    AI position sizing is handled separately by GoalBasedSizer.

    Signal Weighting (Entry):
        Each signal type has a weight (0.0-1.0) that determines its importance.
        The weighted score = sum(weight * signal_strength) for each direction.
        A trade is considered when the score meets the signal_threshold.

    Exit Level Configuration:
        exit_level_sources defines which structural levels to use for TP/SL.
        The ExitLevelProvider finds confluent levels from these sources.
        Falls back to ATR-based calculation if no structural levels found.
    """

    name: str
    strategy_type: StrategyType
    risk: RiskConfig = field(default_factory=RiskConfig)

    # Signal weighting - maps SignalType to importance weight (0.0-1.0)
    # Signals not in this dict are ignored by the strategy
    signal_weights: dict["SignalType", float] = field(default_factory=dict)

    # Minimum weighted score to consider a trade (e.g., 0.7 = 70%)
    signal_threshold: float = 0.5

    # Noise filter - ignore signals below this strength regardless of weight
    min_signal_strength: float = 0.2

    # AI confidence threshold (1-10)
    min_confidence: int = 6

    # Exit level configuration
    # Sources for exit level calculation, ordered by priority
    # Default is ATR_MULTIPLIER only (current behavior)
    exit_level_sources: list["ExitLevelSource"] = field(default_factory=list)

    # How close levels must be to be considered confluent (as % of VA range)
    confluence_distance_pct: float = 0.3

    # Minimum number of sources that must agree for a confluent level
    min_confluence_sources: int = 1

    # Fallback ATR multipliers when no structural levels found
    fallback_sl_atr_multiplier: float = 1.5
    fallback_tp_atr_multiplier: float = 2.0

    def __post_init__(self) -> None:
        """Validate strategy configuration."""
        if not 0 <= self.signal_threshold <= 2.0:
            raise ValueError("signal_threshold must be between 0 and 2.0")
        if not 0 <= self.min_signal_strength <= 1:
            raise ValueError("min_signal_strength must be between 0 and 1")
        if not 1 <= self.min_confidence <= 10:
            raise ValueError("min_confidence must be between 1 and 10")
        if not 0 < self.confluence_distance_pct <= 1.0:
            raise ValueError("confluence_distance_pct must be between 0 and 1.0")
        if self.min_confluence_sources < 1:
            raise ValueError("min_confluence_sources must be at least 1")

        # Validate weights are in valid range
        for signal_type, weight in self.signal_weights.items():
            if not 0 <= weight <= 1.0:
                raise ValueError(
                    f"Weight for {signal_type.value} must be between 0 and 1.0, " f"got {weight}"
                )

        if not self.signal_weights:
            import warnings

            warnings.warn(
                f"Strategy '{self.name}' has no signal_weights - "
                "it will never receive any signals",
                stacklevel=2,
            )

        # Default exit_level_sources to ATR_MULTIPLIER if not set
        # This maintains backwards compatibility
        if not self.exit_level_sources:
            from bot.signals.base import ExitLevelSource

            self.exit_level_sources = [ExitLevelSource.ATR_MULTIPLIER]

    @property
    def signal_types(self) -> list["SignalType"]:
        """Get list of signal types this strategy listens to (for compatibility)."""
        return list(self.signal_weights.keys())

    @property
    def uses_structural_exits(self) -> bool:
        """True if strategy uses structural levels (VP, prev day) for exits."""
        from bot.signals.base import ExitLevelSource

        return any(source != ExitLevelSource.ATR_MULTIPLIER for source in self.exit_level_sources)
