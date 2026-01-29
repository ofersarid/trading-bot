"""
Portfolio Allocator - AI-driven multi-asset allocation decisions.

The Portfolio Allocator receives all trading opportunities across markets
simultaneously and decides:
1. Which opportunities to act on
2. How much capital to allocate to each
3. How much to keep in cash reserve

This is a portfolio-level decision maker, not a single-asset position sizer.
"""

import logging
import re
from typing import TYPE_CHECKING

from bot.ai.models import (
    AllocationDecision,
    PortfolioAllocation,
    PortfolioOpportunity,
    PortfolioState,
)

if TYPE_CHECKING:
    from bot.ai.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


# System prompt for Portfolio Allocator role
PORTFOLIO_SYSTEM_PROMPT = """You are a PORTFOLIO ALLOCATOR, not a chatbot or assistant.

CRITICAL RULES:
1. You MUST output ONLY the exact format requested - no explanations, no preamble
2. Your response MUST start with "ALLOCATION:"
3. You receive MULTIPLE opportunities and decide how to distribute capital
4. Consider correlation, diversification, and goal progress when allocating

You allocate capital across opportunities to maximize goal achievement while managing risk."""

# Portfolio allocation prompt template
PORTFOLIO_ALLOCATION_PROMPT = """## TRADING OPPORTUNITIES

{opportunities}

## PORTFOLIO STATE

{portfolio_state}

## YOUR TASK

You have {num_opportunities} trading opportunities. Decide how to allocate capital.

**Guidelines:**
- Total allocation cannot exceed {max_allocation}% (including existing positions)
- You can allocate 0% to skip an opportunity
- Consider keeping cash reserve for future opportunities
- Correlated assets (e.g., BTC and ETH) should not both get large allocations
- If behind on goal, concentrate on highest-conviction plays
- If ahead on goal, diversify or reduce risk

**Output Format:**
```
ALLOCATION:
{coin_format}
CASH: [0-100]%
REASONING: [One paragraph explaining your portfolio strategy]
```

**Allocation Guidelines per Opportunity:**
- 0% = Skip (weak setup, correlated with existing position, or saving for better opportunity)
- 5-15% = Small position (moderate conviction, high volatility, or hedging)
- 15-30% = Standard position (good conviction, acceptable risk)
- 30-50% = Large position (high conviction, behind on goal, excellent setup)
- CLOSE = Close existing position in this asset"""


