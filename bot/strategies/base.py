"""
Base classes for trading strategies.

Defines the core dataclasses that all strategies use:
- StrategyType: Enum of available strategy types
- RiskConfig: Risk management parameters
- Strategy: Complete strategy definition
"""

from dataclasses import dataclass, field
from enum import Enum


class StrategyType(Enum):
    """Available strategy types."""

    MOMENTUM_SCALPER = "momentum_scalper"
    TREND_FOLLOWER = "trend_follower"
    MEAN_REVERSION = "mean_reversion"
    CONSERVATIVE = "conservative"


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
    A complete trading strategy that defines how the AI trades.

    Combines the trading prompt (mindset/style) with risk parameters
    and signal filtering rules.
    """

    name: str
    strategy_type: StrategyType
    prompt: str  # The AI's trading mindset/style
    risk: RiskConfig = field(default_factory=RiskConfig)

    # Signal filtering
    min_signal_strength: float = 0.3  # Minimum signal strength to consider (0-1)
    min_confidence: int = 6  # Minimum confidence to act (1-10)
    prefer_consensus: bool = True  # Wait for multiple signals to agree

    def __post_init__(self) -> None:
        """Validate strategy configuration."""
        if not 0 <= self.min_signal_strength <= 1:
            raise ValueError("min_signal_strength must be between 0 and 1")
        if not 1 <= self.min_confidence <= 10:
            raise ValueError("min_confidence must be between 1 and 10")
