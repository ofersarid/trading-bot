"""
GoalBasedSizer - AI position sizer based on user trading goals.

This is the only AI component for trading decisions. It receives:
- Signals (already enriched with TP/SL by SignalsFactory)
- Account state
- User goal

And decides: How much $ to risk on this trade?
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from bot.ai.models import AccountContext, RiskTolerance, UserGoal
from bot.ai.ollama_client import OllamaClient

if TYPE_CHECKING:
    from bot.signals.factory import FactoryOutput

logger = logging.getLogger(__name__)


# System prompt for the Position Sizing AI
GOAL_SIZER_SYSTEM_PROMPT = """You are a POSITION SIZING AI for a trading system.

CRITICAL RULES:
1. You MUST output ONLY the exact format requested
2. Your response MUST start with "RISK_PERCENT:"
3. The trade direction (LONG/SHORT) is already decided - you decide HOW MUCH to risk
4. Consider the user's goal, account progress, and signal quality

Your job is to decide position size based on:
- Progress toward the goal
- Time remaining
- Signal quality
- Risk tolerance"""


# Main prompt template
GOAL_SIZER_PROMPT = """{goal_context}

## CURRENT STATE
- Balance: ${balance:,.2f} (started: ${initial_balance:,.2f})
- P&L: ${pnl:+,.2f} ({pnl_pct:+.1f}%)
- Progress toward goal: {progress_pct:.1f}%
- Days elapsed: {days_elapsed} / {total_days}
- Days remaining: {days_remaining}
- Pace status: {pace_status}

## SIGNAL RECEIVED
- Direction: {direction}
- Weighted Score: {score:.2f} (threshold: {threshold})
- Volatility: {volatility}

### Signal Details
{signal_details}

### Position Info
- Entry: ${entry_price:,.2f}
- Stop Loss: ${stop_loss:,.2f} (risk: {risk_pct:.2f}%)
- Take Profit: ${take_profit:,.2f} (reward: {reward_pct:.2f}%)
- Risk/Reward: {risk_reward:.2f}

## YOUR DECISION

Based on the user's goal ({risk_tolerance} risk tolerance):

{sizing_guidance}

RISK_PERCENT guidelines:
- 0.5-1.0% = Very conservative (protecting gains or weak setup)
- 1.0-2.0% = Conservative (on track, moderate setup)
- 2.0-3.0% = Normal (good setup, reasonable progress)
- 3.0-5.0% = Aggressive (behind schedule + strong setup)
- 5.0-10.0% = Very aggressive (urgent catch-up, excellent setup)
- 0.0% = Skip trade (goal reached or setup too risky)

OUTPUT FORMAT (start with RISK_PERCENT:):
RISK_PERCENT: [0.0 - 10.0]
REASONING: [One sentence explaining why this size]"""


# Risk tolerance specific guidance
RISK_GUIDANCE = {
    RiskTolerance.CONSERVATIVE: """
CONSERVATIVE risk tolerance means:
- Prioritize capital preservation
- Maximum RISK_PERCENT: 2.0%
- Only increase size for exceptional setups
- Accept slower progress toward goal
- Skip marginal setups""",
    RiskTolerance.MODERATE: """
MODERATE risk tolerance means:
- Balance growth with capital preservation
- Normal RISK_PERCENT range: 1.0-3.0%
- Increase for strong setups when behind
- Stay smaller when ahead of schedule
- Use full position sizing math""",
    RiskTolerance.AGGRESSIVE: """
