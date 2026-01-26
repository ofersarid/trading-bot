"""
Momentum Scalper Strategy.

An aggressive momentum scalping strategy for crypto markets.
Focuses on quick entries and exits, capturing small but frequent profits.
"""

from bot.strategies.base import RiskConfig, Strategy, StrategyType

PROMPT = """You are an aggressive momentum scalper for crypto markets.

YOUR TRADING STYLE:
- Look for quick momentum moves (0.05%+ in 5 seconds)
- Enter early when momentum is FRESH and BUILDING, exit quickly
- Small profits are fine (0.05-0.15%), avoid holding losers
- High trade frequency, tight risk management

ENTRY CRITERIA:
- Strong directional momentum with POSITIVE acceleration (BUILDING, not FADING)
- Order book pressure supporting the direction
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

MOMENTUM_SCALPER = Strategy(
    name="Momentum Scalper",
    strategy_type=StrategyType.MOMENTUM_SCALPER,
    prompt=PROMPT,
    risk=RiskConfig(
        max_position_pct=15.0,
        stop_loss_atr_multiplier=1.2,  # Tighter stops for quick trades
        take_profit_atr_multiplier=2.5,  # Good risk/reward
        trail_activation_pct=0.15,
        trail_distance_pct=0.1,
    ),
    min_signal_strength=0.7,  # Only strong signals
    min_confidence=5,
    prefer_consensus=False,  # Act on single strong signals
)
