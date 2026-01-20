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
from bot.core.analysis.momentum import (
    MomentumResult,
    calculate_momentum,
    calculate_momentum_with_acceleration,
    get_lookback_price,
)
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
    "MomentumResult",
    "OpportunityAction",
    "OpportunityAnalysisResult",
    "OpportunityAnalyzer",
    "calculate_momentum",
    "calculate_momentum_with_acceleration",
    "get_lookback_price",
]
