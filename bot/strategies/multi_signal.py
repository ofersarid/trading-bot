"""
Multi-Signal Strategy.

Balanced weights: MOMENTUM (0.4), RSI (0.3), MACD (0.3)

Requires multiple signals to align before trading.
Smaller positions, preserves capital, high threshold.
Uses multiple structural sources for high-confidence exits.
"""

from bot.signals.base import ExitLevelSource, SignalType
from bot.strategies.base import RiskConfig, Strategy, StrategyType

MULTI_SIGNAL = Strategy(
    name="Multi-Signal",
    strategy_type=StrategyType.MULTI_SIGNAL,
    risk=RiskConfig(
        max_position_pct=5.0,  # Small positions
        stop_loss_atr_multiplier=2.5,  # Wide stops to avoid shakeouts
        take_profit_atr_multiplier=3.0,
        trail_activation_pct=1.0,
        trail_distance_pct=0.5,
    ),
    signal_weights={
        SignalType.MOMENTUM: 0.4,  # Trend direction
        SignalType.RSI: 0.3,  # Overbought/oversold filter
        SignalType.MACD: 0.3,  # Trend confirmation
    },
    signal_threshold=0.8,  # High bar - need multiple signals aligning
    min_signal_strength=0.3,  # Accept moderate signals
    min_confidence=7,
    # Exit configuration - require high confluence for conservative exits
    exit_level_sources=[
        ExitLevelSource.VP_VAH,
        ExitLevelSource.VP_VAL,
        ExitLevelSource.VP_POC,
        ExitLevelSource.PREV_DAY_VAH,
        ExitLevelSource.PREV_DAY_VAL,
        ExitLevelSource.PREV_DAY_POC,
    ],
    confluence_distance_pct=0.2,  # Tight confluence for conservative trades
    min_confluence_sources=2,  # Require multiple sources agreeing
    fallback_sl_atr_multiplier=2.5,
    fallback_tp_atr_multiplier=3.0,
)
