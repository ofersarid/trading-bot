"""
Scalper Interpreter Service.

Interprets market data through the Scalper persona, returning
AI-derived momentum, pressure, and prediction values.
"""

import logging
from dataclasses import dataclass
from datetime import datetime

from bot.ai.ollama_client import OllamaClient
from bot.ai.personas.scalper import format_scalper_prompt
from bot.core.data_buffer import ScalperDataWindow
from bot.simulation.paper_trader import Position

logger = logging.getLogger(__name__)


@dataclass
class ScalperInterpretation:
    """
    AI Scalper's interpretation of market data.

    All numeric values are AI-interpreted, not calculated.
    """

    coin: str

    # Core metrics (AI-derived, 0-100 scale)
    momentum: int  # 0-100: strength and quality of the move
    pressure: int  # 0-100: buying vs selling pressure (50 = neutral)
    prediction: int  # 0-100: continuation probability

    # Trading guidance
    freshness: str  # FRESH/DEVELOPING/EXTENDED/EXHAUSTED
    action: str  # NONE/LONG/SHORT/EXIT
    confidence: int  # 1-10
    reason: str  # Scalper's tape read

    # Metadata
    response_time_ms: float
    timestamp: datetime

    @property
    def is_bullish(self) -> bool:
        """Whether the interpretation suggests bullish conditions."""
        return self.pressure > 55 and self.momentum > 50

    @property
    def is_bearish(self) -> bool:
        """Whether the interpretation suggests bearish conditions."""
        return self.pressure < 45 and self.momentum > 50

    @property
    def is_actionable(self) -> bool:
        """Whether the AI suggests taking action."""
        return self.action in ("LONG", "SHORT", "EXIT")

    @property
    def age_seconds(self) -> float:
        """Seconds since this interpretation was created."""
        return (datetime.now() - self.timestamp).total_seconds()

    @property
    def is_stale(self) -> bool:
        """Whether this interpretation is considered stale (>20s old)."""
        return self.age_seconds > 20.0

    @classmethod
    def empty(cls, coin: str) -> "ScalperInterpretation":
        """Create an empty/default interpretation."""
        return cls(
            coin=coin,
            momentum=50,
            pressure=50,
            prediction=50,
            freshness="DEVELOPING",
            action="NONE",
            confidence=0,
            reason="No interpretation yet",
            response_time_ms=0,
            timestamp=datetime.now(),
        )

    @classmethod
    def error(cls, coin: str, error_msg: str) -> "ScalperInterpretation":
        """Create an error interpretation."""
        return cls(
            coin=coin,
            momentum=50,
            pressure=50,
            prediction=50,
            freshness="DEVELOPING",
            action="NONE",
            confidence=0,
            reason=f"Error: {error_msg}",
            response_time_ms=0,
            timestamp=datetime.now(),
        )


def _parse_int(value: str, min_val: int, max_val: int, default: int) -> int:
    """Parse an integer from string, clamping to range."""
    try:
        # Handle values like "72/100" or "72"
        if "/" in value:
            value = value.split("/")[0]
        num = int(value.strip())
        return max(min_val, min(max_val, num))
    except (ValueError, AttributeError):
        return default


def parse_scalper_response(
    response: str,
    coin: str,
    response_time_ms: float,
) -> ScalperInterpretation:
    """
    Parse the AI's structured response into a ScalperInterpretation.

    Args:
        response: Raw response text from AI
        coin: Coin symbol
        response_time_ms: Response time in milliseconds

    Returns:
        Parsed ScalperInterpretation
    """
    lines = response.strip().split("\n")
    data: dict[str, str] = {}

    for line in lines:
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip().upper()] = value.strip()

    # Parse values with defaults
    momentum = _parse_int(data.get("MOMENTUM", "50"), 0, 100, 50)
    pressure = _parse_int(data.get("PRESSURE", "50"), 0, 100, 50)
    prediction = _parse_int(data.get("PREDICTION", "50"), 0, 100, 50)
    confidence = _parse_int(data.get("CONFIDENCE", "5"), 1, 10, 5)

    # Parse freshness
    freshness = data.get("FRESHNESS", "DEVELOPING").upper()
    if freshness not in ("FRESH", "DEVELOPING", "EXTENDED", "EXHAUSTED"):
        freshness = "DEVELOPING"

    # Parse action
    action = data.get("ACTION", "NONE").upper()
    if action not in ("NONE", "LONG", "SHORT", "EXIT"):
        action = "NONE"

    # Parse reason
    reason = data.get("REASON", "No reason provided")

    return ScalperInterpretation(
        coin=coin,
        momentum=momentum,
        pressure=pressure,
        prediction=prediction,
        freshness=freshness,
        action=action,
        confidence=confidence,
        reason=reason,
        response_time_ms=response_time_ms,
        timestamp=datetime.now(),
    )


class ScalperInterpreter:
    """
    AI service that interprets market data through the Scalper persona.

    Calls the local AI (Ollama) with formatted prompts and parses
    the structured response into ScalperInterpretation objects.
    """

    def __init__(self, client: OllamaClient | None = None):
        """
        Initialize the interpreter.

        Args:
            client: OllamaClient instance (creates default if None)
        """
        self.client = client or OllamaClient()
        self._interpretations: dict[str, ScalperInterpretation] = {}

    async def interpret(
        self,
        data_window: ScalperDataWindow,
        position: Position | None = None,
    ) -> ScalperInterpretation:
        """
        Get the Scalper's interpretation of current market state.

        Args:
            data_window: ScalperDataWindow with buffered market data
            position: Current position or None

        Returns:
            ScalperInterpretation with AI-derived metrics
        """
        coin = data_window.coin

        try:
            # Format the prompt
            prompt = format_scalper_prompt(data_window, position)

            # Call AI
            response_text, _tokens, response_time_ms = await self.client.analyze(
                prompt,
                temperature=0.3,
                max_tokens=200,
            )

            # Parse response
            interpretation = parse_scalper_response(
                response_text,
                coin,
                response_time_ms,
            )

            # Cache it
            self._interpretations[coin] = interpretation

            logger.info(
                f"Scalper interpretation for {coin}: "
                f"Mom={interpretation.momentum} Press={interpretation.pressure} "
                f"Pred={interpretation.prediction} [{interpretation.freshness}] "
                f"Action={interpretation.action} Conf={interpretation.confidence}/10 "
                f"({response_time_ms:.0f}ms)"
            )

            return interpretation

        except Exception as e:
            logger.error(f"Scalper interpretation failed for {coin}: {e}")
            return ScalperInterpretation.error(coin, str(e))

    def get_last_interpretation(self, coin: str) -> ScalperInterpretation | None:
        """
        Get the most recent interpretation for a coin.

        Args:
            coin: Coin symbol

        Returns:
            Last ScalperInterpretation or None
        """
        return self._interpretations.get(coin)

    def get_all_interpretations(self) -> dict[str, ScalperInterpretation]:
        """Get all cached interpretations."""
        return self._interpretations.copy()

    def clear_interpretations(self) -> None:
        """Clear all cached interpretations."""
        self._interpretations.clear()

    async def is_available(self) -> bool:
        """Check if the AI backend is available."""
        return await self.client.is_available()
