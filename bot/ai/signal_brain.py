"""
Signal Brain - AI decision maker for the 3-layer backtesting architecture.

Receives signals from Layer 2 (Signal Detectors) and outputs TradePlans
based on the configured strategy's trading style and risk parameters.
"""

import logging
from typing import TYPE_CHECKING

from bot.ai.models import AccountContext, MarketContext, TradePlan
from bot.ai.ollama_client import OllamaClient
from bot.strategies import Strategy, get_strategy

if TYPE_CHECKING:
    from bot.ai.decision_logger import AIDecisionLogger
    from bot.signals.base import Signal
    from bot.simulation.models import Position

logger = logging.getLogger(__name__)


# System prompt for Position Sizing Strategist role
TRADING_SYSTEM_PROMPT = """You are a POSITION SIZING STRATEGIST, not a chatbot or assistant.

CRITICAL RULES:
1. You MUST output ONLY the exact format requested - no explanations, no preamble
2. Your response MUST start with "POSITION_MULTIPLIER:"
3. The trade direction (LONG/SHORT) is already decided - you decide HOW MUCH to risk
4. Your job is to adjust position size based on account goals and current progress

You will receive account context and must decide the appropriate position size multiplier."""

# Position Sizing Strategist prompt - AI decides HOW MUCH to risk, not IF to trade
SIGNAL_EVALUATION_PROMPT = """You are a Position Sizing Strategist for a {strategy_name} strategy.

{strategy_prompt}

## TRADE SETUP (Direction already decided)
Direction: {direction}
Signal Score: {winning_score:.2f} (threshold: {threshold})
Volatility: {volatility_level}

## SIGNALS
{signals}

## ACCOUNT CONTEXT
{account_context}

## YOUR JOB
The signals have triggered a {direction} trade. You must decide the POSITION SIZE.

Consider:
1. Are we ahead or behind on our goal? (Adjust aggression)
2. How strong is this signal setup? (Higher score = more confidence)
3. What's the market volatility? (Higher vol = smaller size)
4. How much time do we have left? (Less time + behind = more aggressive OR accept failure)

POSITION_MULTIPLIER guidelines:
- 0.5x = Conservative (protect gains, or weak setup)
- 1.0x = Normal (on track, decent setup)
- 1.5x = Aggressive (behind schedule, strong setup)
- 2.0x = Very aggressive (last chance, excellent setup)
- 0.0x = Skip trade (goal reached, or setup too risky given account state)

OUTPUT FORMAT (start with POSITION_MULTIPLIER:):
POSITION_MULTIPLIER: [0.0 - 2.0]
REASONING: [One sentence - why this size given account state and setup]"""

# Fallback prompt when no account goal is set (simple confirmation mode)
SIMPLE_EVALUATION_PROMPT = """Strategy: "{strategy_name}"

## TRADE SETUP
Direction: {direction}
Signal Score: {winning_score:.2f} (threshold: {threshold})
Volatility: {volatility_level}

## SIGNALS
{signals}

## YOUR JOB
The signals suggest going {direction}. Confirm or adjust:

OUTPUT FORMAT:
POSITION_MULTIPLIER: [0.5 - 1.5]
REASONING: [One sentence]

Guidelines:
- 1.0 = Normal size (signals look good)
- 0.5-0.8 = Reduced size (something off, high volatility)
- 1.2-1.5 = Increased size (strong alignment, low volatility)"""


