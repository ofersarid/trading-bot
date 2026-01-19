"""
Market condition analysis.

Analyzes overall market state based on momentum across tracked coins.
"""

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from bot.core.config import TradingConfig


class MarketConditionLevel(Enum):
    """Market volatility classification levels."""

    VERY_CALM = "very_calm"
    CALM = "calm"
    ACTIVE = "active"
    VOLATILE = "volatile"
    VERY_VOLATILE = "very_volatile"


class CoinStatus(Enum):
    """Individual coin momentum status."""

    RISING = "rising"
    FALLING = "falling"
    FLAT = "flat"


@dataclass
class CoinAnalysis:
    """Analysis result for a single coin."""

    coin: str
    momentum: float
    price: float
    change: float
    status: CoinStatus


@dataclass
class MarketAnalysis:
    """Complete market analysis result."""

    condition: MarketConditionLevel
    avg_abs_momentum: float
    coin_analyses: list[CoinAnalysis]

    @property
    def condition_label(self) -> str:
        """Human-readable condition label with emoji."""
        labels = {
            MarketConditionLevel.VERY_CALM: "😴 VERY CALM",
            MarketConditionLevel.CALM: "😐 CALM",
            MarketConditionLevel.ACTIVE: "📊 ACTIVE",
            MarketConditionLevel.VOLATILE: "⚡ VOLATILE",
            MarketConditionLevel.VERY_VOLATILE: "🔥 VERY VOLATILE",
        }
        return labels[self.condition]

    @property
    def condition_color(self) -> str:
        """Rich markup color for the condition."""
        colors = {
            MarketConditionLevel.VERY_CALM: "dim",
            MarketConditionLevel.CALM: "white",
            MarketConditionLevel.ACTIVE: "yellow",
            MarketConditionLevel.VOLATILE: "cyan",
            MarketConditionLevel.VERY_VOLATILE: "magenta",
        }
        return colors[self.condition]

    @property
    def description(self) -> str:
        """Description of market condition."""
        descriptions = {
            MarketConditionLevel.VERY_CALM: "Prices barely moving. Waiting for action...",
            MarketConditionLevel.CALM: "Low volatility. Minor price fluctuations.",
            MarketConditionLevel.ACTIVE: "Moderate movement. Watching for opportunities...",
            MarketConditionLevel.VOLATILE: "Significant price action! High alert.",
            MarketConditionLevel.VERY_VOLATILE: "Extreme movement! Trading opportunities likely.",
        }
        return descriptions[self.condition]


class MarketAnalyzer:
    """
    Analyzes market conditions based on price momentum.

    Separates the computation logic from UI/display concerns.
    """

    def __init__(self, config: TradingConfig):
        self.config = config

    def analyze(
        self,
        coins: list[str],
        prices: dict[str, float],
        price_history: dict[str, deque],
        momentum_timeframe: int,
    ) -> MarketAnalysis | None:
        """
        Analyze current market conditions.

        Args:
            coins: List of coin symbols to analyze
            prices: Current prices by coin
            price_history: Price history deques by coin
            momentum_timeframe: Lookback period in seconds

        Returns:
            MarketAnalysis result or None if insufficient data
        """
        now = datetime.now()
        coin_analyses: list[CoinAnalysis] = []

        for coin in coins:
            history = price_history.get(coin)
            if not history or len(history) < 2:
                continue

            current_price = prices.get(coin, 0)
            if not current_price:
                continue

            # Get price from configured timeframe ago
            lookback_price = None
            for point in history:
                age = (now - point["time"]).total_seconds()
                if age >= momentum_timeframe:
                    lookback_price = point["price"]
                    break

            if not lookback_price:
                continue

            momentum = ((current_price - lookback_price) / lookback_price) * 100
            change = current_price - lookback_price

            # Determine coin status
            if momentum > self.config.coin_rising_threshold:
                status = CoinStatus.RISING
            elif momentum < self.config.coin_falling_threshold:
                status = CoinStatus.FALLING
            else:
                status = CoinStatus.FLAT

            coin_analyses.append(
                CoinAnalysis(
                    coin=coin,
                    momentum=momentum,
                    price=current_price,
                    change=change,
                    status=status,
                )
            )

        if not coin_analyses:
            return None

        # Calculate overall market volatility
        avg_abs_momentum = sum(abs(ca.momentum) for ca in coin_analyses) / len(coin_analyses)

        # Determine market condition level
        cfg = self.config
        if avg_abs_momentum < cfg.market_very_calm_threshold:
            condition = MarketConditionLevel.VERY_CALM
        elif avg_abs_momentum < cfg.market_calm_threshold:
            condition = MarketConditionLevel.CALM
        elif avg_abs_momentum < cfg.market_active_threshold:
            condition = MarketConditionLevel.ACTIVE
        elif avg_abs_momentum < cfg.market_volatile_threshold:
            condition = MarketConditionLevel.VOLATILE
        else:
            condition = MarketConditionLevel.VERY_VOLATILE

        # Sort by absolute momentum (most volatile first)
        coin_analyses.sort(key=lambda ca: abs(ca.momentum), reverse=True)

        return MarketAnalysis(
            condition=condition,
            avg_abs_momentum=avg_abs_momentum,
            coin_analyses=coin_analyses,
        )
