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
TRADING_SYSTEM_PROMPT = """You are a TRADING DECISION SYSTEM, not a chatbot or assistant.

CRITICAL RULES:
1. You MUST output ONLY the exact format requested - no explanations, no preamble
2. You ARE the decision maker - make definitive choices, never say "I can't" or "I don't"
3. Every response MUST start with "ACTION:" followed by LONG, SHORT, or WAIT
4. Never refuse to trade or explain what you would do - actually decide
5. If uncertain, output "ACTION: WAIT" with a reason - but always use the format

You will receive market signals and must output a trading decision in the specified format."""

# Prompt template for signal-based evaluation
SIGNAL_EVALUATION_PROMPT = """Strategy: "{strategy_name}"

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
    """

    def __init__(
        self,
        strategy: Strategy,
        ollama_client: OllamaClient,
    ) -> None:
        """
        Initialize the signal brain.

        Args:
            strategy: Trading strategy that defines decision-making style
            ollama_client: Client for AI inference
        """
        self.strategy = strategy
        self.ollama = ollama_client
        self._call_count = 0

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

        # Format the prompt
        prompt = self._format_prompt(
            signals=valid_signals,
            positions=current_positions,
            context=market_context,
            weighted_scores=(long_score, short_score),
        )

        # Query the AI with system prompt for role enforcement
        try:
            response_text, tokens, response_time = await self.ollama.analyze(
                prompt=prompt,
                temperature=0.1,  # Lower temperature for more deterministic output
                max_tokens=300,
                system_prompt=TRADING_SYSTEM_PROMPT,
            )
            self._call_count += 1

            logger.debug(
                f"AI response ({tokens} tokens, {response_time:.0f}ms): {response_text[:100]}..."
            )

            # Parse response into TradePlan
            signal_names = [f"{s.signal_type.value}:{s.direction}" for s in valid_signals]
            plan = TradePlan.from_text(response_text, market_context.coin, signal_names)

            # Validate the plan with dynamic risk management
            plan = self._validate_plan(plan, market_context, valid_signals)

            return plan

        except Exception as e:
            logger.error(f"AI evaluation failed: {e}")
            return None

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
        weighted_scores: tuple[float, float] | None = None,
    ) -> str:
        """
        Format the prompt for AI evaluation.

        Args:
            signals: Signals to include
            positions: Current positions
            context: Market context
            weighted_scores: Optional (long_score, short_score) tuple

        Returns:
            Formatted prompt string
        """
        # Format signals with their weights
        signal_lines = []
        for s in signals:
            weight = self.strategy.signal_weights.get(s.signal_type, 0.0)
            weighted_contribution = weight * s.strength
            meta_str = ", ".join(
                f"{k}={v:.4f}" for k, v in s.metadata.items() if isinstance(v, float)
            )
            signal_lines.append(
                f"  - {s.signal_type.value}: {s.direction} "
                f"(strength: {s.strength:.2f}, weight: {weight:.1f}, "
                f"contribution: {weighted_contribution:.2f}) [{meta_str}]"
            )

        # Add weighted score summary
        if weighted_scores:
            long_score, short_score = weighted_scores
            signal_lines.append("")
            signal_lines.append(
                f"  WEIGHTED SCORES: LONG={long_score:.2f}, SHORT={short_score:.2f}"
            )
            signal_lines.append(f"  THRESHOLD: {self.strategy.signal_threshold}")

        signals_str = "\n".join(signal_lines) if signal_lines else "  None"

        # Format positions
        position_lines = []
        for coin, pos in positions.items():
            if coin == context.coin:
                pnl = pos.unrealized_pnl_percent(context.current_price)
                position_lines.append(
                    f"  - {coin}: {pos.side.value.upper()} @ ${pos.entry_price:.2f} "
                    f"(P&L: {pnl:+.2f}%)"
                )
        positions_str = "\n".join(position_lines) if position_lines else "  No open positions"

        # Build the prompt using strategy's trading style
        return SIGNAL_EVALUATION_PROMPT.format(
            strategy_prompt=self.strategy.prompt,
            strategy_name=self.strategy.name,
            signals=signals_str,
            positions=positions_str,
            atr_value=context.atr,
            atr_pct=context.atr_percent,
            volatility_level=context.volatility_level,
            max_position_pct=self.strategy.risk.max_position_pct,
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

    def reset_metrics(self) -> None:
        """Reset call count and AI metrics."""
        self._call_count = 0
        self.ollama.reset_metrics()


def create_signal_brain(
    strategy_name: str = "momentum_scalper",
    ollama_model: str = "mistral",
    ollama_url: str = "http://localhost:11434",
) -> SignalBrain:
    """
    Factory function to create a SignalBrain with a strategy.

    Args:
        strategy_name: Name of strategy (momentum_scalper, trend_follower,
                       mean_reversion, conservative)
        ollama_model: Ollama model to use
        ollama_url: Ollama server URL

    Returns:
        Configured SignalBrain instance

    Example:
        brain = create_signal_brain("momentum_scalper")
        brain = create_signal_brain("conservative", ollama_model="llama2")
    """
    strategy = get_strategy(strategy_name)
    ollama = OllamaClient(base_url=ollama_url, model=ollama_model)

    return SignalBrain(strategy=strategy, ollama_client=ollama)
