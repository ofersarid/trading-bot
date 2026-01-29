"""
AI Decision Logger - Logs every AI decision with full context for analysis.

This module provides infrastructure for the feedback loop:
1. Log every AI decision (confirm/reject) with input context
2. Link decisions to trade outcomes after trade closes
3. Enable post-backtest analysis to identify patterns

The logged data can be used for:
- Confidence calibration analysis
- Pattern identification (which signal combos work/don't)
- Prompt improvement suggestions
- Few-shot example generation
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot.ai.models import MarketContext
    from bot.signals.base import Signal

logger = logging.getLogger(__name__)


@dataclass
class SignalSnapshot:
    """Snapshot of a signal at decision time."""

    signal_type: str
    direction: str
    strength: float
    weight: float  # Weight from strategy


@dataclass
class AIDecision:
    """
    A single AI decision with full context.

    This is the core data structure for the feedback loop.
    """

    # Unique identifier
    decision_id: str

    # Timestamp
    timestamp: datetime

    # Strategy context
    strategy_name: str

    # Input signals
    signals: list[SignalSnapshot]
    weighted_score: float
    threshold: float

    # Market context
    coin: str
    current_price: float
    volatility_level: str
    atr: float

    # AI decision
    direction: str  # LONG, SHORT, or WAIT
    confirmed: bool
    confidence: int
    reason: str

    # Mode (AI or BYPASS)
    mode: str  # "AI" or "BYPASS"

    # Outcome (filled after trade closes)
    trade_id: str | None = None
    outcome: str | None = None  # "WIN", "LOSS", "BREAKEVEN", "REJECTED"
    pnl: float | None = None
    pnl_pct: float | None = None
    exit_reason: str | None = None  # "take_profit", "stop_loss", "trailing", "manual"
    hold_duration_seconds: float | None = None

    # For rejected trades: simulated outcome if trade was taken
    simulated_outcome: str | None = None
    simulated_pnl: float | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "AIDecision":
        """Create from dictionary."""
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        data["signals"] = [SignalSnapshot(**s) for s in data["signals"]]
        return cls(**data)


@dataclass
class DecisionLog:
    """
    Collection of AI decisions from a backtest session.

    Provides methods for analysis and persistence.
    """

    decisions: list[AIDecision] = field(default_factory=list)

    # Metadata
    session_id: str = ""
    strategy_name: str = ""
    data_file: str = ""
    start_time: datetime | None = None
    end_time: datetime | None = None

    def add_decision(self, decision: AIDecision) -> None:
        """Add a decision to the log."""
        self.decisions.append(decision)

    def get_decision(self, decision_id: str) -> AIDecision | None:
        """Get a decision by ID."""
        for d in self.decisions:
            if d.decision_id == decision_id:
                return d
        return None

    def link_trade_outcome(
        self,
        decision_id: str,
        trade_id: str,
        outcome: str,
        pnl: float,
        pnl_pct: float,
        exit_reason: str,
        hold_duration: float,
    ) -> None:
        """Link a trade outcome to a decision."""
        decision = self.get_decision(decision_id)
        if decision:
            decision.trade_id = trade_id
            decision.outcome = outcome
            decision.pnl = pnl
            decision.pnl_pct = pnl_pct
            decision.exit_reason = exit_reason
            decision.hold_duration_seconds = hold_duration

    def save(self, path: Path | str) -> None:
        """Save the log to a JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "session_id": self.session_id,
            "strategy_name": self.strategy_name,
            "data_file": self.data_file,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "decisions": [d.to_dict() for d in self.decisions],
        }

        with Path(path).open("w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved {len(self.decisions)} decisions to {path}")

    @classmethod
    def load(cls, path: Path | str) -> "DecisionLog":
        """Load a log from a JSON file."""
        path = Path(path)

        with path.open() as f:
            data = json.load(f)

        log = cls(
            session_id=data.get("session_id", ""),
            strategy_name=data.get("strategy_name", ""),
            data_file=data.get("data_file", ""),
            start_time=datetime.fromisoformat(data["start_time"])
            if data.get("start_time")
            else None,
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
        )

        for d in data.get("decisions", []):
            log.decisions.append(AIDecision.from_dict(d))

        return log

    # Analysis helpers

    @property
    def confirmed_decisions(self) -> list[AIDecision]:
        """Get all confirmed (trade taken) decisions."""
        return [d for d in self.decisions if d.confirmed]

    @property
    def rejected_decisions(self) -> list[AIDecision]:
        """Get all rejected decisions."""
        return [d for d in self.decisions if not d.confirmed]

    @property
    def decisions_with_outcomes(self) -> list[AIDecision]:
        """Get decisions that have trade outcomes."""
        return [d for d in self.decisions if d.outcome is not None]

    def get_win_rate(self) -> float:
        """Calculate win rate of confirmed trades."""
        with_outcomes = [d for d in self.confirmed_decisions if d.outcome in ("WIN", "LOSS")]
        if not with_outcomes:
            return 0.0
        wins = sum(1 for d in with_outcomes if d.outcome == "WIN")
        return wins / len(with_outcomes)

    def get_confidence_accuracy(self) -> dict[str, dict]:
        """
        Calculate accuracy by confidence level.

        Returns dict like:
        {
            "8-10": {"total": 20, "wins": 15, "accuracy": 0.75},
            "6-7": {"total": 30, "wins": 18, "accuracy": 0.60},
            ...
        }
        """
        bands = {
            "8-10": {"min": 8, "max": 10, "total": 0, "wins": 0},
            "6-7": {"min": 6, "max": 7, "total": 0, "wins": 0},
            "4-5": {"min": 4, "max": 5, "total": 0, "wins": 0},
            "1-3": {"min": 1, "max": 3, "total": 0, "wins": 0},
        }

        for d in self.decisions_with_outcomes:
            if not d.confirmed:
                continue

            for band in bands.values():
                if band["min"] <= d.confidence <= band["max"]:
                    band["total"] += 1
                    if d.outcome == "WIN":
                        band["wins"] += 1
                    break

        # Calculate accuracy
        result = {}
        for band_name, band in bands.items():
            if band["total"] > 0:
                result[band_name] = {
                    "total": band["total"],
                    "wins": band["wins"],
                    "accuracy": band["wins"] / band["total"],
                }

        return result

    def get_signal_pattern_accuracy(self) -> dict[str, dict]:
        """
        Analyze which signal combinations are most/least accurate.

        Returns dict like:
        {
            "MOMENTUM+VOLUME_PROFILE": {"total": 15, "wins": 12, "accuracy": 0.80},
            "MOMENTUM+RSI": {"total": 10, "wins": 4, "accuracy": 0.40},
            ...
        }
        """
        patterns: dict[str, dict] = {}

        for d in self.decisions_with_outcomes:
            if not d.confirmed:
                continue

            # Create pattern key from signal types
            signal_types = sorted({s.signal_type for s in d.signals})
            pattern_key = "+".join(signal_types)

            if pattern_key not in patterns:
                patterns[pattern_key] = {"total": 0, "wins": 0, "losses": 0}

            patterns[pattern_key]["total"] += 1
            if d.outcome == "WIN":
                patterns[pattern_key]["wins"] += 1
            elif d.outcome == "LOSS":
                patterns[pattern_key]["losses"] += 1

        # Calculate accuracy
        for pattern in patterns.values():
            if pattern["total"] > 0:
                pattern["accuracy"] = pattern["wins"] / pattern["total"]
            else:
                pattern["accuracy"] = 0.0

        return patterns


