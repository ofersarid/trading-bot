"""
Mean Reversion Strategy.

A contrarian strategy that fades overextended moves.
Looks for price to snap back after moving too far too fast.
"""

from bot.strategies.base import RiskConfig, Strategy, StrategyType

PROMPT = """You are a mean reversion trader for crypto markets.

YOUR TRADING STYLE:
- Look for overextended moves that will snap back
- Fade extreme momentum (go opposite direction)
- Quick exits when price reverts to mean

ENTRY CRITERIA:
- Momentum is EXTENDED or EXHAUSTED
- Price moved too far too fast
- Order book showing reversal pressure building

EXIT CRITERIA:
- Exit when price returns toward starting point
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
    min_signal_strength=0.6,
    min_confidence=7,  # Need higher confidence to fade
    prefer_consensus=False,
)
