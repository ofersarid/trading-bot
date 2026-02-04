"""
Equal Weight Strategy.

All signals weighted equally: MOMENTUM (0.5), RSI (0.5), MACD (0.5), VOLUME_PROFILE (0.5)

Gives equal importance to all available indicators, requiring broad market
confirmation before trading. Moderate threshold allows trades when multiple
signals align at moderate strength.

Uses all available structural sources for balanced exit placement.
"""

from bot.signals.base import ExitLevelSource, SignalType
from bot.strategies.base import RiskConfig, Strategy, StrategyType

EQUAL_WEIGHT = Strategy(
    name="Equal Weight",
    strategy_type=StrategyType.EQUAL_WEIGHT,
    risk=RiskConfig(
        max_position_pct=10.0,  # Moderate position size
        stop_loss_atr_multiplier=2.0,  # Standard stops
        take_profit_atr_multiplier=2.5,
        trail_activation_pct=0.8,
        trail_distance_pct=0.4,
    ),
    signal_weights={
        SignalType.MOMENTUM: 0.5,  # Trend direction
        SignalType.RSI: 0.5,  # Overbought/oversold
        SignalType.MACD: 0.5,  # Trend confirmation
        SignalType.VOLUME_PROFILE: 0.5,  # Volume-based support/resistance
    },
    signal_threshold=0.7,  # Need decent alignment from multiple signals
    min_signal_strength=0.25,  # Accept moderate signals
    min_confidence=6,
    # Exit configuration - balanced use of all sources
    exit_level_sources=[
        ExitLevelSource.VP_VAH,
        ExitLevelSource.VP_VAL,
        ExitLevelSource.VP_POC,
        ExitLevelSource.PREV_DAY_VAH,
        ExitLevelSource.PREV_DAY_VAL,
        ExitLevelSource.PREV_DAY_POC,
    ],
    confluence_distance_pct=0.3,  # Standard confluence
    min_confluence_sources=1,  # Accept single structural levels
    fallback_sl_atr_multiplier=2.0,
    fallback_tp_atr_multiplier=2.5,
)
