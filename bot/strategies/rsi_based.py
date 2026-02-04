"""
RSI-Based Strategy.

Primary signal: RSI (weight 1.0)
Supporting signal: VOLUME_PROFILE (weight 0.3)

Focuses on overbought/oversold conditions with VP level support.
Smaller positions (fading is risky), quick exits.
Uses POC as primary target (mean reversion).
"""

from bot.signals.base import ExitLevelSource, SignalType
from bot.strategies.base import RiskConfig, Strategy, StrategyType

RSI_BASED = Strategy(
    name="RSI Based",
    strategy_type=StrategyType.RSI_BASED,
    risk=RiskConfig(
        max_position_pct=8.0,  # Smaller positions - fading is risky
        stop_loss_atr_multiplier=1.5,
        take_profit_atr_multiplier=1.5,  # Quick exits
        trail_activation_pct=0.3,
        trail_distance_pct=0.2,
    ),
    signal_weights={
        SignalType.RSI: 1.0,  # Primary - overbought/oversold detection
        SignalType.VOLUME_PROFILE: 0.3,  # Supporting - mean price levels
    },
    signal_threshold=0.8,  # High bar - only fade clearly overextended moves
    min_signal_strength=0.6,  # Need strong RSI signals
    min_confidence=7,  # Need higher confidence to fade
    # Exit configuration - POC is key target for mean reversion
    exit_level_sources=[
        ExitLevelSource.VP_POC,  # Primary target - mean price
        ExitLevelSource.PREV_DAY_POC,
        ExitLevelSource.VP_VAH,
        ExitLevelSource.VP_VAL,
    ],
    confluence_distance_pct=0.35,  # Wider for mean reversion
    min_confluence_sources=1,  # Single level target is typical
    fallback_sl_atr_multiplier=1.5,
    fallback_tp_atr_multiplier=1.5,
)
