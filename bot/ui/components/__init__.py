"""
UI components for the trading dashboard.

Reusable Textual widgets for displaying trading data.
"""

from bot.ui.components.prices_panel import PricesPanel
from bot.ui.components.orderbook_panel import OrderBookPanel
from bot.ui.components.trades_panel import TradesPanel
from bot.ui.components.ai_panel import AIPanel
from bot.ui.components.opportunities_panel import OpportunitiesPanel
from bot.ui.components.positions_panel import PositionsPanel
from bot.ui.components.history_panel import HistoryPanel
from bot.ui.components.status_bar import StatusBar

__all__ = [
    "PricesPanel",
    "OrderBookPanel",
    "TradesPanel",
    "AIPanel",
    "OpportunitiesPanel",
    "PositionsPanel",
    "HistoryPanel",
    "StatusBar",
]
