"""
Signal Validator - Filters signals based on historical accuracy.

Tracks which signal types/strengths predict correctly and filters out
signals with consistently poor predictive value.
"""

from dataclasses import dataclass

from .base import Signal, SignalType


@dataclass
class SignalAccuracy:
    """Track accuracy for a signal type."""

    signal_type: SignalType
    total_signals: int = 0
    correct_predictions: int = 0

    @property
    def accuracy(self) -> float:
        """
        Calculate accuracy rate.

        Returns 0.5 (neutral) if no history exists.
        """
        if self.total_signals == 0:
            return 0.5  # Unknown, assume neutral
        return self.correct_predictions / self.total_signals

    def record(self, was_correct: bool) -> None:
        """Record a signal outcome."""
        self.total_signals += 1
        if was_correct:
            self.correct_predictions += 1


@dataclass
class ValidatorConfig:
    """Configuration for signal validation."""

    min_accuracy: float = 0.4  # Minimum accuracy to pass validation
    min_samples: int = 10  # Minimum samples before filtering kicks in
    track_by_strength: bool = True  # Also track accuracy by strength bands


@dataclass
class StrengthBandAccuracy:
    """Track accuracy for signals in a specific strength band."""

    low: float
    high: float
    total_signals: int = 0
    correct_predictions: int = 0

    @property
    def accuracy(self) -> float:
        """Calculate accuracy rate for this strength band."""
        if self.total_signals == 0:
            return 0.5
        return self.correct_predictions / self.total_signals


class SignalValidator:
    """
    Validates signals based on historical accuracy.

    Tracks which signal types (and optionally strength bands) predict correctly
    and filters out consistently wrong signals.
    """

    def __init__(self, config: ValidatorConfig | None = None) -> None:
        """
        Initialize the validator.

        Args:
            config: Configuration for validation (uses defaults if None)
        """
        self.config = config or ValidatorConfig()
        self._accuracy: dict[SignalType, SignalAccuracy] = {}
        # Track by strength bands: (0-0.25), (0.25-0.5), (0.5-0.75), (0.75-1.0)
        self._strength_bands: dict[SignalType, list[StrengthBandAccuracy]] = {}

    def _get_or_create_accuracy(self, signal_type: SignalType) -> SignalAccuracy:
        """Get or create accuracy tracker for a signal type."""
        if signal_type not in self._accuracy:
            self._accuracy[signal_type] = SignalAccuracy(signal_type=signal_type)
        return self._accuracy[signal_type]

    def _get_strength_band_index(self, strength: float) -> int:
        """Get the index of the strength band for a given strength value."""
        if strength < 0.25:
            return 0
        elif strength < 0.5:
            return 1
        elif strength < 0.75:
            return 2
        else:
            return 3

    def _get_or_create_strength_bands(self, signal_type: SignalType) -> list[StrengthBandAccuracy]:
        """Get or create strength band trackers for a signal type."""
        if signal_type not in self._strength_bands:
            self._strength_bands[signal_type] = [
                StrengthBandAccuracy(low=0.0, high=0.25),
                StrengthBandAccuracy(low=0.25, high=0.5),
                StrengthBandAccuracy(low=0.5, high=0.75),
                StrengthBandAccuracy(low=0.75, high=1.0),
            ]
        return self._strength_bands[signal_type]

    def should_pass(self, signal: Signal) -> bool:
        """
        Check if signal type has acceptable accuracy.

        A signal passes if:
        1. We don't have enough samples yet (min_samples not reached)
        2. The signal type's accuracy is above the threshold
        3. (If tracking by strength) The strength band's accuracy is acceptable

        Args:
            signal: The signal to validate

        Returns:
            True if signal should be used, False if it should be filtered out
        """
        accuracy = self._accuracy.get(signal.signal_type)

        # No history yet, allow through
        if accuracy is None:
            return True

        # Not enough samples to judge, allow through
        if accuracy.total_signals < self.config.min_samples:
            return True

        # Check overall accuracy
        if accuracy.accuracy < self.config.min_accuracy:
            return False

        # Optionally check strength band accuracy
        if self.config.track_by_strength:
            bands = self._strength_bands.get(signal.signal_type)
            if bands:
                band_idx = self._get_strength_band_index(signal.strength)
                band = bands[band_idx]
                # Only filter if we have enough samples in this band
                if (
                    band.total_signals >= self.config.min_samples
                    and band.accuracy < self.config.min_accuracy
                ):
                    return False

        return True

    def record_outcome(
        self,
        signal: Signal,
        breakout_direction: str | None,
    ) -> None:
        """
        Record whether signal predicted correctly.

        Called by backtest engine after a breakout is detected.

        Args:
            signal: The signal that was generated
            breakout_direction: "UP", "DOWN", or None if no breakout
        """
        if breakout_direction is None:
            # No breakout to correlate with
            return

        # Determine if prediction was correct
        expected_direction = "LONG" if breakout_direction == "UP" else "SHORT"
        was_correct = signal.direction == expected_direction

        # Record in overall accuracy
        accuracy = self._get_or_create_accuracy(signal.signal_type)
        accuracy.record(was_correct)

        # Record in strength band
        if self.config.track_by_strength:
            bands = self._get_or_create_strength_bands(signal.signal_type)
            band_idx = self._get_strength_band_index(signal.strength)
            bands[band_idx].total_signals += 1
            if was_correct:
                bands[band_idx].correct_predictions += 1

    def get_accuracy_report(self) -> dict[str, dict]:
        """
        Get a report of all tracked accuracies.

        Returns:
            Dictionary with accuracy data for each signal type
        """
        report: dict[str, dict] = {}

        for signal_type, accuracy in self._accuracy.items():
            type_report: dict = {
                "total_signals": accuracy.total_signals,
                "correct_predictions": accuracy.correct_predictions,
                "accuracy": accuracy.accuracy,
            }

            if self.config.track_by_strength and signal_type in self._strength_bands:
                type_report["strength_bands"] = [
                    {
                        "range": f"{band.low:.2f}-{band.high:.2f}",
                        "total": band.total_signals,
                        "correct": band.correct_predictions,
                        "accuracy": band.accuracy,
                    }
                    for band in self._strength_bands[signal_type]
                ]

            report[signal_type.value] = type_report

        return report

    def reset(self) -> None:
        """Reset all accuracy tracking."""
        self._accuracy.clear()
        self._strength_bands.clear()