class AIDecisionLogger:
    """
    Logger for AI decisions during backtesting.

    Usage:
        logger = AIDecisionLogger(strategy_name="momentum_based")

        # Log a decision
        decision_id = logger.log_decision(
            signals=signals,
            market_context=context,
            direction="LONG",
            confirmed=True,
            confidence=8,
            reason="Strong momentum alignment",
            mode="AI",
        )

        # Later, link trade outcome
        logger.link_outcome(decision_id, trade)

        # Save after backtest
        logger.save("data/logs/backtest_20260128.json")
    """

    def __init__(
        self,
        strategy_name: str = "",
        session_id: str | None = None,
        data_file: str = "",
    ) -> None:
        """
        Initialize the logger.

        Args:
            strategy_name: Name of the strategy being used
            session_id: Unique session identifier (auto-generated if not provided)
            data_file: Path to the data file being backtested
        """
        self.log = DecisionLog(
            session_id=session_id or datetime.now().strftime("%Y%m%d_%H%M%S"),
            strategy_name=strategy_name,
            data_file=data_file,
            start_time=datetime.now(),
        )
        self._decision_counter = 0

    def log_decision(
        self,
        signals: list["Signal"],
        market_context: "MarketContext",
        weighted_score: float,
        threshold: float,
        direction: str,
        confirmed: bool,
        confidence: int,
        reason: str,
        mode: str,
        signal_weights: dict | None = None,
    ) -> str:
        """
        Log an AI decision.

        Args:
            signals: List of signals that were evaluated
            market_context: Market context at decision time
            weighted_score: Calculated weighted score
            threshold: Threshold that needed to be met
            direction: LONG, SHORT, or WAIT
            confirmed: Whether AI confirmed the trade
            confidence: AI confidence level (1-10)
            reason: AI's reason for the decision
            mode: "AI" or "BYPASS"
            signal_weights: Strategy's signal weights (for recording)

        Returns:
            Decision ID for linking to trade outcome later
        """
        self._decision_counter += 1
        decision_id = f"{self.log.session_id}_{self._decision_counter:04d}"

        # Convert signals to snapshots
        signal_weights = signal_weights or {}
        signal_snapshots = [
            SignalSnapshot(
                signal_type=s.signal_type.value,
                direction=s.direction,
                strength=s.strength,
                weight=signal_weights.get(s.signal_type, 0.0),
            )
            for s in signals
        ]

        decision = AIDecision(
            decision_id=decision_id,
            timestamp=datetime.now(),
            strategy_name=self.log.strategy_name,
            signals=signal_snapshots,
            weighted_score=weighted_score,
            threshold=threshold,
            coin=market_context.coin,
            current_price=market_context.current_price,
            volatility_level=market_context.volatility_level,
            atr=market_context.atr,
            direction=direction,
            confirmed=confirmed,
            confidence=confidence,
            reason=reason,
            mode=mode,
        )

        self.log.add_decision(decision)
        logger.debug(
            f"Logged decision {decision_id}: {direction} "
            f"{'CONFIRMED' if confirmed else 'REJECTED'} (conf={confidence})"
        )

        return decision_id

    def link_outcome(
        self,
        decision_id: str,
        trade_id: str,
        outcome: str,
        pnl: float,
        pnl_pct: float,
        exit_reason: str,
        hold_duration: float,
    ) -> None:
        """
        Link a trade outcome to a decision.

        Args:
            decision_id: ID of the decision
            trade_id: ID of the completed trade
            outcome: "WIN", "LOSS", or "BREAKEVEN"
            pnl: Absolute P&L
            pnl_pct: P&L as percentage
            exit_reason: How trade was closed
            hold_duration: Duration in seconds
        """
        self.log.link_trade_outcome(
            decision_id=decision_id,
            trade_id=trade_id,
            outcome=outcome,
            pnl=pnl,
            pnl_pct=pnl_pct,
            exit_reason=exit_reason,
            hold_duration=hold_duration,
        )

    def mark_rejected_outcome(
        self,
        decision_id: str,
        simulated_outcome: str,
        simulated_pnl: float,
    ) -> None:
        """
        Record what would have happened if a rejected trade was taken.

        This is useful for analyzing if AI is rejecting good trades.

        Args:
            decision_id: ID of the rejected decision
            simulated_outcome: What would have happened ("WIN", "LOSS")
            simulated_pnl: Simulated P&L if trade was taken
        """
        decision = self.log.get_decision(decision_id)
        if decision:
            decision.outcome = "REJECTED"
            decision.simulated_outcome = simulated_outcome
            decision.simulated_pnl = simulated_pnl

    def finalize(self) -> DecisionLog:
        """Finalize the log and return it."""
        self.log.end_time = datetime.now()
        return self.log

    def save(self, path: Path | str) -> None:
        """Save the log to a file."""
        self.log.end_time = datetime.now()
        self.log.save(path)

    @property
    def decision_count(self) -> int:
        """Number of decisions logged."""
        return len(self.log.decisions)
