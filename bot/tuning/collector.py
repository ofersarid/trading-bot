"""
Feedback Collector

Captures every trade with a snapshot of the parameters used,
enabling analysis of which parameter combinations work best.
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from bot.simulation.models import Side


@dataclass
class ParameterSnapshot:
    """Snapshot of all tunable parameters at trade time."""

    # Entry thresholds
    track_threshold_pct: float
    trade_threshold_pct: float
    momentum_timeframe_seconds: int

    # Exit thresholds
    take_profit_pct: float
    stop_loss_pct: float

    # Position management
    position_size_pct: float
    cooldown_seconds: float
    max_concurrent_positions: int

    # Market context
    market_condition: str  # "very_calm", "calm", "active", "volatile", "extreme"
    btc_momentum_at_entry: float | None = None
    eth_momentum_at_entry: float | None = None


@dataclass
class TradeRecord:
    """Complete record of a trade for analysis."""

    # Trade identification
    trade_id: str
    timestamp: str

    # Asset info
    coin: str
    side: str  # "LONG" or "SHORT"

    # Price data
    entry_price: float
    exit_price: float
    entry_momentum_pct: float  # Momentum at entry

    # Position details
    size: float
    notional_value: float

    # Outcome
    outcome: Literal["take_profit", "stop_loss", "emergency_exit", "manual", "ai_exit"]
    pnl_usd: float
    pnl_pct: float
    fees_paid: float
    duration_seconds: float

    # Parameters used
    parameters: ParameterSnapshot

    # Additional context
    notes: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        return result


class FeedbackCollector:
    """
    Collects and persists trade feedback for parameter tuning.

    Every trade is logged with:
    - The exact parameters used
    - Market conditions at entry
    - Trade outcome and metrics

    This enables analysis of which parameter combinations
    work best under different market conditions.
    """

    def __init__(self, data_dir: str = "data/feedback"):
        """
        Initialize the feedback collector.

        Args:
            data_dir: Directory to store feedback data
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.trades: list[TradeRecord] = []
        self._trade_counter = 0
        self._load_existing_trades()

    def _load_existing_trades(self):
        """Load existing trades from disk."""
        trades_file = self.data_dir / "trades.json"
        if trades_file.exists():
            try:
                with trades_file.open() as f:
                    data = json.load(f)
                    self._trade_counter = data.get("counter", 0)
                    for trade_dict in data.get("trades", []):
                        params = ParameterSnapshot(**trade_dict.pop("parameters"))
                        self.trades.append(TradeRecord(**trade_dict, parameters=params))
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                print(f"Warning: Could not load existing trades: {e}")

    def _save_trades(self):
        """Persist trades to disk."""
        trades_file = self.data_dir / "trades.json"
        data = {
            "counter": self._trade_counter,
            "trades": [t.to_dict() for t in self.trades],
        }
        with trades_file.open("w") as f:
            json.dump(data, f, indent=2)

    def _generate_trade_id(self) -> str:
        """Generate a unique trade ID."""
        self._trade_counter += 1
        return f"T{self._trade_counter:06d}"

    def record_trade(
        self,
        # Asset info
        coin: str,
        side: Side | str,
        # Price data
        entry_price: float,
        exit_price: float,
        entry_momentum_pct: float,
        # Position details
        size: float,
        # Outcome
        outcome: Literal["take_profit", "stop_loss", "emergency_exit", "manual", "ai_exit"],
        pnl_usd: float,
        fees_paid: float,
        entry_time: datetime,
        exit_time: datetime,
        # Parameters
        track_threshold_pct: float,
        trade_threshold_pct: float,
        momentum_timeframe_seconds: int,
        take_profit_pct: float,
        stop_loss_pct: float,
        position_size_pct: float,
        cooldown_seconds: float,
        max_concurrent_positions: int,
        # Market context
        market_condition: str,
        btc_momentum: float | None = None,
        eth_momentum: float | None = None,
        notes: str = "",
    ) -> TradeRecord:
        """
        Record a completed trade.

        Args:
            coin: Asset symbol (e.g., "BTC")
            side: "LONG" or "SHORT" or Side enum
            entry_price: Price at entry
            exit_price: Price at exit
            entry_momentum_pct: Momentum % that triggered entry
            size: Position size in asset units
            outcome: How the trade was closed
            pnl_usd: Profit/loss in USD
            fees_paid: Total fees for the trade
            entry_time: When position was opened
            exit_time: When position was closed
            track_threshold_pct: Track threshold used
            trade_threshold_pct: Trade threshold used
            momentum_timeframe_seconds: Lookback period used
            take_profit_pct: Take profit % used
            stop_loss_pct: Stop loss % used
            position_size_pct: Position size % used
            cooldown_seconds: Cooldown period used
            max_concurrent_positions: Max positions allowed
            market_condition: Market state at entry
            btc_momentum: BTC momentum at entry (for correlation)
            eth_momentum: ETH momentum at entry (for correlation)
            notes: Any additional notes

        Returns:
            The created TradeRecord
        """
        side_str = side.value if isinstance(side, Side) else side

        notional_value = size * entry_price
        pnl_pct = (pnl_usd / notional_value) * 100 if notional_value > 0 else 0
        duration = (exit_time - entry_time).total_seconds()

        params = ParameterSnapshot(
            track_threshold_pct=track_threshold_pct,
            trade_threshold_pct=trade_threshold_pct,
            momentum_timeframe_seconds=momentum_timeframe_seconds,
            take_profit_pct=take_profit_pct,
            stop_loss_pct=stop_loss_pct,
            position_size_pct=position_size_pct,
            cooldown_seconds=cooldown_seconds,
            max_concurrent_positions=max_concurrent_positions,
            market_condition=market_condition,
            btc_momentum_at_entry=btc_momentum,
            eth_momentum_at_entry=eth_momentum,
        )

        record = TradeRecord(
            trade_id=self._generate_trade_id(),
            timestamp=exit_time.isoformat(),
            coin=coin,
            side=side_str,
            entry_price=entry_price,
            exit_price=exit_price,
            entry_momentum_pct=entry_momentum_pct,
            size=size,
            notional_value=notional_value,
            outcome=outcome,
            pnl_usd=pnl_usd,
            pnl_pct=pnl_pct,
            fees_paid=fees_paid,
            duration_seconds=duration,
            parameters=params,
            notes=notes,
        )

        self.trades.append(record)
        self._save_trades()

        return record

    def get_trades(
        self,
        coin: str | None = None,
        outcome: str | None = None,
        market_condition: str | None = None,
        min_date: datetime | None = None,
        max_date: datetime | None = None,
    ) -> list[TradeRecord]:
        """
        Get trades matching filters.

        Args:
            coin: Filter by coin symbol
            outcome: Filter by outcome type
            market_condition: Filter by market condition
            min_date: Filter by minimum date
            max_date: Filter by maximum date

        Returns:
            List of matching trades
        """
        result = self.trades

        if coin:
            result = [t for t in result if t.coin == coin]
        if outcome:
            result = [t for t in result if t.outcome == outcome]
        if market_condition:
            result = [t for t in result if t.parameters.market_condition == market_condition]
        if min_date:
            result = [t for t in result if datetime.fromisoformat(t.timestamp) >= min_date]
        if max_date:
            result = [t for t in result if datetime.fromisoformat(t.timestamp) <= max_date]

        return result

    def get_trades_since(self, since: datetime | None) -> list[TradeRecord]:
        """
        Get trades executed since a specific timestamp.

        Args:
            since: Only return trades after this time. If None, returns all trades.

        Returns:
            List of trades since the timestamp
        """
        if since is None:
            return self.trades

        return [t for t in self.trades if datetime.fromisoformat(t.timestamp) > since]

    def get_new_trades_count(self, since: datetime | None) -> int:
        """
        Get count of trades since a specific timestamp.

        Args:
            since: Count trades after this time. If None, returns total count.

        Returns:
            Number of trades since the timestamp
        """
        return len(self.get_trades_since(since))

    def get_summary_stats(self) -> dict:
        """Get summary statistics across all trades."""
        if not self.trades:
            return {"total_trades": 0}

        wins = [t for t in self.trades if t.pnl_usd > 0]
        losses = [t for t in self.trades if t.pnl_usd <= 0]

        total_pnl = sum(t.pnl_usd for t in self.trades)
        total_fees = sum(t.fees_paid for t in self.trades)

        return {
            "total_trades": len(self.trades),
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate_pct": (len(wins) / len(self.trades)) * 100,
            "total_pnl_usd": total_pnl,
            "total_fees_usd": total_fees,
            "net_pnl_usd": total_pnl - total_fees,
            "avg_win_usd": sum(t.pnl_usd for t in wins) / len(wins) if wins else 0,
            "avg_loss_usd": sum(t.pnl_usd for t in losses) / len(losses) if losses else 0,
            "avg_duration_seconds": sum(t.duration_seconds for t in self.trades) / len(self.trades),
            "outcomes": {
                "take_profit": len([t for t in self.trades if t.outcome == "take_profit"]),
                "stop_loss": len([t for t in self.trades if t.outcome == "stop_loss"]),
                "emergency_exit": len([t for t in self.trades if t.outcome == "emergency_exit"]),
                "manual": len([t for t in self.trades if t.outcome == "manual"]),
            },
        }

    def clear(self):
        """Clear all trade records."""
        self.trades = []
        self._trade_counter = 0
        self._save_trades()
