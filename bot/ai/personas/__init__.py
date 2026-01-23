"""
AI Trading Personas.

Each persona represents a distinct trading style and mental model
that guides how the AI interprets market data and makes decisions.
"""

from bot.ai.personas.base import (
    BALANCED_PERSONA,
    CONSERVATIVE_PERSONA,
    SCALPER_PERSONA,
    RiskParams,
    TradingPersona,
    get_persona,
)
from bot.ai.personas.scalper import (
    SCALPER_ANALYSIS_PROMPT,
    SCALPER_PERSONA_PROMPT,
    format_book_imbalance,
    format_price_description,
    format_scalper_prompt,
    format_tape_notable,
)

__all__ = [
    # Base classes
    "TradingPersona",
    "RiskParams",
    "get_persona",
    # Pre-defined personas
    "SCALPER_PERSONA",
    "CONSERVATIVE_PERSONA",
    "BALANCED_PERSONA",
    # Legacy scalper functions (for existing dashboard)
    "SCALPER_ANALYSIS_PROMPT",
    "SCALPER_PERSONA_PROMPT",
    "format_book_imbalance",
    "format_price_description",
    "format_scalper_prompt",
    "format_tape_notable",
]
