"""
Market Opportunity Seeker Strategy

Watches BTC, ETH, SOL for trading opportunities based on momentum.
Simple strategy that can be evolved over time.

Strategy Logic:
- Track price changes over a short window
- If price moves significantly → opportunity detected
- Go LONG if price momentum is UP
- Go SHORT if price momentum is DOWN

For React developers:
- This is like a custom hook that reacts to price changes
- It maintains internal state (price history)
- Emits "signals" when opportunities are detected
"""

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Signal(Enum):
    """Trading signal."""

    LONG = "long"  # Go long (buy)
    SHORT = "short"  # Go short (sell)
    HOLD = "hold"  # Do nothing
    CLOSE = "close"  # Close existing position


@dataclass
class Opportunity:
    """A detected trading opportunity."""

    coin: str
    signal: Signal
    price: float
    reason: str
    strength: float  # 0-1, how strong the signal is
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PricePoint:
    """A single price observation."""

    price: float
    timestamp: datetime


class OpportunitySeeker:
    """
    Watches multiple coins for trading opportunities.

    Strategy: Momentum-based
    - If price increases by X% in Y seconds → LONG signal
    - If price decreases by X% in Y seconds → SHORT signal
    - If position is profitable by Z% → CLOSE signal

    Usage:
        seeker = OpportunitySeeker(
            coins=["BTC", "ETH", "SOL"],
            on_opportunity=lambda opp: print(f"Found: {opp}")
        )

        # Feed prices from WebSocket
        seeker.update_price("BTC", 95000)
        seeker.update_price("BTC", 95500)  # Might trigger opportunity!
    """

    def __init__(
        self,
        coins: list[str] | None = None,
        momentum_threshold_pct: float = 0.3,  # 0.3% move = opportunity
        lookback_seconds: float = 60,  # Look at last 60 seconds
        take_profit_pct: float = 0.5,  # Close at 0.5% profit
        stop_loss_pct: float = 0.3,  # Close at 0.3% loss
        cooldown_seconds: float = 30,  # Wait 30s after signal
        on_opportunity: Callable[[Opportunity], None] | None = None,
    ):
        """
        Initialize the opportunity seeker.

        Args:
            coins: Coins to watch (default: BTC, ETH, SOL)
            momentum_threshold_pct: % move to trigger signal
            lookback_seconds: How far back to measure momentum
            take_profit_pct: % profit to trigger close
            stop_loss_pct: % loss to trigger close
            cooldown_seconds: Minimum time between signals
            on_opportunity: Callback when opportunity detected
        """
        self.coins = coins or ["BTC", "ETH", "SOL"]
        self.momentum_threshold = momentum_threshold_pct / 100
        self.lookback_seconds = lookback_seconds
        self.take_profit = take_profit_pct / 100
        self.stop_loss = stop_loss_pct / 100
        self.cooldown_seconds = cooldown_seconds
        self.on_opportunity = on_opportunity

        # Price history for each coin (last N prices)
        self.price_history: dict[str, deque[PricePoint]] = {
            coin: deque(maxlen=1000) for coin in self.coins
        }

        # Current positions (for take profit / stop loss)
        self.positions: dict[str, dict] = {}  # {coin: {side, entry_price}}

        # Last signal time (for cooldown)
        self.last_signal_time: dict[str, datetime] = {}

        # Latest prices
        self.current_prices: dict[str, float] = {}

        # Simulated time (for historical replay mode)
        # If set, this overrides datetime.now()
        self._current_time: datetime | None = None

    def update_price(self, coin: str, price: float) -> Opportunity | None:
        """
        Update price and check for opportunities.

        Args:
            coin: Symbol (e.g., "BTC")
            price: Current price

        Returns:
            Opportunity if one is detected, None otherwise
        """
        if coin not in self.coins:
            return None

        # Use simulated time if set (historical mode), otherwise real time
        now = self._current_time if self._current_time else datetime.now()

        # Record price
        self.price_history[coin].append(PricePoint(price=price, timestamp=now))
        self.current_prices[coin] = price

        # Check for close signals first (take profit / stop loss)
        if coin in self.positions:
            close_opp = self._check_exit(coin, price, now)
            if close_opp:
                return close_opp

        # Check for entry signals (momentum)
        entry_opp = self._check_entry(coin, price, now)
        if entry_opp:
            return entry_opp

        return None

    def _check_exit(self, coin: str, price: float, _now: datetime) -> Opportunity | None:
        """Check if we should close position (take profit or stop loss)."""
        pos = self.positions.get(coin)
        if not pos:
            return None

        entry_price = pos["entry_price"]
        side = pos["side"]

        # Calculate P&L %
        if side == "long":
            pnl_pct = (price - entry_price) / entry_price
        else:
            pnl_pct = (entry_price - price) / entry_price

        # Use simulated time if set (historical mode), otherwise real time
        now = self._current_time if self._current_time else datetime.now()

        # Check take profit
        if pnl_pct >= self.take_profit:
            opp = Opportunity(
                coin=coin,
                signal=Signal.CLOSE,
                price=price,
                reason=f"Take profit hit ({pnl_pct * 100:.2f}%)",
                strength=1.0,
                timestamp=now,
            )
            del self.positions[coin]
            if self.on_opportunity:
                self.on_opportunity(opp)
            return opp

        # Check stop loss
        if pnl_pct <= -self.stop_loss:
            opp = Opportunity(
                coin=coin,
                signal=Signal.CLOSE,
                price=price,
                reason=f"Stop loss hit ({pnl_pct * 100:.2f}%)",
                strength=1.0,
                timestamp=now,
            )
            del self.positions[coin]
            if self.on_opportunity:
                self.on_opportunity(opp)
            return opp

        return None

    def _check_entry(self, coin: str, price: float, now: datetime) -> Opportunity | None:
        """Check if we should enter a position (momentum signal)."""
        # Skip if already in position
        if coin in self.positions:
            return None

        # Skip if in cooldown
        last_signal = self.last_signal_time.get(coin)
        if last_signal:
            elapsed = (now - last_signal).total_seconds()
            if elapsed < self.cooldown_seconds:
                return None

        # Get price from lookback_seconds ago
        history = self.price_history[coin]
        if len(history) < 2:
            return None

        # Find price from ~lookback_seconds ago
        old_price = None
        for point in history:
            age = (now - point.timestamp).total_seconds()
            if age >= self.lookback_seconds:
                old_price = point.price
                break

        if old_price is None:
            # Not enough history yet
            return None

        # Calculate momentum
        momentum = (price - old_price) / old_price

        # Check threshold
        if abs(momentum) < self.momentum_threshold:
            return None

        # Generate signal
        if momentum > 0:
            signal = Signal.LONG
            reason = f"Bullish momentum: +{momentum * 100:.2f}% in {self.lookback_seconds}s"
        else:
            signal = Signal.SHORT
            reason = f"Bearish momentum: {momentum * 100:.2f}% in {self.lookback_seconds}s"

        # Record position and signal time
        self.positions[coin] = {
            "side": "long" if signal == Signal.LONG else "short",
            "entry_price": price,
        }
        self.last_signal_time[coin] = now

        opp = Opportunity(
            coin=coin,
            signal=signal,
            price=price,
            reason=reason,
            strength=min(abs(momentum) / self.momentum_threshold, 1.0),
            timestamp=now,
        )

        if self.on_opportunity:
            self.on_opportunity(opp)

        return opp

    def get_current_prices(self) -> dict[str, float]:
        """Get latest prices for all coins."""
        return self.current_prices.copy()

    def clear_position(self, coin: str):
        """Clear tracked position (call when simulator closes position)."""
        if coin in self.positions:
            del self.positions[coin]
