"""
Signal Aggregator - Batches and manages signals from multiple detectors.

Collects signals from various detectors and provides methods to
retrieve signals within time windows for AI evaluation.
"""

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from .base import Signal, SignalDetector, SignalType

if TYPE_CHECKING:
    from bot.core.candle_aggregator import Candle


@dataclass
class AggregatorConfig:
    """Configuration for signal aggregation."""

    max_signals: int = 1000  # Maximum signals to keep in history
    signal_ttl_seconds: int = 300  # Time-to-live for signals (5 minutes)


class SignalAggregator:
    """
    Aggregates signals from multiple detectors.

    Maintains a history of signals and provides methods to retrieve
    signals within specific time windows or by type.
    """

    def __init__(
        self,
        detectors: list[SignalDetector],
        config: AggregatorConfig | None = None,
    ) -> None:
        """
        Initialize the signal aggregator.

        Args:
            detectors: List of signal detectors to use
            config: Configuration for aggregation (uses defaults if None)
        """
        self.detectors = detectors
        self.config = config or AggregatorConfig()
        self._signals: deque[Signal] = deque(maxlen=self.config.max_signals)
        self._pending_signals: list[Signal] = []

    def process_candle(self, coin: str, candles: list["Candle"]) -> list[Signal]:
        """
        Process a new candle through all detectors.

        Args:
            coin: Trading pair symbol
            candles: List of candles including the new one, most recent last

        Returns:
            List of signals generated from this candle
        """
        new_signals: list[Signal] = []

        for detector in self.detectors:
            signal = detector.detect(coin, candles)
            if signal is not None:
                self._signals.append(signal)
                self._pending_signals.append(signal)
                new_signals.append(signal)

        return new_signals

    def get_pending_signals(self, time_window_seconds: int = 60) -> list[Signal]:
        """
        Get signals within a time window that haven't been processed.

        This method returns signals and clears them from the pending list.
        Use this to batch signals before sending to AI for evaluation.

        Args:
            time_window_seconds: Only include signals from this many seconds ago

        Returns:
            List of pending signals within the time window
        """
        if not self._pending_signals:
            return []

        cutoff = datetime.now() - timedelta(seconds=time_window_seconds)
        valid_signals = [s for s in self._pending_signals if s.timestamp >= cutoff]

        # Clear pending signals
        self._pending_signals.clear()

        return valid_signals

    def get_recent_signals(
        self,
        time_window_seconds: int = 60,
        coin: str | None = None,
        signal_type: SignalType | None = None,
    ) -> list[Signal]:
        """
        Get signals within a time window (doesn't clear them).

        Args:
            time_window_seconds: Only include signals from this many seconds ago
            coin: Filter by coin (optional)
            signal_type: Filter by signal type (optional)

        Returns:
            List of signals matching the criteria
        """
        cutoff = datetime.now() - timedelta(seconds=time_window_seconds)

        signals = [s for s in self._signals if s.timestamp >= cutoff]

        if coin is not None:
            signals = [s for s in signals if s.coin == coin]

        if signal_type is not None:
            signals = [s for s in signals if s.signal_type == signal_type]

        return signals

    def get_signal_count(
        self,
        time_window_seconds: int = 60,
        coin: str | None = None,
    ) -> dict[SignalType, int]:
        """
        Get count of signals by type within a time window.

        Args:
            time_window_seconds: Only count signals from this many seconds ago
            coin: Filter by coin (optional)

        Returns:
            Dictionary mapping signal type to count
        """
        signals = self.get_recent_signals(time_window_seconds, coin)

        counts: dict[SignalType, int] = {}
        for signal in signals:
            counts[signal.signal_type] = counts.get(signal.signal_type, 0) + 1

        return counts

    def has_conflicting_signals(
        self,
        coin: str,
        time_window_seconds: int = 60,
    ) -> bool:
        """
        Check if there are conflicting signals (LONG and SHORT) for a coin.

        Args:
            coin: Trading pair symbol
            time_window_seconds: Time window to check

        Returns:
            True if both LONG and SHORT signals exist
        """
        signals = self.get_recent_signals(time_window_seconds, coin)

        has_long = any(s.direction == "LONG" for s in signals)
        has_short = any(s.direction == "SHORT" for s in signals)

        return has_long and has_short

    def _apply_timing_weight(self, signal: Signal, current_time: datetime) -> float:
        """
        Apply timing-based weight to signal strength.

        Earlier signals get higher weight because they're predictive rather than
        confirmatory. Very fresh signals often just confirm moves already in progress.

        Args:
            signal: The signal to weight
            current_time: Current time for age calculation

        Returns:
            Timing-weighted strength value
        """
        age_seconds = (current_time - signal.timestamp).total_seconds()

        # Peak weight at 30-60 seconds old (gave advance warning)
        # Decay for very fresh signals (confirming, not predicting)
        # Decay for very old signals (stale)
        if age_seconds < 15:
            # Very fresh = likely confirmatory, reduce weight
            timing_factor = 0.5 + (age_seconds / 30)  # 0.5 -> 1.0
        elif age_seconds < 90:
            # Sweet spot - predictive signals
            timing_factor = 1.0
        else:
            # Decay for older signals
            timing_factor = max(0.3, 1.0 - (age_seconds - 90) / 180)

        return signal.strength * timing_factor

    def get_consensus_direction(
        self,
        coin: str,
        time_window_seconds: int = 60,
    ) -> str | None:
        """
        Get the consensus direction from multiple signals.

        Returns the direction with the highest total timing-weighted strength.
        Earlier signals are weighted higher as they're more predictive.

        Args:
            coin: Trading pair symbol
            time_window_seconds: Time window to check

        Returns:
            "LONG", "SHORT", or None if no clear consensus
        """
        signals = self.get_recent_signals(time_window_seconds, coin)

        if not signals:
            return None

        current_time = datetime.now()
        long_strength = sum(
            self._apply_timing_weight(s, current_time) for s in signals if s.direction == "LONG"
        )
        short_strength = sum(
            self._apply_timing_weight(s, current_time) for s in signals if s.direction == "SHORT"
        )

        if long_strength > short_strength:
            return "LONG"
        elif short_strength > long_strength:
            return "SHORT"
        else:
            return None

    def get_weighted_signals(
        self,
        time_window_seconds: int = 60,
        coin: str | None = None,
    ) -> list[tuple[Signal, float]]:
        """
        Get signals with their timing-weighted strengths.

        Args:
            time_window_seconds: Only include signals from this many seconds ago
            coin: Filter by coin (optional)

        Returns:
            List of (signal, weighted_strength) tuples
        """
        signals = self.get_recent_signals(time_window_seconds, coin)
        current_time = datetime.now()

        return [(signal, self._apply_timing_weight(signal, current_time)) for signal in signals]

    def clear_old_signals(self) -> int:
        """
        Remove signals older than TTL.

        Returns:
            Number of signals removed
        """
        cutoff = datetime.now() - timedelta(seconds=self.config.signal_ttl_seconds)
        initial_count = len(self._signals)

        # Filter to keep only recent signals
        self._signals = deque(
            (s for s in self._signals if s.timestamp >= cutoff),
            maxlen=self.config.max_signals,
        )

        return initial_count - len(self._signals)

    def reset(self, coin: str | None = None) -> None:
        """
        Reset aggregator state.

        Args:
            coin: Reset signals for specific coin, or all if None
        """
        if coin is None:
            self._signals.clear()
            self._pending_signals.clear()
            for detector in self.detectors:
                if hasattr(detector, "reset"):
                    detector.reset()
        else:
            self._signals = deque(
                (s for s in self._signals if s.coin != coin),
                maxlen=self.config.max_signals,
            )
            self._pending_signals = [s for s in self._pending_signals if s.coin != coin]
            for detector in self.detectors:
                if hasattr(detector, "reset"):
                    detector.reset(coin)

    @property
    def total_signals(self) -> int:
        """Total number of signals in history."""
        return len(self._signals)

    @property
    def pending_count(self) -> int:
        """Number of pending signals."""
        return len(self._pending_signals)
