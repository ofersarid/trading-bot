"""
Volume Profile Data Models.

Core data structures for Volume Profile analysis:
- Trade: Individual trade from exchange
- VolumeAtPrice: Aggregated volume data at a price level
- VolumeProfile: Complete profile for a trading session
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class Trade:
    """
    Single trade from exchange.

    Represents one executed trade with price, size, and aggressor side.
    """

    timestamp: datetime
    price: float
    size: float
    side: Literal["B", "A"]  # B=buy aggressor (hit ask), A=sell aggressor (hit bid)
    coin: str = ""  # Optional coin identifier

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "price": self.price,
            "size": self.size,
            "side": self.side,
            "coin": self.coin,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Trade":
        """Create from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            price=float(data["price"]),
            size=float(data["size"]),
            side=data["side"],
            coin=data.get("coin", ""),
        )


@dataclass
class VolumeAtPrice:
    """
    Volume data at a single price level.

    Tracks total volume and breakdown by aggressor side (buy/sell).
    Delta = buy_volume - sell_volume indicates net buying pressure.
    """

    price: float
    total_volume: float = 0.0
    buy_volume: float = 0.0  # Volume from buy aggressors (hitting ask)
    sell_volume: float = 0.0  # Volume from sell aggressors (hitting bid)

    @property
    def delta(self) -> float:
        """Net buying pressure (positive = more buyers, negative = more sellers)."""
        return self.buy_volume - self.sell_volume

    @property
    def delta_pct(self) -> float:
        """Delta as percentage of total volume (-100 to +100)."""
        if self.total_volume == 0:
            return 0.0
        return (self.delta / self.total_volume) * 100

    def add_trade(self, size: float, side: Literal["B", "A"]) -> None:
        """Add a trade to this price level."""
        self.total_volume += size
        if side == "B":
            self.buy_volume += size
        else:
            self.sell_volume += size

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "price": self.price,
            "total_volume": self.total_volume,
            "buy_volume": self.buy_volume,
            "sell_volume": self.sell_volume,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VolumeAtPrice":
        """Create from dictionary."""
        return cls(
            price=float(data["price"]),
            total_volume=float(data["total_volume"]),
            buy_volume=float(data["buy_volume"]),
            sell_volume=float(data["sell_volume"]),
        )


@dataclass
class VolumeProfile:
    """
    Complete volume profile for a trading session.

    Contains volume distribution across price levels with buy/sell breakdown.
    Provides methods to calculate POC, Value Area, HVN/LVN, and delta metrics.
    """

    session_start: datetime
    session_end: datetime
    tick_size: float
    levels: dict[float, VolumeAtPrice] = field(default_factory=dict)
    coin: str = ""

    @property
    def total_volume(self) -> float:
        """Total volume across all price levels."""
        return sum(level.total_volume for level in self.levels.values())

    @property
    def total_delta(self) -> float:
        """Total delta (net buying pressure) across all levels."""
        return sum(level.delta for level in self.levels.values())

    @property
    def total_delta_pct(self) -> float:
        """Total delta as percentage of total volume."""
        total = self.total_volume
        if total == 0:
            return 0.0
        return (self.total_delta / total) * 100

    @property
    def poc(self) -> float | None:
        """
        Point of Control - price level with highest volume.

        Returns None if profile is empty.
        """
        if not self.levels:
            return None
        return max(self.levels, key=lambda p: self.levels[p].total_volume)

    @property
    def price_range(self) -> tuple[float, float] | None:
        """
        Price range of the profile (low, high).

        Returns None if profile is empty.
        """
        if not self.levels:
            return None
        prices = list(self.levels.keys())
        return (min(prices), max(prices))

    @property
    def level_count(self) -> int:
        """Number of price levels in the profile."""
        return len(self.levels)

    def get_volume_at_price(self, price: float) -> float:
        """Get total volume at a specific price level."""
        level = self.levels.get(price)
        return level.total_volume if level else 0.0

    def get_delta_at_price(self, price: float) -> float:
        """Get delta at a specific price level."""
        level = self.levels.get(price)
        return level.delta if level else 0.0

    def get_sorted_levels(self, by: str = "price") -> list[VolumeAtPrice]:
        """
        Get levels sorted by specified attribute.

        Args:
            by: "price" (ascending), "volume" (descending), or "delta" (descending)

        Returns:
            Sorted list of VolumeAtPrice objects
        """
        levels = list(self.levels.values())
        if by == "price":
            return sorted(levels, key=lambda x: x.price)
        elif by == "volume":
            return sorted(levels, key=lambda x: x.total_volume, reverse=True)
        elif by == "delta":
            return sorted(levels, key=lambda x: x.delta, reverse=True)
        return levels

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "session_start": self.session_start.isoformat(),
            "session_end": self.session_end.isoformat(),
            "tick_size": self.tick_size,
            "coin": self.coin,
            "levels": {str(k): v.to_dict() for k, v in self.levels.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VolumeProfile":
        """Create from dictionary."""
        return cls(
            session_start=datetime.fromisoformat(data["session_start"]),
            session_end=datetime.fromisoformat(data["session_end"]),
            tick_size=float(data["tick_size"]),
            coin=data.get("coin", ""),
            levels={float(k): VolumeAtPrice.from_dict(v) for k, v in data["levels"].items()},
        )
