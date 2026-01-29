"""
Core business logic for the trading bot.

Modules:
- models: Data classes for opportunities, conditions, trades
- config: Trading configuration and thresholds
- analysis: Market analysis and opportunity detection
- trading_core: Unified trading logic for backtest and live
- levels: Structure-aware TP/SL calculation using VP levels
"""

from bot.core.levels import (
    StructureLevels,
    StructureTPSL,
    calculate_structure_tp_sl,
    find_nearest_resistance,
    find_nearest_support,
)
from bot.core.models import (
    CoinPressure,
    MarketPressure,
    MoveFreshness,
    OpportunityCondition,
    PendingOpportunity,
    PressureLevel,
)
from bot.core.trading_core import TradingCore

__all__ = [
    "CoinPressure",
    "MarketPressure",
    "MoveFreshness",
    "OpportunityCondition",
    "PendingOpportunity",
    "PressureLevel",
    "StructureLevels",
    "StructureTPSL",
    "TradingCore",
    "calculate_structure_tp_sl",
    "find_nearest_resistance",
    "find_nearest_support",
]
