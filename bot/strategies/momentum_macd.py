"""
Momentum + MACD Strategy.

Primary signal: MOMENTUM (weight 0.6)
Secondary signal: MACD (weight 0.4)

Requires both momentum direction and MACD confirmation.
Wider stops to avoid shakeouts, lets winners run.
Uses prev day levels for exits when available.
"""

from bot.signals.base import ExitLevelSource, SignalType
from bot.strategies.base import RiskConfig, Strategy, StrategyType

MOMENTUM_MACD = Strategy(
    name="Momentum + MACD",
    strategy_type=StrategyType.MOMENTUM_MACD,
    risk=RiskConfig(
        max_position_pct=15.0,
        stop_loss_atr_multiplier=2.0,  # Wider stops
        take_profit_atr_multiplier=4.0,  # Let winners run
        trail_activation_pct=0.5,
        trail_distance_pct=0.3,
    ),
    signal_weights={
        SignalType.MOMENTUM: 0.6,  # Primary trend direction
        SignalType.MACD: 0.4,  # Trend confirmation
    },
    signal_threshold=0.6,  # Need both signals to align for higher scores
    min_signal_strength=0.4,  # Accept moderate signals
    min_confidence=6,
    # Exit configuration - use prev day levels for structure
    exit_level_sources=[
        ExitLevelSource.PREV_DAY_VAH,
        ExitLevelSource.PREV_DAY_VAL,
        ExitLevelSource.PREV_DAY_POC,
        ExitLevelSource.VP_VAH,
        ExitLevelSource.VP_VAL,
    ],
    confluence_distance_pct=0.25,  # Tighter confluence for trend trades
    min_confluence_sources=1,  # Single structural level is fine
    fallback_sl_atr_multiplier=2.0,
    fallback_tp_atr_multiplier=4.0,
)
