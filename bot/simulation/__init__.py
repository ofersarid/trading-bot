"""
Paper Trading Simulation

Simulate trades with fake money using real market data.
No risk, unlimited resets, configurable starting balance.
"""

from bot.simulation.models import Position, SimulatorState, Trade
from bot.simulation.paper_trader import PaperTrader
from bot.simulation.state_manager import SessionState, SessionStateManager

__all__ = [
    "PaperTrader",
    "Position",
    "SessionState",
    "SessionStateManager",
    "SimulatorState",
    "Trade",
]
