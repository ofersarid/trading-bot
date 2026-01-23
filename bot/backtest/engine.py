"""
Backtest Engine - Orchestrates the 3-layer backtesting architecture.

Flow: Historical Data → Indicators → Signals → AI Brain → Position Manager

The engine processes historical candles, generates signals through the
signal detectors, optionally passes them to the AI for evaluation, and
executes trades through the position manager.
"""

import logging
import time
from collections import deque
from datetime import datetime
from typing import TYPE_CHECKING

from bot.ai.models import MarketContext, TradePlan
from bot.ai.personas.base import get_persona
from bot.ai.signal_brain import SignalBrain
from bot.backtest.breakout_analyzer import BreakoutAnalysis, BreakoutAnalyzer
from bot.backtest.models import BacktestConfig, BacktestResult, EquityPoint
from bot.backtest.position_manager import PositionManager
from bot.core.candle_aggregator import Candle
from bot.indicators import atr
from bot.signals import (
    MACDSignalDetector,
    MomentumSignalDetector,
    RSISignalDetector,
    Signal,
    SignalAggregator,
    SignalValidator,
)
from bot.simulation.historical_source import HistoricalDataSource, PriceUpdate
from bot.simulation.paper_trader import PaperTrader

if TYPE_CHECKING:
    from bot.ai.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


