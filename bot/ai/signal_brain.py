"""
Signal Brain - AI decision maker for the 3-layer backtesting architecture.

Receives signals from Layer 2 (Signal Detectors) and outputs TradePlans
based on the configured persona's trading style and risk parameters.
"""

import logging
from typing import TYPE_CHECKING

from bot.ai.models import MarketContext, TradePlan
from bot.ai.ollama_client import OllamaClient
from bot.ai.personas.base import TradingPersona

if TYPE_CHECKING:
    from bot.signals.base import Signal
    from bot.simulation.models import Position

logger = logging.getLogger(__name__)


class SignalBrain:
    """
    AI decision maker that evaluates signals and produces trade plans.

    The brain receives signals from multiple detectors, considers the
    current market context and positions, and decides whether to trade
    based on the persona's trading style.
    """

    def __init__(
        self,
        persona: TradingPersona,
        ollama_client: OllamaClient,
    ) -> None:
        """
        Initialize the signal brain.

        Args:
            persona: Trading persona that defines decision-making style
            ollama_client: Client for AI inference
        """
        self.persona = persona
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
        # Pre-filter signals based on persona preferences
        valid_signals = self._filter_signals(signals, market_context.coin)

        if not valid_signals:
            logger.debug(f"No valid signals for {market_context.coin}")
            return TradePlan.wait(market_context.coin, "No signals meet criteria")

        # Check for consensus if persona requires it
        if self.persona.prefer_consensus and not self._has_consensus(valid_signals):
            logger.debug("No signal consensus, waiting")
            return TradePlan.wait(market_context.coin, "Waiting for signal consensus")

        # Format the prompt
        prompt = self._format_prompt(
            signals=valid_signals,
            positions=current_positions,
            context=market_context,
        )

        # Query the AI
        try:
            response_text, tokens, response_time = await self.ollama.analyze(
                prompt=prompt,
                temperature=0.3,
                max_tokens=300,
            )
            self._call_count += 1

            logger.debug(
                f"AI response ({tokens} tokens, {response_time:.0f}ms): {response_text[:100]}..."
            )

            # Parse response into TradePlan
            signal_names = [f"{s.signal_type.value}:{s.direction}" for s in valid_signals]
            plan = TradePlan.from_text(response_text, market_context.coin, signal_names)

            # Validate the plan
            plan = self._validate_plan(plan, market_context)

            return plan

        except Exception as e:
            logger.error(f"AI evaluation failed: {e}")
            return None

    def _filter_signals(self, signals: list["Signal"], coin: str) -> list["Signal"]:
        """
        Filter signals based on persona preferences.

        Args:
            signals: All detected signals
            coin: Coin to filter for

        Returns:
            Signals that meet persona criteria
        """
        filtered = []
        for signal in signals:
            # Only consider signals for this coin
            if signal.coin != coin:
                continue

            # Check signal strength
            if signal.strength < self.persona.min_signal_strength:
                continue

            filtered.append(signal)

        return filtered

    def _has_consensus(self, signals: list["Signal"]) -> bool:
        """
        Check if signals have consensus on direction.

        Args:
            signals: Filtered signals

        Returns:
            True if majority agree on direction
        """
        if len(signals) < 2:
            return len(signals) == 1  # Single signal is fine

        long_count = sum(1 for s in signals if s.direction == "LONG")
        short_count = len(signals) - long_count

        # Need at least 2:1 ratio for consensus
        if long_count >= 2 * short_count:
            return True
        if short_count >= 2 * long_count:
            return True

        return False

    def _format_prompt(
        self,
        signals: list["Signal"],
        positions: dict[str, "Position"],
        context: MarketContext,
    ) -> str:
        """
        Format the prompt for AI evaluation.

        Args:
            signals: Signals to include
            positions: Current positions
            context: Market context

        Returns:
            Formatted prompt string
        """
        # Format signals
        signal_lines = []
        for s in signals:
            meta_str = ", ".join(
                f"{k}={v:.4f}" for k, v in s.metadata.items() if isinstance(v, float)
            )
            signal_lines.append(
                f"  - {s.signal_type.value}: {s.direction} (strength: {s.strength:.2f}) [{meta_str}]"
            )
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

        # Fill in the template
        return self.persona.prompt_template.format(
            style=self.persona.style,
            description=self.persona.description,
            signals=signals_str,
            positions=positions_str,
            atr_value=context.atr,
            atr_pct=context.atr_percent,
            volatility_level=context.volatility_level,
            max_position_pct=self.persona.risk_params.max_position_pct,
        )

    def _validate_plan(self, plan: TradePlan, context: MarketContext) -> TradePlan:
        """
        Validate and adjust the trade plan.

        Args:
            plan: Parsed trade plan
            context: Market context

        Returns:
            Validated (possibly adjusted) plan
        """
        # Check confidence threshold
        if plan.is_actionable and plan.confidence < self.persona.min_confidence:
            logger.debug(
                f"Plan confidence {plan.confidence} below threshold "
                f"{self.persona.min_confidence}, converting to WAIT"
            )
            return TradePlan.wait(plan.coin, f"Confidence too low ({plan.confidence})")

        # Cap position size
        if plan.size_pct > self.persona.risk_params.max_position_pct:
            plan.size_pct = self.persona.risk_params.max_position_pct

        # Ensure stops are set if taking action
        if plan.is_actionable and plan.stop_loss == 0:
            # Calculate default stop loss using ATR
            atr_sl = context.atr * self.persona.risk_params.stop_loss_atr_multiplier
            if plan.is_long:
                plan.stop_loss = context.current_price - atr_sl
            else:
                plan.stop_loss = context.current_price + atr_sl

        if plan.is_actionable and plan.take_profit == 0:
            # Calculate default take profit using ATR
            atr_tp = context.atr * self.persona.risk_params.take_profit_atr_multiplier
            if plan.is_long:
                plan.take_profit = context.current_price + atr_tp
            else:
                plan.take_profit = context.current_price - atr_tp

        return plan

    @property
    def call_count(self) -> int:
        """Number of AI calls made."""
        return self._call_count

    def reset_metrics(self) -> None:
        """Reset call count and AI metrics."""
        self._call_count = 0
        self.ollama.reset_metrics()


def create_signal_brain(
    persona_name: str = "balanced",
    ollama_model: str = "mistral",
    ollama_url: str = "http://localhost:11434",
) -> SignalBrain:
    """
    Factory function to create a SignalBrain with common defaults.

    Args:
        persona_name: Name of pre-defined persona (scalper, conservative, balanced)
        ollama_model: Ollama model to use
        ollama_url: Ollama server URL

    Returns:
        Configured SignalBrain instance
    """
    from bot.ai.personas.base import get_persona

    persona = get_persona(persona_name)
    ollama = OllamaClient(base_url=ollama_url, model=ollama_model)

    return SignalBrain(persona=persona, ollama_client=ollama)
