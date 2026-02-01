"""
AI module for local LLM-powered trading analysis.

Architecture:
- SignalsFactory (bot.signals.factory): Pure signal processing, no AI
- GoalBasedSizer: AI decides position size based on user goals

The architecture separates concerns cleanly:
1. SignalsFactory handles filtering, weighting, and TP/SL calculation (pure)
2. GoalBasedSizer handles AI position sizing based on user goals
"""

from bot.ai.analyzer import AIDecision, MarketAnalyzer
from bot.ai.decision_analyzer import AIAnalysisReport, AIDecisionAnalyzer, analyze_decision_log
from bot.ai.decision_logger import AIDecisionLogger, DecisionLog
from bot.ai.goal_sizer import GoalBasedSizer, SizingDecision, create_goal_sizer
from bot.ai.models import (
    AIMetrics,
    AllocationDecision,
    AnalysisResult,
    CoinMomentum,
    Freshness,
    PortfolioAllocation,
    PortfolioOpportunity,
    PortfolioPosition,
    PortfolioState,
    RiskTolerance,
    Sentiment,
    Signal,
    UserGoal,
)
from bot.ai.ollama_client import OllamaClient
from bot.ai.portfolio_allocator import PortfolioAllocator, create_portfolio_allocator
from bot.ai.prompts import format_ai_trading_prompt, get_strategy_prompt
from bot.strategies import (
    RiskConfig,
    Strategy,
    StrategyType,
    TradingStrategy,
    get_strategy,
    list_strategies,
    register_strategy,
)

__all__ = [
    # Analysis
    "AIAnalysisReport",
    "AIDecision",
    "AIDecisionAnalyzer",
    "AIDecisionLogger",
    "AIMetrics",
    "AnalysisResult",
    "DecisionLog",
    "MarketAnalyzer",
    # Goal-based sizing
    "GoalBasedSizer",
    "SizingDecision",
    "UserGoal",
    "RiskTolerance",
    "create_goal_sizer",
    # Portfolio allocation
    "AllocationDecision",
    "PortfolioAllocation",
    "PortfolioAllocator",
    "PortfolioOpportunity",
    "PortfolioPosition",
    "PortfolioState",
    "create_portfolio_allocator",
    # Models
    "CoinMomentum",
    "Freshness",
    "OllamaClient",
    "Sentiment",
    "Signal",
    # Strategy (re-exported from bot.strategies)
    "RiskConfig",
    "Strategy",
    "StrategyType",
    "TradingStrategy",
    "get_strategy",
    "list_strategies",
    "register_strategy",
    # Prompts
    "analyze_decision_log",
    "format_ai_trading_prompt",
    "get_strategy_prompt",
]
