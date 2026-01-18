"""
Core data models for the trading bot.

Contains dataclasses for:
- Opportunity tracking and validation
- Market conditions
- Market pressure analysis
- Trade signals
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class PressureLevel(Enum):
    """Pressure level classification."""
    STRONG_SELLING = "STRONG_SELLING"  # 0-30
    MODERATE_SELLING = "MODERATE_SELLING"  # 30-45
    NEUTRAL = "NEUTRAL"  # 45-55
    MODERATE_BUYING = "MODERATE_BUYING"  # 55-70
    STRONG_BUYING = "STRONG_BUYING"  # 70-100


@dataclass
class CoinPressure:
    """
    Per-instrument pressure for battle bar visualization.
    
    Visualizes as a "tug of war" where:
    - Sellers push from the left (red)
    - Buyers push from the right (green)
    """
    coin: str
    price: float
    
    # Pressure scores (0-100, where 50 is neutral)
    sell_pressure: float  # 0-100: strength of selling (higher = more selling)
    buy_pressure: float   # 0-100: strength of buying (higher = more buying)
    
    # Raw data for tooltips/details
    bid_volume: float
    ask_volume: float
    momentum: float  # % change
    
    @classmethod
    def calculate(
        cls,
        coin: str,
        book: dict,
        price: float,
        momentum: float = 0.0,
    ) -> "CoinPressure":
        """Calculate pressure for a single coin from its order book."""
        bids = book.get("bids", [])[:5]
        asks = book.get("asks", [])[:5]
        
        bid_volume = sum(float(b.get("sz", 0)) for b in bids)
        ask_volume = sum(float(a.get("sz", 0)) for a in asks)
        total = bid_volume + ask_volume
        
        if total > 0:
            # bid_ratio: 0 = all asks, 100 = all bids
            bid_ratio = (bid_volume / total) * 100
            # Sell pressure is inverse of bid ratio
            sell_pressure = 100 - bid_ratio
            buy_pressure = bid_ratio
        else:
            sell_pressure = 50
            buy_pressure = 50
        
        return cls(
            coin=coin,
            price=price,
            sell_pressure=sell_pressure,
            buy_pressure=buy_pressure,
            bid_volume=bid_volume,
            ask_volume=ask_volume,
            momentum=momentum,
        )
    
    def render_battle_bar(self, width: int = 20) -> str:
        """
        Render the battle bar visualization.
        
        Returns Rich markup string showing sellers vs buyers.
        """
        # Normalize to bar positions
        # sell_pressure 100 means bar fully red from left
        # buy_pressure 100 means bar fully green from right
        
        sell_fill = int((self.sell_pressure / 100) * (width // 2))
        buy_fill = int((self.buy_pressure / 100) * (width // 2))
        
        # Build the bar: [SELL░░░░░░░░░░BUY]
        half = width // 2
        
        # Left side: sells fill from left with █, rest is ░
        left_filled = "█" * sell_fill
        left_empty = "░" * (half - sell_fill)
        left_side = left_filled + left_empty
        
        # Right side: buys fill from right with █, rest is ░
        right_empty = "░" * (half - buy_fill)
        right_filled = "█" * buy_fill
        right_side = right_empty + right_filled
        
        # Color them
        red = "#ff6666"
        green = "#66ff66"
        dim = "#555555"
        
        # Determine which side is "winning"
        if self.sell_pressure > self.buy_pressure + 10:
            mood = "🔴"
        elif self.buy_pressure > self.sell_pressure + 10:
            mood = "🟢"
        else:
            mood = "⚪"
        
        return (
            f"[{red}]{left_filled}[/{red}][{dim}]{left_empty}[/{dim}]"
            f"[{dim}]{right_empty}[/{dim}][{green}]{right_filled}[/{green}]"
            f" {mood}"
        )


class MoveFreshness(Enum):
    """How fresh/extended the current move is."""
    FRESH = "FRESH"  # Just starting, high potential
    DEVELOPING = "DEVELOPING"  # Building momentum
    EXTENDED = "EXTENDED"  # Move may be exhausting
    EXHAUSTED = "EXHAUSTED"  # Likely reversal zone


@dataclass
class MarketPressure:
    """
    Aggregated market pressure score combining multiple signals.
    
    Score is 0-100 where:
    - 0-30: Strong Selling Pressure
    - 30-45: Moderate Selling
    - 45-55: Neutral
    - 55-70: Moderate Buying
    - 70-100: Strong Buying Pressure
    
    Components:
    - Order Book Imbalance (40%): bid_volume / total_volume
    - Trade Flow (40%): buy_count / total_trades  
    - Momentum Alignment (20%): direction consistency across coins
    """
    score: float  # 0-100
    level: PressureLevel
    
    # Component scores (all 0-100)
    orderbook_score: float
    trade_flow_score: float
    momentum_score: float
    
    # Raw data
    bid_ratio: float  # % of orderbook that's bids
    buy_ratio: float  # % of recent trades that are buys
    momentum_alignment: float  # How aligned momentum is across coins (-1 to 1)
    
    @classmethod
    def calculate(
        cls,
        orderbook: dict[str, dict],
        recent_trades: list[dict],
        momentum: dict[str, float],
    ) -> "MarketPressure":
        """
        Calculate market pressure from raw market data.
        
        Args:
            orderbook: {coin: {"bids": [...], "asks": [...]}}
            recent_trades: List of recent trades with "side" field
            momentum: {coin: momentum_pct}
        """
        # 1. Order Book Imbalance (40% weight)
        total_bid_volume = 0.0
        total_ask_volume = 0.0
        for coin, book in orderbook.items():
            for bid in book.get("bids", [])[:5]:
                total_bid_volume += float(bid.get("sz", 0))
            for ask in book.get("asks", [])[:5]:
                total_ask_volume += float(ask.get("sz", 0))
        
        total_volume = total_bid_volume + total_ask_volume
        bid_ratio = (total_bid_volume / total_volume * 100) if total_volume > 0 else 50
        orderbook_score = bid_ratio  # Already 0-100
        
        # 2. Trade Flow (40% weight)
        if recent_trades:
            buys = sum(1 for t in recent_trades if t.get("side") == "buy")
            buy_ratio = (buys / len(recent_trades)) * 100
        else:
            buy_ratio = 50.0
        trade_flow_score = buy_ratio  # Already 0-100
        
        # 3. Momentum Alignment (20% weight)
        # Check if all coins are moving in same direction
        if momentum:
            positive = sum(1 for m in momentum.values() if m and m > 0.05)
            negative = sum(1 for m in momentum.values() if m and m < -0.05)
            total = len(momentum)
            
            if total > 0:
                # Range from -1 (all negative) to +1 (all positive)
                momentum_alignment = (positive - negative) / total
                # Convert to 0-100 score
                momentum_score = (momentum_alignment + 1) * 50
            else:
                momentum_alignment = 0.0
                momentum_score = 50.0
        else:
            momentum_alignment = 0.0
            momentum_score = 50.0
        
        # Weighted score
        score = (
            orderbook_score * 0.40 +
            trade_flow_score * 0.40 +
            momentum_score * 0.20
        )
        
        # Determine level
        if score < 30:
            level = PressureLevel.STRONG_SELLING
        elif score < 45:
            level = PressureLevel.MODERATE_SELLING
        elif score < 55:
            level = PressureLevel.NEUTRAL
        elif score < 70:
            level = PressureLevel.MODERATE_BUYING
        else:
            level = PressureLevel.STRONG_BUYING
        
        return cls(
            score=score,
            level=level,
            orderbook_score=orderbook_score,
            trade_flow_score=trade_flow_score,
            momentum_score=momentum_score,
            bid_ratio=bid_ratio,
            buy_ratio=buy_ratio,
            momentum_alignment=momentum_alignment,
        )
    
    @property
    def label(self) -> str:
        """Human-readable pressure label."""
        labels = {
            PressureLevel.STRONG_SELLING: "Strong Selling",
            PressureLevel.MODERATE_SELLING: "Moderate Selling",
            PressureLevel.NEUTRAL: "Neutral",
            PressureLevel.MODERATE_BUYING: "Moderate Buying",
            PressureLevel.STRONG_BUYING: "Strong Buying",
        }
        return labels.get(self.level, "Unknown")
    
    @property
    def emoji(self) -> str:
        """Emoji indicator for pressure level."""
        emojis = {
            PressureLevel.STRONG_SELLING: "🔴",
            PressureLevel.MODERATE_SELLING: "🟠",
            PressureLevel.NEUTRAL: "⚪",
            PressureLevel.MODERATE_BUYING: "🟢",
            PressureLevel.STRONG_BUYING: "🟢",
        }
        return emojis.get(self.level, "⚪")


@dataclass
class OpportunityCondition:
    """A single condition that must be met for opportunity validation.
    
    Attributes:
        name: Short identifier for the condition (e.g., "Momentum", "Balance")
        description: Human-readable description of what must be true
        met: Whether this condition is currently satisfied
        value: Current value/status to display (e.g., "+0.35%", "✓")
    """
    name: str
    description: str
    met: bool = False
    value: str = ""


@dataclass
class PendingOpportunity:
    """An opportunity being validated before execution.
    
    Tracks a potential trade as conditions are progressively validated.
    When all conditions are met, the opportunity becomes valid for execution.
    
    Attributes:
        coin: Trading pair symbol (e.g., "BTC", "ETH")
        direction: Trade direction - "LONG" or "SHORT"
        conditions: List of conditions to validate
        start_time: When this opportunity was first detected
        current_price: Latest price for this coin
    """
    coin: str
    direction: str  # "LONG" or "SHORT"
    conditions: list[OpportunityCondition] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    current_price: float = 0.0

    @property
    def conditions_met(self) -> int:
        """Number of conditions currently satisfied."""
        return sum(1 for c in self.conditions if c.met)

    @property
    def total_conditions(self) -> int:
        """Total number of conditions to validate."""
        return len(self.conditions)

    @property
    def progress_bar(self) -> str:
        """Visual progress bar showing validation status."""
        filled = self.conditions_met
        total = self.total_conditions
        bar = "█" * filled + "░" * (total - filled)
        return f"[{bar}]"

    @property
    def is_valid(self) -> bool:
        """True when all conditions are met and trade can execute."""
        return all(c.met for c in self.conditions)
