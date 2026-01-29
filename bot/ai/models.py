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
class AccountContext:
    """
    Account context for AI position sizing decisions.

    Contains account state and goal information that enables the AI
    to act as a Position Sizing Strategist rather than a trade filter.
    """

    current_balance: float  # Current account balance
    initial_balance: float  # Starting balance
    account_goal: float | None  # Target balance to reach
    goal_timeframe_days: int | None  # Days to reach the goal
    days_elapsed: int  # Days since start of trading period
    base_position_pct: float  # Base position size from strategy (e.g., 10%)

    @property
    def pnl(self) -> float:
        """Current P&L in dollars."""
        return self.current_balance - self.initial_balance

    @property
    def pnl_pct(self) -> float:
        """Current P&L as percentage of initial balance."""
        if self.initial_balance <= 0:
            return 0
        return (self.pnl / self.initial_balance) * 100

    @property
    def has_goal(self) -> bool:
        """Whether account has a goal set."""
        return self.account_goal is not None and self.goal_timeframe_days is not None

    @property
    def goal_progress_pct(self) -> float | None:
        """Progress toward goal as percentage (0-100+)."""
        if not self.has_goal or self.account_goal is None:
            return None
        total_needed = self.account_goal - self.initial_balance
        if total_needed <= 0:
            return 100.0
        achieved = self.current_balance - self.initial_balance
        return (achieved / total_needed) * 100

    @property
    def time_progress_pct(self) -> float | None:
        """Time elapsed as percentage of goal timeframe."""
        if not self.has_goal or self.goal_timeframe_days is None:
            return None
        return (self.days_elapsed / self.goal_timeframe_days) * 100

    @property
    def days_remaining(self) -> int | None:
        """Days remaining to reach goal."""
        if not self.has_goal or self.goal_timeframe_days is None:
            return None
        return max(0, self.goal_timeframe_days - self.days_elapsed)

    @property
    def required_daily_return_pct(self) -> float | None:
        """Required daily return to reach goal on time."""
        if not self.has_goal or self.account_goal is None:
            return None
        days_left = self.days_remaining
        if days_left is None or days_left <= 0:
            return None
        remaining_gain_needed = self.account_goal - self.current_balance
        if remaining_gain_needed <= 0:
            return 0  # Goal already reached
        # Simple linear calculation (not compound)
        return (remaining_gain_needed / self.current_balance / days_left) * 100

    @property
    def pace_status(self) -> str:
        """Whether we're ahead, behind, or on pace for the goal."""
        if not self.has_goal:
            return "no_goal"
        goal_pct = self.goal_progress_pct
        time_pct = self.time_progress_pct
        if goal_pct is None or time_pct is None:
            return "unknown"
        if goal_pct >= 100:
            return "goal_reached"
        if time_pct <= 0:
            return "just_started"
        ratio = goal_pct / time_pct
        if ratio >= 1.2:
            return "ahead"
        elif ratio >= 0.8:
            return "on_pace"
        else:
            return "behind"


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


# =============================================================================
# Portfolio Allocation Models (Multi-Asset AI Decision Making)
# =============================================================================


@dataclass
class PortfolioOpportunity:
    """
    A trading opportunity detected in a specific market.

    Represents a potential trade that the Portfolio Allocator will
    consider alongside other opportunities across markets.
    """

    coin: str
    direction: Literal["LONG", "SHORT"]
    signal_score: float  # Weighted score from signal detectors
    signal_threshold: float  # The threshold that was met
    signals: list[str]  # Signal types that contributed
    current_price: float
    volatility: Literal["low", "medium", "high"]
    atr_percent: float  # ATR as percentage of price
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def score_strength(self) -> float:
        """How much the score exceeds the threshold (0-1 normalized)."""
        if self.signal_threshold <= 0:
            return 0.5
        excess = self.signal_score - self.signal_threshold
        max_excess = self.signal_threshold  # Assume score can be 2x threshold max
        return min(1.0, max(0.0, 0.5 + (excess / max_excess) * 0.5))

    def to_prompt_string(self) -> str:
        """Format for AI prompt."""
        return (
            f"  {self.coin}: {self.direction} | "
            f"Score: {self.signal_score:.2f} (threshold: {self.signal_threshold}) | "
            f"Volatility: {self.volatility} ({self.atr_percent:.2f}%) | "
            f"Signals: {', '.join(self.signals)}"
        )


