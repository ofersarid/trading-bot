"""
SignalsFactory - Pure signal processing without AI.

Responsibilities:
- Filter signals by strategy weights
- Calculate weighted scores for LONG/SHORT directions
- Check if scores meet strategy threshold
- Enrich signals with TP/SL based on ATR

This is a pure transformation layer - no AI, no side effects.
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from bot.signals.base import Signal, SignalType

if TYPE_CHECKING:
    from bot.ai.models import MarketContext
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

    @property
    def is_long(self) -> bool:
        return self.direction == "LONG"

    @property
    def is_short(self) -> bool:
        return self.direction == "SHORT"


class SignalsFactory:
    """
    Pure signal processing factory.

    Takes raw signals from detectors and:
    1. Filters by strategy's signal_weights
    2. Calculates weighted scores
    3. Checks against threshold
    4. Enriches winning signals with TP/SL

    No AI involvement - this is deterministic signal processing.
    """

    def __init__(self, strategy: "Strategy") -> None:
        """
        Initialize the factory.

        Args:
            strategy: Strategy with signal_weights, threshold, and risk config
        """
        self.strategy = strategy

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

        # Calculate weighted scores
        long_score, short_score = self._calculate_weighted_scores(valid_signals)

        # Check threshold
        meets_threshold, direction = self._meets_threshold(long_score, short_score)

        if not meets_threshold:
            logger.debug(
                f"Signal scores below threshold: LONG={long_score:.2f}, "
                f"SHORT={short_score:.2f}, threshold={self.strategy.signal_threshold}"
            )
            return None

        logger.info(
            f"Signal threshold met: {direction} score={max(long_score, short_score):.2f} "
            f">= {self.strategy.signal_threshold}"
        )

        # Enrich signals with TP/SL
        enriched_signals = self._enrich_signals(valid_signals, market_context, direction)

        winning_score = long_score if direction == "LONG" else short_score

        return FactoryOutput(
            direction=direction,  # type: ignore[arg-type]
            signals=enriched_signals,
            weighted_score=winning_score,
            threshold=self.strategy.signal_threshold,
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

    def _calculate_weighted_scores(self, signals: list[Signal]) -> tuple[float, float]:
        """
        Calculate weighted scores for each direction.

        Each signal contributes: weight * strength to its direction's score.

        Args:
            signals: Filtered signals

        Returns:
            Tuple of (long_score, short_score)
        """
        long_score = 0.0
        short_score = 0.0

        for signal in signals:
            weight = self.strategy.signal_weights.get(signal.signal_type, 0.0)
            weighted_value = weight * signal.strength

            if signal.direction == "LONG":
                long_score += weighted_value
            else:
                short_score += weighted_value

            logger.debug(
                f"  {signal.signal_type.value} {signal.direction}: "
                f"weight={weight:.2f} * strength={signal.strength:.2f} = {weighted_value:.2f}"
            )

        return long_score, short_score

    def _meets_threshold(
        self, long_score: float, short_score: float
    ) -> tuple[bool, Literal["LONG", "SHORT", "WAIT"]]:
        """
        Check if weighted scores meet the strategy's threshold.

        Args:
            long_score: Total weighted score for LONG signals
            short_score: Total weighted score for SHORT signals

        Returns:
            Tuple of (meets_threshold, winning_direction)
        """
        threshold = self.strategy.signal_threshold

        # LONG wins if it meets threshold and beats SHORT
        if long_score >= threshold and long_score > short_score:
            return True, "LONG"

        # SHORT wins if it meets threshold and beats LONG
        if short_score >= threshold and short_score > long_score:
            return True, "SHORT"

        return False, "WAIT"

    def _enrich_signals(
        self,
        signals: list[Signal],
        market_context: "MarketContext",
        direction: str,
    ) -> list[Signal]:
        """
        Enrich signals with entry price, stop loss, and take profit.

        Uses ATR-based calculation from strategy's risk config.

        Args:
            signals: Signals to enrich
            market_context: Market context with price and ATR
            direction: Winning direction (LONG or SHORT)

        Returns:
            Signals with position info populated
        """
        # Volatility adjustment for stops
        vol_factor = {
            "high": 1.5,
            "medium": 1.0,
            "low": 0.7,
        }.get(market_context.volatility_level, 1.0)

        atr = market_context.atr
        price = market_context.current_price

        # Calculate SL/TP distances
        sl_distance = atr * self.strategy.risk.stop_loss_atr_multiplier * vol_factor
        tp_distance = atr * self.strategy.risk.take_profit_atr_multiplier * vol_factor

        # Calculate actual levels based on direction
        if direction == "LONG":
            stop_loss = price - sl_distance
            take_profit = price + tp_distance
        else:
            stop_loss = price + sl_distance
            take_profit = price - tp_distance

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
