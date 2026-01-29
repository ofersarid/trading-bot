"""
AI Decision Analyzer - Analyzes logged AI decisions to identify improvement opportunities.

This module processes decision logs from backtests to:
1. Identify confidence calibration issues
2. Find problematic signal patterns
3. Generate actionable improvement suggestions
4. Produce few-shot examples from best/worst trades

The analysis feeds back into prompt improvements and strategy tuning.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from bot.ai.decision_logger import AIDecision, DecisionLog

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceCalibration:
    """Analysis of AI confidence vs actual outcomes."""

    band: str  # e.g., "8-10"
    min_confidence: int
    max_confidence: int
    total_trades: int
    wins: int
    losses: int
    actual_win_rate: float
    expected_win_rate: float  # Based on confidence (e.g., 80% for 8-10)
    calibration_error: float  # Difference between actual and expected
    is_overconfident: bool
    is_underconfident: bool


@dataclass
class SignalPatternAnalysis:
    """Analysis of a specific signal combination pattern."""

    pattern: str  # e.g., "MOMENTUM+VOLUME_PROFILE"
    signal_types: list[str]
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    avg_pnl: float
    avg_confidence: float
    is_profitable: bool
    recommendation: str  # "TRUST", "AVOID", "NEEDS_DATA"


@dataclass
class RejectionAnalysis:
    """Analysis of rejected trades."""

    total_rejected: int
    would_have_won: int
    would_have_lost: int
    missed_opportunity_rate: float  # % of rejected that would have won
    avg_missed_pnl: float  # Average P&L of missed opportunities
    recommendation: str


@dataclass
class FewShotExample:
    """A trade example suitable for few-shot prompting."""

    signals_description: str
    direction: str
    confidence: int
    outcome: str
    pnl_pct: float
    reason: str
    lesson: str  # What this example teaches


@dataclass
class AIAnalysisReport:
    """Complete analysis report for AI performance."""

    # Summary metrics
    total_decisions: int
    confirmed_trades: int
    rejected_trades: int
    overall_win_rate: float
    overall_pnl: float

    # Confidence calibration
    confidence_calibration: list[ConfidenceCalibration]
    confidence_diagnosis: str
    confidence_recommendation: str

    # Signal patterns
    best_patterns: list[SignalPatternAnalysis]
    worst_patterns: list[SignalPatternAnalysis]
    pattern_recommendations: list[str]

    # Rejection analysis
    rejection_analysis: RejectionAnalysis | None

    # Few-shot examples
    good_examples: list[FewShotExample]
    bad_examples: list[FewShotExample]

    # Overall diagnosis
    primary_issue: str  # "CONFIDENCE", "PATTERNS", "REJECTIONS", "NONE"
    improvement_suggestions: list[str]

    def to_prompt_injection(self) -> str:
        """
        Generate text to inject into AI prompts based on analysis.

        This creates the "learned patterns" section for dynamic prompt injection.
        """
        lines = ["## LEARNED PATTERNS (from historical analysis)\n"]

        # Add confidence guidance
        if self.confidence_diagnosis:
            lines.append(f"**Confidence Calibration:** {self.confidence_diagnosis}")
            lines.append("")

        # Add pattern guidance
        if self.best_patterns:
            lines.append("**HIGH CONFIDENCE patterns (confirm more readily):**")
            for p in self.best_patterns[:3]:
                lines.append(f"- {p.pattern} → {p.win_rate:.0%} historical win rate")
            lines.append("")

        if self.worst_patterns:
            lines.append("**LOW CONFIDENCE patterns (be skeptical):**")
            for p in self.worst_patterns[:3]:
                lines.append(f"- {p.pattern} → {p.win_rate:.0%} historical win rate")
            lines.append("")

        return "\n".join(lines)

    def to_few_shot_examples(self) -> str:
        """
        Generate few-shot examples section for prompts.
        """
        lines = ["## SIMILAR HISTORICAL SETUPS\n"]

        # Add good examples
        for i, ex in enumerate(self.good_examples[:2], 1):
            lines.append(f"Example {i} ({ex.outcome} {ex.pnl_pct:+.2f}%):")
            lines.append(f"  Signals: {ex.signals_description}")
            lines.append(f"  Decision: {ex.direction} (confidence {ex.confidence})")
            lines.append(f"  Lesson: {ex.lesson}")
            lines.append("")

        # Add a bad example for contrast
        if self.bad_examples:
            ex = self.bad_examples[0]
            lines.append(
                f"Example {len(self.good_examples) + 1} ({ex.outcome} {ex.pnl_pct:+.2f}%) - MISTAKE:"
            )
            lines.append(f"  Signals: {ex.signals_description}")
            lines.append(f"  Decision: {ex.direction} (confidence {ex.confidence})")
            lines.append(f"  Lesson: {ex.lesson}")
            lines.append("")

        return "\n".join(lines)

    def print_summary(self) -> None:
        """Print a summary of the analysis."""
        print("\n" + "=" * 60)
        print("🤖 AI DECISION ANALYSIS")
        print("=" * 60)

        print("\n📊 OVERVIEW")
        print("-" * 40)
        print(f"  Total Decisions:    {self.total_decisions}")
        print(f"  Confirmed Trades:   {self.confirmed_trades}")
        print(f"  Rejected Trades:    {self.rejected_trades}")
        print(f"  Overall Win Rate:   {self.overall_win_rate:.1%}")
        print(f"  Overall P&L:        ${self.overall_pnl:+,.2f}")

        print("\n📈 CONFIDENCE CALIBRATION")
        print("-" * 40)
        for cal in self.confidence_calibration:
            status = (
                "⚠️ OVERCONFIDENT"
                if cal.is_overconfident
                else ("⚠️ UNDERCONFIDENT" if cal.is_underconfident else "✅ CALIBRATED")
            )
            print(
                f"  Confidence {cal.band}: {cal.actual_win_rate:.0%} win rate "
                f"(expected ~{cal.expected_win_rate:.0%}) {status}"
            )
        print(f"\n  Diagnosis: {self.confidence_diagnosis}")
        print(f"  Recommendation: {self.confidence_recommendation}")

        print("\n🎯 SIGNAL PATTERNS")
        print("-" * 40)
        if self.best_patterns:
            print("  Best Patterns:")
            for p in self.best_patterns[:3]:
                print(f"    ✅ {p.pattern}: {p.win_rate:.0%} win rate ({p.total_trades} trades)")

        if self.worst_patterns:
            print("\n  Worst Patterns:")
            for p in self.worst_patterns[:3]:
                print(f"    ❌ {p.pattern}: {p.win_rate:.0%} win rate ({p.total_trades} trades)")

        if self.rejection_analysis:
            print("\n🚫 REJECTION ANALYSIS")
            print("-" * 40)
            ra = self.rejection_analysis
            print(f"  Total Rejected:         {ra.total_rejected}")
            print(
                f"  Would Have Won:         {ra.would_have_won} ({ra.missed_opportunity_rate:.0%})"
            )
            print(f"  Avg Missed P&L:         ${ra.avg_missed_pnl:+,.2f}")
            print(f"  Recommendation:         {ra.recommendation}")

        print("\n💡 IMPROVEMENT SUGGESTIONS")
        print("-" * 40)
        print(f"  Primary Issue: {self.primary_issue}")
        for i, suggestion in enumerate(self.improvement_suggestions, 1):
            print(f"  {i}. {suggestion}")

        print("\n" + "=" * 60)


class AIDecisionAnalyzer:
    """
    Analyzes AI decision logs to identify improvement opportunities.

    Usage:
        analyzer = AIDecisionAnalyzer()
        report = analyzer.analyze(decision_log)
        report.print_summary()

        # Get prompt injection text
        prompt_addition = report.to_prompt_injection()
    """

    # Expected win rates by confidence level (ideal calibration)
    EXPECTED_WIN_RATES = {
        "8-10": 0.75,  # High confidence should win ~75%
        "6-7": 0.55,  # Medium confidence ~55%
        "4-5": 0.45,  # Low confidence ~45%
        "1-3": 0.30,  # Very low ~30%
    }

    # Thresholds for pattern classification
    MIN_PATTERN_TRADES = 3  # Need at least 3 trades to evaluate pattern
    GOOD_PATTERN_WIN_RATE = 0.60
    BAD_PATTERN_WIN_RATE = 0.40

    def analyze(self, log: DecisionLog) -> AIAnalysisReport:
        """
        Analyze a decision log and generate a report.

        Args:
            log: DecisionLog from a backtest session

        Returns:
            AIAnalysisReport with analysis and recommendations
        """
        # Summary metrics
        total_decisions = len(log.decisions)
        confirmed = log.confirmed_decisions
        rejected = log.rejected_decisions
        with_outcomes = log.decisions_with_outcomes

        overall_win_rate = log.get_win_rate()
        overall_pnl = sum(d.pnl or 0 for d in with_outcomes if d.confirmed)

        # Confidence calibration
        confidence_calibration = self._analyze_confidence(log)
        conf_diagnosis, conf_recommendation = self._diagnose_confidence(confidence_calibration)

        # Signal patterns
        pattern_data = log.get_signal_pattern_accuracy()
        best_patterns, worst_patterns = self._analyze_patterns(pattern_data)
        pattern_recommendations = self._generate_pattern_recommendations(
            best_patterns, worst_patterns
        )

        # Rejection analysis
        rejection_analysis = self._analyze_rejections(rejected)

        # Generate few-shot examples
        good_examples = self._generate_good_examples(with_outcomes)
        bad_examples = self._generate_bad_examples(with_outcomes)

        # Determine primary issue
        primary_issue = self._determine_primary_issue(
            confidence_calibration, worst_patterns, rejection_analysis
        )

        # Generate improvement suggestions
        suggestions = self._generate_suggestions(
            primary_issue, confidence_calibration, worst_patterns, rejection_analysis
        )

        return AIAnalysisReport(
            total_decisions=total_decisions,
            confirmed_trades=len(confirmed),
            rejected_trades=len(rejected),
            overall_win_rate=overall_win_rate,
            overall_pnl=overall_pnl,
            confidence_calibration=confidence_calibration,
            confidence_diagnosis=conf_diagnosis,
            confidence_recommendation=conf_recommendation,
            best_patterns=best_patterns,
            worst_patterns=worst_patterns,
            pattern_recommendations=pattern_recommendations,
            rejection_analysis=rejection_analysis,
            good_examples=good_examples,
            bad_examples=bad_examples,
            primary_issue=primary_issue,
            improvement_suggestions=suggestions,
        )

    def _analyze_confidence(self, log: DecisionLog) -> list[ConfidenceCalibration]:
        """Analyze confidence calibration."""
        calibration_data = log.get_confidence_accuracy()
        results = []

        for band, expected_rate in self.EXPECTED_WIN_RATES.items():
            data = calibration_data.get(band, {"total": 0, "wins": 0, "accuracy": 0})

            if data["total"] == 0:
                continue

            actual_rate = data["accuracy"]
            error = actual_rate - expected_rate

            # Parse band to get min/max
            parts = band.split("-")
            min_conf = int(parts[0])
            max_conf = int(parts[1])

            results.append(
                ConfidenceCalibration(
                    band=band,
                    min_confidence=min_conf,
                    max_confidence=max_conf,
                    total_trades=data["total"],
                    wins=data["wins"],
                    losses=data["total"] - data["wins"],
                    actual_win_rate=actual_rate,
                    expected_win_rate=expected_rate,
                    calibration_error=error,
                    is_overconfident=error < -0.15,  # >15% worse than expected
                    is_underconfident=error > 0.15,  # >15% better than expected
                )
            )

        return results

    def _diagnose_confidence(self, calibration: list[ConfidenceCalibration]) -> tuple[str, str]:
        """Generate diagnosis and recommendation for confidence."""
        if not calibration:
            return "Not enough data", "Run more backtests to gather data"

        overconfident = [c for c in calibration if c.is_overconfident]
        underconfident = [c for c in calibration if c.is_underconfident]

        if overconfident:
            bands = ", ".join(c.band for c in overconfident)
            return (
                f"AI is OVERCONFIDENT in {bands} range",
                f"Lower min_confidence or add caution to prompt for confidence {bands}",
            )

        if underconfident:
            bands = ", ".join(c.band for c in underconfident)
            return (
                f"AI is UNDERCONFIDENT in {bands} range",
                "AI is being too conservative - can trust high confidence more",
            )

        return "Confidence is well-calibrated", "No confidence adjustments needed"

    def _analyze_patterns(
        self, pattern_data: dict
    ) -> tuple[list[SignalPatternAnalysis], list[SignalPatternAnalysis]]:
        """Analyze signal patterns and identify best/worst."""
        patterns = []

        for pattern_key, data in pattern_data.items():
            if data["total"] < self.MIN_PATTERN_TRADES:
                continue

            win_rate = data["accuracy"]
            is_profitable = win_rate >= 0.5

            if win_rate >= self.GOOD_PATTERN_WIN_RATE:
                recommendation = "TRUST"
            elif win_rate <= self.BAD_PATTERN_WIN_RATE:
                recommendation = "AVOID"
            else:
                recommendation = "NEUTRAL"

            patterns.append(
                SignalPatternAnalysis(
                    pattern=pattern_key,
                    signal_types=pattern_key.split("+"),
                    total_trades=data["total"],
                    wins=data["wins"],
                    losses=data["losses"],
                    win_rate=win_rate,
                    avg_pnl=0,  # Would need to calculate from decisions
                    avg_confidence=0,  # Would need to calculate
                    is_profitable=is_profitable,
                    recommendation=recommendation,
                )
            )

        # Sort by win rate
        patterns.sort(key=lambda p: p.win_rate, reverse=True)

        best = [p for p in patterns if p.recommendation == "TRUST"]
        worst = [p for p in patterns if p.recommendation == "AVOID"]

        return best, worst

    def _generate_pattern_recommendations(
        self,
        best: list[SignalPatternAnalysis],
        worst: list[SignalPatternAnalysis],
    ) -> list[str]:
        """Generate recommendations based on pattern analysis."""
        recommendations = []

        if best:
            top_pattern = best[0]
            recommendations.append(
                f"Trust '{top_pattern.pattern}' combinations - {top_pattern.win_rate:.0%} win rate"
            )

        if worst:
            bad_pattern = worst[0]
            recommendations.append(
                f"Be skeptical of '{bad_pattern.pattern}' - only {bad_pattern.win_rate:.0%} win rate"
            )
            recommendations.append(
                f"Consider adding to prompt: 'Be cautious when seeing {bad_pattern.pattern}'"
            )

        return recommendations

    def _analyze_rejections(self, rejected: list[AIDecision]) -> RejectionAnalysis | None:
        """Analyze rejected trades to see if AI is rejecting good opportunities."""
        if not rejected:
            return None

        # Count simulated outcomes
        with_simulated = [d for d in rejected if d.simulated_outcome is not None]

        if not with_simulated:
            return RejectionAnalysis(
                total_rejected=len(rejected),
                would_have_won=0,
                would_have_lost=0,
                missed_opportunity_rate=0,
                avg_missed_pnl=0,
                recommendation="No simulated data - enable rejection tracking",
            )

        would_have_won = sum(1 for d in with_simulated if d.simulated_outcome == "WIN")
        would_have_lost = len(with_simulated) - would_have_won

        missed_rate = would_have_won / len(with_simulated) if with_simulated else 0
        avg_missed = sum(
            d.simulated_pnl or 0 for d in with_simulated if d.simulated_outcome == "WIN"
        )
        avg_missed = avg_missed / would_have_won if would_have_won > 0 else 0

        # Generate recommendation
        if missed_rate > 0.5:
            recommendation = (
                "AI is rejecting too many good trades - lower min_confidence or relax prompt"
            )
        elif missed_rate < 0.3:
            recommendation = "AI rejections are good - keep current settings"
        else:
            recommendation = "Rejection rate is acceptable"

        return RejectionAnalysis(
            total_rejected=len(rejected),
            would_have_won=would_have_won,
            would_have_lost=would_have_lost,
            missed_opportunity_rate=missed_rate,
            avg_missed_pnl=avg_missed,
            recommendation=recommendation,
        )

    def _generate_good_examples(self, decisions: list[AIDecision]) -> list[FewShotExample]:
        """Generate few-shot examples from winning trades."""
        winners = [d for d in decisions if d.confirmed and d.outcome == "WIN"]
        winners.sort(key=lambda d: d.pnl or 0, reverse=True)

        examples = []
        for d in winners[:3]:  # Top 3 winners
            signals_desc = ", ".join(
                f"{s.signal_type} {s.direction} ({s.strength:.2f})" for s in d.signals
            )
            examples.append(
                FewShotExample(
                    signals_description=signals_desc,
                    direction=d.direction,
                    confidence=d.confidence,
                    outcome="WON",
                    pnl_pct=d.pnl_pct or 0,
                    reason=d.reason,
                    lesson=f"Aligned {len(d.signals)} signals in same direction led to profit",
                )
            )

        return examples

    def _generate_bad_examples(self, decisions: list[AIDecision]) -> list[FewShotExample]:
        """Generate few-shot examples from losing trades (mistakes to avoid)."""
        losers = [d for d in decisions if d.confirmed and d.outcome == "LOSS"]
        losers.sort(key=lambda d: d.pnl or 0)  # Worst losses first

        examples = []
        for d in losers[:2]:  # Top 2 worst losses
            signals_desc = ", ".join(
                f"{s.signal_type} {s.direction} ({s.strength:.2f})" for s in d.signals
            )

            # Try to identify what went wrong
            signal_directions = {s.direction for s in d.signals}
            if len(signal_directions) > 1:
                lesson = "Conflicting signals were a warning sign"
            elif d.confidence >= 7:
                lesson = "High confidence doesn't guarantee success - check signal quality"
            else:
                lesson = "Weak setup that should have been rejected"

            examples.append(
                FewShotExample(
                    signals_description=signals_desc,
                    direction=d.direction,
                    confidence=d.confidence,
                    outcome="LOST",
                    pnl_pct=d.pnl_pct or 0,
                    reason=d.reason,
                    lesson=lesson,
                )
            )

        return examples

    def _determine_primary_issue(
        self,
        calibration: list[ConfidenceCalibration],
        worst_patterns: list[SignalPatternAnalysis],
        rejection_analysis: RejectionAnalysis | None,  # noqa: ARG002
    ) -> str:
        """Determine the primary issue to fix first."""
        # Check confidence calibration
        severely_overconfident = any(c.calibration_error < -0.20 for c in calibration)
        if severely_overconfident:
            return "CONFIDENCE"

        # Check patterns
        very_bad_patterns = [p for p in worst_patterns if p.win_rate < 0.30 and p.total_trades >= 5]
        if very_bad_patterns:
            return "PATTERNS"

        # Future: Check rejections when rejection tracking is enabled
        # if rejection_analysis and rejection_analysis.missed_opportunity_rate > 0.6:
        #     return "REJECTIONS"

        return "NONE"

    def _generate_suggestions(
        self,
        primary_issue: str,
        calibration: list[ConfidenceCalibration],
        worst_patterns: list[SignalPatternAnalysis],
        rejection_analysis: RejectionAnalysis | None,  # noqa: ARG002 - used for REJECTIONS issue type
    ) -> list[str]:
        """Generate actionable improvement suggestions."""
        suggestions = []

        if primary_issue == "CONFIDENCE":
            overconfident = [c for c in calibration if c.is_overconfident]
            for c in overconfident:
                suggestions.append(
                    f"Lower min_confidence for {c.band} range or add 'be more cautious' to prompt"
                )

        elif primary_issue == "PATTERNS":
            for p in worst_patterns[:2]:
                suggestions.append(
                    f"Add to prompt: 'Be skeptical when {' and '.join(p.signal_types)} appear together'"
                )

        elif primary_issue == "REJECTIONS":
            suggestions.append("Lower min_confidence threshold to accept more trades")
            suggestions.append("Modify prompt to be less conservative")

        else:
            suggestions.append("AI performance is acceptable - focus on signal quality instead")
            suggestions.append("Consider running more backtests to gather more decision data")

        # Always suggest few-shot examples if we have enough data
        if len(calibration) > 0:
            suggestions.append(
                "Add few-shot examples to prompt using report.to_few_shot_examples()"
            )

        return suggestions


def analyze_decision_log(log_path: Path | str) -> AIAnalysisReport:
    """
    Convenience function to analyze a saved decision log.

    Args:
        log_path: Path to the saved decision log JSON file

    Returns:
        AIAnalysisReport with analysis and recommendations
    """
    log = DecisionLog.load(log_path)
    analyzer = AIDecisionAnalyzer()
    return analyzer.analyze(log)