class PortfolioAllocator:
    """
    AI-driven portfolio allocation across multiple trading opportunities.

    Unlike the SignalBrain which evaluates one asset at a time, the
    PortfolioAllocator receives ALL opportunities and makes a holistic
    decision about capital allocation.
    """

    def __init__(
        self,
        ollama_client: "OllamaClient",
        max_total_allocation: float = 80.0,  # Max % in positions
    ) -> None:
        """
        Initialize the portfolio allocator.

        Args:
            ollama_client: Client for AI inference
            max_total_allocation: Maximum % of portfolio in positions (rest is cash buffer)
        """
        self.ollama = ollama_client
        self.max_total_allocation = max_total_allocation
        self._call_count = 0
        self._skip_count = 0

    async def allocate(
        self,
        opportunities: list[PortfolioOpportunity],
        portfolio_state: PortfolioState,
    ) -> PortfolioAllocation | None:
        """
        Decide how to allocate capital across multiple opportunities.

        Args:
            opportunities: List of trading opportunities across markets
            portfolio_state: Current portfolio state including positions and goals

        Returns:
            PortfolioAllocation with decisions for each opportunity, or None on error
        """
        if not opportunities:
            logger.debug("No opportunities to allocate")
            return PortfolioAllocation(
                decisions=[],
                cash_reserve_pct=100.0,
                overall_reasoning="No opportunities available",
            )

        # Calculate available allocation (accounting for existing positions)
        current_exposure = portfolio_state.total_exposure_pct
        available_allocation = max(0, self.max_total_allocation - current_exposure)

        prompt = self._format_prompt(opportunities, portfolio_state, available_allocation)

        try:
            response_text, tokens, response_time = await self.ollama.analyze(
                prompt=prompt,
                temperature=0.3,  # Slightly creative for portfolio decisions
                max_tokens=500,  # More tokens needed for multi-asset response
                system_prompt=PORTFOLIO_SYSTEM_PROMPT,
            )
            self._call_count += 1

            logger.debug(f"AI response ({tokens} tokens, {response_time:.0f}ms): {response_text}")

            allocation = self._parse_allocation_response(response_text, opportunities)

            # Log summary
            actionable = allocation.actionable_decisions
            if actionable:
                summary = ", ".join(f"{d.coin}:{d.allocation_pct:.0f}%" for d in actionable)
                logger.info(
                    f"Portfolio allocation: {summary}, Cash: {allocation.cash_reserve_pct:.0f}%"
                )
            else:
                self._skip_count += 1
                logger.info(
                    f"Portfolio allocation: All skipped, Cash: {allocation.cash_reserve_pct:.0f}%"
                )

            return allocation

        except Exception as e:
            logger.error(f"Portfolio allocation failed: {e}")
            return None

    def _format_prompt(
        self,
        opportunities: list[PortfolioOpportunity],
        portfolio_state: PortfolioState,
        available_allocation: float,
    ) -> str:
        """Format the prompt for portfolio allocation."""
        # Format opportunities
        opp_lines = []
        for i, opp in enumerate(opportunities, 1):
            opp_lines.append(f"{i}. {opp.to_prompt_string()}")
        opportunities_str = "\n".join(opp_lines)

        # Format coin allocation format for output
        coin_format = "\n".join(f"{opp.coin}: [0-50]% or CLOSE" for opp in opportunities)

        return PORTFOLIO_ALLOCATION_PROMPT.format(
            opportunities=opportunities_str,
            portfolio_state=portfolio_state.to_prompt_string(),
            num_opportunities=len(opportunities),
            max_allocation=available_allocation,
            coin_format=coin_format,
        )

    def _parse_allocation_response(
        self,
        response: str,
        opportunities: list[PortfolioOpportunity],
    ) -> PortfolioAllocation:
        """
        Parse the AI's allocation response.

        Args:
            response: Raw AI response text
            opportunities: Original opportunities for reference

        Returns:
            PortfolioAllocation with decisions
        """
        lines = response.strip().split("\n")
        decisions: list[AllocationDecision] = []
        cash_reserve = 20.0  # Default
        overall_reasoning = ""

        # Track which coins we've seen
        coin_to_opp = {opp.coin: opp for opp in opportunities}
        seen_coins: set[str] = set()

        for line in lines:
            line = line.strip()
            if not line or line.startswith("```") or line == "ALLOCATION:":
                continue

            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip().upper()
                value = value.strip()

                if key == "CASH":
                    cash_reserve = self._parse_percentage(value, 20.0)
                elif key == "REASONING":
                    overall_reasoning = value
                elif key in coin_to_opp:
                    # This is a coin allocation
                    opp = coin_to_opp[key]
                    seen_coins.add(key)

                    if value.upper() == "CLOSE":
                        decisions.append(
                            AllocationDecision(
                                coin=key,
                                action="CLOSE",
                                allocation_pct=0,
                                reasoning="AI requested position close",
                            )
                        )
                    else:
                        pct = self._parse_percentage(value, 0)
                        action = opp.direction if pct > 0 else "SKIP"
                        decisions.append(
                            AllocationDecision(
                                coin=key,
                                action=action,
                                allocation_pct=pct,
                                reasoning=f"Allocated {pct:.0f}% to {opp.direction}",
                            )
                        )

        # Add SKIP decisions for any opportunities not mentioned
        for coin in coin_to_opp:
            if coin not in seen_coins:
                decisions.append(
                    AllocationDecision(
                        coin=coin,
                        action="SKIP",
                        allocation_pct=0,
                        reasoning="Not mentioned in AI response",
                    )
                )

        return PortfolioAllocation(
            decisions=decisions,
            cash_reserve_pct=cash_reserve,
            overall_reasoning=overall_reasoning or "No reasoning provided",
        )

    def _parse_percentage(self, value: str, default: float) -> float:
        """Parse a percentage value from string."""
        try:
            # Remove % sign and any extra text
            cleaned = re.sub(r"[^\d.]", "", value.split("%")[0])
            return float(cleaned) if cleaned else default
        except ValueError:
            return default

    def reset_metrics(self) -> None:
        """Reset call counters."""
        self._call_count = 0
        self._skip_count = 0

    def get_metrics_summary(self) -> dict:
        """Get summary of allocator usage."""
        return {
            "total_calls": self._call_count,
            "all_skipped_count": self._skip_count,
            "action_rate": (
                (self._call_count - self._skip_count) / self._call_count * 100
                if self._call_count > 0
                else 0
            ),
        }


async def create_portfolio_allocator(
    ollama_client: "OllamaClient",
    max_total_allocation: float = 80.0,
) -> PortfolioAllocator:
    """
    Factory function to create a portfolio allocator.

    Args:
        ollama_client: Client for AI inference
        max_total_allocation: Maximum % of portfolio in positions

    Returns:
        Configured PortfolioAllocator
    """
    return PortfolioAllocator(
        ollama_client=ollama_client,
        max_total_allocation=max_total_allocation,
    )
