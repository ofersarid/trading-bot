"""
Multi-Signal Strategy.

Balanced weights: MOMENTUM (0.4), RSI (0.3), MACD (0.3)

Requires multiple signals to align before trading.
Smaller positions, preserves capital, high threshold.
"""

from bot.signals.base import SignalType
from bot.strategies.base import RiskConfig, Strategy, StrategyType

PROMPT = """You are a multi-signal trader for crypto markets.

SIGNAL WEIGHTS:
- MOMENTUM: 0.4 (trend direction)
- RSI: 0.3 (overbought/oversold filter)
- MACD: 0.3 (trend confirmation)

All three signals contribute. You need multiple signals to align for the weighted score to reach the high threshold.

YOUR TRADING STYLE:
- Only trade high-probability setups
- Wait for multiple signals to agree on direction
- Preserve capital above all else
- Miss opportunities rather than take bad trades

ENTRY CRITERIA:
- Multiple signals pointing the same direction
- MOMENTUM showing strong directional move
- RSI confirming (not overbought for longs, not oversold for shorts)
- MACD alignment (histogram and signal line agreement)
- Order book heavily skewed (65%+ in direction)

EXIT CRITERIA:
- Exit at first sign of weakness in any indicator
- Take profits early and often
- Never let a winner turn into a loser

RISK RULES:
- Confidence must be 8+ to enter
- Skip anything uncertain
- Maximum position: 5% of balance"""

MULTI_SIGNAL = Strategy(
    name="Multi-Signal",
    strategy_type=StrategyType.MULTI_SIGNAL,
    prompt=PROMPT,
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
)
