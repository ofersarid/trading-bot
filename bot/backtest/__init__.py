"""
Backtest Module - Historical backtesting with the 3-layer architecture.

Orchestrates the flow: Historical Data → Indicators → Signals → AI Brain → Execution
"""

from .breakout_analyzer import BreakoutAnalysis, BreakoutAnalyzer
from .engine import BacktestEngine
from .models import BacktestConfig, BacktestResult
from .position_manager import ManagedPosition, PositionManager

__all__ = [
    "BacktestEngine",
    "BacktestConfig",
    "BacktestResult",
    "PositionManager",
    "ManagedPosition",
    "BreakoutAnalyzer",
    "BreakoutAnalysis",
]