# Legacy prompt for backward compatibility (kept but not used)
LEGACY_SIGNAL_EVALUATION_PROMPT = """Strategy: "{strategy_name}"

{strategy_prompt}

## SIGNALS DETECTED
{signals}

## CURRENT POSITIONS
{positions}

## MARKET CONTEXT
- ATR (14-period): ${atr_value:.2f} ({atr_pct:.2f}% of price)
- Current volatility: {volatility_level}

## YOUR TASK
Based on these signals and your strategy, decide:

1. ACTION: Should we LONG, SHORT, or WAIT?
2. SIZE: Position size as % of balance (max {max_position_pct}%)
3. STOP_LOSS: Price level for stop loss
4. TAKE_PROFIT: Price level for take profit
5. TRAIL_ACTIVATION: Price level to activate trailing stop
6. TRAIL_DISTANCE: Trailing stop distance as % of price
7. CONFIDENCE: Your confidence in this trade (1-10)
8. REASON: One sentence explaining your decision

OUTPUT FORMAT (start your response with ACTION:):
ACTION: [LONG/SHORT/WAIT]
SIZE: [0-{max_position_pct}]
STOP_LOSS: [price]
TAKE_PROFIT: [price]
TRAIL_ACTIVATION: [price]
TRAIL_DISTANCE: [0.1-2.0]
CONFIDENCE: [1-10]
REASON: [your reasoning]

RULES:
- Only act if signals align with strategy
- Consider volatility for stop placement
- If uncertain, output ACTION: WAIT"""


