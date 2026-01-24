"""
RSI Signal Detector - Overbought/Oversold and Divergence detection.

Generates signals based on:
1. RSI threshold crossings (oversold/overbought)
2. RSI/Price divergence (more reliable reversal signals)

Divergence signals are weighted higher as they catch reversals earlier.
"""

from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bot.indicators import rsi

from ..base import Signal, SignalType

if TYPE_CHECKING:
    from bot.core.candle_aggregator import Candle


@dataclass
class RSIConfig:
    """Configuration for RSI signal detection."""

    period: int = 14
    oversold: float = 30.0
    overbought: float = 70.0
    cooldown_candles: int = 5  # Minimum candles between signals
    # Divergence detection settings
    divergence_lookback: int = 20  # Candles to look back for divergence
    divergence_strength_boost: float = 0.3  # Extra strength for divergence signals


class RSISignalDetector:
    """
    Detects trading signals based on RSI extremes and divergences.

    Generates signals when:
    1. RSI enters oversold or overbought territory
    2. RSI/Price divergence is detected (more predictive)

    Divergence signals are weighted higher as they catch reversals earlier.
    """

    def __init__(self, config: RSIConfig | None = None) -> None:
        """
        Initialize the RSI detector.

        Args:
            config: Configuration for signal detection (uses defaults if None)
        """
        self.config = config or RSIConfig()
        self._candles_since_signal: dict[str, int] = {}
        self._last_signal_direction: dict[str, str | None] = {}
        # Track recent RSI values for divergence detection
        self._rsi_history: dict[str, deque[float]] = {}
        self._price_history: dict[str, deque[float]] = {}

    def _find_local_extremes(
        self,
        values: list[float],
        window: int = 3,
    ) -> tuple[list[tuple[int, float]], list[tuple[int, float]]]:
        """
        Find local highs and lows in a series.

        Args:
            values: List of values to analyze
            window: Number of points on each side to compare

        Returns:
            (highs, lows) where each is a list of (index, value) tuples
        """
        highs: list[tuple[int, float]] = []
        lows: list[tuple[int, float]] = []

        for i in range(window, len(values) - window):
            val = values[i]
            left = values[i - window : i]
            right = values[i + 1 : i + window + 1]

            # Check if local high
            if all(val > v for v in left) and all(val >= v for v in right):
                highs.append((i, val))

            # Check if local low
            if all(val < v for v in left) and all(val <= v for v in right):
                lows.append((i, val))

        return highs, lows

    def _detect_divergence(
        self,
        prices: list[float],
        rsi_values: list[float],
    ) -> tuple[str | None, float]:
        """
        Detect RSI/price divergence.

        Bullish divergence: Price makes lower low, RSI makes higher low
        Bearish divergence: Price makes higher high, RSI makes lower high

        Args:
            prices: Recent price values (aligned with RSI values)
            rsi_values: Recent RSI values

        Returns:
            (direction, strength) or (None, 0) if no divergence
        """
        if len(prices) < 10 or len(rsi_values) < 10:
            return None, 0.0

        # Align lengths
        min_len = min(len(prices), len(rsi_values))
        prices = prices[-min_len:]
        rsi_values = rsi_values[-min_len:]

        # Find local extremes
        price_highs, price_lows = self._find_local_extremes(prices)
        rsi_highs, rsi_lows = self._find_local_extremes(rsi_values)

        # Check for bullish divergence (price lower low, RSI higher low)
        if len(price_lows) >= 2 and len(rsi_lows) >= 2:
            # Get two most recent lows
            recent_price_lows = price_lows[-2:]
            recent_rsi_lows = rsi_lows[-2:]

            # Price made lower low
            price_lower_low = recent_price_lows[-1][1] < recent_price_lows[-2][1]
            # RSI made higher low
            rsi_higher_low = recent_rsi_lows[-1][1] > recent_rsi_lows[-2][1]

            if price_lower_low and rsi_higher_low:
                # Calculate divergence strength based on RSI difference
                rsi_diff = recent_rsi_lows[-1][1] - recent_rsi_lows[-2][1]
                strength = min(rsi_diff / 20, 1.0)  # Normalize
                return "LONG", strength

        # Check for bearish divergence (price higher high, RSI lower high)
        if len(price_highs) >= 2 and len(rsi_highs) >= 2:
            # Get two most recent highs
            recent_price_highs = price_highs[-2:]
            recent_rsi_highs = rsi_highs[-2:]

            # Price made higher high
            price_higher_high = recent_price_highs[-1][1] > recent_price_highs[-2][1]
            # RSI made lower high
            rsi_lower_high = recent_rsi_highs[-1][1] < recent_rsi_highs[-2][1]

            if price_higher_high and rsi_lower_high:
                # Calculate divergence strength based on RSI difference
                rsi_diff = recent_rsi_highs[-2][1] - recent_rsi_highs[-1][1]
                strength = min(rsi_diff / 20, 1.0)  # Normalize
                return "SHORT", strength

        return None, 0.0

    def detect(self, coin: str, candles: list["Candle"]) -> Signal | None:
        """
        Detect RSI signal from overbought/oversold conditions or divergence.

        Divergence signals are prioritized as they're more predictive.

        Args:
            coin: Trading pair symbol
            candles: List of candles, most recent last

        Returns:
            Signal if RSI extreme or divergence detected, None otherwise
        """
        min_candles = self.config.period + 1
        if len(candles) < min_candles:
            return None

        # Update cooldown counter
        if coin in self._candles_since_signal:
            self._candles_since_signal[coin] += 1

        # Extract close prices
        prices = [c.close for c in candles]

        # Calculate RSI
        rsi_value = rsi(prices, self.config.period)
        if rsi_value is None:
            return None

        # Update history for divergence detection
        if coin not in self._rsi_history:
            self._rsi_history[coin] = deque(maxlen=self.config.divergence_lookback)
            self._price_history[coin] = deque(maxlen=self.config.divergence_lookback)

        self._rsi_history[coin].append(rsi_value)
        self._price_history[coin].append(prices[-1])

        # Check for divergence first (higher priority signal)
        divergence_direction, divergence_strength = self._detect_divergence(
            list(self._price_history[coin]),
            list(self._rsi_history[coin]),
        )

        if divergence_direction is not None:
            # Check cooldown for divergence signals too
            candles_since = self._candles_since_signal.get(coin, self.config.cooldown_candles)
            # Check if different from last signal and cooldown passed
            if (
                candles_since >= self.config.cooldown_candles
                and self._last_signal_direction.get(coin) != divergence_direction
            ):
                self._candles_since_signal[coin] = 0
                self._last_signal_direction[coin] = divergence_direction

                # Boost strength for divergence signals
                strength = min(
                    divergence_strength + self.config.divergence_strength_boost,
                    1.0,
                )

                return Signal(
                    coin=coin,
                    signal_type=SignalType.RSI,
                    direction=divergence_direction,  # type: ignore[arg-type]
                    strength=strength,
                    timestamp=candles[-1].timestamp,
                    metadata={
                        "rsi": rsi_value,
                        "signal_source": "divergence",
                        "oversold_threshold": self.config.oversold,
                        "overbought_threshold": self.config.overbought,
                        "period": self.config.period,
                    },
                )

        # Fall back to threshold-based detection
        direction: str | None = None
        if rsi_value < self.config.oversold:
            direction = "LONG"
        elif rsi_value > self.config.overbought:
            direction = "SHORT"

        if direction is None:
            return None

        # Check cooldown
        candles_since = self._candles_since_signal.get(coin, self.config.cooldown_candles)
        if candles_since < self.config.cooldown_candles:
            return None

        # Check if same direction as last signal (avoid duplicates)
        if self._last_signal_direction.get(coin) == direction:
            # Only allow repeat signal if RSI crossed back through neutral first
            return None

        # Reset cooldown and update last direction
        self._candles_since_signal[coin] = 0
        self._last_signal_direction[coin] = direction

        # Calculate signal strength based on proximity to threshold (inverted)
        # RATIONALE: Early signals (RSI just entering oversold/overbought) are MORE
        # predictive than late signals (deeply oversold/overbought). Extreme RSI values
        # often indicate the move has already happened, reducing predictive value.
        if direction == "LONG":
            # Stronger signal when RSI just entered oversold (closer to threshold)
            # RSI=28 → high strength (early), RSI=10 → low strength (late)
            extremity = (self.config.oversold - rsi_value) / self.config.oversold
            strength = 1.0 - extremity
        else:
            # Stronger signal when RSI just entered overbought (closer to threshold)
            # RSI=72 → high strength (early), RSI=90 → low strength (late)
            extremity = (rsi_value - self.config.overbought) / (100 - self.config.overbought)
            strength = 1.0 - extremity

        strength = max(0.1, min(1.0, strength))  # Floor at 0.1 to avoid filtering

        return Signal(
            coin=coin,
            signal_type=SignalType.RSI,
            direction=direction,  # type: ignore[arg-type]
            strength=strength,
            timestamp=candles[-1].timestamp,
            metadata={
                "rsi": rsi_value,
                "signal_source": "threshold",
                "oversold_threshold": self.config.oversold,
                "overbought_threshold": self.config.overbought,
                "period": self.config.period,
            },
        )

    def reset(self, coin: str | None = None) -> None:
        """
        Reset detector state.

        Args:
            coin: Reset state for specific coin, or all if None
        """
        if coin is None:
            self._candles_since_signal.clear()
            self._last_signal_direction.clear()
            self._rsi_history.clear()
            self._price_history.clear()
        else:
            self._candles_since_signal.pop(coin, None)
            self._last_signal_direction.pop(coin, None)
            self._rsi_history.pop(coin, None)
            self._price_history.pop(coin, None)

    def update_neutral_cross(self, coin: str, candles: list["Candle"]) -> None:
        """
        Check if RSI has crossed back through neutral territory.

        Call this to allow repeat signals in the same direction
        after RSI has normalized.

        Args:
            coin: Trading pair symbol
            candles: List of candles, most recent last
        """
        if len(candles) < self.config.period + 1:
            return

        prices = [c.close for c in candles]
        rsi_value = rsi(prices, self.config.period)

        if rsi_value is None:
            return

        # If RSI is in neutral territory, clear last direction
        if self.config.oversold < rsi_value < self.config.overbought:
            self._last_signal_direction[coin] = None
