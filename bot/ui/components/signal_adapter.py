"""
Signal Brain Adapter for real-time UI updates.

Provides a lightweight interface for streaming signal detector outputs
to the UI without requiring full SignalBrain AI calls on every update.

Key features:
- Debounces detector calls (not every price tick)
- Caches signals for UI display
- Calculates weighted scores per strategy
- Only used for DISPLAY - actual trading decisions use SignalBrain directly
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from bot.signals.aggregator import SignalAggregator
from bot.signals.base import Signal, SignalType

if TYPE_CHECKING:
    from bot.core.candle_aggregator import Candle
    from bot.signals.base import SignalDetector
    from bot.strategies import Strategy

logger = logging.getLogger(__name__)


@dataclass
class CoinSignalState:
    """Cached signal state for a single coin."""

    signals: list[Signal] = field(default_factory=list)
    net_score: float = 0.0  # Positive = LONG bias, Negative = SHORT bias
    last_update: datetime = field(default_factory=datetime.now)


class SignalBrainAdapter:
    """
    Adapter for real-time signal streaming without full SignalBrain AI calls.

    This adapter is used ONLY for UI display purposes:
    - Runs signal detectors on candles
    - Caches signals for each coin
    - Calculates weighted scores using strategy weights
    - Provides data for MarketsPanel display

    Actual trading decisions are made by SignalBrain with AI involvement.
    This adapter just shows users what the system "sees" in real-time.
    """

    # Minimum interval between detector sweeps (seconds)
    MIN_UPDATE_INTERVAL = 5.0

    # Maximum signal age to display (seconds)
    SIGNAL_TTL = 60.0

    def __init__(
        self,
        strategy: Strategy,
        detectors: list[SignalDetector],
    ) -> None:
        """
        Initialize the signal adapter.

        Args:
            strategy: Trading strategy with signal weights and threshold
            detectors: List of signal detectors to use
        """
        self.strategy = strategy
        self.aggregator = SignalAggregator(detectors)

        # Cache per coin
        self._state: dict[str, CoinSignalState] = {}

        # Last sweep time (for debouncing)
        self._last_sweep: datetime = datetime.min

    def process_candles(
        self,
        coin: str,
        candles: list[Candle],
        force: bool = False,
    ) -> list[Signal]:
        """
        Process candles through detectors and update cache.

        Args:
            coin: Coin symbol
            candles: List of candles (most recent last)
            force: Force update even if within debounce interval

        Returns:
            List of new signals detected (may be empty)
        """
        now = datetime.now()

        # Debounce: don't run detectors too frequently
        if not force:
            time_since_last = (now - self._last_sweep).total_seconds()
            if time_since_last < self.MIN_UPDATE_INTERVAL:
                return []

        self._last_sweep = now

        # Run detectors through aggregator
        new_signals = self.aggregator.process_candle(coin, candles)

        # Update state for this coin
        if coin not in self._state:
            self._state[coin] = CoinSignalState()

        state = self._state[coin]

        # Get recent signals for this coin (within TTL)
        recent_signals = self.aggregator.get_recent_signals(
            time_window_seconds=int(self.SIGNAL_TTL),
            coin=coin,
        )

        # Filter to only signals with weights in current strategy
        filtered_signals = [
            s for s in recent_signals if s.signal_type in self.strategy.signal_weights
        ]

        state.signals = filtered_signals
        state.last_update = now

        # Recalculate net conviction score
        state.net_score = self._calculate_net_score(filtered_signals)

        if new_signals:
            logger.debug(
                f"SignalAdapter: {coin} detected {len(new_signals)} new signals, "
                f"net_score:{state.net_score:.2f}"
            )

        return new_signals

    def get_signals_for_display(self, coin: str) -> list[Signal]:
        """
        Get cached signals for UI display.

        Args:
            coin: Coin symbol

        Returns:
            List of recent signals (may be empty)
        """
        if coin not in self._state:
            return []

        # Clean stale signals
        cutoff = datetime.now() - timedelta(seconds=self.SIGNAL_TTL)
        signals = [s for s in self._state[coin].signals if s.timestamp >= cutoff]
        self._state[coin].signals = signals

        return signals

    def get_signal_score(self, coin: str) -> tuple[float, float]:
        """
        Get net conviction score and threshold for a coin.

        Args:
            coin: Coin symbol

        Returns:
            Tuple of (net_score, threshold)
        """
        if coin not in self._state:
            return 0.0, self.strategy.signal_threshold

        state = self._state[coin]
        return state.net_score, self.strategy.signal_threshold

    def get_signal_display_data(
        self,
        coin: str,
    ) -> tuple[list[Signal], float, float]:
        """
        Get all data needed for UI display in one call.

        Args:
            coin: Coin symbol

        Returns:
            Tuple of (signals, net_score, threshold)
        """
        signals = self.get_signals_for_display(coin)
        net_score, threshold = self.get_signal_score(coin)
        return signals, net_score, threshold

    def _calculate_net_score(
        self,
        signals: list[Signal],
    ) -> float:
        """
        Calculate NET conviction score.

        LONG signals contribute positive values, SHORT signals contribute negative.
        Conflicting signals cancel out.

        Args:
            signals: List of signals to score

        Returns:
            Net score (positive = LONG bias, negative = SHORT bias)
        """
        net_score = 0.0

        for signal in signals:
            weight = self.strategy.signal_weights.get(signal.signal_type, 0.0)
            weighted_value = weight * signal.strength

            if signal.direction == "LONG":
                net_score += weighted_value
            else:
                net_score -= weighted_value

        return net_score

    def update_strategy(self, strategy: Strategy) -> None:
        """
        Update the strategy (used when user switches strategies).

        Args:
            strategy: New strategy to use for weight calculations
        """
        self.strategy = strategy

        # Recalculate scores for all cached coins
        for state in self._state.values():
            state.net_score = self._calculate_net_score(state.signals)

    def reset(self, coin: str | None = None) -> None:
        """
        Reset adapter state.

        Args:
            coin: Reset specific coin, or all if None
        """
        if coin is None:
            self._state.clear()
            self.aggregator.reset()
        else:
            self._state.pop(coin, None)
            self.aggregator.reset(coin)

    def format_signal_summary(self, coin: str) -> str:
        """
        Format a text summary of signals for logging.

        Args:
            coin: Coin symbol

        Returns:
            Formatted string like "MOM▲0.85 RSI▲0.60 MACD─"
        """
        signals = self.get_signals_for_display(coin)

        if not signals:
            return "No signals"

        # Group by signal type
        by_type: dict[SignalType, Signal] = {}
        for signal in signals:
            # Keep the most recent signal of each type
            if (
                signal.signal_type not in by_type
                or signal.timestamp > by_type[signal.signal_type].timestamp
            ):
                by_type[signal.signal_type] = signal

        # Format each signal type
        parts: list[str] = []
        for signal_type in SignalType:
            if signal_type in by_type:
                signal = by_type[signal_type]
                arrow = "▲" if signal.direction == "LONG" else "▼"
                name = signal_type.value[:3]  # MOM, RSI, MAC, VOL
                parts.append(f"{name}{arrow}{signal.strength:.2f}")

        return " ".join(parts) if parts else "─"
