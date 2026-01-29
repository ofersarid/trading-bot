"""AI module for local LLM-powered trading analysis."""

from bot.ai.analyzer import AIDecision, MarketAnalyzer
from bot.ai.decision_analyzer import AIAnalysisReport, AIDecisionAnalyzer, analyze_decision_log
from bot.ai.decision_logger import AIDecisionLogger, DecisionLog
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
    Sentiment,
    Signal,
)
from bot.ai.ollama_client import OllamaClient
from bot.ai.portfolio_allocator import PortfolioAllocator, create_portfolio_allocator
from bot.ai.prompts import format_ai_trading_prompt, get_strategy_prompt
from bot.ai.signal_brain import SignalBrain, create_signal_brain
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
    "AIAnalysisReport",
    "AIDecision",
    "AIDecisionAnalyzer",
    "AIDecisionLogger",
    "AIMetrics",
    "AllocationDecision",
    "AnalysisResult",
    "CoinMomentum",
    "DecisionLog",
    "Freshness",
    "MarketAnalyzer",
    "OllamaClient",
    "PortfolioAllocation",
    "PortfolioAllocator",
    "PortfolioOpportunity",
    "PortfolioPosition",
    "PortfolioState",
    "RiskConfig",
    "Sentiment",
    "Signal",
    "SignalBrain",
    "Strategy",
    "StrategyType",
    "TradingStrategy",
    "analyze_decision_log",
    "create_portfolio_allocator",
    "create_signal_brain",
    "format_ai_trading_prompt",
    "get_strategy",
    "get_strategy_prompt",
    "list_strategies",
    "register_strategy",
]
