"""
Core analysis utilities for the trading bot.

Provides market analysis, momentum calculation, and opportunity detection.
"""

from bot.core.analysis.momentum import calculate_momentum, get_lookback_price
from bot.core.analysis.market import (
    MarketAnalyzer,
    MarketAnalysis,
    MarketConditionLevel,
    CoinAnalysis,
    CoinStatus,
)
from bot.core.analysis.opportunities import (
    OpportunityAnalyzer,
    OpportunityAnalysisResult,
    OpportunityAction,
)

__all__ = [
    "calculate_momentum",
    "get_lookback_price",
    "MarketAnalyzer",
    "MarketAnalysis",
    "MarketConditionLevel",
    "CoinAnalysis",
    "CoinStatus",
    "OpportunityAnalyzer",
    "OpportunityAnalysisResult",
    "OpportunityAction",
]
