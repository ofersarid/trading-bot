"""
Trend Follower Strategy.

A patient trend following strategy for crypto markets.
Waits for confirmed trends and rides them until exhaustion.
"""

from bot.signals.base import SignalType
from bot.strategies.base import RiskConfig, Strategy, StrategyType

PROMPT = """You are a patient trend follower for crypto markets.

SIGNAL WEIGHTS:
- MOMENTUM: 0.6 (primary trend direction)
- MACD: 0.4 (trend confirmation)

YOUR TRADING STYLE:
- Wait for confirmed trends (sustained momentum over 30+ seconds)
- Let winners run, cut losers quickly
- Fewer trades but larger moves
- Ride the trend until exhaustion

ENTRY CRITERIA:
- Clear directional trend established (strong MOMENTUM signal)
- MACD confirmation (crossover or histogram alignment)
- Order book heavily favoring trend direction

EXIT CRITERIA:
- Exit when trend shows exhaustion (momentum fading)
- Use trailing stops mentally (exit if gives back 30% of gains)
- Don't exit just because of small pullbacks

RISK RULES:
- Wait for high-confidence setups only
- Accept missing some moves for better entries
- Maximum position: 15% of balance"""

TREND_FOLLOWER = Strategy(
    name="Trend Follower",
    strategy_type=StrategyType.TREND_FOLLOWER,
    prompt=PROMPT,
    risk=RiskConfig(
        max_position_pct=15.0,
        stop_loss_atr_multiplier=2.0,  # Wider stops for trends
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
