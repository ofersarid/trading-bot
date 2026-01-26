"""AI module for local LLM-powered trading analysis."""

from bot.ai.analyzer import AIDecision, MarketAnalyzer
from bot.ai.interpretation_scheduler import InterpretationScheduler
from bot.ai.models import AIMetrics, AnalysisResult, CoinMomentum, Freshness, Sentiment, Signal
from bot.ai.ollama_client import OllamaClient
from bot.ai.prompts import format_ai_trading_prompt, get_strategy_prompt
from bot.ai.scalper_interpreter import ScalperInterpretation, ScalperInterpreter
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
    "AIDecision",
    "AIMetrics",
    "AnalysisResult",
    "CoinMomentum",
    "Freshness",
    "InterpretationScheduler",
    "MarketAnalyzer",
    "OllamaClient",
    "RiskConfig",
    "ScalperInterpretation",
    "ScalperInterpreter",
    "Sentiment",
    "Signal",
    "SignalBrain",
    "Strategy",
    "StrategyType",
    "TradingStrategy",
    "create_signal_brain",
    "format_ai_trading_prompt",
    "get_strategy",
    "get_strategy_prompt",
    "list_strategies",
    "register_strategy",
]
