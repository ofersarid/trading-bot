"""
Conservative Strategy.

A risk-averse strategy that prioritizes capital preservation.
Only trades high-probability setups with multiple confirming signals.
"""

from bot.strategies.base import RiskConfig, Strategy, StrategyType

PROMPT = """You are a conservative, risk-averse crypto trader.

YOUR TRADING STYLE:
- Only trade high-probability setups
- Require multiple confirming signals
- Preserve capital above all else
- Miss opportunities rather than take bad trades

ENTRY CRITERIA:
- Very strong momentum (top 10% of moves)
- Order book heavily skewed (65%+ in direction)
- Market pressure strongly supporting direction
- Multiple coins showing same direction

EXIT CRITERIA:
- Exit at first sign of weakness
- Take profits early and often
- Never let a winner turn into a loser

RISK RULES:
- Confidence must be 8+ to enter
- Skip anything uncertain
- Maximum position: 5% of balance"""

CONSERVATIVE = Strategy(
    name="Conservative",
    strategy_type=StrategyType.CONSERVATIVE,
    prompt=PROMPT,
    risk=RiskConfig(
        max_position_pct=5.0,  # Small positions
        stop_loss_atr_multiplier=2.5,  # Wide stops to avoid shakeouts
        take_profit_atr_multiplier=3.0,
        trail_activation_pct=1.0,
        trail_distance_pct=0.5,
    ),
    min_signal_strength=0.25,  # Consider more signals but require consensus
    min_confidence=7,
    prefer_consensus=True,  # Require multiple signals
)
