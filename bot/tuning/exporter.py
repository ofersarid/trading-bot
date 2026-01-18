"""
Tuning Report Exporter

Exports analysis results in formats suitable for AI analysis
and human review.
"""

import json
from datetime import datetime
from pathlib import Path

from bot.tuning.collector import FeedbackCollector
from bot.tuning.analyzer import PerformanceAnalyzer


class TuningReportExporter:
    """
    Exports tuning data and analysis in various formats.
    
    Formats:
    - JSON: Machine-readable, full data
    - Markdown: Human-readable report, perfect for AI analysis
    """
    
    def __init__(
        self,
        collector: FeedbackCollector,
        analyzer: PerformanceAnalyzer,
        output_dir: str = "data/reports",
    ):
        self.collector = collector
        self.analyzer = analyzer
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export_json(
        self, 
        filename: str | None = None,
        since: datetime | None = None,
    ) -> Path:
        """
        Export analysis as JSON.
        
        Args:
            filename: Optional filename (default: report.json - overwrites existing)
            since: If provided, only include trades since this timestamp (incremental)
        
        Returns:
            Path to the exported file
        """
        # Get trades (all or incremental)
        trades = self.collector.get_trades_since(since)
        analysis = self.analyzer.analyze(trades=trades)
        
        # Add raw trade data and report metadata
        analysis["raw_trades"] = [t.to_dict() for t in trades]
        analysis["is_incremental"] = since is not None
        analysis["new_trades_count"] = len(trades)
        analysis["total_trades_count"] = len(self.collector.trades)
        if since:
            analysis["since_timestamp"] = since.isoformat()
        
        # Use fixed filename - overwrites on each update
        if not filename:
            filename = "report.json"
        
        filepath = self.output_dir / filename
        with open(filepath, "w") as f:
            json.dump(analysis, f, indent=2, default=str)
        
        return filepath
    
    def export_markdown(
        self, 
        filename: str | None = None,
        since: datetime | None = None,
    ) -> Path:
        """
        Export analysis as markdown report.
        
        This format is optimized for AI analysis - includes context,
        clear data presentation, and explicit questions for the AI.
        
        Args:
            filename: Optional filename (default: report.md - overwrites existing)
            since: If provided, only include trades since this timestamp (incremental)
        
        Returns:
            Path to the exported file
        """
        # Get trades (all or incremental)
        trades = self.collector.get_trades_since(since)
        analysis = self.analyzer.analyze(trades=trades)
        analysis["is_incremental"] = since is not None
        analysis["new_trades_count"] = len(trades)
        analysis["total_trades_count"] = len(self.collector.trades)
        if since:
            analysis["since_timestamp"] = since.isoformat()
        
        # Use fixed filename - overwrites on each update
        if not filename:
            filename = "report.md"
        
        report = self._generate_markdown_report(analysis)
        
        filepath = self.output_dir / filename
        with open(filepath, "w") as f:
            f.write(report)
        
        return filepath
    
    def _generate_markdown_report(self, analysis: dict) -> str:
        """Generate the markdown report content."""
        lines = []
        
        # Header - check if incremental
        is_incremental = analysis.get("is_incremental", False)
        new_trades = analysis.get("new_trades_count", 0)
        total_trades = analysis.get("total_trades_count", analysis.get("trade_count", 0))
        
        lines.extend([
            "# Trading Strategy Tuning Report",
            "",
            f"> Generated: {analysis.get('timestamp', datetime.now().isoformat())}",
            f"> Total Trades: {total_trades}",
        ])
        
        if is_incremental:
            since_ts = analysis.get("since_timestamp", "unknown")
            lines.append(f"> New Trades (this update): {new_trades}")
            lines.append(f"> Since: {since_ts}")
        
        lines.extend([
            "",
            "---",
            "",
        ])
        
        # Status check
        if analysis.get("status") == "insufficient_data":
            lines.extend([
                "## ⚠️ Insufficient Data",
                "",
                analysis.get("message", "Need more trades for analysis."),
                "",
                "Continue trading to collect more data for meaningful analysis.",
                "",
            ])
            return "\n".join(lines)
        
        # Overall Metrics
        if "overall_metrics" in analysis:
            metrics = analysis["overall_metrics"]
            lines.extend([
                "## 📊 Overall Performance",
                "",
                "| Metric | Value |",
                "|--------|-------|",
                f"| Total Trades | {metrics['total_trades']} |",
                f"| Win Rate | {metrics['win_rate_pct']:.1f}% |",
                f"| Profit Factor | {metrics['profit_factor']:.2f} |",
                f"| Expectancy | ${metrics['expectancy_usd']:+.2f}/trade |",
                f"| Total P&L | ${metrics['total_pnl_usd']:+.2f} |",
                f"| Total Fees | ${metrics['total_fees_usd']:.2f} |",
                f"| Avg Win | ${metrics['avg_win_usd']:.2f} |",
                f"| Avg Loss | ${metrics['avg_loss_usd']:.2f} |",
                f"| Win/Loss Ratio | {metrics['win_loss_ratio']:.2f} |",
                f"| Avg Duration | {metrics['avg_duration_seconds']:.0f}s |",
                "",
            ])
            
            # Performance assessment
            pf = metrics['profit_factor']
            if pf < 1:
                assessment = "🔴 **Losing strategy** - needs significant adjustment"
            elif pf < 1.5:
                assessment = "🟡 **Marginal** - profitable but fragile"
            elif pf < 2:
                assessment = "🟢 **Good** - solid foundation"
            else:
                assessment = "🟢 **Excellent** - strong performance"
            
            lines.extend([
                f"**Assessment:** {assessment}",
                "",
                "---",
                "",
            ])
        
        # Outcomes Breakdown
        if "by_outcome" in analysis:
            outcomes = analysis["by_outcome"]
            lines.extend([
                "## 🎯 Exit Analysis",
                "",
                "| Exit Type | Count | % of Total | Avg P&L | Avg Duration |",
                "|-----------|-------|------------|---------|--------------|",
            ])
            for outcome, stats in outcomes.items():
                lines.append(
                    f"| {outcome.replace('_', ' ').title()} | "
                    f"{stats['count']} | "
                    f"{stats['pct_of_total']:.1f}% | "
                    f"${stats['avg_pnl_usd']:+.2f} | "
                    f"{stats['avg_duration_seconds']:.0f}s |"
                )
            lines.extend(["", ""])
        
        # Market Condition Performance
        if "by_market_condition" in analysis:
            conditions = analysis["by_market_condition"]
            lines.extend([
                "## 🌡️ Performance by Market Condition",
                "",
                "| Condition | Trades | Win Rate | Avg P&L | Total P&L |",
                "|-----------|--------|----------|---------|-----------|",
            ])
            for cond in conditions:
                emoji = "🟢" if cond["win_rate_pct"] > 50 else "🔴" if cond["win_rate_pct"] < 40 else "🟡"
                lines.append(
                    f"| {cond['condition']} | "
                    f"{cond['trade_count']} | "
                    f"{emoji} {cond['win_rate_pct']:.1f}% | "
                    f"${cond['avg_pnl_usd']:+.2f} | "
                    f"${cond['total_pnl_usd']:+.2f} |"
                )
            lines.extend(["", ""])
        
        # Parameter Effectiveness
        if "parameter_effectiveness" in analysis:
            effectiveness = analysis["parameter_effectiveness"]
            
            lines.extend([
                "## 📈 Parameter Effectiveness",
                "",
            ])
            
            # Trade Threshold
            if effectiveness.get("trade_threshold"):
                lines.extend([
                    "### Trade Threshold Performance",
                    "",
                    "| Threshold Range | Trades | Win Rate | Avg P&L |",
                    "|-----------------|--------|----------|---------|",
                ])
                for bucket in effectiveness["trade_threshold"]:
                    emoji = "🟢" if bucket["win_rate_pct"] > 50 else "🔴"
                    lines.append(
                        f"| {bucket['range']}% | "
                        f"{bucket['trade_count']} | "
                        f"{emoji} {bucket['win_rate_pct']:.1f}% | "
                        f"${bucket['avg_pnl_usd']:+.2f} |"
                    )
                lines.extend(["", ""])
            
            # Momentum Timeframe
            if effectiveness.get("momentum_timeframe"):
                lines.extend([
                    "### Momentum Timeframe Performance",
                    "",
                    "| Timeframe | Trades | Win Rate | Avg P&L |",
                    "|-----------|--------|----------|---------|",
                ])
                for bucket in effectiveness["momentum_timeframe"]:
                    emoji = "🟢" if bucket["win_rate_pct"] > 50 else "🔴"
                    lines.append(
                        f"| {bucket['range']}s | "
                        f"{bucket['trade_count']} | "
                        f"{emoji} {bucket['win_rate_pct']:.1f}% | "
                        f"${bucket['avg_pnl_usd']:+.2f} |"
                    )
                lines.extend(["", ""])
        
        # Temporal Patterns
        if "temporal_patterns" in analysis:
            patterns = analysis["temporal_patterns"]
            
            if patterns.get("by_duration"):
                lines.extend([
                    "## ⏱️ Trade Duration Analysis",
                    "",
                    "| Duration | Trades | Win Rate | Avg P&L |",
                    "|----------|--------|----------|---------|",
                ])
                for duration in patterns["by_duration"]:
                    lines.append(
                        f"| {duration['duration_range']} | "
                        f"{duration['trade_count']} | "
                        f"{duration['win_rate_pct']:.1f}% | "
                        f"${duration['avg_pnl_usd']:+.2f} |"
                    )
                lines.extend(["", ""])
        
        # Suggestions
        if "suggestions" in analysis and analysis["suggestions"]:
            lines.extend([
                "## 💡 Tuning Suggestions",
                "",
            ])
            
            for i, suggestion in enumerate(analysis["suggestions"], 1):
                if suggestion.get("type") == "data_collection":
                    lines.extend([
                        f"### {i}. Data Collection",
                        f"**Priority:** {suggestion.get('priority', 'medium')}",
                        "",
                        suggestion.get("message", ""),
                        "",
                    ])
                elif suggestion.get("type") == "market_condition_warning":
                    lines.extend([
                        f"### {i}. ⚠️ {suggestion.get('message', 'Warning')}",
                        f"**Condition:** {suggestion.get('condition')}",
                        f"**Evidence:** {suggestion.get('evidence')}",
                        f"**Suggestion:** {suggestion.get('suggestion')}",
                        "",
                    ])
                else:
                    param = suggestion.get("parameter", "Unknown")
                    direction = suggestion.get("direction", "")
                    confidence = suggestion.get("confidence", "medium")
                    
                    arrow = "⬆️" if direction == "increase" else "⬇️" if direction == "decrease" else "➡️"
                    confidence_badge = "🔴" if confidence == "high" else "🟡" if confidence == "medium" else "⚪"
                    
                    lines.extend([
                        f"### {i}. {arrow} {param.replace('_', ' ').title()}",
                        f"**Confidence:** {confidence_badge} {confidence}",
                        "",
                        f"**Current:** `{suggestion.get('current_value')}`",
                        f"**Suggested:** `{suggestion.get('suggested_value')}`",
                        "",
                        f"**Reason:** {suggestion.get('reason', '')}",
                        "",
                        f"**Evidence:** {suggestion.get('evidence', '')}",
                        "",
                    ])
        
        # AI Analysis Section
        lines.extend([
            "---",
            "",
            "## 🤖 For AI Analysis",
            "",
            "Based on the data above, please analyze:",
            "",
            "1. **Parameter Optimization Priority**: Which parameters should be adjusted first?",
            "2. **Market Condition Strategy**: Should we use different parameters for different market conditions?",
            "3. **Risk Assessment**: Is the current risk/reward profile appropriate?",
            "4. **Missing Signals**: Are there patterns suggesting we need additional parameters?",
            "5. **Correlation Analysis**: How do BTC/ETH movements affect trade outcomes?",
            "",
            "### Current Tunable Parameters",
            "",
            "```",
            "Entry:",
            "  - track_threshold_pct: 0.01% - 0.10%",
            "  - trade_threshold_pct: 0.02% - 0.20%",
            "  - momentum_timeframe_seconds: 1-30s",
            "",
            "Exit:",
            "  - take_profit_pct: 1% - 20%",
            "  - stop_loss_pct: -2% to -10%",
            "",
            "Position:",
            "  - position_size_pct: 5% - 25%",
            "  - cooldown_seconds: 10-120s",
            "  - max_concurrent_positions: 1-5",
            "```",
            "",
            "### Suggested New Parameters to Consider",
            "",
            "- **Volatility-adaptive thresholds**: Adjust entry thresholds based on current market volatility",
            "- **Time-of-day filters**: Avoid trading during historically poor hours",
            "- **Correlation filter**: Skip trades when BTC/ETH move together (reduces diversification)",
            "- **Volume confirmation**: Require above-average volume for entries",
            "- **Trailing stop**: Dynamic stop loss that follows price",
            "",
        ])
        
        return "\n".join(lines)
    
    def export_both(
        self, 
        since: datetime | None = None,
    ) -> tuple[Path, Path]:
        """
        Export both JSON and Markdown reports.
        
        Reports are saved as report.json and report.md, overwriting previous versions.
        
        Args:
            since: If provided, only include trades since this timestamp (incremental)
            
        Returns:
            Tuple of (json_path, markdown_path)
        """
        json_path = self.export_json(since=since)
        md_path = self.export_markdown(since=since)
        return json_path, md_path
