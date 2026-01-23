"""Data models for AI analysis responses and metrics."""

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Literal


class Sentiment(Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class LegacySignal(Enum):
    """Legacy signal enum - kept for backward compatibility."""

    LONG = "LONG"
    SHORT = "SHORT"
    WAIT = "WAIT"


# Alias for backward compatibility
Signal = LegacySignal


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
            signal = LegacySignal[signal_str]
        except KeyError:
            signal = LegacySignal.WAIT

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


# =============================================================================
# New models for Signal-based AI (Layer 3 of backtesting architecture)
# =============================================================================


@dataclass
class MarketContext:
    """
    Market context for AI decision making.

    Contains volatility and price information needed for
    stop-loss and take-profit calculations.
    """

    coin: str
    current_price: float
    atr: float  # Average True Range
    atr_percent: float  # ATR as % of price
    volatility_level: Literal["low", "medium", "high"]

    @classmethod
    def from_atr(cls, coin: str, current_price: float, atr: float) -> "MarketContext":
        """Create MarketContext from ATR value."""
        atr_pct = (atr / current_price) * 100 if current_price > 0 else 0

        # Classify volatility based on ATR%
        volatility: Literal["low", "medium", "high"]
        if atr_pct < 0.5:
            volatility = "low"
        elif atr_pct < 1.5:
            volatility = "medium"
        else:
            volatility = "high"

        return cls(
            coin=coin,
            current_price=current_price,
            atr=atr,
            atr_percent=atr_pct,
            volatility_level=volatility,
        )


@dataclass
class TradePlan:
    """
    A complete trade plan output by the AI.

    Contains all parameters needed to execute and manage a trade,
    including entry, exit, and trailing stop configuration.
    """

    action: Literal["LONG", "SHORT", "WAIT"]
    coin: str
    size_pct: float  # Position size as % of balance
    stop_loss: float  # Price level
    take_profit: float  # Price level
    trail_activation: float  # Price to activate trailing stop
    trail_distance_pct: float  # Trail distance as % of price
    confidence: int  # 1-10
    reason: str
    signals_considered: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def is_actionable(self) -> bool:
        """True if this plan suggests taking a position."""
        return self.action in ("LONG", "SHORT")

    @property
    def is_long(self) -> bool:
        """True if this is a LONG trade."""
        return self.action == "LONG"

    @property
    def is_short(self) -> bool:
        """True if this is a SHORT trade."""
        return self.action == "SHORT"

    @property
    def risk_reward_ratio(self) -> float | None:
        """Calculate risk/reward ratio based on entry and stops."""
        if self.action == "WAIT":
            return None

        # Assuming entry at current time (would need current_price)
        # This is a simplified calculation
        return 0.0  # Placeholder - calculated during execution

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "action": self.action,
            "coin": self.coin,
            "size_pct": self.size_pct,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "trail_activation": self.trail_activation,
            "trail_distance_pct": self.trail_distance_pct,
            "confidence": self.confidence,
            "reason": self.reason,
            "signals_considered": self.signals_considered,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def wait(cls, coin: str, reason: str = "No actionable signals") -> "TradePlan":
        """Create a WAIT plan (no action)."""
        return cls(
            action="WAIT",
            coin=coin,
            size_pct=0,
            stop_loss=0,
            take_profit=0,
            trail_activation=0,
            trail_distance_pct=0,
            confidence=0,
            reason=reason,
        )

    @classmethod
    def from_text(
        cls,
        text: str,
        coin: str,
        signals_considered: list[str],
    ) -> "TradePlan":
        """
        Parse structured AI response into TradePlan.

        Expected format:
        ACTION: LONG
        SIZE: 10
        STOP_LOSS: 99500
        TAKE_PROFIT: 101000
        TRAIL_ACTIVATION: 100500
        TRAIL_DISTANCE: 0.3
        CONFIDENCE: 7
        REASON: Strong momentum with RSI confirmation
        """
        lines = text.strip().split("\n")
        data: dict[str, str] = {}

        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                data[key.strip().upper()] = value.strip()

        # Parse action
        action_str = data.get("ACTION", "WAIT").upper()
        if action_str not in ("LONG", "SHORT", "WAIT"):
            action_str = "WAIT"

        # Parse numeric fields with defaults
        def parse_float(key: str, default: float = 0.0) -> float:
            try:
                return float(data.get(key, str(default)))
            except ValueError:
                return default

        def parse_int(key: str, default: int = 0) -> int:
            try:
                return int(data.get(key, str(default)))
            except ValueError:
                return default

        return cls(
            action=action_str,  # type: ignore[arg-type]
            coin=coin,
            size_pct=parse_float("SIZE", 0),
            stop_loss=parse_float("STOP_LOSS", 0),
            take_profit=parse_float("TAKE_PROFIT", 0),
            trail_activation=parse_float("TRAIL_ACTIVATION", 0),
            trail_distance_pct=parse_float("TRAIL_DISTANCE", 0.3),
            confidence=parse_int("CONFIDENCE", 5),
            reason=data.get("REASON", "No reason provided"),
            signals_considered=signals_considered,
        )
