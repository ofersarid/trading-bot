"""
Unified Trading Core - The single source of truth for trading logic.

This module contains the core trading logic used by BOTH:
- BacktestEngine (historical data)
- LiveEngine (real-time WebSocket data)

The logic is IDENTICAL - only the data source differs.
This ensures backtest results are predictive of live performance.

Architecture:
    Data Source → TradingCore → Decisions

    Data Source can be:
    - HistoricalDataSource (backtest)
    - WebSocketManager (live)

    TradingCore handles:
    - Candle buffering
    - Signal detection via SignalsFactory (pure, no AI)
    - AI position sizing via GoalBasedSizer
    - Stop/TP calculation

Available Signal Detectors:
    - momentum: Price momentum detection
    - rsi: RSI overbought/oversold
    - macd: MACD crossover signals
    - vp / volume_profile: Intraday volume profile (POC, VAH, VAL)
    - pdvp / prev_day_vp: Previous day's VP levels

Volume Profile Usage:
    VP detectors require external data setup:
    - set_volume_profile(profile) - for intraday VP
    - set_prev_day_vp_levels(levels) - for previous day's levels

    These are typically built from trade data files (parquet) in backtest,
    or from the trade stream in live trading.
"""

import logging
from collections import deque
from datetime import datetime
from typing import TYPE_CHECKING

from bot.ai.models import AccountContext, MarketContext, PortfolioOpportunity, TradePlan, UserGoal
from bot.core.candle_aggregator import Candle
from bot.indicators.atr import atr as calculate_atr
from bot.signals import (
    MACDSignalDetector,
    MomentumSignalDetector,
    PrevDayVPSignalDetector,
    RSISignalDetector,
    Signal,
    SignalAggregator,
    SignalsFactory,
    SignalValidator,
    VolumeProfileSignalDetector,
)
from bot.strategies import get_strategy

if TYPE_CHECKING:
    from bot.ai.goal_sizer import GoalBasedSizer
    from bot.ai.ollama_client import OllamaClient
    from bot.ai.portfolio_allocator import PortfolioAllocator
    from bot.indicators.volume_profile import VolumeProfile
    from bot.signals.detectors.prev_day_vp import PrevDayVPLevels

logger = logging.getLogger(__name__)


