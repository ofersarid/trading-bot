"""
Core business logic for the trading bot.

Modules:
- models: Data classes for opportunities, conditions, trades
- config: Trading configuration and thresholds
- analysis: Market analysis and opportunity detection
"""

from bot.core.models import (
    CoinPressure,
    MarketPressure,
    MoveFreshness,
    OpportunityCondition,
    PendingOpportunity,
    PressureLevel,
)

__all__ = [
    "CoinPressure",
    "MarketPressure",
    "MoveFreshness",
    "OpportunityCondition",
    "PendingOpportunity",
    "PressureLevel",
]
