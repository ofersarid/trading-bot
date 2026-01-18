"""
Paper Trading Simulator

Simulates trading with fake money using real market data.
Tracks positions, calculates P&L, applies fees.

For React developers:
- This is like a state manager (Redux/Zustand) for trading
- Methods modify internal state and return results
- All "trades" happen locally - no real money involved!
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from bot.simulation.models import (
    FeeStructure,
    HYPERLIQUID_FEES,
    Position,
    Side,
    SimulatorState,
    Trade,
)


@dataclass
class OrderResult:
    """Result of attempting to place an order."""
    success: bool
    message: str
    position: Position | None = None
    trade: Trade | None = None  # Only if closing a position


class PaperTrader:
    """
    Paper trading simulator with real-time P&L tracking.
    
    Usage:
        trader = PaperTrader(starting_balance=10000)
        trader.open_long("BTC", size=0.1, price=95000)
        trader.close_position("BTC", price=96000)
        print(trader.get_state())
    """
    
    def __init__(
        self,
        starting_balance: float = 10000,
        fees: FeeStructure = HYPERLIQUID_FEES,
        max_position_size_pct: float = 0.25,  # Max 25% of balance per position
        on_trade: Callable[[Trade], None] | None = None,
    ):
        """
        Initialize the paper trader.
        
        Args:
            starting_balance: Starting cash in USD
            fees: Fee structure to use (default: Hyperliquid)
            max_position_size_pct: Maximum position size as % of balance
            on_trade: Optional callback when a trade completes
        """
        self.starting_balance = starting_balance
        self.balance = starting_balance
        self.fees = fees
        self.max_position_size_pct = max_position_size_pct
        self.on_trade = on_trade
        
        # State
        self.positions: dict[str, Position] = {}
        self.trade_history: list[Trade] = []
        self.total_fees_paid: float = 0.0
        
    def open_long(
        self,
        coin: str,
        size: float,
        price: float,
        is_maker: bool = False,
    ) -> OrderResult:
        """
        Open a LONG position (betting price goes UP).
        
        Args:
            coin: Symbol (e.g., "BTC")
            size: Amount to buy (e.g., 0.1 BTC)
            price: Current market price
            is_maker: True if simulating a limit order fill
        
        Returns:
            OrderResult with success status and details
        """
        return self._open_position(coin, Side.LONG, size, price, is_maker)
    
    def open_short(
        self,
        coin: str,
        size: float,
        price: float,
        is_maker: bool = False,
    ) -> OrderResult:
        """
        Open a SHORT position (betting price goes DOWN).
        
        Args:
            coin: Symbol (e.g., "BTC")
            size: Amount to sell (e.g., 0.1 BTC)
            price: Current market price
            is_maker: True if simulating a limit order fill
        
        Returns:
            OrderResult with success status and details
        """
        return self._open_position(coin, Side.SHORT, size, price, is_maker)
    
    def _open_position(
        self,
        coin: str,
        side: Side,
        size: float,
        price: float,
        is_maker: bool,
    ) -> OrderResult:
        """Internal: Open a position."""
        # Check if already have position in this coin
        if coin in self.positions:
            return OrderResult(
                success=False,
                message=f"Already have open position in {coin}. Close it first.",
            )
        
        # Calculate notional value and fee
        notional_value = size * price
        fee = self.fees.calculate_fee(notional_value, is_maker)
        
        # Check if enough balance (need margin for position + fee)
        required_margin = notional_value * 0.1  # Assume 10x leverage available
        total_required = required_margin + max(fee, 0)  # Only add fee if positive
        
        if total_required > self.balance:
            return OrderResult(
                success=False,
                message=f"Insufficient balance. Need ${total_required:.2f}, have ${self.balance:.2f}",
            )
        
        # Check position size limit
        max_notional = self.balance * self.max_position_size_pct * 10  # With 10x leverage
        if notional_value > max_notional:
            return OrderResult(
                success=False,
                message=f"Position too large. Max ${max_notional:.2f}, requested ${notional_value:.2f}",
            )
        
        # Create position
        position = Position(
            coin=coin,
            side=side,
            size=size,
            entry_price=price,
            entry_time=datetime.now(),
        )
        
        # Update state
        self.positions[coin] = position
        self.balance -= max(fee, 0)  # Deduct fee if positive (or add rebate)
        if fee < 0:
            self.balance -= fee  # Negative fee = rebate = add to balance
        self.total_fees_paid += fee
        
        side_str = "LONG" if side == Side.LONG else "SHORT"
        return OrderResult(
            success=True,
            message=f"Opened {side_str} {size} {coin} @ ${price:,.2f} (fee: ${fee:.4f})",
            position=position,
        )
    
    def close_position(
        self,
        coin: str,
        price: float,
        is_maker: bool = False,
    ) -> OrderResult:
        """
        Close an open position.
        
        Args:
            coin: Symbol to close
            price: Current market price
            is_maker: True if simulating a limit order fill
        
        Returns:
            OrderResult with trade details
        """
        if coin not in self.positions:
            return OrderResult(
                success=False,
                message=f"No open position in {coin}",
            )
        
        position = self.positions[coin]
        
        # Calculate P&L
        raw_pnl = position.unrealized_pnl(price)
        
        # Calculate closing fee
        notional_value = position.size * price
        fee = self.fees.calculate_fee(notional_value, is_maker)
        
        # Net P&L after fees
        net_pnl = raw_pnl - fee
        
        # Create trade record
        trade = Trade(
            coin=coin,
            side=position.side,
            size=position.size,
            entry_price=position.entry_price,
            exit_price=price,
            entry_time=position.entry_time,
            exit_time=datetime.now(),
            pnl=net_pnl,
            fees_paid=fee,
        )
        
        # Update state
        del self.positions[coin]
        self.balance += net_pnl
        self.total_fees_paid += fee
        self.trade_history.append(trade)
        
        # Callback
        if self.on_trade:
            self.on_trade(trade)
        
        pnl_str = f"+${net_pnl:.2f}" if net_pnl >= 0 else f"-${abs(net_pnl):.2f}"
        side_str = "LONG" if position.side == Side.LONG else "SHORT"
        return OrderResult(
            success=True,
            message=f"Closed {side_str} {position.size} {coin} @ ${price:,.2f} | P&L: {pnl_str}",
            trade=trade,
        )
    
    def get_equity(self, current_prices: dict[str, float]) -> float:
        """
        Calculate total equity (balance + unrealized P&L).
        
        Args:
            current_prices: Dict of current prices {"BTC": 95000, ...}
        
        Returns:
            Total equity in USD
        """
        unrealized_pnl = 0.0
        for coin, position in self.positions.items():
            if coin in current_prices:
                unrealized_pnl += position.unrealized_pnl(current_prices[coin])
        
        return self.balance + unrealized_pnl
    
    def get_state(self, current_prices: dict[str, float] | None = None) -> SimulatorState:
        """
        Get current simulator state.
        
        Args:
            current_prices: Optional current prices for equity calculation
        
        Returns:
            SimulatorState snapshot
        """
        equity = self.balance
        if current_prices:
            equity = self.get_equity(current_prices)
        
        winning = sum(1 for t in self.trade_history if t.pnl > 0)
        total_pnl = sum(t.pnl for t in self.trade_history)
        
        return SimulatorState(
            balance=self.balance,
            equity=equity,
            positions=self.positions.copy(),
            total_trades=len(self.trade_history),
            winning_trades=winning,
            total_pnl=total_pnl,
            total_fees=self.total_fees_paid,
        )
    
    def reset(self):
        """Reset simulator to starting state."""
        self.balance = self.starting_balance
        self.positions.clear()
        self.trade_history.clear()
        self.total_fees_paid = 0.0
    
    def load_state(
        self,
        balance: float,
        positions: dict[str, Position],
        total_fees_paid: float,
    ) -> None:
        """
        Load state from a saved session.
        
        Args:
            balance: The balance to restore
            positions: Dictionary of open positions to restore
            total_fees_paid: Total fees paid in the session
        """
        self.balance = balance
        self.positions = positions.copy()
        self.total_fees_paid = total_fees_paid
    
    def get_winning_count(self) -> int:
        """Get the number of winning trades in history."""
        return sum(1 for t in self.trade_history if t.pnl > 0)
    
    def print_status(self, current_prices: dict[str, float] | None = None):
        """Print current status to console."""
        state = self.get_state(current_prices)
        
        print("\n" + "=" * 50)
        print("📊 PAPER TRADING STATUS")
        print("=" * 50)
        print(f"💰 Balance:     ${state.balance:,.2f}")
        print(f"📈 Equity:      ${state.equity:,.2f}")
        print(f"💵 Total P&L:   ${state.total_pnl:+,.2f}")
        print(f"💸 Fees Paid:   ${state.total_fees:,.2f}")
        print(f"📊 Win Rate:    {state.win_rate:.1f}% ({state.winning_trades}/{state.total_trades})")
        
        if state.positions:
            print("\n📌 OPEN POSITIONS:")
            print("-" * 50)
            for coin, pos in state.positions.items():
                price = current_prices.get(coin, pos.entry_price) if current_prices else pos.entry_price
                pnl = pos.unrealized_pnl(price)
                pnl_pct = pos.unrealized_pnl_percent(price)
                side = "LONG" if pos.side == Side.LONG else "SHORT"
                print(f"  {coin}: {side} {pos.size} @ ${pos.entry_price:,.2f}")
                print(f"       Current: ${price:,.2f} | P&L: ${pnl:+,.2f} ({pnl_pct:+.2f}%)")
        else:
            print("\n📌 No open positions")
        
        print("=" * 50 + "\n")
