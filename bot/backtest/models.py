"""
Data models for backtesting configuration and results.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot.backtest.breakout_analyzer import BreakoutAnalysis
    from bot.simulation.models import Trade


@dataclass
class BacktestConfig:
    """
    Configuration for a backtest run.

    Defines the data source, trading parameters, and which
    components to use during the backtest.
    """

    data_source: str  # Path to CSV file
    coins: list[str]  # Coins to trade (derived from data if not specified)
    initial_balance: float = 10000.0
    strategy_name: str = "momentum_scalper"  # Name of strategy to use
    signal_detectors: list[str] = field(default_factory=lambda: ["momentum", "rsi", "macd"])
    ai_enabled: bool = True  # False = signals-only mode, True = AI decisions

    # Optional date range filter (uses full data if not specified)
    start_date: datetime | None = None
    end_date: datetime | None = None

    # Performance tuning
    min_candles_for_signals: int = 50  # Warm-up period before generating signals
    max_ai_calls_per_hour: int = 100  # Rate limit for AI

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.initial_balance <= 0:
            raise ValueError("initial_balance must be positive")
        if not self.signal_detectors:
            raise ValueError("At least one signal detector required")

    @classmethod
    def from_dict(cls, data: dict) -> "BacktestConfig":
        """Create config from dictionary."""
        return cls(
            data_source=data["data_source"],
            coins=data.get("coins", []),
            initial_balance=data.get("initial_balance", 10000.0),
            strategy_name=data.get("strategy_name", "momentum_scalper"),
            signal_detectors=data.get("signal_detectors", ["momentum", "rsi", "macd"]),
            ai_enabled=data.get("ai_enabled", True),
            start_date=datetime.fromisoformat(data["start_date"])
            if data.get("start_date")
            else None,
            end_date=datetime.fromisoformat(data["end_date"]) if data.get("end_date") else None,
        )


@dataclass
class BacktestResult:
    """
    Results from a completed backtest run.

    Contains performance metrics, trade history, and execution statistics.
    """

    config: BacktestConfig
    trades: list["Trade"]
    final_balance: float
    final_equity: float

    # Performance metrics
    pnl: float  # Total P&L
    pnl_pct: float  # P&L as % of initial balance
    win_rate: float  # % of winning trades
    max_drawdown: float  # Maximum drawdown %
    max_drawdown_duration: float  # Longest drawdown in seconds

    # Risk-adjusted metrics
    sharpe_ratio: float  # Risk-adjusted return
    profit_factor: float  # Gross profit / gross loss

    # Execution statistics
    signals_generated: int
    ai_calls_made: int
    execution_time_seconds: float

    # Time range
    start_time: datetime
    end_time: datetime
    total_candles: int

    # Breakout analysis (optional, populated after run)
    breakout_analysis: "BreakoutAnalysis | None" = None

    # Signal accuracy report (optional, populated after run)
    signal_accuracy_report: dict | None = None

    @property
    def total_trades(self) -> int:
        """Total number of completed trades."""
        return len(self.trades)

    @property
    def winning_trades(self) -> int:
        """Number of winning trades."""
        return sum(1 for t in self.trades if t.pnl > 0)

    @property
    def losing_trades(self) -> int:
        """Number of losing trades."""
        return sum(1 for t in self.trades if t.pnl < 0)

    @property
    def avg_win(self) -> float:
        """Average profit on winning trades."""
        wins = [t.pnl for t in self.trades if t.pnl > 0]
        return sum(wins) / len(wins) if wins else 0

    @property
    def avg_loss(self) -> float:
        """Average loss on losing trades."""
        losses = [t.pnl for t in self.trades if t.pnl < 0]
        return sum(losses) / len(losses) if losses else 0

    @property
    def avg_trade_duration(self) -> float:
        """Average trade duration in seconds."""
        if not self.trades:
            return 0
        return sum(t.duration_seconds for t in self.trades) / len(self.trades)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "config": {
                "data_source": self.config.data_source,
                "coins": self.config.coins,
                "initial_balance": self.config.initial_balance,
                "strategy_name": self.config.strategy_name,
                "signal_detectors": self.config.signal_detectors,
                "ai_enabled": self.config.ai_enabled,
            },
            "performance": {
                "final_balance": self.final_balance,
                "final_equity": self.final_equity,
                "pnl": self.pnl,
                "pnl_pct": self.pnl_pct,
                "win_rate": self.win_rate,
                "max_drawdown": self.max_drawdown,
                "sharpe_ratio": self.sharpe_ratio,
                "profit_factor": self.profit_factor,
            },
            "trades": {
                "total": self.total_trades,
                "winning": self.winning_trades,
                "losing": self.losing_trades,
                "avg_win": self.avg_win,
                "avg_loss": self.avg_loss,
                "avg_duration_seconds": self.avg_trade_duration,
            },
            "execution": {
                "signals_generated": self.signals_generated,
                "ai_calls_made": self.ai_calls_made,
                "execution_time_seconds": self.execution_time_seconds,
                "total_candles": self.total_candles,
            },
            "time_range": {
                "start": self.start_time.isoformat(),
                "end": self.end_time.isoformat(),
            },
        }

    def print_summary(self) -> None:
        """Print a summary of backtest results."""
        print("\n" + "=" * 60)
        print("📊 BACKTEST RESULTS")
        print("=" * 60)

        print(
            f"\n📅 Period: {self.start_time.strftime('%Y-%m-%d %H:%M')} to "
            f"{self.end_time.strftime('%Y-%m-%d %H:%M')}"
        )
        print(f"📈 Candles: {self.total_candles}")

        print("\n💰 PERFORMANCE")
        print("-" * 40)
        print(f"  Initial Balance: ${self.config.initial_balance:,.2f}")
        print(f"  Final Balance:   ${self.final_balance:,.2f}")
        print(f"  Final Equity:    ${self.final_equity:,.2f}")
        print(f"  Total P&L:       ${self.pnl:+,.2f} ({self.pnl_pct:+.2f}%)")

        print("\n📊 RISK METRICS")
        print("-" * 40)
        print(f"  Win Rate:        {self.win_rate:.1f}%")
        print(f"  Max Drawdown:    {self.max_drawdown:.2f}%")
        print(f"  Sharpe Ratio:    {self.sharpe_ratio:.2f}")
        print(f"  Profit Factor:   {self.profit_factor:.2f}")

        print("\n🔄 TRADE STATISTICS")
        print("-" * 40)
        print(f"  Total Trades:    {self.total_trades}")
        print(f"  Winning:         {self.winning_trades}")
        print(f"  Losing:          {self.losing_trades}")
        print(f"  Avg Win:         ${self.avg_win:+,.2f}")
        print(f"  Avg Loss:        ${self.avg_loss:+,.2f}")
        print(f"  Avg Duration:    {self.avg_trade_duration:.0f}s")

        print("\n⚙️  EXECUTION")
        print("-" * 40)
        print(f"  Signals:         {self.signals_generated}")
        print(f"  AI Calls:        {self.ai_calls_made}")
        print(f"  Runtime:         {self.execution_time_seconds:.1f}s")

        print("=" * 60 + "\n")

        # Print breakout analysis if available
        if self.breakout_analysis:
            self._print_breakout_analysis()

        # Print signal accuracy report if available
        if self.signal_accuracy_report:
            self._print_signal_accuracy()

    def _print_breakout_analysis(self) -> None:
        """Print breakout analysis section."""
        ba = self.breakout_analysis
        if not ba:
            return

        print("\n" + "=" * 60)
        print("🔍 BREAKOUT ANALYSIS (for AI)")
        print("=" * 60)
        print(ba.to_metrics_string())
        print("=" * 60 + "\n")

    def _print_signal_accuracy(self) -> None:
        """Print signal accuracy report section."""
        if not self.signal_accuracy_report:
            return

        print("\n" + "=" * 60)
        print("📈 SIGNAL ACCURACY REPORT")
        print("=" * 60)

        for signal_type, data in self.signal_accuracy_report.items():
            total = data.get("total_signals", 0)
            correct = data.get("correct_predictions", 0)
            accuracy = data.get("accuracy", 0)

            print(f"\n{signal_type}:")
            print(f"  Total Signals:      {total}")
            print(f"  Correct:            {correct}")
            print(f"  Accuracy:           {accuracy:.1%}")

            # Print strength bands if available
            if "strength_bands" in data:
                print("  Strength Bands:")
                for band in data["strength_bands"]:
                    if band["total"] > 0:
                        print(
                            f"    [{band['range']}]: "
                            f"{band['correct']}/{band['total']} "
                            f"({band['accuracy']:.1%})"
                        )

        print("\n" + "=" * 60 + "\n")


@dataclass
class EquityPoint:
    """A single point in the equity curve."""

    timestamp: datetime
    equity: float
    balance: float
    positions_value: float
