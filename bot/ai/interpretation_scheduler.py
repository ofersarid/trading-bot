"""
Interpretation Scheduler.

Determines when to request AI interpretation based on:
- Periodic intervals (every 12s)
- Price moves (>0.15%)
- Large trades (>3x average)
- Position monitoring (every 10s when in position)

Matches human decision-making pace, not algorithmic.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CoinScheduleState:
    """Scheduling state for a single coin."""

    last_interpretation_time: datetime | None = None
    last_interpretation_price: float = 0.0
    avg_trade_size: float = 0.0
    trade_size_samples: list[float] = field(default_factory=list)

    def update_avg_trade_size(self, trade_size: float, max_samples: int = 50) -> None:
        """Update rolling average trade size."""
        self.trade_size_samples.append(trade_size)
        if len(self.trade_size_samples) > max_samples:
            self.trade_size_samples.pop(0)

        if self.trade_size_samples:
            self.avg_trade_size = sum(self.trade_size_samples) / len(self.trade_size_samples)


class InterpretationScheduler:
    """
    Manages when to request AI interpretation - human decision pace.

    Triggers interpretation on:
    - Periodic interval (default 12s)
    - Significant price move (default 0.15%)
    - Large trade detected (default 3x average size)
    - Position check (default 10s when in position)
    """

    def __init__(
        self,
        periodic_interval: float = 12.0,
        price_move_threshold: float = 0.0015,  # 0.15%
        large_trade_multiplier: float = 3.0,
        position_check_interval: float = 10.0,
    ):
        """
        Initialize the scheduler.

        Args:
            periodic_interval: Seconds between periodic interpretations
            price_move_threshold: Price change threshold (as decimal, 0.0015 = 0.15%)
            large_trade_multiplier: Trade size multiplier to consider "large"
            position_check_interval: Seconds between position checks
        """
        self.periodic_interval = periodic_interval
        self.price_move_threshold = price_move_threshold
        self.large_trade_multiplier = large_trade_multiplier
        self.position_check_interval = position_check_interval

        self._coin_states: dict[str, CoinScheduleState] = {}

    def _get_state(self, coin: str) -> CoinScheduleState:
        """Get or create state for a coin."""
        if coin not in self._coin_states:
            self._coin_states[coin] = CoinScheduleState()
        return self._coin_states[coin]

    def _seconds_since_last(self, coin: str) -> float:
        """Get seconds since last interpretation for a coin."""
        state = self._get_state(coin)
        if state.last_interpretation_time is None:
            return float("inf")  # Never interpreted
        return (datetime.now() - state.last_interpretation_time).total_seconds()

    def should_interpret(
        self,
        coin: str,
        current_price: float,
        last_trade_size: float = 0.0,
        has_position: bool = False,
    ) -> tuple[bool, str]:
        """
        Determine if we should request AI interpretation now.

        Args:
            coin: Coin symbol
            current_price: Current market price
            last_trade_size: Size of the most recent trade
            has_position: Whether we have an open position in this coin

        Returns:
            Tuple of (should_interpret, reason)
            Reasons: "periodic", "price_move", "large_trade", "position_check", "none"
        """
        state = self._get_state(coin)
        seconds_since = self._seconds_since_last(coin)

        # Update average trade size if we got a trade
        if last_trade_size > 0:
            state.update_avg_trade_size(last_trade_size)

        # 1. Price move trigger
        if state.last_interpretation_price > 0 and current_price > 0:
            price_change = (
                abs(current_price - state.last_interpretation_price)
                / state.last_interpretation_price
            )
            if price_change >= self.price_move_threshold:
                return True, "price_move"

        # 2. Large trade trigger (don't spam - require at least 3s since last)
        if (
            last_trade_size > 0
            and state.avg_trade_size > 0
            and last_trade_size >= state.avg_trade_size * self.large_trade_multiplier
            and seconds_since >= 3.0
        ):
            return True, "large_trade"

        # 3. Position check (more frequent when in position)
        if has_position and seconds_since >= self.position_check_interval:
            return True, "position_check"

        # 4. Periodic refresh (regular rhythm)
        if seconds_since >= self.periodic_interval:
            return True, "periodic"

        return False, "none"

    def mark_interpreted(self, coin: str, price: float) -> None:
        """
        Mark that interpretation was just performed for a coin.

        Args:
            coin: Coin symbol
            price: Price at time of interpretation
        """
        state = self._get_state(coin)
        state.last_interpretation_time = datetime.now()
        state.last_interpretation_price = price

    def record_trade(self, coin: str, trade_size: float) -> None:
        """
        Record a trade for average size calculation.

        Args:
            coin: Coin symbol
            trade_size: Size of the trade
        """
        if trade_size > 0:
            state = self._get_state(coin)
            state.update_avg_trade_size(trade_size)

    def get_seconds_until_next(self, coin: str, has_position: bool = False) -> float:
        """
        Get estimated seconds until next scheduled interpretation.

        Args:
            coin: Coin symbol
            has_position: Whether we have an open position

        Returns:
            Seconds until next scheduled interpretation (may trigger sooner on events)
        """
        seconds_since = self._seconds_since_last(coin)

        if has_position:
            return max(0, self.position_check_interval - seconds_since)
        else:
            return max(0, self.periodic_interval - seconds_since)

    def get_last_interpretation_age(self, coin: str) -> float | None:
        """
        Get age of last interpretation in seconds.

        Args:
            coin: Coin symbol

        Returns:
            Seconds since last interpretation, or None if never interpreted
        """
        state = self._get_state(coin)
        if state.last_interpretation_time is None:
            return None
        return (datetime.now() - state.last_interpretation_time).total_seconds()

    def reset(self, coin: str | None = None) -> None:
        """
        Reset scheduling state.

        Args:
            coin: Coin to reset, or None to reset all
        """
        if coin is None:
            self._coin_states.clear()
        elif coin in self._coin_states:
            self._coin_states[coin] = CoinScheduleState()
