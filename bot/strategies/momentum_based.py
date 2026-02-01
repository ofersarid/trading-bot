"""
Momentum-Based Strategy.

Primary signal: MOMENTUM (weight 1.0)
Supporting signal: VOLUME_PROFILE (weight 0.5)

Optimized for quick momentum moves with VP level confirmation.
Tighter stops, good risk/reward ratio.
"""

from bot.signals.base import SignalType
from bot.strategies.base import RiskConfig, Strategy, StrategyType

MOMENTUM_BASED = Strategy(
    name="Momentum Based",
    strategy_type=StrategyType.MOMENTUM_BASED,
    risk=RiskConfig(
        max_position_pct=15.0,
        stop_loss_atr_multiplier=1.2,  # Tighter stops for quick trades
        take_profit_atr_multiplier=2.5,  # Good risk/reward
        trail_activation_pct=0.15,
        trail_distance_pct=0.1,
    ),
    signal_weights={
        SignalType.MOMENTUM: 1.0,  # Primary signal - full weight
        SignalType.VOLUME_PROFILE: 0.5,  # Supporting signal - half weight
    },
    signal_threshold=0.7,  # Need 0.7+ weighted score to trade
    min_signal_strength=0.5,  # Filter out weak signals
    min_confidence=5,
)
