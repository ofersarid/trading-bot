"""
Breakout analyzer for backtesting.

Detects significant price moves and correlates them with signals
to measure signal predictive quality.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot.core.candle_aggregator import Candle
    from bot.signals.base import Signal


@dataclass
class Breakout:
    """A detected breakout (significant price move)."""

    index: int  # Candle index where breakout completed
    timestamp: datetime
    direction: str  # "UP" or "DOWN"
    start_price: float
    end_price: float
    pct_change: float
    lookback_candles: int  # How many candles the move took


@dataclass
class BreakoutSignalMatch:
    """A signal that occurred before a breakout."""

    breakout: Breakout
    signal: "Signal"
    candles_before: int  # How many candles before the breakout
    direction_match: bool  # Did signal predict breakout direction?


@dataclass
class BreakoutAnalysis:
    """
    Analysis of breakouts vs signals.

    Provides metrics for AI analysis of signal quality.
    """

    total_breakouts: int = 0
    breakouts_with_signals: int = 0  # Had at least one signal before
    breakouts_with_correct_signal: int = 0  # Had a correct-direction signal

    # Signal strength correlation
    correct_signals_avg_strength: float = 0.0
    wrong_signals_avg_strength: float = 0.0
    strength_correlation: str = "unknown"  # "positive", "negative", "neutral"

    # Raw data for detailed analysis
    breakouts: list[Breakout] = field(default_factory=list)
    matches: list[BreakoutSignalMatch] = field(default_factory=list)

    def to_metrics_string(self) -> str:
        """
        Generate concise metrics for AI analysis.

        Format designed for copy-paste into Cursor chat.
        """
        lines = [
            "## Breakout Analysis Metrics",
            "",
            f"- Total breakouts detected: {self.total_breakouts}",
            f"- Breakouts with pre-signals: {self.breakouts_with_signals}/{self.total_breakouts} "
            f"({self._pct(self.breakouts_with_signals, self.total_breakouts)}%)",
            f"- Breakouts with CORRECT signal: {self.breakouts_with_correct_signal}/{self.total_breakouts} "
            f"({self._pct(self.breakouts_with_correct_signal, self.total_breakouts)}%)",
            "",
            "### Signal Strength vs Accuracy",
            f"- Correct signals avg strength: {self.correct_signals_avg_strength:.4f}",
            f"- Wrong signals avg strength: {self.wrong_signals_avg_strength:.4f}",
            f"- Correlation: {self.strength_correlation}",
            "",
            "### Breakout Details",
        ]

        for b in self.breakouts:
            emoji = "📈" if b.direction == "UP" else "📉"
            lines.append(
                f"- {emoji} {b.timestamp.strftime('%H:%M')} {b.direction} {b.pct_change:+.2f}%"
            )

            # Find signals for this breakout
            breakout_matches = [m for m in self.matches if m.breakout == b]
            if breakout_matches:
                for m in breakout_matches:
                    match_emoji = "✅" if m.direction_match else "❌"
                    lines.append(
                        f"  - {match_emoji} {m.signal.signal_type.value} {m.signal.direction} "
                        f"(strength: {m.signal.strength:.4f}, {m.candles_before} candles before)"
                    )
            else:
                lines.append("  - ⚠️ No signals before this breakout")

        return "\n".join(lines)

    def _pct(self, num: int, denom: int) -> str:
        """Calculate percentage safely."""
        if denom == 0:
            return "0"
        return f"{num / denom * 100:.0f}"


class BreakoutAnalyzer:
    """
    Analyzes price data to find breakouts and correlate with signals.
    """

    def __init__(
        self,
        min_move_pct: float = 0.5,
        lookback_candles: int = 15,
        signal_window_candles: int = 20,
    ):
        """
        Initialize analyzer.

        Args:
            min_move_pct: Minimum % move to consider a breakout
            lookback_candles: Number of candles to measure move over
            signal_window_candles: Look for signals this many candles before breakout
        """
        self.min_move_pct = min_move_pct
        self.lookback_candles = lookback_candles
        self.signal_window_candles = signal_window_candles

    def analyze(
        self,
        candles: list["Candle"],
        signals: list[tuple[int, "Signal"]],  # (candle_index, signal)
    ) -> BreakoutAnalysis:
        """
        Analyze candles for breakouts and correlate with signals.

        Args:
            candles: List of candles from backtest
            signals: List of (candle_index, signal) tuples

        Returns:
            BreakoutAnalysis with metrics
        """
        # Find breakouts
        raw_breakouts = self._find_breakouts(candles)

        # Filter to distinct breakouts (not overlapping)
        breakouts = self._filter_distinct_breakouts(raw_breakouts)

        # Correlate with signals
        matches: list[BreakoutSignalMatch] = []
        breakouts_with_signals = 0
        breakouts_with_correct = 0

        for breakout in breakouts:
            # Find signals in window before breakout
            start_idx = max(0, breakout.index - self.lookback_candles - self.signal_window_candles)
            end_idx = breakout.index - self.lookback_candles  # Start of the breakout

            breakout_signals = [(idx, sig) for idx, sig in signals if start_idx <= idx <= end_idx]

            if breakout_signals:
                breakouts_with_signals += 1

                # Check if any signal predicted the direction
                expected_dir = "LONG" if breakout.direction == "UP" else "SHORT"
                has_correct = False

                for idx, sig in breakout_signals:
                    is_correct = sig.direction == expected_dir
                    if is_correct:
                        has_correct = True

                    matches.append(
                        BreakoutSignalMatch(
                            breakout=breakout,
                            signal=sig,
                            candles_before=breakout.index - self.lookback_candles - idx,
                            direction_match=is_correct,
                        )
                    )

                if has_correct:
                    breakouts_with_correct += 1

        # Calculate strength correlation
        correct_strengths = [m.signal.strength for m in matches if m.direction_match]
        wrong_strengths = [m.signal.strength for m in matches if not m.direction_match]

        correct_avg = sum(correct_strengths) / len(correct_strengths) if correct_strengths else 0
        wrong_avg = sum(wrong_strengths) / len(wrong_strengths) if wrong_strengths else 0

        # Determine correlation
        if correct_avg > wrong_avg * 1.2:
            correlation = "positive (strength predicts accuracy)"
        elif wrong_avg > correct_avg * 1.2:
            correlation = "NEGATIVE (stronger signals are WRONG)"
        else:
            correlation = "neutral (no clear correlation)"

        return BreakoutAnalysis(
            total_breakouts=len(breakouts),
            breakouts_with_signals=breakouts_with_signals,
            breakouts_with_correct_signal=breakouts_with_correct,
            correct_signals_avg_strength=correct_avg,
            wrong_signals_avg_strength=wrong_avg,
            strength_correlation=correlation,
            breakouts=breakouts,
            matches=matches,
        )

    def _find_breakouts(self, candles: list["Candle"]) -> list[Breakout]:
        """Find all potential breakouts in candle data."""
        breakouts = []

        for i in range(self.lookback_candles, len(candles)):
            start_price = candles[i - self.lookback_candles].close
            end_price = candles[i].close
            pct_change = (end_price - start_price) / start_price * 100

            if abs(pct_change) >= self.min_move_pct:
                breakouts.append(
                    Breakout(
                        index=i,
                        timestamp=candles[i].timestamp,
                        direction="UP" if pct_change > 0 else "DOWN",
                        start_price=start_price,
                        end_price=end_price,
                        pct_change=pct_change,
                        lookback_candles=self.lookback_candles,
                    )
                )

        return breakouts

    def _filter_distinct_breakouts(
        self, breakouts: list[Breakout], min_gap: int = 10
    ) -> list[Breakout]:
        """Filter to only distinct breakouts (not overlapping)."""
        if not breakouts:
            return []

        filtered = []
        last_idx = -min_gap - 1

        for b in breakouts:
            if b.index - last_idx > min_gap:
                filtered.append(b)
                last_idx = b.index

        return filtered
