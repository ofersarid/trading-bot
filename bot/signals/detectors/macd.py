"""
MACD Signal Detector - Crossover detection using MACD indicator.

Generates LONG signals when MACD crosses above signal line,
and SHORT signals when MACD crosses below signal line.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bot.indicators.macd import macd_series

from ..base import Signal, SignalType

if TYPE_CHECKING:
    from bot.core.candle_aggregator import Candle


@dataclass
class MACDConfig:
    """Configuration for MACD signal detection."""

    fast: int = 12
    slow: int = 26
    signal: int = 9
    # DISABLED: MACD showing only 40% accuracy with all signals in weak band
    # Set extremely high threshold to effectively disable
    # TODO: Re-evaluate MACD with different parameters or remove entirely
    min_histogram: float = 100000.0


class MACDSignalDetector:
    """
    Detects trading signals based on MACD crossovers.

    Generates signals when MACD line crosses the signal line,
    indicating potential trend changes.
    """

    def __init__(self, config: MACDConfig | None = None) -> None:
        """
        Initialize the MACD detector.

        Args:
            config: Configuration for signal detection (uses defaults if None)
        """
        self.config = config or MACDConfig()
        self._last_crossover_direction: dict[str, str | None] = {}

    def detect(self, coin: str, candles: list["Candle"]) -> Signal | None:
        """
        Detect MACD crossover signal.

        Args:
            coin: Trading pair symbol
            candles: List of candles, most recent last

        Returns:
            Signal if crossover detected, None otherwise
        """
        min_candles = self.config.slow + self.config.signal + 1
        if len(candles) < min_candles:
            return None

        # Extract close prices
        prices = [c.close for c in candles]

        # Calculate MACD series to detect crossover
        macd_results = macd_series(
            prices,
            fast=self.config.fast,
            slow=self.config.slow,
            signal=self.config.signal,
        )

        if len(macd_results) < 2:
            return None

        current = macd_results[-1]
        previous = macd_results[-2]

        # Detect crossover
        was_bullish = previous.histogram > 0
        is_bullish = current.histogram > 0

        crossover_direction: str | None = None
        if not was_bullish and is_bullish:
            crossover_direction = "LONG"
        elif was_bullish and not is_bullish:
            crossover_direction = "SHORT"

        if crossover_direction is None:
            return None

        # Check if this is a new crossover
        if self._last_crossover_direction.get(coin) == crossover_direction:
            return None

        self._last_crossover_direction[coin] = crossover_direction

        # Check minimum histogram magnitude
        if abs(current.histogram) < self.config.min_histogram:
            return None

        # Calculate signal strength based on histogram magnitude
        # Normalize by price to make comparable across different price levels
        current_price = prices[-1]
        histogram_pct = abs(current.histogram) / current_price

        # Scale strength - typical MACD histogram is 0.1-1% of price
        strength = min(histogram_pct * 100, 1.0)

        return Signal(
            coin=coin,
            signal_type=SignalType.MACD,
            direction=crossover_direction,  # type: ignore[arg-type]
            strength=strength,
            timestamp=candles[-1].timestamp,
            metadata={
                "macd_line": current.macd_line,
                "signal_line": current.signal_line,
                "histogram": current.histogram,
                "histogram_pct": histogram_pct * 100,
                "fast": self.config.fast,
                "slow": self.config.slow,
                "signal": self.config.signal,
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
