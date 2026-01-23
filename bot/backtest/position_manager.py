"""
Position Manager - Handles position lifecycle and trailing stops.

Manages open positions during backtesting, including:
- Opening positions from TradePlans
- Updating trailing stops as price moves
- Checking stop-loss and take-profit conditions
"""

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from bot.simulation.models import Position, Side, Trade

if TYPE_CHECKING:
    from bot.ai.models import TradePlan
    from bot.simulation.paper_trader import PaperTrader


@dataclass
class ManagedPosition:
    """
    A position with trailing stop management.

    Extends the base Position with stop-loss, take-profit, and
    trailing stop functionality.
    """

    position: Position
    stop_loss: float
    take_profit: float
    trail_activation: float
    trail_distance_pct: float

    # Trailing stop state
    trailing_active: bool = False
    trailing_stop: float = 0.0
    highest_price: float = 0.0  # For long positions
    lowest_price: float = float("inf")  # For short positions

    def __post_init__(self) -> None:
        """Initialize price tracking."""
        self.highest_price = self.position.entry_price
        self.lowest_price = self.position.entry_price

    @property
    def coin(self) -> str:
        """Get the coin symbol."""
        return self.position.coin

    @property
    def is_long(self) -> bool:
        """True if this is a long position."""
        return self.position.side == Side.LONG

    def update_price(self, current_price: float) -> None:
        """
        Update price tracking and trailing stop.

        Args:
            current_price: Current market price
        """
        if self.is_long:
            # Track highest price for long positions
            if current_price > self.highest_price:
                self.highest_price = current_price

            # Check if trailing should activate
            if not self.trailing_active and current_price >= self.trail_activation:
                self.trailing_active = True
                self._update_trailing_stop(current_price)

            # Update trailing stop if active
            elif self.trailing_active:
                self._update_trailing_stop(current_price)
        else:
            # Track lowest price for short positions
            if current_price < self.lowest_price:
                self.lowest_price = current_price

            # Check if trailing should activate
            if not self.trailing_active and current_price <= self.trail_activation:
                self.trailing_active = True
                self._update_trailing_stop(current_price)

            # Update trailing stop if active
            elif self.trailing_active:
                self._update_trailing_stop(current_price)

    def _update_trailing_stop(self, current_price: float) -> None:
        """Update trailing stop based on current price."""
        trail_distance = current_price * (self.trail_distance_pct / 100)

        if self.is_long:
            # Trail below the highest price
            new_stop = self.highest_price - trail_distance
            # Only move stop up, never down
            if new_stop > self.trailing_stop:
                self.trailing_stop = new_stop
        else:
            # Trail above the lowest price
            new_stop = self.lowest_price + trail_distance
            # Only move stop down, never up
            if self.trailing_stop == 0 or new_stop < self.trailing_stop:
                self.trailing_stop = new_stop

    def check_exit(self, current_price: float) -> str | None:
        """
        Check if position should be closed.

        Args:
            current_price: Current market price

        Returns:
            Exit reason string if should exit, None otherwise
        """
        if self.is_long:
            # Check stop loss (fixed or trailing)
            active_stop = self.trailing_stop if self.trailing_active else self.stop_loss
            if current_price <= active_stop:
                return "trailing_stop" if self.trailing_active else "stop_loss"

            # Check take profit
            if current_price >= self.take_profit:
                return "take_profit"
        else:
            # Short position - reversed logic
            active_stop = self.trailing_stop if self.trailing_active else self.stop_loss
            if current_price >= active_stop:
                return "trailing_stop" if self.trailing_active else "stop_loss"

            # Check take profit (price going down is profit for shorts)
            if current_price <= self.take_profit:
                return "take_profit"

        return None

    def get_current_stop(self) -> float:
        """Get the current active stop price."""
        if self.trailing_active:
            return self.trailing_stop
        return self.stop_loss