AGGRESSIVE risk tolerance means:
- Prioritize goal achievement
- Normal RISK_PERCENT range: 2.0-5.0%
- Significantly increase when behind schedule
- Accept larger drawdowns for growth
- Only reduce size for very weak setups""",
}


@dataclass
class SizingDecision:
    """Output from GoalBasedSizer."""

    risk_percent: float  # % of account to risk (not position size)
    position_size_pct: float  # Actual position size based on risk
    reasoning: str

    @property
    def should_trade(self) -> bool:
        """Whether to take this trade."""
        return self.risk_percent > 0

    def to_dict(self) -> dict:
        """Serialize for logging."""
        return {
            "risk_percent": self.risk_percent,
            "position_size_pct": self.position_size_pct,
            "reasoning": self.reasoning,
            "should_trade": self.should_trade,
        }


class GoalBasedSizer:
    """
    AI position sizer that decides risk based on user trading goals.

    The GoalBasedSizer is the ONLY AI component in the refactored architecture.
    SignalsFactory handles pure signal processing (no AI).
    GoalBasedSizer handles position sizing (with AI).

    Flow:
        Signals → SignalsFactory → FactoryOutput → GoalBasedSizer → SizingDecision
    """

    def __init__(
        self,
        ollama: OllamaClient,
        goal: UserGoal,
    ) -> None:
        """
        Initialize the sizer.

        Args:
            ollama: Ollama client for AI inference
            goal: User's trading goal
        """
        self.ollama = ollama
        self.goal = goal
        self._call_count = 0

    async def size_position(
        self,
        factory_output: "FactoryOutput",
        account: AccountContext,
    ) -> SizingDecision:
        """
        Decide how much to risk on this signal.

        Args:
            factory_output: Processed signals from SignalsFactory
            account: Current account state

        Returns:
            SizingDecision with risk % and position size
        """
        # Get first signal for price reference (all signals have same TP/SL)
        primary_signal = factory_output.signals[0]

        # Calculate risk/reward from signal
        entry = primary_signal.entry_price or 0
        stop_loss = primary_signal.stop_loss or 0
        take_profit = primary_signal.take_profit or 0

        risk_distance = abs(entry - stop_loss)
        reward_distance = abs(take_profit - entry)
        risk_pct = (risk_distance / entry * 100) if entry > 0 else 0
        reward_pct = (reward_distance / entry * 100) if entry > 0 else 0
        risk_reward = reward_distance / risk_distance if risk_distance > 0 else 0

        # Format signal details
        signal_details = []
        for s in factory_output.signals:
            signal_details.append(
                f"  - {s.signal_type.value}: {s.direction} (strength: {s.strength:.2f})"
            )

        # Calculate progress
        progress_pct = account.goal_progress_pct or 0
        days_remaining = account.days_remaining or 0
        pace_status = account.pace_status

        # Format the prompt
        prompt = GOAL_SIZER_PROMPT.format(
            goal_context=self.goal.to_prompt_context(),
            balance=account.current_balance,
            initial_balance=account.initial_balance,
            pnl=account.pnl,
            pnl_pct=account.pnl_pct,
            progress_pct=progress_pct,
            days_elapsed=account.days_elapsed,
            total_days=self.goal.timeframe_days,
            days_remaining=days_remaining,
            pace_status=pace_status.upper(),
            direction=factory_output.direction,
            score=factory_output.weighted_score,
            threshold=factory_output.threshold,
            volatility=self._get_volatility_from_signals(factory_output),
            signal_details="\n".join(signal_details),
            entry_price=entry,
            stop_loss=stop_loss,
            risk_pct=risk_pct,
            take_profit=take_profit,
            reward_pct=reward_pct,
            risk_reward=risk_reward,
            risk_tolerance=self.goal.risk_tolerance.value,
            sizing_guidance=RISK_GUIDANCE[self.goal.risk_tolerance],
        )

        try:
            response_text, tokens, response_time = await self.ollama.analyze(
                prompt=prompt,
                temperature=0.2,
                max_tokens=100,
                system_prompt=GOAL_SIZER_SYSTEM_PROMPT,
            )
            self._call_count += 1

            logger.debug(
                f"GoalSizer response ({tokens} tokens, {response_time:.0f}ms): {response_text}"
            )

            # Parse response
            risk_percent, reasoning = self._parse_response(response_text)

            # Calculate actual position size from risk %
            # If we're risking X% of account, and the trade has Y% risk to stop loss,
            # then position size = X% / Y%
            position_size_pct = 0.0
            if risk_pct > 0:
                position_size_pct = (risk_percent / risk_pct) * 100
                # Cap at reasonable maximum
                position_size_pct = min(position_size_pct, 50.0)

            logger.info(
                f"GoalSizer: {factory_output.direction} risk={risk_percent:.1f}% "
                f"→ position={position_size_pct:.1f}% | {reasoning}"
            )

            return SizingDecision(
                risk_percent=risk_percent,
                position_size_pct=position_size_pct,
                reasoning=reasoning,
            )

        except Exception as e:
            logger.error(f"GoalSizer failed: {e}")
            # Return conservative fallback
            return SizingDecision(
                risk_percent=1.0,
                position_size_pct=5.0,
                reasoning=f"Fallback sizing due to error: {e}",
            )

    def size_position_deterministic(
        self,
        factory_output: "FactoryOutput",
        account: AccountContext,
    ) -> SizingDecision:
        """
        Deterministic fallback position sizing (no AI).

        Uses goal parameters and account state to calculate position size
        without calling the AI. Useful for testing or when AI is unavailable.

        Args:
            factory_output: Processed signals from SignalsFactory
            account: Current account state

        Returns:
            SizingDecision based on rules
        """
        # Base risk based on tolerance
        base_risk = {
            RiskTolerance.CONSERVATIVE: 1.0,
            RiskTolerance.MODERATE: 2.0,
            RiskTolerance.AGGRESSIVE: 3.0,
        }[self.goal.risk_tolerance]

        # Adjust based on pace
        pace_multiplier = {
            "ahead": 0.7,
            "on_pace": 1.0,
            "behind": 1.3,
            "goal_reached": 0.0,
            "just_started": 1.0,
            "no_goal": 1.0,
            "unknown": 1.0,
        }.get(account.pace_status, 1.0)

        # Adjust based on signal strength
        score_ratio = factory_output.weighted_score / factory_output.threshold
        signal_multiplier = min(1.5, max(0.5, score_ratio))

        # Calculate final risk
        risk_percent = base_risk * pace_multiplier * signal_multiplier
        risk_percent = max(0.0, min(10.0, risk_percent))

        # Skip if goal reached
        if account.pace_status == "goal_reached":
            return SizingDecision(
                risk_percent=0.0,
                position_size_pct=0.0,
                reasoning="Goal reached - no new positions",
            )

        # Calculate position size
        primary_signal = factory_output.signals[0]
        entry = primary_signal.entry_price or 0
        stop_loss = primary_signal.stop_loss or 0
        risk_distance = abs(entry - stop_loss)
        risk_pct = (risk_distance / entry * 100) if entry > 0 else 1.0

        position_size_pct = (risk_percent / risk_pct) * 100 if risk_pct > 0 else 5.0
        position_size_pct = min(position_size_pct, 50.0)

        reasoning = (
            f"Deterministic: base={base_risk:.1f}% x "
            f"pace={pace_multiplier:.1f} x "
            f"signal={signal_multiplier:.1f}"
        )

        return SizingDecision(
            risk_percent=risk_percent,
            position_size_pct=position_size_pct,
            reasoning=reasoning,
        )

    def _parse_response(self, response: str) -> tuple[float, str]:
        """Parse AI response for risk percent and reasoning."""
        lines = response.strip().split("\n")
        data: dict[str, str] = {}

        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                data[key.strip().upper()] = value.strip()

        # Parse RISK_PERCENT
        try:
            risk_str = data.get("RISK_PERCENT", "1.0")
            risk_str = risk_str.lower().replace("%", "").strip()
            risk_percent = float(risk_str)
            risk_percent = max(0.0, min(10.0, risk_percent))
        except ValueError:
            risk_percent = 1.0

        # Parse REASONING
        reasoning = data.get("REASONING", data.get("REASON", "No reasoning provided"))

        return risk_percent, reasoning

    def _get_volatility_from_signals(
        self, factory_output: "FactoryOutput"
    ) -> Literal["low", "medium", "high"]:
        """Extract volatility level from signal metadata."""
        for signal in factory_output.signals:
            if "volatility" in signal.metadata:
                vol: str = signal.metadata["volatility"]
                if vol == "low":
                    return "low"
                if vol == "high":
                    return "high"
        return "medium"

    @property
    def call_count(self) -> int:
        """Number of AI calls made."""
        return self._call_count

    def reset_metrics(self) -> None:
        """Reset call count."""
        self._call_count = 0
        self.ollama.reset_metrics()

    def get_metrics_summary(self) -> dict:
        """Get metrics summary."""
        return {
            "ai_calls": self._call_count,
            "goal": {
                "description": self.goal.description,
                "target_multiplier": self.goal.target_multiplier,
                "risk_tolerance": self.goal.risk_tolerance.value,
            },
        }


def create_goal_sizer(
    goal: UserGoal | None = None,
    ollama_model: str = "mistral",
    ollama_url: str = "http://localhost:11434",
) -> GoalBasedSizer:
    """
    Factory function to create a GoalBasedSizer.

    Args:
        goal: User's trading goal (defaults to moderate growth)
        ollama_model: Ollama model to use
        ollama_url: Ollama server URL

    Returns:
        Configured GoalBasedSizer instance
    """
    if goal is None:
        goal = UserGoal.default()

    ollama = OllamaClient(base_url=ollama_url, model=ollama_model)

    return GoalBasedSizer(ollama=ollama, goal=goal)
