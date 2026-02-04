"""
Exit Level Provider - Structural exit level calculation.

Calculates TP/SL levels from structural sources (VP levels, prev day levels)
rather than using only ATR-based calculation.

Key features:
- Extracts levels from signal metadata and market context
- Finds confluent levels (multiple sources agreeing within X%)
- Calculates confidence score based on confluence
- Falls back to ATR-based calculation if no structural levels found
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from bot.signals.base import ExitLevelSource, Signal

if TYPE_CHECKING:
    from bot.ai.models import MarketContext
    from bot.backtest.models import PrevDayVPLevels
    from bot.indicators.volume_profile import VolumeProfile
    from bot.strategies.base import Strategy

logger = logging.getLogger(__name__)


@dataclass
class LevelCandidate:
    """A candidate level for TP or SL placement."""

    price: float
    source: ExitLevelSource
    role: Literal["tp", "sl"]  # Whether this is a TP or SL candidate


@dataclass
class ExitLevels:
    """
    Calculated exit levels with confidence information.

    Contains the final TP/SL levels along with information about
    what sources contributed to the calculation.
    """

    take_profit: float
    stop_loss: float
    tp_sources: list[ExitLevelSource]  # Sources that contributed to TP
    sl_sources: list[ExitLevelSource]  # Sources that contributed to SL
    confidence: float  # 0-1, based on confluence quality

    @property
    def is_structural(self) -> bool:
        """True if exit levels are based on structural sources (not just ATR)."""
        non_atr_tp = any(s != ExitLevelSource.ATR_MULTIPLIER for s in self.tp_sources)
        non_atr_sl = any(s != ExitLevelSource.ATR_MULTIPLIER for s in self.sl_sources)
        return non_atr_tp or non_atr_sl

    @property
    def tp_confluence_count(self) -> int:
        """Number of sources agreeing on TP level."""
        return len(self.tp_sources)

    @property
    def sl_confluence_count(self) -> int:
        """Number of sources agreeing on SL level."""
        return len(self.sl_sources)


class ExitLevelProvider:
    """
    Provides exit levels (TP/SL) based on structural market levels.

    Uses Volume Profile levels, previous day levels, and signal metadata
    to find optimal exit points. Falls back to ATR-based calculation
    when no structural levels are available or confluent.
    """

    def __init__(
        self,
        strategy: "Strategy",
        current_vp: "VolumeProfile | None" = None,
        prev_day_levels: "PrevDayVPLevels | None" = None,
    ) -> None:
        """
        Initialize the provider.

        Args:
            strategy: Strategy with exit_level_sources configuration
            current_vp: Current session's Volume Profile (optional)
            prev_day_levels: Previous day's VP levels (optional)
        """
        self.strategy = strategy
        self._current_vp = current_vp
        self._prev_day_levels = prev_day_levels

    def update_vp(self, vp: "VolumeProfile") -> None:
        """Update the current session's Volume Profile."""
        self._current_vp = vp

    def update_prev_day_levels(self, levels: "PrevDayVPLevels") -> None:
        """Update the previous day's levels."""
        self._prev_day_levels = levels

    def calculate_exit_levels(
        self,
        signals: list[Signal],
        market_context: "MarketContext",
        direction: Literal["LONG", "SHORT"],
    ) -> ExitLevels:
        """
        Calculate exit levels for a trade.

        Args:
            signals: Signals that contributed to the entry decision
            market_context: Current market context with price and ATR
            direction: Trade direction (LONG or SHORT)

        Returns:
            ExitLevels with TP, SL, sources, and confidence
        """
        entry_price = market_context.current_price

        # Extract all candidate levels from available sources
        candidates = self._extract_level_candidates(signals, market_context, direction)

        # Separate into TP and SL candidates
        tp_candidates = [c for c in candidates if c.role == "tp"]
        sl_candidates = [c for c in candidates if c.role == "sl"]

        logger.debug(
            f"Found {len(tp_candidates)} TP candidates, {len(sl_candidates)} SL candidates"
        )

        # Find confluent levels
        tp_level, tp_sources = self._find_confluent_level(
            tp_candidates, entry_price, direction, "tp"
        )
        sl_level, sl_sources = self._find_confluent_level(
            sl_candidates, entry_price, direction, "sl"
        )

        # Calculate confidence based on confluence
        confidence = self._calculate_confidence(tp_sources, sl_sources)

        # Fall back to ATR if no structural levels found
        if tp_level is None or sl_level is None:
            atr_tp, atr_sl = self._calculate_atr_exits(market_context, direction)

            if tp_level is None:
                tp_level = atr_tp
                tp_sources = [ExitLevelSource.ATR_MULTIPLIER]
                logger.debug(f"Using ATR-based TP: {tp_level:.2f}")

            if sl_level is None:
                sl_level = atr_sl
                sl_sources = [ExitLevelSource.ATR_MULTIPLIER]
                logger.debug(f"Using ATR-based SL: {sl_level:.2f}")

        # Validate and adjust levels if needed
        tp_level, sl_level = self._validate_levels(
            tp_level, sl_level, entry_price, direction, market_context
        )

        logger.info(
            f"Exit levels for {direction}: TP={tp_level:.2f} ({len(tp_sources)} sources), "
            f"SL={sl_level:.2f} ({len(sl_sources)} sources), confidence={confidence:.2f}"
        )

        return ExitLevels(
            take_profit=tp_level,
            stop_loss=sl_level,
            tp_sources=tp_sources,
            sl_sources=sl_sources,
            confidence=confidence,
        )

    def _extract_level_candidates(
        self,
        signals: list[Signal],
        market_context: "MarketContext",
        direction: Literal["LONG", "SHORT"],
    ) -> list[LevelCandidate]:
        """
        Extract all candidate levels from available sources.

        Considers:
        - Signal metadata (target levels from VP detectors)
        - Current VP levels (VAH, VAL, POC)
        - Previous day VP levels
        """
        candidates: list[LevelCandidate] = []
        entry_price = market_context.current_price
        sources = self.strategy.exit_level_sources

        # Skip ATR_MULTIPLIER source - it's handled separately as fallback
        structural_sources = [s for s in sources if s != ExitLevelSource.ATR_MULTIPLIER]

        # Extract levels from signal metadata
        for signal in signals:
            metadata = signal.metadata
            candidates.extend(self._extract_from_signal_metadata(metadata, entry_price, direction))

        # Extract from current VP
        if self._current_vp is not None:
            candidates.extend(
                self._extract_from_current_vp(structural_sources, entry_price, direction)
            )

        # Extract from previous day levels
        if self._prev_day_levels is not None:
            candidates.extend(
                self._extract_from_prev_day(structural_sources, entry_price, direction)
            )

        return candidates

    def _extract_from_signal_metadata(
        self,
        metadata: dict,
        entry_price: float,
        direction: Literal["LONG", "SHORT"],
    ) -> list[LevelCandidate]:
        """Extract level candidates from signal metadata."""
        candidates: list[LevelCandidate] = []

        # Check for explicit target in metadata (from VP detectors)
        target = metadata.get("target")
        if target is not None and isinstance(target, int | float):
            # Determine if target is TP or SL based on direction and price
            if direction == "LONG":
                role: Literal["tp", "sl"] = "tp" if target > entry_price else "sl"
            else:
                role = "tp" if target < entry_price else "sl"

            # Infer source from metadata
            source = self._infer_source_from_metadata(metadata, role)
            if source is not None:
                candidates.append(LevelCandidate(price=target, source=source, role=role))
                logger.debug(f"Found target in metadata: {target:.2f} as {role} ({source})")

        # Extract VP levels from metadata
        vp_levels = [
            ("va_high", ExitLevelSource.VP_VAH),
            ("va_low", ExitLevelSource.VP_VAL),
            ("poc", ExitLevelSource.VP_POC),
            ("prev_day_vah", ExitLevelSource.PREV_DAY_VAH),
            ("prev_day_val", ExitLevelSource.PREV_DAY_VAL),
            ("prev_day_poc", ExitLevelSource.PREV_DAY_POC),
        ]

        for key, source in vp_levels:
            value = metadata.get(key)
            if value is not None and isinstance(value, int | float):
                role = self._determine_role(value, entry_price, direction)
                candidates.append(LevelCandidate(price=value, source=source, role=role))

        return candidates

    def _extract_from_current_vp(
        self,
        sources: Sequence[ExitLevelSource],
        entry_price: float,
        direction: Literal["LONG", "SHORT"],
    ) -> list[LevelCandidate]:
        """Extract level candidates from current VP."""
        from bot.indicators.volume_profile import get_poc, get_value_area

        candidates: list[LevelCandidate] = []

        if self._current_vp is None:
            return candidates

        va = get_value_area(self._current_vp)
        poc = get_poc(self._current_vp)

        if va is not None:
            va_low, va_high = va
            if ExitLevelSource.VP_VAH in sources:
                role = self._determine_role(va_high, entry_price, direction)
                candidates.append(
                    LevelCandidate(price=va_high, source=ExitLevelSource.VP_VAH, role=role)
                )
            if ExitLevelSource.VP_VAL in sources:
                role = self._determine_role(va_low, entry_price, direction)
                candidates.append(
                    LevelCandidate(price=va_low, source=ExitLevelSource.VP_VAL, role=role)
                )

        if poc is not None and ExitLevelSource.VP_POC in sources:
            role = self._determine_role(poc, entry_price, direction)
            candidates.append(LevelCandidate(price=poc, source=ExitLevelSource.VP_POC, role=role))

        return candidates

    def _extract_from_prev_day(
        self,
        sources: Sequence[ExitLevelSource],
        entry_price: float,
        direction: Literal["LONG", "SHORT"],
    ) -> list[LevelCandidate]:
        """Extract level candidates from previous day levels."""
        candidates: list[LevelCandidate] = []

        if self._prev_day_levels is None:
            return candidates

        level_map = {
            ExitLevelSource.PREV_DAY_VAH: self._prev_day_levels.vah,
            ExitLevelSource.PREV_DAY_VAL: self._prev_day_levels.val,
            ExitLevelSource.PREV_DAY_POC: self._prev_day_levels.poc,
        }

        for source, price in level_map.items():
            if source in sources and price > 0:
                role = self._determine_role(price, entry_price, direction)
                candidates.append(LevelCandidate(price=price, source=source, role=role))

        return candidates

    def _determine_role(
        self, level: float, entry_price: float, direction: Literal["LONG", "SHORT"]
    ) -> Literal["tp", "sl"]:
        """
        Determine if a level should be TP or SL based on direction.

        For LONG: Levels above entry are TP, below are SL
        For SHORT: Levels below entry are TP, above are SL
        """
        if direction == "LONG":
            return "tp" if level > entry_price else "sl"
        else:
            return "tp" if level < entry_price else "sl"

    def _infer_source_from_metadata(
        self, metadata: dict, role: Literal["tp", "sl"]
    ) -> ExitLevelSource | None:
        """Infer the exit level source from signal metadata."""
        setup = metadata.get("setup", "")

        # Map setup types to sources
        if "prev_day" in setup or "prev_day_vah" in metadata:
            if role == "tp":
                return ExitLevelSource.PREV_DAY_VAH
            else:
                return ExitLevelSource.PREV_DAY_VAL
        elif "poc" in setup:
            return ExitLevelSource.PREV_DAY_POC
        elif "va" in setup:
            return ExitLevelSource.VP_VAH if role == "tp" else ExitLevelSource.VP_VAL

        return ExitLevelSource.VP_POC  # Default for VP signals

    def _find_confluent_level(
        self,
        candidates: list[LevelCandidate],
        entry_price: float,
        _direction: Literal["LONG", "SHORT"],
        role: Literal["tp", "sl"],
    ) -> tuple[float | None, list[ExitLevelSource]]:
        """
        Find the most confluent level from candidates.

        Groups nearby levels and returns the cluster with most sources.

        Returns:
            Tuple of (level_price, contributing_sources)
        """
        if not candidates:
            return None, []

        # Get reference range for confluence distance calculation
        if self._prev_day_levels is not None:
            va_range = self._prev_day_levels.vah - self._prev_day_levels.val
        elif self._current_vp is not None:
            from bot.indicators.volume_profile import get_value_area

            va = get_value_area(self._current_vp)
            va_range = (va[1] - va[0]) if va else entry_price * 0.02
        else:
            va_range = entry_price * 0.02  # Default 2% range

        confluence_distance = va_range * self.strategy.confluence_distance_pct

        # Group candidates into clusters
        clusters: list[list[LevelCandidate]] = []

        for candidate in candidates:
            # Find existing cluster within confluence distance
            added_to_cluster = False
            for cluster in clusters:
                cluster_avg = sum(c.price for c in cluster) / len(cluster)
                if abs(candidate.price - cluster_avg) <= confluence_distance:
                    cluster.append(candidate)
                    added_to_cluster = True
                    break

            if not added_to_cluster:
                clusters.append([candidate])

        # Filter clusters by minimum confluence requirement
        valid_clusters = [c for c in clusters if len(c) >= self.strategy.min_confluence_sources]

        if not valid_clusters:
            # If no cluster meets minimum, use the best single level
            if clusters:
                best_cluster = max(clusters, key=len)
                if len(best_cluster) > 0:
                    avg_price = sum(c.price for c in best_cluster) / len(best_cluster)
                    sources = list({c.source for c in best_cluster})
                    return avg_price, sources
            return None, []

        # Select the best cluster (most sources)
        best_cluster = max(valid_clusters, key=len)
        avg_price = sum(c.price for c in best_cluster) / len(best_cluster)
        sources = list({c.source for c in best_cluster})

        logger.debug(
            f"Found confluent {role} level at {avg_price:.2f} "
            f"with {len(sources)} sources: {[s.value for s in sources]}"
        )

        return avg_price, sources

    def _calculate_confidence(
        self,
        tp_sources: list[ExitLevelSource],
        sl_sources: list[ExitLevelSource],
    ) -> float:
        """
        Calculate confidence score based on exit level quality.

        Higher confidence when:
        - More sources agree (confluence)
        - Structural levels used (not just ATR)
        """
        tp_count = len(tp_sources)
        sl_count = len(sl_sources)

        # Base confidence from confluence count
        max_sources = 5  # Normalize to max 5 sources
        tp_conf = min(tp_count / max_sources, 1.0)
        sl_conf = min(sl_count / max_sources, 1.0)

        # Average TP and SL confidence
        base_confidence = (tp_conf + sl_conf) / 2

        # Bonus for structural (non-ATR) levels
        structural_bonus = 0.0
        if any(s != ExitLevelSource.ATR_MULTIPLIER for s in tp_sources):
            structural_bonus += 0.15
        if any(s != ExitLevelSource.ATR_MULTIPLIER for s in sl_sources):
            structural_bonus += 0.15

        return min(base_confidence + structural_bonus, 1.0)

    def _calculate_atr_exits(
        self,
        market_context: "MarketContext",
        direction: Literal["LONG", "SHORT"],
    ) -> tuple[float, float]:
        """Calculate fallback ATR-based exit levels."""
        price = market_context.current_price
        atr = market_context.atr

        # Volatility adjustment
        vol_factor = {
            "high": 1.5,
            "medium": 1.0,
            "low": 0.7,
        }.get(market_context.volatility_level, 1.0)

        sl_distance = atr * self.strategy.fallback_sl_atr_multiplier * vol_factor
        tp_distance = atr * self.strategy.fallback_tp_atr_multiplier * vol_factor

        if direction == "LONG":
            return price + tp_distance, price - sl_distance
        else:
            return price - tp_distance, price + sl_distance

    def _validate_levels(
        self,
        tp: float,
        sl: float,
        entry_price: float,
        direction: Literal["LONG", "SHORT"],
        market_context: "MarketContext",
    ) -> tuple[float, float]:
        """
        Validate and adjust exit levels if needed.

        Ensures:
        - TP is in the profitable direction
        - SL is in the loss direction
        - Minimum distance from entry (using ATR)
        """
        atr = market_context.atr
        min_distance = atr * 0.5  # Minimum half ATR distance

        if direction == "LONG":
            # TP must be above entry
            if tp <= entry_price:
                tp = entry_price + atr * self.strategy.fallback_tp_atr_multiplier
                logger.warning(f"Adjusted TP to be above entry: {tp:.2f}")

            # SL must be below entry
            if sl >= entry_price:
                sl = entry_price - atr * self.strategy.fallback_sl_atr_multiplier
                logger.warning(f"Adjusted SL to be below entry: {sl:.2f}")

            # Ensure minimum distance
            if tp - entry_price < min_distance:
                tp = entry_price + min_distance
            if entry_price - sl < min_distance:
                sl = entry_price - min_distance

        else:  # SHORT
            # TP must be below entry
            if tp >= entry_price:
                tp = entry_price - atr * self.strategy.fallback_tp_atr_multiplier
                logger.warning(f"Adjusted TP to be below entry: {tp:.2f}")

            # SL must be above entry
            if sl <= entry_price:
                sl = entry_price + atr * self.strategy.fallback_sl_atr_multiplier
                logger.warning(f"Adjusted SL to be above entry: {sl:.2f}")

            # Ensure minimum distance
            if entry_price - tp < min_distance:
                tp = entry_price - min_distance
            if sl - entry_price < min_distance:
                sl = entry_price + min_distance

        return tp, sl
