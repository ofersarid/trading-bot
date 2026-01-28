"""
Signal Brain - AI decision maker for the 3-layer backtesting architecture.

Receives signals from Layer 2 (Signal Detectors) and outputs TradePlans
based on the configured strategy's trading style and risk parameters.
"""

import logging
from typing import TYPE_CHECKING

from bot.ai.models import MarketContext, TradePlan
from bot.ai.ollama_client import OllamaClient
from bot.strategies import Strategy, get_strategy

if TYPE_CHECKING:
    from bot.signals.base import Signal
    from bot.simulation.models import Position

logger = logging.getLogger(__name__)


# System prompt to enforce trading role - prevents "I'm an assistant" responses
TRADING_SYSTEM_PROMPT = """You are a TRADING SIGNAL FILTER, not a chatbot or assistant.

CRITICAL RULES:
1. You MUST output ONLY the exact format requested - no explanations, no preamble
2. Your response MUST start with "CONFIRM:" followed by YES or NO
3. You are evaluating a pre-calculated trade setup - confirm or reject it
4. Risk parameters (stops, size) are handled separately - focus ONLY on setup quality

You will receive market signals and must evaluate if this is a quality trade setup."""

# Simplified prompt template - focused on judgment, not parameter calculation
SIGNAL_EVALUATION_PROMPT = """Strategy: "{strategy_name}"

{strategy_prompt}

## TRADE SETUP TO EVALUATE
Direction: {direction}
Weighted Score: {winning_score:.2f} (threshold: {threshold})

## SIGNALS DETECTED
{signals}

## CURRENT POSITIONS
{positions}

## MARKET CONTEXT
- Volatility: {volatility_level}

## YOUR JOB
The signals suggest going {direction}. Evaluate this setup:

1. Do these signals tell a coherent story, or are they contradictory?
2. Is anything suspicious (e.g., strong RSI but weak momentum)?
3. Would a disciplined trader take this trade?

OUTPUT FORMAT (start with CONFIRM:):
CONFIRM: [YES/NO]
CONFIDENCE: [1-10]
REASON: [One sentence - what makes this setup good or questionable]

Guidelines:
- YES = Signals align well, clean setup, take the trade
- NO = Something off, contradictory signals, or low quality setup"""


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
    AI decision maker that evaluates signals and produces trade plans.

    The brain receives signals from multiple detectors, considers the
    current market context and positions, and decides whether to trade
    based on the strategy's trading style.

    Supports two modes:
    - use_ai=True: AI confirms/rejects trades based on signal quality
    - use_ai=False: Bypass AI, auto-confirm trades that meet threshold (for A/B testing)
    """

    def __init__(
        self,
        strategy: Strategy,
        ollama_client: OllamaClient,
        use_ai: bool = True,
    ) -> None:
        """
        Initialize the signal brain.

        Args:
            strategy: Trading strategy that defines decision-making style
            ollama_client: Client for AI inference
            use_ai: If True, use AI for trade confirmation. If False, bypass AI
                    and auto-confirm trades that meet signal threshold.
        """
        self.strategy = strategy
        self.ollama = ollama_client
        self.use_ai = use_ai
        self._call_count = 0
        self._bypass_count = 0  # Track trades that bypassed AI

    async def evaluate_signals(
        self,
        signals: list["Signal"],
        current_positions: dict[str, "Position"],
        market_context: MarketContext,
    ) -> TradePlan | None:
        """
        Evaluate signals and decide on a trade plan.

        Args:
            signals: List of signals to evaluate
            current_positions: Current open positions by coin
            market_context: Market context with volatility info

        Returns:
            TradePlan if AI decides to act, None if no valid response
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

        # MODE: AI Bypass - auto-confirm trades that meet threshold
        if not self.use_ai:
            self._bypass_count += 1
            logger.info(f"AI BYPASS: Auto-confirming {direction} (score={winning_score:.2f})")

            # Create plan directly from threshold result
            plan = self._create_plan_from_signals(
                direction=direction,
                coin=market_context.coin,
                confidence=7,  # Default confidence for bypass mode
                reason=f"AI bypass: threshold met (score={winning_score:.2f})",
                signal_names=signal_names,
            )

            # Apply risk management
            return self._validate_plan(plan, market_context, valid_signals)

        # MODE: AI Confirmation - ask AI to confirm/reject the setup
        prompt = self._format_prompt(
            signals=valid_signals,
            positions=current_positions,
            context=market_context,
            direction=direction,
            winning_score=winning_score,
        )

        try:
            response_text, tokens, response_time = await self.ollama.analyze(
                prompt=prompt,
                temperature=0.1,  # Lower temperature for more deterministic output
                max_tokens=100,  # Reduced - only need CONFIRM/CONFIDENCE/REASON
                system_prompt=TRADING_SYSTEM_PROMPT,
            )
            self._call_count += 1

            logger.debug(f"AI response ({tokens} tokens, {response_time:.0f}ms): {response_text}")

            # Parse simplified response
            confirmed, confidence, reason = self._parse_confirmation_response(response_text)

            if not confirmed:
                logger.info(f"AI REJECTED {direction}: {reason}")
                return TradePlan.wait(market_context.coin, f"AI rejected: {reason}")

            logger.info(f"AI CONFIRMED {direction} (confidence={confidence}): {reason}")

            # Create plan with AI's confidence
            plan = self._create_plan_from_signals(
                direction=direction,
                coin=market_context.coin,
                confidence=confidence,
                reason=reason,
                signal_names=signal_names,
            )

            # Validate the plan with dynamic risk management
            return self._validate_plan(plan, market_context, valid_signals)

        except Exception as e:
            logger.error(f"AI evaluation failed: {e}")
            return None

    def _parse_confirmation_response(self, response: str) -> tuple[bool, int, str]:
        """
        Parse the simplified AI confirmation response.

        Args:
            response: Raw AI response text

        Returns:
            Tuple of (confirmed, confidence, reason)
        """
        lines = response.strip().split("\n")
        data: dict[str, str] = {}

        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                data[key.strip().upper()] = value.strip()

        # Parse CONFIRM
        confirm_str = data.get("CONFIRM", "NO").upper()
        confirmed = confirm_str in ("YES", "Y", "TRUE", "1")

        # Parse CONFIDENCE
        try:
            confidence = int(data.get("CONFIDENCE", "5"))
            confidence = max(1, min(10, confidence))
        except ValueError:
            confidence = 5

        # Parse REASON
        reason = data.get("REASON", "No reason provided")

        return confirmed, confidence, reason

    def _create_plan_from_signals(
        self,
        direction: str,
        coin: str,
        confidence: int,
        reason: str,
        signal_names: list[str],
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
        positions: dict[str, "Position"],
        context: MarketContext,
        direction: str,
        winning_score: float,
    ) -> str:
        """
        Format the simplified prompt for AI confirmation.

        Args:
            signals: Signals to include
            positions: Current positions
            context: Market context
            direction: LONG or SHORT (pre-determined by threshold)
            winning_score: The winning weighted score

        Returns:
            Formatted prompt string
        """
        # Format signals with their weights - simplified
        signal_lines = []
        for s in signals:
            weight = self.strategy.signal_weights.get(s.signal_type, 0.0)
            signal_lines.append(
                f"  - {s.signal_type.value}: {s.direction} "
                f"(strength: {s.strength:.2f}, weight: {weight:.1f})"
            )

        signals_str = "\n".join(signal_lines) if signal_lines else "  None"

        # Format positions - simplified
        position_lines = []
        for coin, pos in positions.items():
            if coin == context.coin:
                pnl = pos.unrealized_pnl_percent(context.current_price)
                position_lines.append(f"  - {coin}: {pos.side.value.upper()} (P&L: {pnl:+.2f}%)")
        positions_str = "\n".join(position_lines) if position_lines else "  No open positions"

        # Build the simplified prompt
        return SIGNAL_EVALUATION_PROMPT.format(
            strategy_prompt=self.strategy.prompt,
            strategy_name=self.strategy.name,
            direction=direction,
            winning_score=winning_score,
            threshold=self.strategy.signal_threshold,
            signals=signals_str,
            positions=positions_str,
            volatility_level=context.volatility_level,
        )

    def _validate_plan(
        self,
        plan: TradePlan,
        context: MarketContext,
        signals: list["Signal"] | None = None,
    ) -> TradePlan:
        """
        Validate and adjust the trade plan with DYNAMIC risk management.

        Risk is adjusted based on:
        1. Signal strength (stronger signals → larger positions, tighter stops)
        2. Volatility (higher volatility → smaller positions, wider stops)
        3. Confidence (higher confidence → better risk/reward targets)

        Args:
            plan: Parsed trade plan
            context: Market context
            signals: Original signals for strength-based adjustments

        Returns:
            Validated (possibly adjusted) plan
        """
        # Check confidence threshold
        if plan.is_actionable and plan.confidence < self.strategy.min_confidence:
            logger.debug(
                f"Plan confidence {plan.confidence} below threshold "
                f"{self.strategy.min_confidence}, converting to WAIT"
            )
            return TradePlan.wait(plan.coin, f"Confidence too low ({plan.confidence})")

        # Calculate dynamic risk parameters
        avg_signal_strength = self._get_avg_signal_strength(signals)
        risk_params = self._calculate_dynamic_risk(avg_signal_strength, plan.confidence, context)

        # Apply dynamic position sizing
        plan.size_pct = min(risk_params["position_pct"], self.strategy.risk.max_position_pct)

        # Apply dynamic stops
        if plan.is_actionable:
            atr_sl = context.atr * risk_params["stop_multiplier"]
            atr_tp = context.atr * risk_params["tp_multiplier"]

            if plan.is_long:
                plan.stop_loss = context.current_price - atr_sl
                plan.take_profit = context.current_price + atr_tp
            else:
                plan.stop_loss = context.current_price + atr_sl
                plan.take_profit = context.current_price - atr_tp

            logger.debug(
                f"Dynamic risk: strength={avg_signal_strength:.2f}, "
                f"size={plan.size_pct:.1f}%, SL={risk_params['stop_multiplier']:.1f}x ATR, "
                f"TP={risk_params['tp_multiplier']:.1f}x ATR"
            )

        return plan

    def _get_avg_signal_strength(self, signals: list["Signal"] | None) -> float:
        """Calculate weighted average signal strength."""
        if not signals:
            return 0.5

        total_weight = 0.0
        weighted_sum = 0.0

        for s in signals:
            weight = self.strategy.signal_weights.get(s.signal_type, 0.0)
            weighted_sum += weight * s.strength
            total_weight += weight

        if total_weight == 0:
            return 0.5

        return weighted_sum / total_weight

    def _calculate_dynamic_risk(
        self,
        signal_strength: float,
        confidence: int,
        context: MarketContext,
    ) -> dict[str, float]:
        """
        Calculate dynamic risk parameters - CUT LOSSES FAST strategy.

        Key insight: At ~50% win rate, need avg_win > avg_loss.
        Use TIGHT stops to cut losers quickly.

        Returns:
            Dict with position_pct, stop_multiplier, tp_multiplier
        """
        base_position = self.strategy.risk.max_position_pct
        base_stop = self.strategy.risk.stop_loss_atr_multiplier
        base_tp = self.strategy.risk.take_profit_atr_multiplier

        # Volatility adjustment
        vol_factor = {"high": 0.6, "medium": 0.8, "low": 1.0}.get(context.volatility_level, 1.0)

        # Signal strength adjustments - VERY TIGHT STOPS to match signals-only performance
        if signal_strength >= 0.8:
            # Strong signal: moderate position, very tight stop
            position_pct = base_position * 0.7 * vol_factor
            stop_mult = base_stop * 0.4  # 60% tighter stop
            tp_mult = base_tp * 1.0
        elif signal_strength >= 0.5:
            # Medium signal: smaller position, tight stop
            position_pct = base_position * 0.5 * vol_factor
            stop_mult = base_stop * 0.5  # 50% tighter
            tp_mult = base_tp * 1.0
        else:
            # Weak signal: tiny position, tight stop
            position_pct = base_position * 0.3 * vol_factor
            stop_mult = base_stop * 0.6
            tp_mult = base_tp * 0.9

        # Confidence boost
        conf_factor = max(0, (confidence - 5)) / 5
        position_pct *= 1 + (conf_factor * 0.2)

        return {
            "position_pct": position_pct,
            "stop_multiplier": stop_mult,
            "tp_multiplier": tp_mult,
        }

    @property
    def call_count(self) -> int:
        """Number of AI calls made."""
        return self._call_count

    @property
    def bypass_count(self) -> int:
        """Number of trades that bypassed AI (when use_ai=False)."""
        return self._bypass_count

    def reset_metrics(self) -> None:
        """Reset call count and AI metrics."""
        self._call_count = 0
        self._bypass_count = 0
        self.ollama.reset_metrics()

    def get_metrics_summary(self) -> dict:
        """Get a summary of AI usage metrics for comparison."""
        return {
            "mode": "AI" if self.use_ai else "BYPASS",
            "ai_calls": self._call_count,
            "bypass_trades": self._bypass_count,
            "ollama_metrics": {
                "total_tokens": self.ollama.metrics.total_tokens,
                "avg_response_ms": self.ollama.metrics.avg_response_time_ms,
            },
        }


def create_signal_brain(
    strategy_name: str = "momentum_scalper",
    ollama_model: str = "mistral",
    ollama_url: str = "http://localhost:11434",
    use_ai: bool = True,
) -> SignalBrain:
    """
    Factory function to create a SignalBrain with a strategy.

    Args:
        strategy_name: Name of strategy (momentum_scalper, trend_follower,
                       mean_reversion, conservative)
        ollama_model: Ollama model to use
        ollama_url: Ollama server URL
        use_ai: If True (default), use AI for trade confirmation.
                If False, bypass AI and auto-confirm trades that meet threshold.
                Use False for A/B testing to compare AI vs no-AI performance.

    Returns:
        Configured SignalBrain instance

    Example:
        # With AI confirmation (default)
        brain = create_signal_brain("momentum_scalper")

        # Without AI (for A/B testing)
        brain = create_signal_brain("momentum_scalper", use_ai=False)

        # With different model
        brain = create_signal_brain("conservative", ollama_model="llama2")
    """
    strategy = get_strategy(strategy_name)
    ollama = OllamaClient(base_url=ollama_url, model=ollama_model)

    return SignalBrain(strategy=strategy, ollama_client=ollama, use_ai=use_ai)