@dataclass
class PortfolioPosition:
    """
    Current position in a specific market.

    Used to inform the AI about existing exposure when making
    new allocation decisions.
    """

    coin: str
    side: Literal["long", "short"]
    size_pct: float  # Size as % of portfolio
    entry_price: float
    current_price: float
    unrealized_pnl_pct: float

    def to_prompt_string(self) -> str:
        """Format for AI prompt."""
        return (
            f"  {self.coin}: {self.side.upper()} {self.size_pct:.1f}% | "
            f"Entry: ${self.entry_price:,.2f} | "
            f"P&L: {self.unrealized_pnl_pct:+.2f}%"
        )


@dataclass
class PortfolioState:
    """
    Complete portfolio state for AI decision making.

    Contains all information needed for the AI to make
    informed allocation decisions across multiple markets.
    """

    total_balance: float
    available_capital_pct: float  # % not in positions
    positions: list[PortfolioPosition]
    account_context: AccountContext | None  # Goal tracking

    @property
    def total_exposure_pct(self) -> float:
        """Total % of portfolio in positions."""
        return sum(p.size_pct for p in self.positions)

    @property
    def long_exposure_pct(self) -> float:
        """Total % in long positions."""
        return sum(p.size_pct for p in self.positions if p.side == "long")

    @property
    def short_exposure_pct(self) -> float:
        """Total % in short positions."""
        return sum(p.size_pct for p in self.positions if p.side == "short")

    @property
    def net_exposure_pct(self) -> float:
        """Net directional exposure (long - short)."""
        return self.long_exposure_pct - self.short_exposure_pct

    def to_prompt_string(self) -> str:
        """Format portfolio state for AI prompt."""
        lines = [
            f"Total Balance: ${self.total_balance:,.2f}",
            f"Available Capital: {self.available_capital_pct:.1f}%",
            f"Current Exposure: {self.total_exposure_pct:.1f}% "
            f"(Long: {self.long_exposure_pct:.1f}%, Short: {self.short_exposure_pct:.1f}%)",
            f"Net Direction: {self.net_exposure_pct:+.1f}%",
        ]

        if self.positions:
            lines.append("\nCurrent Positions:")
            for pos in self.positions:
                lines.append(pos.to_prompt_string())
        else:
            lines.append("\nNo open positions.")

        if self.account_context and self.account_context.has_goal:
            ctx = self.account_context
            lines.extend(
                [
                    "",
                    "GOAL TRACKING:",
                    f"  Target: ${ctx.account_goal:,.2f} in {ctx.goal_timeframe_days} days",
                    f"  Progress: {ctx.goal_progress_pct:.1f}% of goal, "
                    f"{ctx.time_progress_pct:.1f}% of time elapsed",
                    f"  Status: {ctx.pace_status.upper()}",
                ]
            )
            if ctx.required_daily_return_pct is not None:
                lines.append(f"  Required Daily Return: {ctx.required_daily_return_pct:.2f}%")

        return "\n".join(lines)


@dataclass
class AllocationDecision:
    """
    AI's decision for a single market within the portfolio allocation.
    """

    coin: str
    action: Literal["LONG", "SHORT", "SKIP", "CLOSE"]
    allocation_pct: float  # % of total portfolio to allocate
    reasoning: str

    @property
    def is_actionable(self) -> bool:
        """Whether this decision requires a trade."""
        return self.action in ("LONG", "SHORT") and self.allocation_pct > 0


@dataclass
class PortfolioAllocation:
    """
    Complete portfolio allocation decision from the AI.

    Contains allocation decisions for all considered opportunities
    plus overall reasoning about the portfolio strategy.
    """

    decisions: list[AllocationDecision]
    cash_reserve_pct: float  # % to keep in cash
    overall_reasoning: str
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def total_allocated_pct(self) -> float:
        """Total % allocated to positions."""
        return sum(d.allocation_pct for d in self.decisions if d.is_actionable)

    @property
    def actionable_decisions(self) -> list[AllocationDecision]:
        """Decisions that require trades."""
        return [d for d in self.decisions if d.is_actionable]

    def get_decision(self, coin: str) -> AllocationDecision | None:
        """Get decision for a specific coin."""
        for d in self.decisions:
            if d.coin == coin:
                return d
        return None

    def to_dict(self) -> dict:
        """Serialize for logging."""
        return {
            "decisions": [
                {
                    "coin": d.coin,
                    "action": d.action,
                    "allocation_pct": d.allocation_pct,
                    "reasoning": d.reasoning,
                }
                for d in self.decisions
            ],
            "cash_reserve_pct": self.cash_reserve_pct,
            "overall_reasoning": self.overall_reasoning,
            "timestamp": self.timestamp.isoformat(),
        }
