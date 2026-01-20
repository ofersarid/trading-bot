"""
AI Trading Personas.

Each persona represents a distinct trading style and mental model
that guides how the AI interprets market data and makes decisions.
"""

from bot.ai.personas.scalper import (
    SCALPER_ANALYSIS_PROMPT,
    SCALPER_PERSONA_PROMPT,
    format_book_imbalance,
    format_price_description,
    format_scalper_prompt,
    format_tape_notable,
)

__all__ = [
    "SCALPER_ANALYSIS_PROMPT",
    "SCALPER_PERSONA_PROMPT",
    "format_book_imbalance",
    "format_price_description",
    "format_scalper_prompt",
    "format_tape_notable",
]
