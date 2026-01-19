"""
Data models for paper trading simulation.

For React developers:
- These are like TypeScript interfaces/types
- @dataclass automatically creates __init__, __repr__, etc.
- Similar to defining a type with required fields
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Side(Enum):
    """Trade direction."""

    LONG = "long"  # Betting price goes UP
    SHORT = "short"  # Betting price goes DOWN


@dataclass
class Position:
    """
    An open position in the simulator.

    Example: You're LONG 0.1 BTC at $95,000
    """

    coin: str  # "BTC", "ETH", "SOL"
    side: Side  # LONG or SHORT
    size: float  # Amount (e.g., 0.1 BTC)
    entry_price: float  # Price when opened
    entry_time: datetime  # When position was opened

    def unrealized_pnl(self, current_price: float) -> float:
        """Calculate unrealized P&L based on current price."""
        price_diff = current_price - self.entry_price

        if self.side == Side.LONG:
            # Long: profit when price goes up
            return price_diff * self.size
        else:
            # Short: profit when price goes down
            return -price_diff * self.size

    def unrealized_pnl_percent(self, current_price: float) -> float:
        """Calculate unrealized P&L as percentage."""
        pnl = self.unrealized_pnl(current_price)
        position_value = self.entry_price * self.size
        return (pnl / position_value) * 100 if position_value > 0 else 0


@dataclass
class Trade:
    """
    A completed trade (for history).

    Created when a position is closed.
    """

    coin: str
    side: Side
    size: float
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    pnl: float  # Realized profit/loss (after fees)
    fees_paid: float  # Total fees for this trade

    @property
    def pnl_percent(self) -> float:
        """P&L as percentage of position value."""
        position_value = self.entry_price * self.size
        return (self.pnl / position_value) * 100 if position_value > 0 else 0

    @property
    def duration_seconds(self) -> float:
        """How long the position was held."""
        return (self.exit_time - self.entry_time).total_seconds()


@dataclass
class SimulatorState:
    """
    Current state of the paper trading simulator.

    Snapshot of everything at a point in time.
    """

    balance: float  # Available cash (USDC)
    equity: float  # Balance + unrealized P&L
    positions: dict[str, Position]  # Open positions by coin
    total_trades: int  # Number of completed trades
    winning_trades: int  # Trades with positive P&L
    total_pnl: float  # Sum of all realized P&L
    total_fees: float  # Sum of all fees paid

    @property
    def win_rate(self) -> float:
        """Percentage of winning trades."""
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100


@dataclass
class FeeStructure:
    """
    Exchange fee structure.

    Hyperliquid fees (default):
    - Maker: -0.02% (you GET paid for limit orders!)
    - Taker: 0.05% (you pay for market orders)
    """

    maker_fee: float = -0.0002  # Negative = rebate!
    taker_fee: float = 0.0005  # 0.05%

    def calculate_fee(self, notional_value: float, is_maker: bool = False) -> float:
        """
        Calculate fee for a trade.

        Args:
            notional_value: Position size in USD (size * price)
            is_maker: True if limit order, False if market order

        Returns:
            Fee amount (negative = rebate)
        """
        rate = self.maker_fee if is_maker else self.taker_fee
        return notional_value * rate


# Preset fee structures
HYPERLIQUID_FEES = FeeStructure(maker_fee=-0.0002, taker_fee=0.0005)
BYBIT_FEES = FeeStructure(maker_fee=0.0002, taker_fee=0.00055)
