"""
Mean Reversion Strategy.

A contrarian strategy that fades overextended moves.
Looks for price to snap back after moving too far too fast.
"""

from bot.signals.base import SignalType
from bot.strategies.base import RiskConfig, Strategy, StrategyType

PROMPT = """You are a mean reversion trader for crypto markets.

SIGNAL WEIGHTS:
- RSI: 1.0 (primary signal for overbought/oversold)
- VOLUME_PROFILE: 0.3 (supporting signal for mean price levels)

YOUR TRADING STYLE:
- Look for overextended moves that will snap back
- Fade extreme RSI readings (overbought/oversold)
- Use POC (Point of Control) as the "mean" price target
- Quick exits when price reverts to mean

ENTRY CRITERIA:
- RSI showing overbought (>70) or oversold (<30) conditions
- Price extended away from Volume Profile POC
- Order book showing reversal pressure building

EXIT CRITERIA:
- Exit when price returns toward POC
- Take profits quickly on reversals
- Cut if trend continues against you

RISK RULES:
- Only fade CLEARLY overextended moves
- Small position sizes (fading is risky)
- Maximum position: 8% of balance"""

MEAN_REVERSION = Strategy(
    name="Mean Reversion",
    strategy_type=StrategyType.MEAN_REVERSION,
    prompt=PROMPT,
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
)
