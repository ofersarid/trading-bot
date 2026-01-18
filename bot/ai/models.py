"""Data models for AI analysis responses and metrics."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import time


class Sentiment(Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class Signal(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    WAIT = "WAIT"


@dataclass
class AnalysisResult:
    """Result of AI market analysis."""

    sentiment: Sentiment
    confidence: int  # 1-10
    signal: Signal
    coin: str
    reason: str
    response_time_ms: float

    @classmethod
    def from_text(cls, text: str, coin: str, response_time_ms: float) -> "AnalysisResult":
        """Parse structured AI response into AnalysisResult."""
        lines = text.strip().split("\n")
        data = {}

        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                data[key.strip().upper()] = value.strip()

        sentiment_str = data.get("SENTIMENT", "NEUTRAL")
        try:
            sentiment = Sentiment[sentiment_str]
        except KeyError:
            sentiment = Sentiment.NEUTRAL

        try:
            confidence = int(data.get("CONFIDENCE", "5"))
            confidence = max(1, min(10, confidence))
        except ValueError:
            confidence = 5

        signal_str = data.get("SIGNAL", "WAIT")
        try:
            signal = Signal[signal_str]
        except KeyError:
            signal = Signal.WAIT

        reason = data.get("REASON", "No reason provided")

        return cls(
            sentiment=sentiment,
            confidence=confidence,
            signal=signal,
            coin=coin,
            reason=reason,
            response_time_ms=response_time_ms,
        )

    @classmethod
    def error_result(cls, coin: str, error: str) -> "AnalysisResult":
        """Create an error result when analysis fails."""
        return cls(
            sentiment=Sentiment.NEUTRAL,
            confidence=0,
            signal=Signal.WAIT,
            coin=coin,
            reason=f"Error: {error}",
            response_time_ms=0,
        )


@dataclass
class AIMetrics:
    """Tracks AI usage metrics for the session."""

    total_tokens: int = 0
    total_calls: int = 0
    total_response_time_ms: float = 0
    model_name: str = ""
    session_start: float = field(default_factory=time.time)

    # Per-session stats
    session_tokens: int = 0
    session_calls: int = 0

    @property
    def avg_response_time_ms(self) -> float:
        """Average response time across all calls."""
        if self.total_calls == 0:
            return 0
        return self.total_response_time_ms / self.total_calls

    def record_call(self, tokens: int, response_time_ms: float) -> None:
        """Record a new AI call."""
        self.total_tokens += tokens
        self.total_calls += 1
        self.total_response_time_ms += response_time_ms
        self.session_tokens += tokens
        self.session_calls += 1

    def reset_session(self) -> None:
        """Reset session-specific stats."""
        self.session_tokens = 0
        self.session_calls = 0
        self.session_start = time.time()
