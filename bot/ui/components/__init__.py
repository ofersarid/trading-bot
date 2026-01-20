"""
UI components for the trading dashboard.

Reusable Textual widgets for displaying trading data.
"""

from bot.ui.components.ai_panel import AIPanel
from bot.ui.components.charts_panel import ChartsPanel, MiniChart, PriceLineChart
from bot.ui.components.history_panel import HistoryPanel
from bot.ui.components.markets_panel import MarketData, MarketsPanel
from bot.ui.components.status_bar import StatusBar

__all__ = [
    "AIPanel",
    "ChartsPanel",
    "HistoryPanel",
    "MarketData",
    "MarketsPanel",
    "MiniChart",
    "PriceLineChart",
    "StatusBar",
]