class BacktestEngine:
    """
    Orchestrates backtesting with the 3-layer architecture.

    Processes historical data through:
    1. Indicators (pure math functions)
    2. Signal detectors (pattern recognition)
    3. AI Brain (optional, for decision making)
    4. Position Manager (execution with trailing stops)
    """

    def __init__(
        self,
        config: BacktestConfig,
        ollama_client: "OllamaClient | None" = None,
    ) -> None:
        """
        Initialize the backtest engine.

        Args:
            config: Backtest configuration
            ollama_client: Optional Ollama client (created if AI enabled and not provided)
        """
        self.config = config
        self._ollama = ollama_client

        # Initialize components
        self.trader = PaperTrader(starting_balance=config.initial_balance)
        self.position_manager = PositionManager(self.trader)

        # Initialize signal detectors based on config
        self.detectors = self._create_detectors()
        self.aggregator = SignalAggregator(self.detectors)

        # Signal validator - filters historically inaccurate signals
        self.validator = SignalValidator()

        # AI Brain (lazy initialized)
        self._brain: SignalBrain | None = None

        # Candle buffers per coin
        self._candle_buffers: dict[str, deque[Candle]] = {}
        self._max_candles = 100  # Keep last 100 candles for indicators

        # Tracking
        self._signals_generated = 0
        self._ai_calls = 0
        self._equity_curve: list[EquityPoint] = []

        # For breakout analysis
        self._all_candles: list[Candle] = []
        self._all_signals: list[tuple[int, Signal]] = []  # (candle_index, signal)

    def _create_detectors(self) -> list:
        """Create signal detectors based on config."""
        detectors = []

        detector_map = {
            "momentum": MomentumSignalDetector,
            "rsi": RSISignalDetector,
            "macd": MACDSignalDetector,
        }

        for name in self.config.signal_detectors:
            if name.lower() in detector_map:
                detectors.append(detector_map[name.lower()]())
            else:
                logger.warning(f"Unknown signal detector: {name}")

        return detectors

    async def _get_brain(self) -> SignalBrain:
        """Get or create the AI brain."""
        if self._brain is None:
            from bot.ai.ollama_client import OllamaClient

            if self._ollama is None:
                self._ollama = OllamaClient()

            persona = get_persona(self.config.persona_name)
            self._brain = SignalBrain(persona=persona, ollama_client=self._ollama)

        return self._brain

    def _load_data(self) -> HistoricalDataSource:
        """Load historical data from CSV."""
        source = HistoricalDataSource(self.config.data_source)

        # Update config with coin from data if not specified
        if not self.config.coins:
            self.config.coins = [source.coin]

        return source

    def _price_update_to_candle(self, update: PriceUpdate) -> Candle:
        """Convert PriceUpdate to Candle."""
        return Candle(
            timestamp=update.timestamp,
            open=update.open,
            high=update.high,
            low=update.low,
            close=update.close,
            volume=update.volume,
        )

    def _get_candles(self, coin: str) -> list[Candle]:
        """Get candle buffer for a coin."""
        if coin not in self._candle_buffers:
            self._candle_buffers[coin] = deque(maxlen=self._max_candles)
        return list(self._candle_buffers[coin])

    def _add_candle(self, coin: str, candle: Candle) -> None:
        """Add a candle to the buffer."""
        if coin not in self._candle_buffers:
            self._candle_buffers[coin] = deque(maxlen=self._max_candles)
        self._candle_buffers[coin].append(candle)

    def _calculate_market_context(self, coin: str, current_price: float) -> MarketContext:
        """Calculate market context including ATR."""
        candles = self._get_candles(coin)

        atr_value = atr(candles, period=14) if len(candles) >= 15 else None
        if atr_value is None:
            # Estimate ATR from recent price range
            if candles:
                recent = candles[-14:] if len(candles) >= 14 else candles
                avg_range = sum(c.high - c.low for c in recent) / len(recent)
                atr_value = avg_range
            else:
                atr_value = current_price * 0.01  # Default 1% of price

        return MarketContext.from_atr(coin, current_price, atr_value)

    def _record_equity(self, timestamp: datetime, prices: dict[str, float]) -> None:
        """Record a point on the equity curve."""
        equity = self.trader.get_equity(prices)
        self._equity_curve.append(
            EquityPoint(
                timestamp=timestamp,
                equity=equity,
                balance=self.trader.balance,
                positions_value=equity - self.trader.balance,
            )
        )

    def _calculate_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        total_candles: int,
        execution_time: float,
    ) -> BacktestResult:
        """Calculate final backtest metrics."""
        trades = self.trader.trade_history
        final_balance = self.trader.balance

        # Get final equity (assuming no open positions at end)
        final_equity = final_balance

        # P&L
        pnl = final_balance - self.config.initial_balance
        pnl_pct = (pnl / self.config.initial_balance) * 100

        # Win rate
        winning = sum(1 for t in trades if t.pnl > 0)
        win_rate = (winning / len(trades) * 100) if trades else 0

        # Max drawdown from equity curve
        max_drawdown, max_dd_duration = self._calculate_drawdown()

        # Sharpe ratio (simplified - assumes risk-free rate = 0)
        sharpe = self._calculate_sharpe()

        # Profit factor
        gross_profit = sum(t.pnl for t in trades if t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in trades if t.pnl < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        return BacktestResult(
            config=self.config,
            trades=trades,
            final_balance=final_balance,
            final_equity=final_equity,
            pnl=pnl,
            pnl_pct=pnl_pct,
            win_rate=win_rate,
            max_drawdown=max_drawdown,
            max_drawdown_duration=max_dd_duration,
            sharpe_ratio=sharpe,
            profit_factor=profit_factor,
            signals_generated=self._signals_generated,
            ai_calls_made=self._ai_calls,
            execution_time_seconds=execution_time,
            start_time=start_time,
            end_time=end_time,
            total_candles=total_candles,
        )

    def _calculate_drawdown(self) -> tuple[float, float]:
        """Calculate max drawdown and duration from equity curve."""
        if not self._equity_curve:
            return 0.0, 0.0

        peak = self._equity_curve[0].equity
        max_dd = 0.0
        dd_start: datetime | None = None
        max_dd_duration = 0.0

        for point in self._equity_curve:
            if point.equity > peak:
                # New peak - reset drawdown tracking
                peak = point.equity
                if dd_start is not None:
                    duration = (point.timestamp - dd_start).total_seconds()
                    max_dd_duration = max(max_dd_duration, duration)
                dd_start = None
            else:
                # In drawdown
                dd = (peak - point.equity) / peak * 100
                max_dd = max(max_dd, dd)
                if dd_start is None:
                    dd_start = point.timestamp

        return max_dd, max_dd_duration

    def _calculate_sharpe(self) -> float:
        """Calculate Sharpe ratio from equity curve."""
        if len(self._equity_curve) < 2:
            return 0.0

        # Calculate returns
        returns = []
        for i in range(1, len(self._equity_curve)):
            prev_equity = self._equity_curve[i - 1].equity
            curr_equity = self._equity_curve[i].equity
            if prev_equity > 0:
                returns.append((curr_equity - prev_equity) / prev_equity)

        if not returns:
            return 0.0

        # Mean and std of returns
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        std_return = variance**0.5

        if std_return == 0:
            return 0.0

        # Annualize (assuming 1-minute candles)
        # 525600 minutes per year
        annualization_factor = (525600 / len(returns)) ** 0.5

        return float((mean_return / std_return) * annualization_factor)

    async def run(self) -> BacktestResult:
        """
        Run the backtest.

        Returns:
            BacktestResult with performance metrics
        """
        start_time = time.time()
        logger.info(f"Starting backtest: {self.config.data_source}")

        # Load historical data
        source = self._load_data()
        logger.info(f"Loaded {source.candle_count} candles for {source.coin}")

        candle_count = 0
        first_timestamp: datetime | None = None
        last_timestamp: datetime | None = None

        # Process each candle
        for update in source.stream():
            # Track time range
            if first_timestamp is None:
                first_timestamp = update.timestamp
            last_timestamp = update.timestamp

            # Convert to candle and add to buffer
            candle = self._price_update_to_candle(update)
            self._add_candle(update.coin, candle)
            self._all_candles.append(candle)  # Track for breakout analysis
            candle_count += 1

            # Current prices dict
            prices = {update.coin: update.close}

            # Check exits first (stop-loss, take-profit, trailing)
            self.position_manager.check_exits(prices)

            # Skip signal generation during warm-up
            if candle_count < self.config.min_candles_for_signals:
                continue

            # Get candles for this coin
            candles = self._get_candles(update.coin)

            # Process through signal aggregator
            new_signals = self.aggregator.process_candle(update.coin, candles)
            self._signals_generated += len(new_signals)

            # Track all signals with candle index for breakout analysis (before filtering)
            for sig in new_signals:
                self._all_signals.append((candle_count - 1, sig))

            # Filter through validator (removes historically inaccurate signals)
            new_signals = [s for s in new_signals if self.validator.should_pass(s)]

            # If we have signals and no position, evaluate
            if new_signals and not self.position_manager.has_position(update.coin):
                plan = await self._evaluate_signals(new_signals, update.coin, update.close)

                if plan and plan.is_actionable:
                    self.position_manager.open_position(plan, update.close)

            # Record equity periodically (every 10 candles to reduce memory)
            if candle_count % 10 == 0:
                self._record_equity(update.timestamp, prices)

        # Close any remaining positions
        if last_timestamp:
            final_prices = {source.coin: source._candles[-1]["close"]}
            final_prices = {source.coin: float(source._candles[-1]["close"])}
            self.position_manager.close_all(final_prices)

        execution_time = time.time() - start_time

        # Calculate and return results
        result = self._calculate_metrics(
            start_time=first_timestamp or datetime.now(),
            end_time=last_timestamp or datetime.now(),
            total_candles=candle_count,
            execution_time=execution_time,
        )

        # Run breakout analysis
        analyzer = BreakoutAnalyzer()
        result.breakout_analysis = analyzer.analyze(self._all_candles, self._all_signals)

        # Record signal outcomes in validator for future filtering
        self._record_signal_outcomes(result.breakout_analysis)

        # Include signal accuracy report in results
        result.signal_accuracy_report = self.validator.get_accuracy_report()

        logger.info(
            f"Backtest complete: {result.total_trades} trades, "
            f"P&L: {result.pnl_pct:+.2f}%, "
            f"Runtime: {execution_time:.1f}s"
        )

        return result

    async def _evaluate_signals(
        self,
        signals: list[Signal],
        coin: str,
        current_price: float,
    ) -> TradePlan | None:
        """
        Evaluate signals and decide on action.

        Args:
            signals: List of detected signals
            coin: Coin being evaluated
            current_price: Current price

        Returns:
            TradePlan if action should be taken
        """
        if not self.config.ai_enabled:
            # Signals-only mode - create simple plan from strongest signal
            return self._signals_to_plan(signals, coin, current_price)

        # AI-enabled mode
        brain = await self._get_brain()
        context = self._calculate_market_context(coin, current_price)

        # Get current positions from paper trader
        positions = self.trader.positions

        plan = await brain.evaluate_signals(signals, positions, context)
        self._ai_calls += 1

        return plan

    def _signals_to_plan(
        self,
        signals: list[Signal],
        coin: str,
        current_price: float,
    ) -> TradePlan | None:
        """
        Convert signals directly to a trade plan (no AI).

        Uses simple consensus from the provided signals and persona's risk params.
        """
        if not signals:
            return None

        # Calculate consensus directly from provided signals (not time-based query)
        long_strength = sum(s.strength for s in signals if s.direction == "LONG")
        short_strength = sum(s.strength for s in signals if s.direction == "SHORT")

        if long_strength > short_strength:
            direction = "LONG"
        elif short_strength > long_strength:
            direction = "SHORT"
        else:
            return TradePlan.wait(coin, "No signal consensus")

        # Get persona for risk params
        persona = get_persona(self.config.persona_name)

        # Calculate stops using persona's risk params
        context = self._calculate_market_context(coin, current_price)
        atr_value = context.atr

        if direction == "LONG":
            stop_loss = current_price - (atr_value * persona.risk_params.stop_loss_atr_multiplier)
            take_profit = current_price + (
                atr_value * persona.risk_params.take_profit_atr_multiplier
            )
            trail_activation = current_price * (1 + persona.risk_params.trail_activation_pct / 100)
        else:
            stop_loss = current_price + (atr_value * persona.risk_params.stop_loss_atr_multiplier)
            take_profit = current_price - (
                atr_value * persona.risk_params.take_profit_atr_multiplier
            )
            trail_activation = current_price * (1 - persona.risk_params.trail_activation_pct / 100)

        # Calculate average signal strength
        avg_strength = sum(s.strength for s in signals) / len(signals)

        return TradePlan(
            action=direction,  # type: ignore[arg-type]
            coin=coin,
            size_pct=persona.risk_params.max_position_pct * avg_strength,
            stop_loss=stop_loss,
            take_profit=take_profit,
            trail_activation=trail_activation,
            trail_distance_pct=persona.risk_params.trail_distance_pct,
            confidence=int(avg_strength * 10),
            reason=f"Signal consensus: {direction}",
            signals_considered=[f"{s.signal_type.value}:{s.direction}" for s in signals],
        )

    def _record_signal_outcomes(self, analysis: BreakoutAnalysis | None) -> None:
        """
        Record signal outcomes in validator based on breakout analysis.

        This updates the validator's accuracy tracking so it can filter
        historically inaccurate signals in future runs.

        Args:
            analysis: Breakout analysis with signal matches
        """
        if not analysis or not analysis.matches:
            return

        for match in analysis.matches:
            # Convert breakout direction to expected signal direction
            breakout_direction = match.breakout.direction  # "UP" or "DOWN"
            self.validator.record_outcome(match.signal, breakout_direction)

        logger.debug(
            f"Recorded {len(analysis.matches)} signal outcomes. "
            f"Validator report: {self.validator.get_accuracy_report()}"
        )

    def reset(self) -> None:
        """Reset the engine for a new backtest."""
        self.trader.reset()
        self.position_manager = PositionManager(self.trader)
        self.aggregator.reset()
        self.validator.reset()
        self._candle_buffers.clear()
        self._signals_generated = 0
        self._ai_calls = 0
        self._equity_curve.clear()
        self._all_candles.clear()
        self._all_signals.clear()


async def run_backtest(
    data_source: str,
    ai_enabled: bool = True,
    persona_name: str = "balanced",
    initial_balance: float = 10000.0,
) -> BacktestResult:
    """
    Convenience function to run a backtest with common defaults.

    Args:
        data_source: Path to CSV file
        ai_enabled: Whether to use AI for decisions
        persona_name: Name of persona to use
        initial_balance: Starting balance

    Returns:
        BacktestResult
    """
    config = BacktestConfig(
        data_source=data_source,
        coins=[],  # Will be derived from data
        initial_balance=initial_balance,
        persona_name=persona_name,
        ai_enabled=ai_enabled,
    )

    engine = BacktestEngine(config)
    return await engine.run()