class SignalBrain:
    """
    AI Position Sizing Strategist for the 3-layer backtesting architecture.

    The brain receives signals from multiple detectors and decides HOW MUCH
    to risk on each trade based on:
    - Signal strength and quality
    - Account state and goals
    - Market volatility
    - Progress toward trading objectives

    The direction (LONG/SHORT) is determined by weighted signal scoring.
    The AI's job is to decide position SIZE, not direction.
    """

    def __init__(
        self,
        strategy: Strategy,
        ollama_client: OllamaClient,
        decision_logger: "AIDecisionLogger | None" = None,
    ) -> None:
        """
        Initialize the signal brain.

        Args:
            strategy: Trading strategy that defines decision-making style
            ollama_client: Client for AI inference
            decision_logger: Optional logger to track AI decisions for analysis
        """
        self.strategy = strategy
        self.ollama = ollama_client
        self.decision_logger = decision_logger
        self._call_count = 0
        self._last_decision_id: str | None = None  # Track for linking outcomes

    async def evaluate_signals(
        self,
        signals: list["Signal"],
        current_positions: dict[str, "Position"],
        market_context: MarketContext,
        account_context: AccountContext | None = None,
    ) -> TradePlan | None:
        """
        Evaluate signals and decide on a trade plan with AI-determined position sizing.

        Args:
            signals: List of signals to evaluate
            current_positions: Current open positions by coin
            market_context: Market context with volatility info
            account_context: Account state and goals for position sizing decisions

        Returns:
            TradePlan if trade should be taken, None if no valid response
        """
        # Pre-filter signals based on strategy's signal_weights
        valid_signals = self._filter_signals(signals, market_context.coin)

        if not valid_signals:
            logger.debug(f"No valid signals for {market_context.coin}")
            return TradePlan.wait(market_context.coin, "No signals meet criteria")

        # Calculate weighted scores and check threshold
        long_score, short_score = self._calculate_weighted_scores(valid_signals)
        meets_threshold, direction = self._meets_threshold(long_score, short_score)

        if not meets_threshold:
            logger.debug(
                f"Signal scores below threshold: LONG={long_score:.2f}, "
                f"SHORT={short_score:.2f}, threshold={self.strategy.signal_threshold}"
            )
            return TradePlan.wait(
                market_context.coin,
                f"Weighted score ({max(long_score, short_score):.2f}) below threshold ({self.strategy.signal_threshold})",
            )

        logger.info(
            f"Signal threshold met: {direction} score={max(long_score, short_score):.2f} "
            f">= {self.strategy.signal_threshold}"
        )

        # Get signal names for the plan
        signal_names = [f"{s.signal_type.value}:{s.direction}" for s in valid_signals]
        winning_score = max(long_score, short_score)

        # AI Position Sizing - ask AI to determine position size
        prompt = self._format_prompt(
            signals=valid_signals,
            positions=current_positions,
            context=market_context,
            direction=direction,
            winning_score=winning_score,
            account_context=account_context,
        )

        try:
            response_text, tokens, response_time = await self.ollama.analyze(
                prompt=prompt,
                temperature=0.2,  # Slightly higher for position sizing creativity
                max_tokens=100,
                system_prompt=TRADING_SYSTEM_PROMPT,
            )
            self._call_count += 1

            logger.debug(f"AI response ({tokens} tokens, {response_time:.0f}ms): {response_text}")

            # Parse position sizing response
            position_multiplier, reasoning = self._parse_position_sizing_response(response_text)

            # If AI says 0.0x, skip the trade
            if position_multiplier <= 0:
                logger.info(f"AI SKIPPED {direction}: {reasoning}")

                # Log the skip decision
                if self.decision_logger:
                    self._last_decision_id = self.decision_logger.log_decision(
                        signals=valid_signals,
                        market_context=market_context,
                        weighted_score=winning_score,
                        threshold=self.strategy.signal_threshold,
                        direction=direction,
                        confirmed=False,
                        confidence=0,
                        reason=reasoning,
                        mode="AI_SIZING",
                        signal_weights=self.strategy.signal_weights,
                    )

                return TradePlan.wait(market_context.coin, f"AI skipped: {reasoning}")

            logger.info(f"AI SIZED {direction} at {position_multiplier:.1f}x: {reasoning}")

            # Log the position sizing decision
            if self.decision_logger:
                self._last_decision_id = self.decision_logger.log_decision(
                    signals=valid_signals,
                    market_context=market_context,
                    weighted_score=winning_score,
                    threshold=self.strategy.signal_threshold,
                    direction=direction,
                    confirmed=True,
                    confidence=int(position_multiplier * 5),  # Convert multiplier to confidence
                    reason=reasoning,
                    mode="AI_SIZING",
                    signal_weights=self.strategy.signal_weights,
                )

            # Create plan with AI-determined position size
            plan = self._create_plan_from_signals(
                direction=direction,
                coin=market_context.coin,
                confidence=int(position_multiplier * 5),
                reason=reasoning,
                signal_names=signal_names,
                position_multiplier=position_multiplier,
            )

            # Validate the plan with AI-determined position multiplier
            return self._validate_plan(
                plan, market_context, valid_signals, position_multiplier=position_multiplier
            )

        except Exception as e:
            logger.error(f"AI evaluation failed: {e}")
            return None

    def _parse_position_sizing_response(self, response: str) -> tuple[float, str]:
        """
        Parse the AI position sizing response.

        Args:
            response: Raw AI response text

        Returns:
            Tuple of (position_multiplier, reasoning)
        """
        lines = response.strip().split("\n")
        data: dict[str, str] = {}

        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                data[key.strip().upper()] = value.strip()

        # Parse POSITION_MULTIPLIER
        try:
            multiplier_str = data.get("POSITION_MULTIPLIER", "1.0")
            # Handle formats like "1.5x" or "1.5"
            multiplier_str = multiplier_str.lower().replace("x", "").strip()
            position_multiplier = float(multiplier_str)
            # Clamp to valid range
            position_multiplier = max(0.0, min(2.0, position_multiplier))
        except ValueError:
            position_multiplier = 1.0

        # Parse REASONING
        reasoning = data.get("REASONING", data.get("REASON", "No reasoning provided"))

        return position_multiplier, reasoning

    def _create_plan_from_signals(
        self,
        direction: str,
        coin: str,
        confidence: int,
        reason: str,
        signal_names: list[str],
        position_multiplier: float = 1.0,  # noqa: ARG002 - reserved for future use
    ) -> TradePlan:
        """
        Create a TradePlan from the signal direction.

        Risk parameters (stops, size) are set to defaults here
        and will be adjusted by _validate_plan().

        Args:
            direction: LONG or SHORT
            coin: Coin symbol
            confidence: Confidence level 1-10
            reason: Reason for the trade
            signal_names: List of signal names
            position_multiplier: AI-determined multiplier for position size (0.0-2.0)

        Returns:
            TradePlan with direction set, risk params to be filled by validation
        """
        return TradePlan(
            action=direction,  # type: ignore[arg-type]
            coin=coin,
            size_pct=0,  # Will be set by _validate_plan
            stop_loss=0,  # Will be set by _validate_plan
            take_profit=0,  # Will be set by _validate_plan
            trail_activation=0,
            trail_distance_pct=0.3,
            confidence=confidence,
            reason=reason,
            signals_considered=signal_names,
        )

    def _filter_signals(self, signals: list["Signal"], coin: str) -> list["Signal"]:
        """
        Filter signals based on strategy's signal_weights.

        Args:
            signals: All detected signals
            coin: Coin to filter for

        Returns:
            Signals that have a weight in the strategy
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

    def _calculate_weighted_scores(self, signals: list["Signal"]) -> tuple[float, float]:
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

    def _meets_threshold(self, long_score: float, short_score: float) -> tuple[bool, str]:
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

    def _format_prompt(
        self,
        signals: list["Signal"],
        positions: dict[str, "Position"],  # noqa: ARG002 - reserved for position context
        context: MarketContext,
        direction: str,
        winning_score: float,
        account_context: AccountContext | None = None,
    ) -> str:
        """
        Format the prompt for AI position sizing.

        Args:
            signals: Signals to include
            positions: Current positions
            context: Market context
            direction: LONG or SHORT (pre-determined by threshold)
            winning_score: The winning weighted score
            account_context: Account state and goals for position sizing

        Returns:
            Formatted prompt string
        """
        # Format signals with their weights
        signal_lines = []
        for s in signals:
            weight = self.strategy.signal_weights.get(s.signal_type, 0.0)
            signal_lines.append(
                f"  - {s.signal_type.value}: {s.direction} "
                f"(strength: {s.strength:.2f}, weight: {weight:.1f})"
            )

        signals_str = "\n".join(signal_lines) if signal_lines else "  None"

        # Format account context
        if account_context and account_context.has_goal:
            account_context_str = self._format_account_context(account_context)
        else:
            account_context_str = "No account goal set. Use standard position sizing."

        # Build the prompt
        return SIGNAL_EVALUATION_PROMPT.format(
            strategy_prompt=self.strategy.prompt,
            strategy_name=self.strategy.name,
            direction=direction,
            winning_score=winning_score,
            threshold=self.strategy.signal_threshold,
            signals=signals_str,
            volatility_level=context.volatility_level,
            account_context=account_context_str,
        )

    def _format_account_context(self, account_context: AccountContext) -> str:
        """
        Format account context for the AI prompt.

        Args:
            account_context: Account state and goals

        Returns:
            Formatted account context string
        """
        lines = [
            f"Current Balance: ${account_context.current_balance:,.2f}",
            f"Starting Balance: ${account_context.initial_balance:,.2f}",
            f"Current P&L: ${account_context.pnl:+,.2f} ({account_context.pnl_pct:+.1f}%)",
        ]

        if account_context.has_goal:
            lines.extend(
                [
                    "",
                    f"GOAL: ${account_context.account_goal:,.2f}",
                    f"Timeframe: {account_context.goal_timeframe_days} days",
                    f"Days Elapsed: {account_context.days_elapsed}",
                    f"Days Remaining: {account_context.days_remaining}",
                    "",
                    f"Goal Progress: {account_context.goal_progress_pct:.1f}%",
                    f"Time Progress: {account_context.time_progress_pct:.1f}%",
                    f"Pace Status: {account_context.pace_status.upper()}",
                ]
            )

            req_daily = account_context.required_daily_return_pct
            if req_daily is not None:
                lines.append(f"Required Daily Return: {req_daily:.2f}%")

        lines.append("")
        lines.append(f"Base Position Size: {account_context.base_position_pct:.1f}%")

        return "\n".join(lines)

    def _validate_plan(
        self,
        plan: TradePlan,
        context: MarketContext,
        signals: list["Signal"] | None = None,  # noqa: ARG002 - reserved for signal-based stops
        position_multiplier: float = 1.0,
    ) -> TradePlan:
        """
        Validate and adjust the trade plan.

        POSITION SIZE: Determined SOLELY by AI multiplier.
        The AI receives the base position size and decides the multiplier.
        No deterministic adjustment - AI is the only decider.

        STOPS: Determined by ATR and volatility (deterministic).
        AI does not decide stops - that's pure risk management math.

        Args:
            plan: Parsed trade plan
            context: Market context
            signals: Original signals (for stop calculation only)
            position_multiplier: AI-determined multiplier (0.0-2.0)

        Returns:
            Validated plan with AI-determined size and ATR-based stops
        """
        # POSITION SIZE: AI decides via multiplier
        # Base is strategy's max_position_pct, AI scales it 0x-2x
        base_position = self.strategy.risk.max_position_pct
        plan.size_pct = base_position * position_multiplier
        # Hard cap at 2x base (AI can go aggressive, but not crazy)
        plan.size_pct = min(plan.size_pct, base_position * 2.0)

        # STOPS: Deterministic ATR-based calculation
        # This is pure math, not competing with AI
        if plan.is_actionable:
            # Volatility adjustment for stops only (not position size)
            vol_factor = {"high": 1.5, "medium": 1.0, "low": 0.7}.get(context.volatility_level, 1.0)

            atr_sl = context.atr * self.strategy.risk.stop_loss_atr_multiplier * vol_factor
            atr_tp = context.atr * self.strategy.risk.take_profit_atr_multiplier * vol_factor

            if plan.is_long:
                plan.stop_loss = context.current_price - atr_sl
                plan.take_profit = context.current_price + atr_tp
            else:
                plan.stop_loss = context.current_price + atr_sl
                plan.take_profit = context.current_price - atr_tp

            logger.debug(
                f"Plan validated: size={plan.size_pct:.1f}% "
                f"(base {base_position:.1f}% x {position_multiplier:.1f}x), "
                f"SL={atr_sl:.2f}, TP={atr_tp:.2f}"
            )

        return plan

    @property
    def call_count(self) -> int:
        """Number of AI calls made."""
        return self._call_count

    @property
    def last_decision_id(self) -> str | None:
        """Get the last decision ID for linking to trade outcomes."""
        return self._last_decision_id

    def reset_metrics(self) -> None:
        """Reset call count and AI metrics."""
        self._call_count = 0
        self._last_decision_id = None
        self.ollama.reset_metrics()

    def get_metrics_summary(self) -> dict:
        """Get a summary of AI usage metrics."""
        return {
            "ai_calls": self._call_count,
            "ollama_metrics": {
                "total_tokens": self.ollama.metrics.total_tokens,
                "avg_response_ms": self.ollama.metrics.avg_response_time_ms,
            },
        }


def create_signal_brain(
    strategy_name: str = "momentum_based",
    ollama_model: str = "mistral",
    ollama_url: str = "http://localhost:11434",
    decision_logger: "AIDecisionLogger | None" = None,
) -> SignalBrain:
    """
    Factory function to create a SignalBrain with a strategy.

    Args:
        strategy_name: Name of strategy (momentum_based, momentum_macd,
                       rsi_based, multi_signal)
        ollama_model: Ollama model to use
        ollama_url: Ollama server URL
        decision_logger: Optional logger to track AI decisions for analysis.
                        When provided, all decisions are logged for post-backtest
                        analysis of confidence calibration, pattern accuracy, etc.

    Returns:
        Configured SignalBrain instance

    Example:
        # Create a signal brain
        brain = create_signal_brain("momentum_based")

        # With different model
        brain = create_signal_brain("multi_signal", ollama_model="llama2")

        # With decision logging for analysis
        from bot.ai.decision_logger import AIDecisionLogger
        logger = AIDecisionLogger(strategy_name="momentum_based")
        brain = create_signal_brain("momentum_based", decision_logger=logger)
    """
    strategy = get_strategy(strategy_name)
    ollama = OllamaClient(base_url=ollama_url, model=ollama_model)

    return SignalBrain(
        strategy=strategy,
        ollama_client=ollama,
        decision_logger=decision_logger,
    )
