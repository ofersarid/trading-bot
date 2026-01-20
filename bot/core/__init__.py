"""
Core business logic for the trading bot.

Modules:
- models: Data classes for opportunities, conditions, trades
- config: Trading configuration and thresholds
- analysis: Market analysis and opportunity detection
- data_buffer: Data buffering for AI interpretation
"""

from bot.core.data_buffer import CoinDataBufferManager, ScalperDataWindow
from bot.core.models import (
    CoinPressure,
    MarketPressure,
    MoveFreshness,
    OpportunityCondition,
    PendingOpportunity,
    PressureLevel,
)

__all__ = [
    "CoinDataBufferManager",
    "CoinPressure",
    "MarketPressure",
    "MoveFreshness",
    "OpportunityCondition",
    "PendingOpportunity",
    "PressureLevel",
    "ScalperDataWindow",
]
