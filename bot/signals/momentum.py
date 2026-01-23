"""
Momentum Signal Detector - EMA crossover based momentum detection.

Generates LONG signals when fast EMA crosses above slow EMA,
and SHORT signals when fast EMA crosses below slow EMA.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bot.indicators import ema_series

from .base import Signal, SignalType

if TYPE_CHECKING:
    from bot.core.candle_aggregator import Candle


@dataclass
class MomentumConfig:
    """Configuration for momentum signal detection."""

    fast_period: int = 9
    slow_period: int = 21
    threshold: float = 0.001  # Minimum EMA difference as % of price


class MomentumSignalDetector:
    """
    Detects momentum signals using EMA crossover.

    Tracks the relationship between fast and slow EMAs to identify
    trend changes and momentum shifts.
    """

    def __init__(self, config: MomentumConfig | None = None) -> None:
        """
        Initialize the momentum detector.

        Args:
            config: Configuration for signal detection (uses defaults if None)
        """
        self.config = config or MomentumConfig()
        self._last_crossover_direction: dict[str, str | None] = {}

    def detect(self, coin: str, candles: list["Candle"]) -> Signal | None:
        """
        Detect momentum signal from EMA crossover.

        Args:
            coin: Trading pair symbol
            candles: List of candles, most recent last

        Returns:
            Signal if crossover detected, None otherwise
        """
        min_candles = self.config.slow_period + 2  # Need extra for crossover detection
        if len(candles) < min_candles:
            return None

        # Extract close prices
        prices = [c.close for c in candles]

        # Calculate EMA series
        fast_ema = ema_series(prices, self.config.fast_period)
        slow_ema = ema_series(prices, self.config.slow_period)

        if len(fast_ema) < 2 or len(slow_ema) < 2:
            return None

        # Align EMAs (fast starts earlier)
        offset = self.config.slow_period - self.config.fast_period
        aligned_fast = fast_ema[offset:]

        if len(aligned_fast) < 2:
            return None

        # Get current and previous values
        current_fast = aligned_fast[-1]
        current_slow = slow_ema[-1]
        prev_fast = aligned_fast[-2]
        prev_slow = slow_ema[-2]

        # Calculate difference as percentage of price
        current_price = prices[-1]
        diff_pct = abs(current_fast - current_slow) / current_price

        # Check for crossover
        was_above = prev_fast > prev_slow
        is_above = current_fast > current_slow

        # Determine crossover direction
        crossover_direction: str | None = None
        if not was_above and is_above:
            crossover_direction = "LONG"
        elif was_above and not is_above:
            crossover_direction = "SHORT"

        # No crossover detected
        if crossover_direction is None:
            return None

        # Check if this is a new crossover (not a repeat)
        last_direction = self._last_crossover_direction.get(coin)
        if last_direction == crossover_direction:
            return None

        # Update last crossover direction
        self._last_crossover_direction[coin] = crossover_direction

        # Check if difference exceeds threshold
        if diff_pct < self.config.threshold:
            return None

        # Calculate signal strength based on EMA separation
        # Stronger signal when EMAs are further apart after crossover
        strength = min(diff_pct / (self.config.threshold * 5), 1.0)

        return Signal(
            coin=coin,
            signal_type=SignalType.MOMENTUM,
            direction=crossover_direction,  # type: ignore[arg-type]
            strength=strength,
            timestamp=candles[-1].timestamp,
            metadata={
                "fast_ema": current_fast,
                "slow_ema": current_slow,
                "ema_diff_pct": diff_pct * 100,
                "fast_period": self.config.fast_period,
                "slow_period": self.config.slow_period,
            },
        )

    def reset(self, coin: str | None = None) -> None:
        """
        Reset detector state.

        Args:
            coin: Reset state for specific coin, or all if None
        """
        if coin is None:
            self._last_crossover_direction.clear()
        else:
            self._last_crossover_direction.pop(coin, None)
