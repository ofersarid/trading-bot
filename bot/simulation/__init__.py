"""
Paper Trading Simulation

Simulate trades with fake money using real market data.
No risk, unlimited resets, configurable starting balance.
"""

from bot.simulation.paper_trader import PaperTrader
from bot.simulation.models import Position, Trade, SimulatorState
from bot.simulation.state_manager import SessionStateManager, SessionState

__all__ = [
    "PaperTrader",
    "Position",
    "Trade",
    "SimulatorState",
    "SessionStateManager",
    "SessionState",
]
