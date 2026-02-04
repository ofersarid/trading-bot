"""
SignalsFactory - Pure signal processing without AI.

Responsibilities:
- Filter signals by strategy weights
- Calculate weighted scores for LONG/SHORT directions
- Check if scores meet strategy threshold
- Enrich signals with TP/SL using structural levels or ATR fallback

This is a pure transformation layer - no AI, no side effects.
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from bot.signals.base import Signal, SignalType
from bot.signals.exit_levels import ExitLevelProvider, ExitLevels

if TYPE_CHECKING:
    from bot.ai.models import MarketContext
    from bot.backtest.models import PrevDayVPLevels
    from bot.indicators.volume_profile import VolumeProfile
    from bot.strategies.base import Strategy

logger = logging.getLogger(__name__)


@dataclass
class FactoryOutput:
    """
    Output from SignalsFactory.process_signals().

    Contains the winning direction, enriched signals with TP/SL,
    and scoring information.
    """

    direction: Literal["LONG", "SHORT"]
    signals: list[Signal]  # Enriched with entry_price, stop_loss, take_profit
    weighted_score: float
    threshold: float
    exit_levels: ExitLevels | None = None  # Detailed exit level info

    @property
    def is_long(self) -> bool:
        return self.direction == "LONG"

    @property
    def is_short(self) -> bool:
        return self.direction == "SHORT"

    @property
    def uses_structural_exits(self) -> bool:
        """True if exit levels are based on structural sources."""
        return self.exit_levels is not None and self.exit_levels.is_structural

    @property
    def exit_confidence(self) -> float:
        """Confidence in exit level calculation."""
        return self.exit_levels.confidence if self.exit_levels else 0.0


class SignalsFactory:
    """
    Pure signal processing factory.

    Takes raw signals from detectors and:
    1. Filters by strategy's signal_weights
    2. Calculates weighted scores
    3. Checks against threshold
    4. Enriches winning signals with TP/SL (using structural levels or ATR)

    No AI involvement - this is deterministic signal processing.
    """

    def __init__(self, strategy: "Strategy") -> None:
        """
        Initialize the factory.

        Args:
            strategy: Strategy with signal_weights, threshold, and risk config
        """
        self.strategy = strategy
        self._exit_provider = ExitLevelProvider(strategy)

    def update_vp(self, vp: "VolumeProfile") -> None:
        """
        Update the current session's Volume Profile.

        This allows structural exit level calculation using current VP.
        """
        self._exit_provider.update_vp(vp)

    def update_prev_day_levels(self, levels: "PrevDayVPLevels") -> None:
        """
        Update the previous day's VP levels.

        This allows structural exit level calculation using prev day levels.
        """
        self._exit_provider.update_prev_day_levels(levels)

    def process_signals(
        self,
        signals: list[Signal],
        market_context: "MarketContext",
    ) -> FactoryOutput | None:
        """
        Process signals through strategy weights and threshold.

        Args:
            signals: Raw signals from detectors
            market_context: Current market context with price and ATR

        Returns:
            FactoryOutput if threshold met, None otherwise
        """
        coin = market_context.coin

        # Filter signals by strategy weights and minimum strength
        valid_signals = self._filter_signals(signals, coin)

        if not valid_signals:
            logger.debug(f"No valid signals for {coin}")
            return None

        # Calculate net conviction score
        net_score = self._calculate_net_score(valid_signals)

        # Check threshold
        meets_threshold, direction = self._meets_threshold(net_score)

        if not meets_threshold:
            logger.debug(
                f"Signal scores below threshold: net={net_score:.2f}, "
                f"threshold=±{self.strategy.signal_threshold}"
            )
            return None

        logger.info(
            f"Signal threshold met: {direction} net_score={net_score:.2f} "
            f"(threshold=±{self.strategy.signal_threshold})"
        )

        # Calculate exit levels using ExitLevelProvider
        exit_levels = self._exit_provider.calculate_exit_levels(
            valid_signals,
            market_context,
            direction,  # type: ignore[arg-type]
        )

        # Enrich signals with TP/SL from exit levels
        enriched_signals = self._enrich_signals(
            valid_signals, market_context, direction, exit_levels
        )

        # Conviction is always positive (absolute value of net score)
        conviction = abs(net_score)

        return FactoryOutput(
            direction=direction,  # type: ignore[arg-type]
            signals=enriched_signals,
            weighted_score=conviction,
            threshold=self.strategy.signal_threshold,
            exit_levels=exit_levels,
        )

    def _filter_signals(self, signals: list[Signal], coin: str) -> list[Signal]:
        """
        Filter signals based on strategy's signal_weights.

        Args:
            signals: All detected signals
            coin: Coin to filter for

        Returns:
            Signals that have a weight in the strategy and meet min strength
        """
        filtered = []
        for signal in signals:
            # Only consider signals for this coin
            if signal.coin != coin:
                continue

            # Only consider signal types that have a weight in this strategy
            if signal.signal_type not in self.strategy.signal_weights:
                logger.debug(
                    f"Filtering out {signal.signal_type.value} signal - "
                    f"not in strategy's signal_weights"
                )
                continue

            # Apply noise filter - ignore very weak signals
            if signal.strength < self.strategy.min_signal_strength:
                logger.debug(
                    f"Filtering out {signal.signal_type.value} signal - "
                    f"strength {signal.strength:.2f} below min {self.strategy.min_signal_strength}"
                )
                continue

            filtered.append(signal)

        return filtered

    def _calculate_net_score(self, signals: list[Signal]) -> float:
        """
        Calculate NET conviction score.

        LONG signals contribute positive values, SHORT signals contribute negative.
        Conflicting signals cancel out, resulting in low conviction.

        Args:
            signals: Filtered signals

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

            logger.debug(
                f"  {signal.signal_type.value} {signal.direction}: "
                f"weight={weight:.2f} * strength={signal.strength:.2f} = {weighted_value:.2f}"
            )

        return net_score

    def _meets_threshold(self, net_score: float) -> tuple[bool, Literal["LONG", "SHORT", "WAIT"]]:
        """
        Check if net conviction score meets the strategy's threshold.

        Args:
            net_score: Net conviction score (positive = LONG, negative = SHORT)

        Returns:
            Tuple of (meets_threshold, winning_direction)
        """
        threshold = self.strategy.signal_threshold

        # LONG if net score meets positive threshold
        if net_score >= threshold:
            return True, "LONG"

        # SHORT if net score meets negative threshold
        if net_score <= -threshold:
            return True, "SHORT"

        return False, "WAIT"

    def _enrich_signals(
        self,
        signals: list[Signal],
        market_context: "MarketContext",
        _direction: str,
        exit_levels: ExitLevels,
    ) -> list[Signal]:
        """
        Enrich signals with entry price, stop loss, and take profit.

        Uses exit levels calculated by ExitLevelProvider (structural or ATR-based).

        Args:
            signals: Signals to enrich
            market_context: Market context with price and ATR
            direction: Winning direction (LONG or SHORT)
            exit_levels: Calculated exit levels with TP/SL

        Returns:
            Signals with position info populated
        """
        price = market_context.current_price
        atr = market_context.atr

        # Use levels from ExitLevelProvider
        stop_loss = exit_levels.stop_loss
        take_profit = exit_levels.take_profit

        # Enrich each signal
        enriched = []
        for signal in signals:
            # Create a copy with position info
            enriched_signal = Signal(
                coin=signal.coin,
                signal_type=signal.signal_type,
                direction=signal.direction,
                strength=signal.strength,
                timestamp=signal.timestamp,
                metadata=signal.metadata.copy(),
                entry_price=price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                atr=atr,
            )
            enriched.append(enriched_signal)

        return enriched

    def get_signal_contributions(self, signals: list[Signal], coin: str) -> dict[SignalType, float]:
        """
        Get weighted contributions from each signal type.

        Useful for displaying signal breakdown in UI.

        Args:
            signals: Raw signals
            coin: Coin to filter for

        Returns:
            Dict mapping signal type to its weighted contribution
        """
        filtered = self._filter_signals(signals, coin)
        contributions: dict[SignalType, float] = {}

        for signal in filtered:
            weight = self.strategy.signal_weights.get(signal.signal_type, 0.0)
            weighted_value = weight * signal.strength

            if signal.signal_type not in contributions:
                contributions[signal.signal_type] = 0.0

            # Add or subtract based on direction
            if signal.direction == "LONG":
                contributions[signal.signal_type] += weighted_value
            else:
                contributions[signal.signal_type] -= weighted_value

        return contributions
