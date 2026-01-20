"""AI module for local LLM-powered trading analysis."""

from bot.ai.analyzer import AIDecision, MarketAnalyzer
from bot.ai.interpretation_scheduler import InterpretationScheduler
from bot.ai.models import AIMetrics, AnalysisResult, CoinMomentum, Freshness, Sentiment, Signal
from bot.ai.ollama_client import OllamaClient
from bot.ai.scalper_interpreter import ScalperInterpretation, ScalperInterpreter
from bot.ai.strategies import TradingStrategy, get_strategy_prompt, list_strategies

__all__ = [
    "AIDecision",
    "AIMetrics",
    "AnalysisResult",
    "CoinMomentum",
    "Freshness",
    "InterpretationScheduler",
    "MarketAnalyzer",
    "OllamaClient",
    "ScalperInterpretation",
    "ScalperInterpreter",
    "Sentiment",
    "Signal",
    "TradingStrategy",
    "get_strategy_prompt",
    "list_strategies",
]