class PositionManager:
    """
    Manages positions with trailing stop logic.

    Coordinates with PaperTrader for execution while managing
    the additional trailing stop state.
    """

    def __init__(self, paper_trader: "PaperTrader") -> None:
        """
        Initialize position manager.

        Args:
            paper_trader: PaperTrader instance for execution
        """
        self.trader = paper_trader
        self.managed_positions: dict[str, ManagedPosition] = {}
        self.exit_reasons: dict[str, str] = {}  # Track why positions were closed

    def open_position(
        self,
        plan: "TradePlan",
        current_price: float,
        _timestamp: datetime | None = None,
    ) -> ManagedPosition | None:
        """
        Open a new position from a TradePlan.

        Args:
            plan: TradePlan from AI
            current_price: Current market price
            timestamp: Optional timestamp (for backtesting)

        Returns:
            ManagedPosition if opened successfully, None otherwise
        """
        if not plan.is_actionable:
            return None

        # Calculate position size
        balance = self.trader.balance
        position_value = balance * (plan.size_pct / 100)
        size = position_value / current_price

        # Open position via PaperTrader
        if plan.is_long:
            result = self.trader.open_long(plan.coin, size, current_price)
        else:
            result = self.trader.open_short(plan.coin, size, current_price)

        if not result.success or result.position is None:
            return None

        # Create managed position with trailing stop info
        managed = ManagedPosition(
            position=result.position,
            stop_loss=plan.stop_loss,
            take_profit=plan.take_profit,
            trail_activation=plan.trail_activation,
            trail_distance_pct=plan.trail_distance_pct,
        )

        self.managed_positions[plan.coin] = managed
        return managed

    def update_prices(self, prices: dict[str, float]) -> list[str]:
        """
        Update all positions with current prices.

        Args:
            prices: Dict of current prices by coin

        Returns:
            List of coins that hit exit conditions
        """
        exits_triggered: list[str] = []

        for coin, managed in list(self.managed_positions.items()):
            if coin not in prices:
                continue

            current_price = prices[coin]
            managed.update_price(current_price)

            exit_reason = managed.check_exit(current_price)
            if exit_reason:
                exits_triggered.append(coin)
                self.exit_reasons[coin] = exit_reason

        return exits_triggered

    def close_position(
        self,
        coin: str,
        current_price: float,
        reason: str = "manual",
    ) -> Trade | None:
        """
        Close a managed position.

        Args:
            coin: Coin to close
            current_price: Current market price
            reason: Exit reason for logging

        Returns:
            Trade record if closed, None otherwise
        """
        if coin not in self.managed_positions:
            return None

        result = self.trader.close_position(coin, current_price)

        if result.success:
            del self.managed_positions[coin]
            self.exit_reasons[coin] = reason
            return result.trade

        return None

    def check_exits(self, prices: dict[str, float]) -> list[tuple[str, str]]:
        """
        Check all positions for exit conditions and close them.

        Args:
            prices: Dict of current prices by coin

        Returns:
            List of (coin, exit_reason) tuples for closed positions
        """
        closed: list[tuple[str, str]] = []

        exits = self.update_prices(prices)
        for coin in exits:
            if coin in prices:
                reason = self.exit_reasons.get(coin, "unknown")
                trade = self.close_position(coin, prices[coin], reason)
                if trade:
                    closed.append((coin, reason))

        return closed

    def get_position(self, coin: str) -> ManagedPosition | None:
        """Get a managed position by coin."""
        return self.managed_positions.get(coin)

    def has_position(self, coin: str) -> bool:
        """Check if there's an open position for a coin."""
        return coin in self.managed_positions

    @property
    def open_positions(self) -> dict[str, ManagedPosition]:
        """Get all open managed positions."""
        return self.managed_positions.copy()

    @property
    def position_count(self) -> int:
        """Number of open positions."""
        return len(self.managed_positions)

    def close_all(self, prices: dict[str, float]) -> list[Trade]:
        """
        Close all open positions.

        Args:
            prices: Current prices by coin

        Returns:
            List of Trade records
        """
        trades: list[Trade] = []

        for coin in list(self.managed_positions.keys()):
            if coin in prices:
                trade = self.close_position(coin, prices[coin], "end_of_backtest")
                if trade:
                    trades.append(trade)

        return trades
