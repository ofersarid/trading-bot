"""
Momentum-Based Strategy.

Primary signal: MOMENTUM (weight 1.0)
Supporting signal: VOLUME_PROFILE (weight 0.5)

Optimized for quick momentum moves with VP level confirmation.
Uses VP structural levels for TP/SL placement when available.
"""

from bot.signals.base import ExitLevelSource, SignalType
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
    # Exit level configuration - use VP levels for structural exits
    exit_level_sources=[
        ExitLevelSource.VP_VAH,
        ExitLevelSource.VP_VAL,
        ExitLevelSource.VP_POC,
        ExitLevelSource.PREV_DAY_VAH,
        ExitLevelSource.PREV_DAY_VAL,
    ],
    confluence_distance_pct=0.3,  # Levels within 30% of VA range are confluent
    min_confluence_sources=2,  # Want at least 2 levels agreeing
    fallback_sl_atr_multiplier=1.2,  # Match RiskConfig for consistency
    fallback_tp_atr_multiplier=2.5,
)
