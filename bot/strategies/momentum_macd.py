"""
Momentum + MACD Strategy.

Primary signal: MOMENTUM (weight 0.6)
Secondary signal: MACD (weight 0.4)

Requires both momentum direction and MACD confirmation.
Wider stops to avoid shakeouts, lets winners run.
"""

from bot.signals.base import SignalType
from bot.strategies.base import RiskConfig, Strategy, StrategyType

PROMPT = """You are a momentum trader with MACD confirmation for crypto markets.

SIGNAL WEIGHTS:
- MOMENTUM: 0.6 (primary trend direction)
- MACD: 0.4 (trend confirmation)

YOUR TRADING STYLE:
- Wait for confirmed moves (momentum + MACD alignment)
- Let winners run, cut losers quickly
- Fewer trades but larger moves
- Ride the move until exhaustion

ENTRY CRITERIA:
- Clear directional move established (strong MOMENTUM signal)
- MACD confirmation (crossover or histogram alignment)
- Order book heavily favoring direction

EXIT CRITERIA:
- Exit when momentum shows exhaustion (fading)
- Use trailing stops mentally (exit if gives back 30% of gains)
- Don't exit just because of small pullbacks

RISK RULES:
- Wait for high-confidence setups only
- Accept missing some moves for better entries
- Maximum position: 15% of balance"""

MOMENTUM_MACD = Strategy(
    name="Momentum + MACD",
    strategy_type=StrategyType.MOMENTUM_MACD,
    prompt=PROMPT,
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
)
