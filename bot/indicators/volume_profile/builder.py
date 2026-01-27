"""
Volume Profile Builder.

Builds Volume Profile from trade data (tick-by-tick).

Works with both:
- Historical trades (from Parquet files for backtesting)
- Live trades (from WebSocket stream for live trading)

Usage:
    builder = VolumeProfileBuilder(tick_size=10.0)

    for trade in trades:
        builder.add_trade(trade)

    profile = builder.get_profile()
    print(f"POC: {profile.poc}")
"""

from datetime import datetime, timedelta
from typing import Literal

from .models import Trade, VolumeAtPrice, VolumeProfile


class VolumeProfileBuilder:
    """
    Builds Volume Profile from trade data.

    Aggregates trades into price buckets based on tick_size.
    Tracks buy/sell volume separately for delta calculation.

    Session types:
    - "daily": Reset at UTC midnight
    - "rolling": Continuous, no automatic reset
    - "custom": Manual session management
    """

    def __init__(
        self,
        tick_size: float = 10.0,
        session_type: Literal["daily", "rolling", "custom"] = "daily",
        coin: str = "",
    ):
        """
        Initialize the builder.

        Args:
            tick_size: Price bucket size (e.g., $10 for BTC)
            session_type: How sessions are managed
            coin: Coin symbol for the profile
        """
        self.tick_size = tick_size
        self.session_type = session_type
        self.coin = coin

        # Internal state
        self._levels: dict[float, VolumeAtPrice] = {}
        self._session_start: datetime | None = None
        self._session_end: datetime | None = None
        self._trade_count: int = 0
        self._last_trade_time: datetime | None = None

    def add_trade(self, trade: Trade) -> None:
        """
        Add a single trade to the profile.

        Args:
            trade: Trade object to add
        """
        # Handle session boundaries
        if self.session_type == "daily":
            self._check_daily_session(trade.timestamp)

        # Initialize session if needed
        if self._session_start is None:
            self._session_start = trade.timestamp

        # Update session end
        self._session_end = trade.timestamp
        self._last_trade_time = trade.timestamp

        # Calculate price bucket
        bucket = self._price_to_bucket(trade.price)

        # Get or create level
        if bucket not in self._levels:
            self._levels[bucket] = VolumeAtPrice(price=bucket)

        # Add trade to level
        self._levels[bucket].add_trade(trade.size, trade.side)
        self._trade_count += 1

    def add_trades(self, trades: list[Trade]) -> None:
        """
        Add multiple trades to the profile.

        Args:
            trades: List of Trade objects
        """
        for trade in trades:
            self.add_trade(trade)

    def _price_to_bucket(self, price: float) -> float:
        """Round price to nearest tick_size bucket."""
        return round(price / self.tick_size) * self.tick_size

    def _check_daily_session(self, timestamp: datetime) -> None:
        """Check and handle daily session boundary."""
        if self._session_start is None:
            return

        # Check if we've crossed UTC midnight
        current_day = timestamp.date()
        session_day = self._session_start.date()

        if current_day != session_day:
            # New day - reset session
            self.reset_session(datetime(current_day.year, current_day.month, current_day.day))

    def get_profile(self) -> VolumeProfile:
        """
        Get the current volume profile.

        Returns:
            VolumeProfile object with current state
        """
        now = datetime.now()

        return VolumeProfile(
            session_start=self._session_start or now,
            session_end=self._session_end or now,
            tick_size=self.tick_size,
            levels=dict(self._levels),
            coin=self.coin,
        )

    def reset_session(self, session_start: datetime | None = None) -> VolumeProfile:
        """
        Start a new session.

        Clears current profile and returns the previous one.

        Args:
            session_start: Start time for new session (defaults to now)

        Returns:
            The previous session's VolumeProfile
        """
        # Get current profile before reset
        previous = self.get_profile()

        # Clear state
        self._levels.clear()
        self._session_start = session_start
        self._session_end = None
        self._trade_count = 0

        return previous

    def reset(self) -> None:
        """Clear all data and reset to initial state."""
        self._levels.clear()
        self._session_start = None
        self._session_end = None
        self._trade_count = 0
        self._last_trade_time = None

    @property
    def trade_count(self) -> int:
        """Number of trades processed in current session."""
        return self._trade_count

    @property
    def level_count(self) -> int:
        """Number of price levels in current profile."""
        return len(self._levels)

    @property
    def total_volume(self) -> float:
        """Total volume in current profile."""
        return sum(level.total_volume for level in self._levels.values())

    @property
    def total_delta(self) -> float:
        """Total delta (buy - sell) in current profile."""
        return sum(level.delta for level in self._levels.values())

    @property
    def is_empty(self) -> bool:
        """Check if profile has no data."""
        return len(self._levels) == 0

    @property
    def session_duration(self) -> timedelta | None:
        """Duration of current session."""
        if self._session_start and self._session_end:
            return self._session_end - self._session_start
        return None


class MultiSessionProfileBuilder:
    """
    Manages multiple volume profiles for different sessions.

    Useful for:
    - Tracking composite profiles (multiple days)
    - Comparing session profiles
    - Building multi-timeframe analysis
    """

    def __init__(
        self,
        tick_size: float = 10.0,
        coin: str = "",
    ):
        """
        Initialize the multi-session builder.

        Args:
            tick_size: Price bucket size
            coin: Coin symbol
        """
        self.tick_size = tick_size
        self.coin = coin

        # Current session builder
        self._current = VolumeProfileBuilder(
            tick_size=tick_size,
            session_type="custom",
            coin=coin,
        )

        # Stored session profiles
        self._sessions: list[VolumeProfile] = []

        # Composite profile (all sessions combined)
        self._composite = VolumeProfileBuilder(
            tick_size=tick_size,
            session_type="rolling",
            coin=coin,
        )

    def add_trade(self, trade: Trade) -> None:
        """Add trade to current session and composite."""
        self._current.add_trade(trade)
        self._composite.add_trade(trade)

    def end_session(self) -> VolumeProfile:
        """
        End current session and start a new one.

        Returns:
            The completed session profile
        """
        profile = self._current.reset_session()
        self._sessions.append(profile)
        return profile

    def get_current_profile(self) -> VolumeProfile:
        """Get the current session's profile."""
        return self._current.get_profile()

    def get_composite_profile(self) -> VolumeProfile:
        """Get the composite profile (all sessions)."""
        return self._composite.get_profile()

    def get_session_profiles(self) -> list[VolumeProfile]:
        """Get all stored session profiles."""
        return list(self._sessions)

    @property
    def session_count(self) -> int:
        """Number of completed sessions."""
        return len(self._sessions)

    def reset(self) -> None:
        """Clear all data."""
        self._current.reset()
        self._composite.reset()
        self._sessions.clear()