class TradingCore:
    """
    Unified trading logic for both backtest and live trading.

    This class contains ALL the decision-making logic:
    - Signal detection via SignalAggregator
    - Signal processing via SignalsFactory (filtering, weighting, TP/SL)
    - AI position sizing via GoalBasedSizer (optional)

    The only thing it doesn't handle is:
    - Where candles come from (backtest vs live)
    - Order execution (paper trader vs real exchange)
    """

    def __init__(
        self,
        strategy_name: str = "equal_weight",
        signal_detectors: list[str] | None = None,
        ai_enabled: bool = True,
        portfolio_mode: bool = False,
        account_goal: float | None = None,
        goal_timeframe_days: int | None = None,
        initial_balance: float = 10000.0,
        ollama_client: "OllamaClient | None" = None,
    ) -> None:
        """
        Initialize the trading core.

        Args:
            strategy_name: Strategy to use (from bot.strategies)
            signal_detectors: List of detectors to use ["momentum", "rsi", "macd"]
            ai_enabled: Whether to use AI for position sizing
            portfolio_mode: If True, use portfolio allocator for multi-asset
            account_goal: Target balance for AI position sizing
            goal_timeframe_days: Days to reach the goal
            initial_balance: Starting balance for goal tracking
            ollama_client: Optional Ollama client (created if AI enabled)
        """
        self.strategy_name = strategy_name
        self.strategy = get_strategy(strategy_name)
        self.ai_enabled = ai_enabled
        self.portfolio_mode = portfolio_mode
        self.account_goal = account_goal
        self.goal_timeframe_days = goal_timeframe_days
        self.initial_balance = initial_balance

        self._ollama = ollama_client
        self._goal_sizer: "GoalBasedSizer | None" = None
        self._portfolio_allocator: "PortfolioAllocator | None" = None

        # Signal detection
        detector_names = signal_detectors or ["momentum", "rsi", "macd"]
        self.detectors = self._create_detectors(detector_names)
        self.aggregator = SignalAggregator(self.detectors)
        self.validator = SignalValidator()

        # Signal processing (pure - no AI)
        self.signals_factory = SignalsFactory(self.strategy)

        # Candle buffers per coin
        self._candle_buffers: dict[str, deque[Candle]] = {}
        self._max_candles = 100

        # Tracking
        self._signals_generated = 0
        self._ai_calls = 0
        self._start_time: datetime | None = None

    def _create_detectors(self, names: list[str]) -> list:
        """Create signal detectors from names."""
        detectors = []
        detector_map = {
            "momentum": MomentumSignalDetector,
            "rsi": RSISignalDetector,
            "macd": MACDSignalDetector,
            "volume_profile": VolumeProfileSignalDetector,
            "vp": VolumeProfileSignalDetector,
            "prev_day_vp": PrevDayVPSignalDetector,
            "pdvp": PrevDayVPSignalDetector,
        }
        for name in names:
            if name.lower() in detector_map:
                detectors.append(detector_map[name.lower()]())
            else:
                logger.warning(f"Unknown detector: {name}")
        return detectors

    def get_volume_profile_detector(self) -> VolumeProfileSignalDetector | None:
        """Get the VolumeProfile detector if configured."""
        for d in self.detectors:
            if isinstance(d, VolumeProfileSignalDetector):
                return d
        return None

    def get_prev_day_vp_detector(self) -> PrevDayVPSignalDetector | None:
        """Get the PrevDayVP detector if configured."""
        for d in self.detectors:
            if isinstance(d, PrevDayVPSignalDetector):
                return d
        return None

    def set_volume_profile(self, profile: "VolumeProfile") -> None:
        """
        Set the volume profile for the VolumeProfileSignalDetector.

        Volume profiles must be built externally (from trade data) and
        passed to the detector. This is typically done:
        - In backtest: Built from historical trade parquet files
        - In live: Built from real-time trade stream

        Args:
            profile: VolumeProfile built by VolumeProfileBuilder
        """
        detector = self.get_volume_profile_detector()
        if detector:
            detector.update_profile(profile)
        else:
            logger.warning("set_volume_profile called but no VP detector configured")

    def set_prev_day_vp_levels(self, levels: "PrevDayVPLevels") -> None:
        """
        Set previous day's volume profile levels (POC, VAH, VAL).

        These levels are used by PrevDayVPSignalDetector to generate
        signals when price interacts with significant levels.

        Args:
            levels: PrevDayVPLevels with poc, vah, val prices
        """

        detector = self.get_prev_day_vp_detector()
        if detector:
            detector.set_prev_day_levels(levels)
        else:
            logger.warning("set_prev_day_vp_levels called but no PDVP detector configured")

    def add_candle(self, coin: str, candle: Candle) -> None:
        """
        Add a candle to the buffer for a coin.

        Args:
            coin: Coin symbol (e.g., "BTC")
            candle: Candle data
        """
        if coin not in self._candle_buffers:
            self._candle_buffers[coin] = deque(maxlen=self._max_candles)
        self._candle_buffers[coin].append(candle)

        if self._start_time is None:
            self._start_time = candle.timestamp

    def get_candles(self, coin: str) -> list[Candle]:
        """Get candle buffer for a coin."""
        if coin not in self._candle_buffers:
            return []
        return list(self._candle_buffers[coin])

    def has_enough_candles(self, coin: str, min_candles: int = 50) -> bool:
        """Check if we have enough candles for signal generation."""
        return len(self._candle_buffers.get(coin, [])) >= min_candles

    def detect_signals(self, coin: str) -> list[Signal]:
        """
        Detect signals for a coin using all configured detectors.

        Args:
            coin: Coin symbol

        Returns:
            List of detected signals (may be empty)
        """
        candles = self.get_candles(coin)
        if not candles:
            return []

        # Process through signal aggregator
        signals = self.aggregator.process_candle(coin, candles)

        # Filter through validator
        signals = [s for s in signals if self.validator.should_pass(s)]

        self._signals_generated += len(signals)
        return signals

    def calculate_market_context(self, coin: str, current_price: float) -> MarketContext:
        """
        Calculate market context for signal processing and AI.

        Args:
            coin: Coin symbol
            current_price: Current price

        Returns:
            MarketContext with volatility info
        """
        candles = self.get_candles(coin)

        # Calculate ATR
        atr_result = calculate_atr(candles, period=14) if len(candles) >= 14 else None
        atr_value = atr_result if atr_result is not None else 0.0

        return MarketContext.from_atr(coin, current_price, atr_value)

    def create_account_context(self, current_balance: float) -> AccountContext:
        """
        Create account context for AI position sizing.

        Args:
            current_balance: Current account balance

        Returns:
            AccountContext with goal tracking
        """
        days_elapsed = 0
        if self._start_time:
            days_elapsed = (datetime.now() - self._start_time).days

        return AccountContext(
            current_balance=current_balance,
            initial_balance=self.initial_balance,
            account_goal=self.account_goal,
            goal_timeframe_days=self.goal_timeframe_days,
            days_elapsed=days_elapsed,
            base_position_pct=self.strategy.risk.max_position_pct,
        )

    async def evaluate_signals(
        self,
        signals: list[Signal],
        coin: str,
        current_price: float,
        current_balance: float,
        current_positions: dict | None = None,  # noqa: ARG002 - kept for API compatibility
    ) -> TradePlan | None:
        """
        Evaluate signals and decide on a trade plan.

        FLOW:
        1. SignalsFactory filters and weights signals (pure, no AI)
        2. If threshold met, signals are enriched with TP/SL
        3. GoalBasedSizer determines position size (AI if enabled)
        4. Returns TradePlan with all execution details

        Args:
            signals: Detected signals
            coin: Coin symbol
            current_price: Current price
            current_balance: Current account balance
            current_positions: Dict of current positions (unused, kept for API compat)

        Returns:
            TradePlan if trade should be taken, None otherwise
        """
        if not signals:
            return None

        # Calculate market context
        market_context = self.calculate_market_context(coin, current_price)

        # Process through SignalsFactory (pure - no AI)
        factory_output = self.signals_factory.process_signals(signals, market_context)

        if factory_output is None:
            # Threshold not met
            return TradePlan.wait(
                coin, f"Signal threshold not met ({self.strategy.signal_threshold})"
            )

        # Get first signal for position info (all have same TP/SL)
        primary_signal = factory_output.signals[0]

        # Determine position size
        if self.ai_enabled:
            # AI position sizing
            sizer = await self._get_goal_sizer()
            account_context = self.create_account_context(current_balance)
            sizing = await sizer.size_position(factory_output, account_context)
            self._ai_calls += 1

            if not sizing.should_trade:
                return TradePlan.wait(coin, f"AI skipped: {sizing.reasoning}")

            position_pct = sizing.position_size_pct
            confidence = int(min(10, max(1, sizing.risk_percent * 2)))
            reason = sizing.reasoning
        else:
            # Deterministic position sizing
            position_pct = self._calculate_deterministic_size(
                factory_output.weighted_score,
                factory_output.threshold,
                market_context.volatility_level,
            )
            confidence = int(factory_output.weighted_score * 10)
            reason = f"Signal score: {factory_output.weighted_score:.2f}"

        # Build TradePlan
        return TradePlan(
            action=factory_output.direction,
            coin=coin,
            size_pct=position_pct,
            stop_loss=primary_signal.stop_loss or 0,
            take_profit=primary_signal.take_profit or 0,
            trail_activation=0,
            trail_distance_pct=self.strategy.risk.trail_distance_pct,
            confidence=confidence,
            reason=reason,
            signals_considered=[
                f"{s.signal_type.value}:{s.direction}" for s in factory_output.signals
            ],
        )

    def _calculate_deterministic_size(
        self,
        weighted_score: float,
        threshold: float,
        volatility_level: str,
    ) -> float:
        """
        Calculate position size without AI (deterministic).

        Args:
            weighted_score: Score from SignalsFactory
            threshold: Strategy threshold
            volatility_level: Market volatility

        Returns:
            Position size as percentage
        """
        base_position = self.strategy.risk.max_position_pct

        # Score strength multiplier
        score_ratio = weighted_score / threshold if threshold > 0 else 1.0
        score_mult = min(1.5, max(0.5, score_ratio))

        # Volatility adjustment
        vol_mult = {"high": 0.6, "medium": 0.8, "low": 1.0}.get(volatility_level, 0.8)

        return base_position * score_mult * vol_mult

    def signals_to_opportunity(
        self,
        signals: list[Signal],
        coin: str,
        current_price: float,
    ) -> PortfolioOpportunity | None:
        """
        Convert signals to a portfolio opportunity for multi-asset allocation.

        Uses SignalsFactory for consistent scoring.

        Args:
            signals: Detected signals
            coin: Coin symbol
            current_price: Current price

        Returns:
            PortfolioOpportunity if signals meet threshold, None otherwise
        """
        if not signals:
            return None

        market_context = self.calculate_market_context(coin, current_price)
        factory_output = self.signals_factory.process_signals(signals, market_context)

        if factory_output is None:
            return None

        return PortfolioOpportunity(
            coin=coin,
            direction=factory_output.direction,
            signal_score=factory_output.weighted_score,
            signal_threshold=factory_output.threshold,
            signals=[s.signal_type.value for s in factory_output.signals],
            current_price=current_price,
            volatility=market_context.volatility_level,
            atr_percent=market_context.atr_percent,
        )

    async def _get_goal_sizer(self) -> "GoalBasedSizer":
        """
        Get or create the GoalBasedSizer for AI position sizing.

        Creates a UserGoal from account_goal and goal_timeframe_days if set,
        otherwise uses default moderate goal.
        """
        if self._goal_sizer is None:
            from bot.ai.goal_sizer import GoalBasedSizer
            from bot.ai.models import RiskTolerance
            from bot.ai.ollama_client import OllamaClient

            if self._ollama is None:
                self._ollama = OllamaClient()

            # Create UserGoal from settings
            if self.account_goal and self.goal_timeframe_days:
                # Calculate target multiplier
                multiplier = self.account_goal / self.initial_balance
                goal = UserGoal(
                    description=f"Reach ${self.account_goal:,.0f} in {self.goal_timeframe_days} days",
                    target_multiplier=multiplier,
                    timeframe_days=self.goal_timeframe_days,
                    risk_tolerance=RiskTolerance.MODERATE,
                )
            else:
                goal = UserGoal.default()

            self._goal_sizer = GoalBasedSizer(
                ollama=self._ollama,
                goal=goal,
            )

        return self._goal_sizer

    async def _get_portfolio_allocator(self) -> "PortfolioAllocator":
        """Get or create the portfolio allocator."""
        if self._portfolio_allocator is None:
            from bot.ai.ollama_client import OllamaClient
            from bot.ai.portfolio_allocator import PortfolioAllocator

            if self._ollama is None:
                self._ollama = OllamaClient()

            self._portfolio_allocator = PortfolioAllocator(
                ollama_client=self._ollama,
                max_total_allocation=80.0,
            )

        return self._portfolio_allocator

    def get_metrics(self) -> dict:
        """Get trading core metrics."""
        return {
            "signals_generated": self._signals_generated,
            "ai_calls": self._ai_calls,
            "strategy": self.strategy_name,
            "ai_enabled": self.ai_enabled,
        }

    def reset(self) -> None:
        """Reset state for a new session."""
        self._candle_buffers.clear()
        self._signals_generated = 0
        self._ai_calls = 0
        self._start_time = None
        if self._goal_sizer:
            self._goal_sizer.reset_metrics()
