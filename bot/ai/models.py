"""Data models for AI analysis responses and metrics."""

import time
from dataclasses import dataclass, field
from enum import Enum


class Sentiment(Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class Signal(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    WAIT = "WAIT"


class Freshness(Enum):
    """How fresh/extended the current move is."""

    FRESH = "FRESH"  # Just starting
    DEVELOPING = "DEVELOPING"  # Building
    EXTENDED = "EXTENDED"  # May be exhausting
    EXHAUSTED = "EXHAUSTED"  # Reversal zone


@dataclass
class CoinMomentum:
    """Momentum data for a single coin."""

    coin: str
    momentum_pct: float
    direction: str  # "UP", "DOWN", "FLAT"

    @classmethod
    def from_value(cls, coin: str, momentum: float) -> "CoinMomentum":
        if momentum > 0.05:
            direction = "UP"
        elif momentum < -0.05:
            direction = "DOWN"
        else:
            direction = "FLAT"
        return cls(coin=coin, momentum_pct=momentum, direction=direction)


@dataclass
class AnalysisResult:
    """Result of AI market analysis."""

    sentiment: Sentiment
    confidence: int  # 1-10
    signal: Signal
    coin: str
    reason: str
    response_time_ms: float

    # Enhanced fields
    momentum_by_coin: dict[str, float] = field(default_factory=dict)  # {coin: momentum%}
    pressure_score: int = 50  # 0-100
    pressure_label: str = "Neutral"  # Human-readable
    freshness: Freshness = Freshness.DEVELOPING

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

        # Parse enhanced fields
        momentum_by_coin = cls._parse_momentum(data.get("MOMENTUM", ""))
        pressure_score, pressure_label = cls._parse_pressure(data.get("PRESSURE", "50"))
        freshness = cls._parse_freshness(data.get("FRESHNESS", "DEVELOPING"))

        return cls(
            sentiment=sentiment,
            confidence=confidence,
            signal=signal,
            coin=coin,
            reason=reason,
            response_time_ms=response_time_ms,
            momentum_by_coin=momentum_by_coin,
            pressure_score=pressure_score,
            pressure_label=pressure_label,
            freshness=freshness,
        )

    @staticmethod
    def _parse_momentum(momentum_str: str) -> dict[str, float]:
        """Parse momentum string like 'BTC +0.45% | ETH +0.32%'"""
        result: dict[str, float] = {}
        if not momentum_str:
            return result

        parts = momentum_str.split("|")
        for part in parts:
            part = part.strip()
            if not part:
                continue
            # Parse "BTC +0.45%" or "BTC -0.32%"
            tokens = part.split()
            if len(tokens) >= 2:
                coin = tokens[0].strip()
                try:
                    # Remove % sign and parse
                    value_str = tokens[1].replace("%", "").strip()
                    result[coin] = float(value_str)
                except ValueError:
                    pass
        return result

    @staticmethod
    def _parse_pressure(pressure_str: str) -> tuple[int, str]:
        """Parse pressure string like '72 (Strong Buying)' or just '72'"""
        try:
            # Handle format: "72 (Strong Buying)"
            if "(" in pressure_str:
                score_part = pressure_str.split("(")[0].strip()
                label_part = pressure_str.split("(")[1].rstrip(")").strip()
                return int(score_part), label_part
            else:
                score = int(pressure_str)
                # Generate label from score
                if score < 30:
                    label = "Strong Selling"
                elif score < 45:
                    label = "Moderate Selling"
                elif score < 55:
                    label = "Neutral"
                elif score < 70:
                    label = "Moderate Buying"
                else:
                    label = "Strong Buying"
                return score, label
        except ValueError:
            return 50, "Neutral"

    @staticmethod
    def _parse_freshness(freshness_str: str) -> Freshness:
        """Parse freshness string."""
        try:
            return Freshness[freshness_str.upper()]
        except KeyError:
            return Freshness.DEVELOPING

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
