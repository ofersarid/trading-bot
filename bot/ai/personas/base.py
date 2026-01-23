"""
Base classes for AI Trading Personas.

Defines the TradingPersona and RiskParams dataclasses that all
personas inherit from. These are used by the SignalBrain to make
trading decisions based on detected signals.
"""

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class RiskParams:
    """
    Risk management parameters for a trading persona.

    These parameters control position sizing, stop-loss placement,
    and trailing stop behavior.
    """

    max_position_pct: float = 10.0  # Max % of balance per trade
    stop_loss_atr_multiplier: float = 1.5  # SL = entry ± ATR * multiplier
    take_profit_atr_multiplier: float = 2.0  # TP = entry ± ATR * multiplier
    trail_activation_pct: float = 0.5  # When to activate trailing (% profit)
    trail_distance_pct: float = 0.3  # Trail distance as % of price

    def validate(self) -> None:
        """Validate risk parameters are within reasonable bounds."""
        if not 0 < self.max_position_pct <= 100:
            raise ValueError("max_position_pct must be between 0 and 100")
        if self.stop_loss_atr_multiplier <= 0:
            raise ValueError("stop_loss_atr_multiplier must be positive")
        if self.take_profit_atr_multiplier <= 0:
            raise ValueError("take_profit_atr_multiplier must be positive")
        if self.trail_activation_pct < 0:
            raise ValueError("trail_activation_pct must be non-negative")
        if self.trail_distance_pct <= 0:
            raise ValueError("trail_distance_pct must be positive")


@dataclass
class TradingPersona:
    """
    A trading persona that defines how the AI makes decisions.

    Each persona has a distinct trading style, risk tolerance,
    and prompt template that guides its decision-making.
    """

    name: str
    style: Literal["aggressive", "conservative", "balanced"]
    description: str
    prompt_template: str
    risk_params: RiskParams = field(default_factory=RiskParams)

    # Persona-specific behavior modifiers
    min_signal_strength: float = 0.3  # Minimum signal strength to consider
    min_confidence: int = 6  # Minimum confidence to act (1-10)
    prefer_consensus: bool = True  # Wait for multiple signals to agree

    def __post_init__(self) -> None:
        """Validate persona configuration."""
        self.risk_params.validate()
        if not 0 <= self.min_signal_strength <= 1:
            raise ValueError("min_signal_strength must be between 0 and 1")
        if not 1 <= self.min_confidence <= 10:
            raise ValueError("min_confidence must be between 1 and 10")


# Default prompt template for signal-based personas
SIGNAL_BASED_PROMPT_TEMPLATE = """You are a {style} crypto trader evaluating trading signals.

## YOUR TRADING STYLE
{description}

## SIGNALS DETECTED
{signals}

## CURRENT POSITIONS
{positions}

## MARKET CONTEXT
- ATR (14-period): ${atr_value:.2f} ({atr_pct:.2f}% of price)
- Current volatility: {volatility_level}

## YOUR TASK
Based on these signals and your trading style, decide:

1. ACTION: Should we LONG, SHORT, or WAIT?
2. SIZE: Position size as % of balance (max {max_position_pct}%)
3. STOP_LOSS: Price level for stop loss
4. TAKE_PROFIT: Price level for take profit
5. TRAIL_ACTIVATION: Price level to activate trailing stop
6. TRAIL_DISTANCE: Trailing stop distance as % of price
7. CONFIDENCE: Your confidence in this trade (1-10)
8. REASON: One sentence explaining your decision

Respond in this EXACT format:
ACTION: [LONG/SHORT/WAIT]
SIZE: [0-{max_position_pct}]
STOP_LOSS: [price]
TAKE_PROFIT: [price]
TRAIL_ACTIVATION: [price]
TRAIL_DISTANCE: [0.1-2.0]
CONFIDENCE: [1-10]
REASON: [your reasoning]

IMPORTANT:
- Only act if signals align with your style
- Consider current volatility for stop placement
- If in doubt, WAIT for better setup"""


# Pre-defined personas for common trading styles

SCALPER_PERSONA = TradingPersona(
    name="Scalper",
    style="aggressive",
    description="""You are an aggressive momentum scalper. You look for quick moves
and trade frequently. You're comfortable with higher risk for higher reward.
You trust strong momentum signals and act quickly when multiple indicators align.
Your targets are small (0.1-0.3%) but you expect to hit them fast.""",
    prompt_template=SIGNAL_BASED_PROMPT_TEMPLATE,
    risk_params=RiskParams(
        max_position_pct=15.0,
        stop_loss_atr_multiplier=1.2,  # Slightly wider stops to reduce stop-outs
        take_profit_atr_multiplier=2.5,  # Wider take profits for better risk/reward
        trail_activation_pct=0.15,
        trail_distance_pct=0.1,
    ),
    min_signal_strength=0.7,  # Higher threshold - only act on strong RSI signals (66%+ accuracy)
    min_confidence=5,
    prefer_consensus=False,  # Scalpers act on single strong signals
)

CONSERVATIVE_PERSONA = TradingPersona(
    name="Conservative",
    style="conservative",
    description="""You are a conservative trader who prioritizes capital preservation.
You only trade when multiple signals strongly agree. You use wider stops
to avoid getting shaken out, and you're patient with your entries.
You'd rather miss a trade than take a bad one.""",
    prompt_template=SIGNAL_BASED_PROMPT_TEMPLATE,
    risk_params=RiskParams(
        max_position_pct=5.0,
        stop_loss_atr_multiplier=2.5,
        take_profit_atr_multiplier=3.0,
        trail_activation_pct=1.0,
        trail_distance_pct=0.5,
    ),
    min_signal_strength=0.25,  # Higher threshold - only stronger signals
    min_confidence=7,
    prefer_consensus=True,  # Wait for multiple signals
)

BALANCED_PERSONA = TradingPersona(
    name="Balanced",
    style="balanced",
    description="""You are a balanced trader who weighs risk and reward carefully.
You look for good setups but don't force trades. You use moderate position
sizes and reasonable stop-losses. You're adaptable and adjust your approach
based on market conditions.""",
    prompt_template=SIGNAL_BASED_PROMPT_TEMPLATE,
    risk_params=RiskParams(
        max_position_pct=10.0,
        stop_loss_atr_multiplier=1.5,
        take_profit_atr_multiplier=2.0,
        trail_activation_pct=0.5,
        trail_distance_pct=0.3,
    ),
    min_signal_strength=0.15,  # Moderate threshold
    min_confidence=6,
    prefer_consensus=True,
)


def get_persona(name: str) -> TradingPersona:
    """
    Get a pre-defined persona by name.

    Args:
        name: Persona name (case-insensitive)

    Returns:
        TradingPersona instance

    Raises:
        ValueError if persona not found
    """
    personas = {
        "scalper": SCALPER_PERSONA,
        "conservative": CONSERVATIVE_PERSONA,
        "balanced": BALANCED_PERSONA,
    }

    key = name.lower()
    if key not in personas:
        available = ", ".join(personas.keys())
        raise ValueError(f"Unknown persona '{name}'. Available: {available}")

    return personas[key]
