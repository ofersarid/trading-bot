"""
Previous Day Volume Profile Signal Detector.

Detects trading signals based on previous day's Volume Profile levels.

Key Concept:
Previous day's VP levels (POC, VAH, VAL) act as support/resistance
for the current trading day. These levels are "memory" of where
significant trading activity occurred.

Signals:
1. Opening Drive - Market opens outside VA and continues
2. VA Rejection - Price tests VA edge and reverses
3. POC Magnet - Price approaching POC (potential reversal zone)
4. VA Reclaim - Price re-enters VA after being outside

This is a Layer 2 detector in the 3-layer architecture.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..base import Signal, SignalType

if TYPE_CHECKING:
    from bot.backtest.models import PrevDayVPLevels
    from bot.core.candle_aggregator import Candle


@dataclass
class PrevDayVPConfig:
    """Configuration for Previous Day VP signal detection."""

    # Buffer zone around levels (as % of price)
    level_buffer_pct: float = 0.001

    # Candles required to confirm a setup
    confirmation_candles: int = 2

    # Minimum signal strength threshold
    min_strength: float = 0.5

    # Cooldown candles between signals
    cooldown_candles: int = 10

    # Distance from POC to trigger magnet signal (as % of VA range)
    poc_magnet_distance_pct: float = 0.3


class PrevDayVPSignalDetector:
    """
    Detects trading signals from previous day's Volume Profile levels.

    This detector uses pre-calculated VP levels (POC, VAH, VAL) from
    the previous trading session to identify key levels for the current day.

    Signal Types:
    - opening_drive_bullish: Open above VAH, continuation higher
    - opening_drive_bearish: Open below VAL, continuation lower
    - vah_rejection: Price rejects from VAH (bearish)
    - val_rejection: Price rejects from VAL (bullish)
    - poc_test_bullish: Price testing POC from above, bouncing
    - poc_test_bearish: Price testing POC from below, rejecting
    - va_reclaim_bullish: Re-entering VA from below (bullish)
    - va_reclaim_bearish: Re-entering VA from above (bearish)
    """

    def __init__(self, config: PrevDayVPConfig | None = None):
        """
        Initialize the detector.

        Args:
            config: Configuration for signal detection
        """
        self.config = config or PrevDayVPConfig()
        self._prev_day_vp: "PrevDayVPLevels | None" = None
        self._last_signal_candle: dict[str, int] = {}
        self._candle_count: dict[str, int] = {}
        self._session_open_price: dict[str, float] = {}
        self._session_started: dict[str, bool] = {}

    def set_prev_day_levels(self, levels: "PrevDayVPLevels") -> None:
        """
        Set the previous day's VP levels.

        Must be called before detection with the pre-calculated levels.

        Args:
            levels: Previous day's POC, VAH, VAL levels
        """
        self._prev_day_vp = levels

    def detect(self, coin: str, candles: list["Candle"]) -> Signal | None:
        """
        Detect trading signal based on previous day's VP levels.

        Args:
            coin: Trading pair symbol
            candles: List of candles, most recent last

        Returns:
            Signal if pattern detected, None otherwise
        """
        if self._prev_day_vp is None:
            return None

        if len(candles) < self.config.confirmation_candles + 1:
            return None

        # Track candle count for cooldown
        self._candle_count[coin] = self._candle_count.get(coin, 0) + 1

        # Record session open price (first candle)
        if not self._session_started.get(coin, False):
            self._session_open_price[coin] = candles[0].open
            self._session_started[coin] = True

        # Check cooldown
        last_signal = self._last_signal_candle.get(coin, 0)
        if self._candle_count[coin] - last_signal < self.config.cooldown_candles:
            return None

        current = candles[-1]
        poc = self._prev_day_vp.poc
        vah = self._prev_day_vp.vah
        val = self._prev_day_vp.val
        va_range = vah - val if vah > val else 1

        # Calculate buffer
        buffer = current.close * self.config.level_buffer_pct

        # Check signals in priority order
        signal = None

        # 1. Opening Drive (only check in first 15 candles)
        if self._candle_count[coin] <= 15:
            signal = self._check_opening_drive(coin, candles, vah, val, buffer)
            if signal:
                return self._record_signal(coin, signal)

        # 2. VAH Rejection (bearish)
        signal = self._check_vah_rejection(coin, candles, vah, poc, val, buffer, va_range)
        if signal:
            return self._record_signal(coin, signal)

        # 3. VAL Rejection (bullish)
        signal = self._check_val_rejection(coin, candles, vah, poc, val, buffer, va_range)
        if signal:
            return self._record_signal(coin, signal)

        # 4. POC Test
        signal = self._check_poc_test(coin, candles, poc, vah, val, buffer, va_range)
        if signal:
            return self._record_signal(coin, signal)

        # 5. VA Reclaim
        signal = self._check_va_reclaim(coin, candles, vah, val, poc, buffer, va_range)
        if signal:
            return self._record_signal(coin, signal)

        return None

    def _record_signal(self, coin: str, signal: Signal) -> Signal:
        """Record signal and return it."""
        self._last_signal_candle[coin] = self._candle_count.get(coin, 0)
        return signal

    def _check_opening_drive(
        self,
        coin: str,
        candles: list["Candle"],
        vah: float,
        val: float,
        buffer: float,
    ) -> Signal | None:
        """
        Check for opening drive signal.

        Pattern: Session opens outside previous day's VA and continues in that direction.
        - Open above VAH + continuation = bullish
        - Open below VAL + continuation = bearish
        """
        open_price = self._session_open_price.get(coin)
        if open_price is None:
            return None

        current = candles[-1]
        recent = candles[-self.config.confirmation_candles :]

        # Bullish Opening Drive: Open above VAH, staying above
        if open_price > vah + buffer:
            all_above_vah = all(c.low > vah for c in recent)
            trending_up = recent[-1].close > recent[0].open

            if all_above_vah and trending_up:
                strength = min((current.close - vah) / (vah * 0.01) * 0.2 + 0.6, 1.0)
                if strength >= self.config.min_strength:
                    return Signal(
                        coin=coin,
                        signal_type=SignalType.VOLUME_PROFILE,
                        direction="LONG",
                        strength=strength,
                        timestamp=current.timestamp,
                        metadata={
                            "setup": "opening_drive_bullish",
                            "prev_day_vah": vah,
                            "prev_day_val": val,
                            "session_open": open_price,
                            "close_price": current.close,
                        },
                    )

        # Bearish Opening Drive: Open below VAL, staying below
        if open_price < val - buffer:
            all_below_val = all(c.high < val for c in recent)
            trending_down = recent[-1].close < recent[0].open

            if all_below_val and trending_down:
                strength = min((val - current.close) / (val * 0.01) * 0.2 + 0.6, 1.0)
                if strength >= self.config.min_strength:
                    return Signal(
                        coin=coin,
                        signal_type=SignalType.VOLUME_PROFILE,
                        direction="SHORT",
                        strength=strength,
                        timestamp=current.timestamp,
                        metadata={
                            "setup": "opening_drive_bearish",
                            "prev_day_vah": vah,
                            "prev_day_val": val,
                            "session_open": open_price,
                            "close_price": current.close,
                        },
                    )

        return None

    def _check_vah_rejection(
        self,
        coin: str,
        candles: list["Candle"],
        vah: float,
        poc: float,
        val: float,
        buffer: float,
        va_range: float,
    ) -> Signal | None:
        """
        Check for rejection from previous day's VAH.

        Pattern: Price approaches VAH from below, shows rejection.
        VAH acts as resistance - bearish signal.
        """
        lookback = min(5, len(candles))
        recent = candles[-lookback:]
        current = candles[-1]

        # Price approached VAH (touched or exceeded)
        touched_vah = any(c.high >= vah - buffer for c in recent[:-1])

        # Current candle closes below VAH with bearish characteristics
        closed_below = current.close < vah - buffer
        bearish_candle = current.close < current.open  # Red candle

        if touched_vah and closed_below and bearish_candle:
            # Strength based on rejection quality
            highest = max(c.high for c in recent)
            rejection_distance = highest - current.close

            strength = min(rejection_distance / va_range * 2, 0.85)

            if strength >= self.config.min_strength:
                return Signal(
                    coin=coin,
                    signal_type=SignalType.VOLUME_PROFILE,
                    direction="SHORT",
                    strength=strength,
                    timestamp=current.timestamp,
                    metadata={
                        "setup": "vah_rejection",
                        "prev_day_vah": vah,
                        "prev_day_poc": poc,
                        "prev_day_val": val,
                        "rejection_from": highest,
                        "close_price": current.close,
                        "target": poc,  # First target is POC
                    },
                )

        return None

    def _check_val_rejection(
        self,
        coin: str,
        candles: list["Candle"],
        vah: float,
        poc: float,
        val: float,
        buffer: float,
        va_range: float,
    ) -> Signal | None:
        """
        Check for rejection from previous day's VAL.

        Pattern: Price approaches VAL from above, shows rejection.
        VAL acts as support - bullish signal.
        """
        lookback = min(5, len(candles))
        recent = candles[-lookback:]
        current = candles[-1]

        # Price approached VAL (touched or exceeded)
        touched_val = any(c.low <= val + buffer for c in recent[:-1])

        # Current candle closes above VAL with bullish characteristics
        closed_above = current.close > val + buffer
        bullish_candle = current.close > current.open  # Green candle

        if touched_val and closed_above and bullish_candle:
            # Strength based on rejection quality
            lowest = min(c.low for c in recent)
            rejection_distance = current.close - lowest

            strength = min(rejection_distance / va_range * 2, 0.85)

            if strength >= self.config.min_strength:
                return Signal(
                    coin=coin,
                    signal_type=SignalType.VOLUME_PROFILE,
                    direction="LONG",
                    strength=strength,
                    timestamp=current.timestamp,
                    metadata={
                        "setup": "val_rejection",
                        "prev_day_vah": vah,
                        "prev_day_poc": poc,
                        "prev_day_val": val,
                        "rejection_from": lowest,
                        "close_price": current.close,
                        "target": poc,  # First target is POC
                    },
                )

        return None

    def _check_poc_test(
        self,
        coin: str,
        candles: list["Candle"],
        poc: float,
        vah: float,
        val: float,
        buffer: float,
        va_range: float,
    ) -> Signal | None:
        """
        Check for POC test and reaction.

        Pattern: Price tests previous day's POC and shows reversal.
        POC is the "fair value" level and often acts as a magnet.
        """
        if len(candles) < 3:
            return None

        current = candles[-1]
        prev = candles[-2]

        # Check if price touched POC
        poc_buffer = buffer * 2  # Slightly wider buffer for POC
        touched_poc = (
            min(prev.low, current.low) <= poc + poc_buffer
            and max(prev.high, current.high) >= poc - poc_buffer
        )

        if not touched_poc:
            return None

        # Bullish: Price came from below, touched POC, bouncing up
        came_from_below = prev.close < poc
        bouncing_up = current.close > poc and current.close > prev.close

        if came_from_below and bouncing_up:
            strength = min(abs(current.close - poc) / va_range * 3, 0.75)
            if strength >= self.config.min_strength:
                return Signal(
                    coin=coin,
                    signal_type=SignalType.VOLUME_PROFILE,
                    direction="LONG",
                    strength=strength,
                    timestamp=current.timestamp,
                    metadata={
                        "setup": "poc_test_bullish",
                        "prev_day_poc": poc,
                        "prev_day_vah": vah,
                        "prev_day_val": val,
                        "close_price": current.close,
                        "target": vah,  # Target is VAH
                    },
                )

        # Bearish: Price came from above, touched POC, rejecting down
        came_from_above = prev.close > poc
        rejecting_down = current.close < poc and current.close < prev.close

        if came_from_above and rejecting_down:
            strength = min(abs(poc - current.close) / va_range * 3, 0.75)
            if strength >= self.config.min_strength:
                return Signal(
                    coin=coin,
                    signal_type=SignalType.VOLUME_PROFILE,
                    direction="SHORT",
                    strength=strength,
                    timestamp=current.timestamp,
                    metadata={
                        "setup": "poc_test_bearish",
                        "prev_day_poc": poc,
                        "prev_day_vah": vah,
                        "prev_day_val": val,
                        "close_price": current.close,
                        "target": val,  # Target is VAL
                    },
                )

        return None

    def _check_va_reclaim(
        self,
        coin: str,
        candles: list["Candle"],
        vah: float,
        val: float,
        poc: float,
        buffer: float,
        va_range: float,
    ) -> Signal | None:
        """
        Check for Value Area reclaim.

        Pattern: Price was outside VA, then re-enters.
        Re-entering VA suggests returning to "fair value" range.
        """
        if len(candles) < self.config.confirmation_candles + 2:
            return None

        current = candles[-1]
        prev_candles = candles[-(self.config.confirmation_candles + 2) : -1]

        # Bullish: Was below VAL, now re-entering VA
        was_below = all(c.close < val - buffer for c in prev_candles)
        now_inside = current.close > val + buffer and current.close < vah - buffer

        if was_below and now_inside:
            strength = min((current.close - val) / va_range * 2, 0.7)
            if strength >= self.config.min_strength:
                return Signal(
                    coin=coin,
                    signal_type=SignalType.VOLUME_PROFILE,
                    direction="LONG",
                    strength=strength,
                    timestamp=current.timestamp,
                    metadata={
                        "setup": "va_reclaim_bullish",
                        "prev_day_vah": vah,
                        "prev_day_val": val,
                        "prev_day_poc": poc,
                        "close_price": current.close,
                        "target": poc,  # Target is POC
                    },
                )

        # Bearish: Was above VAH, now re-entering VA
        was_above = all(c.close > vah + buffer for c in prev_candles)
        now_inside_bear = current.close < vah - buffer and current.close > val + buffer

        if was_above and now_inside_bear:
            strength = min((vah - current.close) / va_range * 2, 0.7)
            if strength >= self.config.min_strength:
                return Signal(
                    coin=coin,
                    signal_type=SignalType.VOLUME_PROFILE,
                    direction="SHORT",
                    strength=strength,
                    timestamp=current.timestamp,
                    metadata={
                        "setup": "va_reclaim_bearish",
                        "prev_day_vah": vah,
                        "prev_day_val": val,
                        "prev_day_poc": poc,
                        "close_price": current.close,
                        "target": poc,  # Target is POC
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
            self._session_open_price.clear()
            self._session_started.clear()
        else:
            self._last_signal_candle.pop(coin, None)
            self._candle_count.pop(coin, None)
            self._session_open_price.pop(coin, None)
            self._session_started.pop(coin, None)
