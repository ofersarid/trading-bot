"""
Core analysis utilities for the trading bot.

Provides market analysis, momentum calculation, and opportunity detection.
"""

from bot.core.analysis.market import (
    CoinAnalysis,
    CoinStatus,
    MarketAnalysis,
    MarketAnalyzer,
    MarketConditionLevel,
)
from bot.core.analysis.momentum import calculate_momentum, get_lookback_price
from bot.core.analysis.opportunities import (
    OpportunityAction,
    OpportunityAnalysisResult,
    OpportunityAnalyzer,
)

__all__ = [
    "CoinAnalysis",
    "CoinStatus",
    "MarketAnalysis",
    "MarketAnalyzer",
    "MarketConditionLevel",
    "OpportunityAction",
    "OpportunityAnalysisResult",
    "OpportunityAnalyzer",
    "calculate_momentum",
    "get_lookback_price",
]
