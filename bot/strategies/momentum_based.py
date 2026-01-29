"""
Momentum-Based Strategy.

Primary signal: MOMENTUM (weight 1.0)
Supporting signal: VOLUME_PROFILE (weight 0.5)

Optimized for quick momentum moves with VP level confirmation.
Tighter stops, good risk/reward ratio.
"""

from bot.signals.base import SignalType
from bot.strategies.base import RiskConfig, Strategy, StrategyType

PROMPT = """You are a momentum-focused trader for crypto markets.

SIGNAL WEIGHTS:
- MOMENTUM: 1.0 (primary signal - full weight)
- VOLUME_PROFILE: 0.5 (supporting signal - half weight)

YOUR TRADING STYLE:
- Look for quick momentum moves (0.05%+ in 5 seconds)
- Enter early when momentum is FRESH and BUILDING, exit quickly
- Small profits are fine (0.05-0.15%), avoid holding losers
- High trade frequency, tight risk management

ENTRY CRITERIA:
- Strong directional momentum with POSITIVE acceleration (BUILDING, not FADING)
- Order book pressure supporting the direction
- Volume Profile levels (POC, VAH, VAL) as support/resistance confirmation
- DO NOT enter if acceleration is negative - momentum is fading, you'll chase a dying move

EXIT CRITERIA:
- Exit when acceleration turns negative (momentum FADING)
- Don't wait for price reversal - fading momentum IS the exit signal
- Take small profits rather than waiting for big moves
- Cut losses fast if momentum turns against you

RISK RULES:
- Never hold a losing position hoping it recovers
- Exit immediately if momentum reverses OR starts fading
- Maximum position: 10% of balance"""

MOMENTUM_BASED = Strategy(
    name="Momentum Based",
    strategy_type=StrategyType.MOMENTUM_BASED,
    prompt=PROMPT,
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
