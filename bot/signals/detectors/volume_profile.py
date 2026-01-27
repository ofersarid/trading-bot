"""
Volume Profile Signal Detector.

Detects trading signals based on Volume Profile analysis.

Signals:
1. Failed Auction - price rejects from Value Area edge
2. Value Area Breakout - price establishes outside Value Area
3. POC Test - price tests Point of Control
4. Delta Divergence - price vs delta disagreement

This is a Layer 2 detector in the 3-layer architecture.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bot.indicators.volume_profile import (
    VolumeProfile,
    get_poc,
    get_total_delta,
    get_value_area,
)

from ..base import Signal, SignalType

if TYPE_CHECKING:
    from bot.core.candle_aggregator import Candle


@dataclass
class VolumeProfileConfig:
    """Configuration for Volume Profile signal detection."""

    # Value Area buffer (as % of price) - prevents triggering on noise
    va_buffer_pct: float = 0.001

    # Candles required outside VA to confirm breakout
    breakout_candles: int = 3

    # Minimum candles to look back for rejection detection
    rejection_lookback: int = 5

    # Delta imbalance threshold (as % of total volume)
    delta_threshold_pct: float = 30.0

    # Minimum signal strength threshold
    min_strength: float = 0.4

    # Cooldown candles between signals
    cooldown_candles: int = 5


class VolumeProfileSignalDetector:
    """
    Detects trading signals from Volume Profile analysis.

    This detector requires an external Volume Profile to be provided
    via update_profile() before detection can work.

    Signal Types:
    - failed_auction_low: Price rejected from below VA (bullish)
    - failed_auction_high: Price rejected from above VA (bearish)
    - va_breakout_up: Price breaking out above VA (bullish)
    - va_breakout_down: Price breaking out below VA (bearish)
    - poc_bounce: Price bouncing from POC
    - delta_divergence_bullish: Price down but delta positive
    - delta_divergence_bearish: Price up but delta negative
    """

    def __init__(self, config: VolumeProfileConfig | None = None):
        """
        Initialize the detector.

        Args:
            config: Configuration for signal detection
        """
        self.config = config or VolumeProfileConfig()
        self._profile: VolumeProfile | None = None
        self._last_signal_candle: dict[str, int] = {}  # coin -> candle count
        self._candle_count: dict[str, int] = {}  # coin -> total candles seen

    def update_profile(self, profile: VolumeProfile) -> None:
        """
        Update the current volume profile.

        Must be called with fresh profile data before detection.

        Args:
            profile: VolumeProfile to use for detection
        """
        self._profile = profile

    def detect(self, coin: str, candles: list["Candle"]) -> Signal | None:
        """
        Detect VP-based trading signal.

        Args:
            coin: Trading pair symbol
            candles: List of candles, most recent last

        Returns:
            Signal if pattern detected, None otherwise
        """
        if self._profile is None:
            return None

        if len(candles) < self.config.rejection_lookback:
            return None

        # Track candle count for cooldown
        self._candle_count[coin] = self._candle_count.get(coin, 0) + 1

        # Check cooldown
        last_signal = self._last_signal_candle.get(coin, 0)
        if self._candle_count[coin] - last_signal < self.config.cooldown_candles:
            return None

        # Get Value Area and POC
        va = get_value_area(self._profile)
        poc = get_poc(self._profile)

        if va is None or poc is None:
            return None

        va_low, va_high = va
        current_candle = candles[-1]
        current_price = current_candle.close

        # Calculate buffer
        buffer = current_price * self.config.va_buffer_pct

        # Check for signals in priority order
        signal = None

        # 1. Failed Auction at VA Low (bullish)
        signal = self._check_failed_auction_low(coin, candles, va_low, va_high, poc, buffer)
        if signal:
            return self._record_signal(coin, signal)

        # 2. Failed Auction at VA High (bearish)
        signal = self._check_failed_auction_high(coin, candles, va_low, va_high, poc, buffer)
        if signal:
            return self._record_signal(coin, signal)

        # 3. Value Area Breakout Up (bullish)
        signal = self._check_va_breakout_up(coin, candles, va_low, va_high, poc, buffer)
        if signal:
            return self._record_signal(coin, signal)

        # 4. Value Area Breakout Down (bearish)
        signal = self._check_va_breakout_down(coin, candles, va_low, va_high, poc, buffer)
        if signal:
            return self._record_signal(coin, signal)

        # 5. POC Bounce
        signal = self._check_poc_bounce(coin, candles, poc, buffer)
        if signal:
            return self._record_signal(coin, signal)

        # 6. Delta Divergence
        signal = self._check_delta_divergence(coin, candles, current_price)
        if signal:
            return self._record_signal(coin, signal)

        return None

    def _record_signal(self, coin: str, signal: Signal) -> Signal:
        """Record signal and return it."""
        self._last_signal_candle[coin] = self._candle_count.get(coin, 0)
        return signal

    def _check_failed_auction_low(
        self,
        coin: str,
        candles: list["Candle"],
        va_low: float,
        va_high: float,
        poc: float,
        buffer: float,
    ) -> Signal | None:
        """
        Check for failed auction at VA low.

        Pattern: Price goes below VA low, then closes back inside.
        This indicates rejection of lower prices - bullish.
        """
        lookback = min(self.config.rejection_lookback, len(candles))
        recent = candles[-lookback:]

        # Check if any candle went below VA low
        went_below = any(c.low < va_low - buffer for c in recent[:-1])

        # Current candle should close inside VA
        current = candles[-1]
        closed_inside = current.close > va_low + buffer

        if went_below and closed_inside:
            # Calculate strength based on rejection quality
            lowest_point = min(c.low for c in recent)
            rejection_distance = current.close - lowest_point
            va_range = va_high - va_low if va_high > va_low else 1

            strength = min(rejection_distance / va_range, 1.0)

            if strength >= self.config.min_strength:
                return Signal(
                    coin=coin,
                    signal_type=SignalType.VOLUME_PROFILE,
                    direction="LONG",
                    strength=strength,
                    timestamp=current.timestamp,
                    metadata={
                        "setup": "failed_auction_low",
                        "va_low": va_low,
                        "va_high": va_high,
                        "poc": poc,
                        "rejection_from": lowest_point,
                        "close_price": current.close,
                    },
                )

        return None

    def _check_failed_auction_high(
        self,
        coin: str,
        candles: list["Candle"],
        va_low: float,
        va_high: float,
        poc: float,
        buffer: float,
    ) -> Signal | None:
        """
        Check for failed auction at VA high.

        Pattern: Price goes above VA high, then closes back inside.
        This indicates rejection of higher prices - bearish.
        """
        lookback = min(self.config.rejection_lookback, len(candles))
        recent = candles[-lookback:]

        # Check if any candle went above VA high
        went_above = any(c.high > va_high + buffer for c in recent[:-1])

        # Current candle should close inside VA
        current = candles[-1]
        closed_inside = current.close < va_high - buffer

        if went_above and closed_inside:
            # Calculate strength based on rejection quality
            highest_point = max(c.high for c in recent)
            rejection_distance = highest_point - current.close
            va_range = va_high - va_low if va_high > va_low else 1

            strength = min(rejection_distance / va_range, 1.0)

            if strength >= self.config.min_strength:
                return Signal(
                    coin=coin,
                    signal_type=SignalType.VOLUME_PROFILE,
                    direction="SHORT",
                    strength=strength,
                    timestamp=current.timestamp,
                    metadata={
                        "setup": "failed_auction_high",
                        "va_low": va_low,
                        "va_high": va_high,
                        "poc": poc,
                        "rejection_from": highest_point,
                        "close_price": current.close,
                    },
                )

        return None

    def _check_va_breakout_up(
        self,
        coin: str,
        candles: list["Candle"],
        va_low: float,
        va_high: float,
        poc: float,
        buffer: float,
    ) -> Signal | None:
        """
        Check for Value Area breakout to the upside.

        Pattern: Multiple candles closing above VA high.
        Indicates acceptance of higher prices - bullish continuation.
        """
        if len(candles) < self.config.breakout_candles:
            return None

        recent = candles[-self.config.breakout_candles :]

        # All recent candles should close above VA high
        all_above = all(c.close > va_high + buffer for c in recent)

        if all_above:
            current = candles[-1]
            breakout_distance = current.close - va_high
            va_range = va_high - va_low if va_high > va_low else 1

            strength = min(breakout_distance / va_range * 0.5 + 0.5, 1.0)

            if strength >= self.config.min_strength:
                return Signal(
                    coin=coin,
                    signal_type=SignalType.VOLUME_PROFILE,
                    direction="LONG",
                    strength=strength,
                    timestamp=current.timestamp,
                    metadata={
                        "setup": "va_breakout_up",
                        "va_low": va_low,
                        "va_high": va_high,
                        "poc": poc,
                        "breakout_candles": self.config.breakout_candles,
                        "close_price": current.close,
                    },
                )

        return None

    def _check_va_breakout_down(
        self,
        coin: str,
        candles: list["Candle"],
        va_low: float,
        va_high: float,
        poc: float,
        buffer: float,
    ) -> Signal | None:
        """
        Check for Value Area breakout to the downside.

        Pattern: Multiple candles closing below VA low.
        Indicates acceptance of lower prices - bearish continuation.
        """
        if len(candles) < self.config.breakout_candles:
            return None

        recent = candles[-self.config.breakout_candles :]

        # All recent candles should close below VA low
        all_below = all(c.close < va_low - buffer for c in recent)

        if all_below:
            current = candles[-1]
            breakout_distance = va_low - current.close
            va_range = va_high - va_low if va_high > va_low else 1

            strength = min(breakout_distance / va_range * 0.5 + 0.5, 1.0)

            if strength >= self.config.min_strength:
                return Signal(
                    coin=coin,
                    signal_type=SignalType.VOLUME_PROFILE,
                    direction="SHORT",
                    strength=strength,
                    timestamp=current.timestamp,
                    metadata={
                        "setup": "va_breakout_down",
                        "va_low": va_low,
                        "va_high": va_high,
                        "poc": poc,
                        "breakout_candles": self.config.breakout_candles,
                        "close_price": current.close,
                    },
                )

        return None

    def _check_poc_bounce(
        self,
        coin: str,
        candles: list["Candle"],
        poc: float,
        buffer: float,
    ) -> Signal | None:
        """
        Check for bounce from Point of Control.

        Pattern: Price touches POC level and reverses.
        POC often acts as a magnet/support level.
        """
        if len(candles) < 3:
            return None

        current = candles[-1]
        prev = candles[-2]

        # Price touched POC (wick or body)
        touched_poc = (
            min(prev.low, current.low) <= poc + buffer
            and max(prev.high, current.high) >= poc - buffer
        )

        if not touched_poc:
            return None

        # Determine bounce direction
        if current.close > poc and current.close > prev.close:
            # Bullish bounce from POC
            strength = min(abs(current.close - poc) / (buffer * 10), 0.7)
            if strength >= self.config.min_strength:
                return Signal(
                    coin=coin,
                    signal_type=SignalType.VOLUME_PROFILE,
                    direction="LONG",
                    strength=strength,
                    timestamp=current.timestamp,
                    metadata={
                        "setup": "poc_bounce",
                        "poc": poc,
                        "bounce_direction": "up",
                        "close_price": current.close,
                    },
                )

        elif current.close < poc and current.close < prev.close:
            # Bearish rejection from POC
            strength = min(abs(poc - current.close) / (buffer * 10), 0.7)
            if strength >= self.config.min_strength:
                return Signal(
                    coin=coin,
                    signal_type=SignalType.VOLUME_PROFILE,
                    direction="SHORT",
                    strength=strength,
                    timestamp=current.timestamp,
                    metadata={
                        "setup": "poc_bounce",
                        "poc": poc,
                        "bounce_direction": "down",
                        "close_price": current.close,
                    },
                )

        return None

    def _check_delta_divergence(
        self,
        coin: str,
        candles: list["Candle"],
        current_price: float,
    ) -> Signal | None:
        """
        Check for delta divergence.

        Pattern: Price moves one direction but delta shows opposite pressure.
        This can indicate exhaustion/reversal.
        """
        if self._profile is None or len(candles) < 5:
            return None

        # Get recent price movement
        recent_candles = candles[-5:]
        price_change = recent_candles[-1].close - recent_candles[0].close
        price_change_pct = (price_change / recent_candles[0].close) * 100

        # Get total delta
        total_delta = get_total_delta(self._profile)
        total_volume = self._profile.total_volume

        if total_volume == 0:
            return None

        delta_pct = (total_delta / total_volume) * 100

        # Check for divergence
        current = candles[-1]

        # Price up but delta negative (bearish divergence)
        if price_change_pct > 0.1 and delta_pct < -self.config.delta_threshold_pct:
            strength = min(abs(delta_pct) / 100, 0.8)
            if strength >= self.config.min_strength:
                return Signal(
                    coin=coin,
                    signal_type=SignalType.VOLUME_PROFILE,
                    direction="SHORT",
                    strength=strength,
                    timestamp=current.timestamp,
                    metadata={
                        "setup": "delta_divergence_bearish",
                        "price_change_pct": price_change_pct,
                        "delta_pct": delta_pct,
                        "close_price": current_price,
                    },
                )

        # Price down but delta positive (bullish divergence)
        if price_change_pct < -0.1 and delta_pct > self.config.delta_threshold_pct:
            strength = min(abs(delta_pct) / 100, 0.8)
            if strength >= self.config.min_strength:
                return Signal(
                    coin=coin,
                    signal_type=SignalType.VOLUME_PROFILE,
                    direction="LONG",
                    strength=strength,
                    timestamp=current.timestamp,
                    metadata={
                        "setup": "delta_divergence_bullish",
                        "price_change_pct": price_change_pct,
                        "delta_pct": delta_pct,
                        "close_price": current_price,
                    },
                )

        return None

    def reset(self, coin: str | None = None) -> None:
        """
        Reset detector state.

        Args:
            coin: Reset state for specific coin, or all if None
        """
        if coin is None:
            self._last_signal_candle.clear()
            self._candle_count.clear()
        else:
            self._last_signal_candle.pop(coin, None)
            self._candle_count.pop(coin, None)
