"""
Performance Analyzer

Analyzes trade history to identify patterns and suggest
parameter adjustments for improved performance.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import mean, stdev
from typing import Literal

from bot.tuning.collector import FeedbackCollector, TradeRecord


@dataclass
class ParameterSuggestion:
    """A suggested parameter adjustment."""
    
    parameter: str
    current_value: float | int
    suggested_value: float | int
    direction: Literal["increase", "decrease", "maintain"]
    confidence: Literal["high", "medium", "low"]
    reason: str
    evidence: str  # Supporting data points
    
    def to_dict(self) -> dict:
        return {
            "parameter": self.parameter,
            "current_value": self.current_value,
            "suggested_value": self.suggested_value,
            "direction": self.direction,
            "confidence": self.confidence,
            "reason": self.reason,
            "evidence": self.evidence,
        }


@dataclass
class MarketConditionStats:
    """Stats for a specific market condition."""
    
    condition: str
    trade_count: int
    win_rate: float
    avg_pnl: float
    avg_duration: float
    most_used_trade_threshold: float
    most_used_momentum_timeframe: int


class PerformanceAnalyzer:
    """
    Analyzes trade performance to suggest parameter optimizations.
    
    Analysis dimensions:
    1. Overall performance metrics
    2. Performance by market condition
    3. Performance by parameter values
    4. Temporal patterns (time of day, duration)
    5. Correlation analysis (BTC/ETH moves)
    """
    
    def __init__(self, collector: FeedbackCollector):
        self.collector = collector
    
    def analyze(self, trades: list[TradeRecord] | None = None) -> dict:
        """
        Run full analysis and return comprehensive report.
        
        Args:
            trades: Optional list of trades to analyze. If None, uses all trades
                   from the collector. This allows incremental analysis.
        
        Returns:
            Dictionary with analysis results and suggestions
        """
        if trades is None:
            trades = self.collector.trades
        
        if len(trades) < 5:
            return {
                "status": "insufficient_data",
                "message": f"Need at least 5 trades for analysis, have {len(trades)}",
                "trade_count": len(trades),
                "suggestions": [],
            }
        
        return {
            "status": "complete",
            "timestamp": datetime.now().isoformat(),
            "trade_count": len(trades),
            "overall_metrics": self._calculate_overall_metrics(trades),
            "by_market_condition": self._analyze_by_market_condition(trades),
            "by_outcome": self._analyze_by_outcome(trades),
            "parameter_effectiveness": self._analyze_parameter_effectiveness(trades),
            "temporal_patterns": self._analyze_temporal_patterns(trades),
            "suggestions": self._generate_suggestions(trades),
        }
    
    def _calculate_overall_metrics(self, trades: list[TradeRecord]) -> dict:
        """Calculate overall performance metrics."""
        wins = [t for t in trades if t.pnl_usd > 0]
        losses = [t for t in trades if t.pnl_usd <= 0]
        
        total_pnl = sum(t.pnl_usd for t in trades)
        gross_profit = sum(t.pnl_usd for t in wins) if wins else 0
        gross_loss = abs(sum(t.pnl_usd for t in losses)) if losses else 0
        
        # Profit factor = gross profit / gross loss
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Average win/loss ratio
        avg_win = mean([t.pnl_usd for t in wins]) if wins else 0
        avg_loss = abs(mean([t.pnl_usd for t in losses])) if losses else 0
        win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else float('inf')
        
        # Expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)
        win_rate = len(wins) / len(trades)
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
        
        return {
            "total_trades": len(trades),
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate_pct": win_rate * 100,
            "total_pnl_usd": total_pnl,
            "gross_profit_usd": gross_profit,
            "gross_loss_usd": gross_loss,
            "profit_factor": profit_factor,
            "avg_win_usd": avg_win,
            "avg_loss_usd": avg_loss,
            "win_loss_ratio": win_loss_ratio,
            "expectancy_usd": expectancy,
            "avg_duration_seconds": mean([t.duration_seconds for t in trades]),
            "total_fees_usd": sum(t.fees_paid for t in trades),
        }
    
    def _analyze_by_market_condition(self, trades: list[TradeRecord]) -> list[dict]:
        """Analyze performance broken down by market condition."""
        conditions = set(t.parameters.market_condition for t in trades)
        results = []
        
        for condition in conditions:
            condition_trades = [t for t in trades if t.parameters.market_condition == condition]
            wins = [t for t in condition_trades if t.pnl_usd > 0]
            
            # Find most common parameter values for this condition
            thresholds = [t.parameters.trade_threshold_pct for t in condition_trades]
            timeframes = [t.parameters.momentum_timeframe_seconds for t in condition_trades]
            
            results.append({
                "condition": condition,
                "trade_count": len(condition_trades),
                "win_rate_pct": (len(wins) / len(condition_trades)) * 100 if condition_trades else 0,
                "avg_pnl_usd": mean([t.pnl_usd for t in condition_trades]) if condition_trades else 0,
                "total_pnl_usd": sum(t.pnl_usd for t in condition_trades),
                "avg_duration_seconds": mean([t.duration_seconds for t in condition_trades]) if condition_trades else 0,
                "avg_trade_threshold_used": mean(thresholds) if thresholds else 0,
                "avg_momentum_timeframe_used": mean(timeframes) if timeframes else 0,
            })
        
        return sorted(results, key=lambda x: x["trade_count"], reverse=True)
    
    def _analyze_by_outcome(self, trades: list[TradeRecord]) -> dict:
        """Analyze trades by outcome type."""
        outcomes = {}
        
        for outcome in ["take_profit", "stop_loss", "emergency_exit", "manual"]:
            outcome_trades = [t for t in trades if t.outcome == outcome]
            if outcome_trades:
                outcomes[outcome] = {
                    "count": len(outcome_trades),
                    "pct_of_total": (len(outcome_trades) / len(trades)) * 100,
                    "avg_pnl_usd": mean([t.pnl_usd for t in outcome_trades]),
                    "avg_duration_seconds": mean([t.duration_seconds for t in outcome_trades]),
                }
        
        return outcomes
    
    def _analyze_parameter_effectiveness(self, trades: list[TradeRecord]) -> dict:
        """Analyze how different parameter values affect performance."""
        
        def analyze_parameter_buckets(trades: list[TradeRecord], param_getter, bucket_size: float) -> list[dict]:
            """Group trades by parameter value and analyze each bucket."""
            values = [param_getter(t) for t in trades]
            min_val, max_val = min(values), max(values)
            
            buckets = []
            current = min_val
            while current <= max_val:
                bucket_trades = [
                    t for t in trades 
                    if current <= param_getter(t) < current + bucket_size
                ]
                if bucket_trades:
                    wins = [t for t in bucket_trades if t.pnl_usd > 0]
                    buckets.append({
                        "range": f"{current:.3f}-{current + bucket_size:.3f}",
                        "trade_count": len(bucket_trades),
                        "win_rate_pct": (len(wins) / len(bucket_trades)) * 100,
                        "avg_pnl_usd": mean([t.pnl_usd for t in bucket_trades]),
                    })
                current += bucket_size
            
            return buckets
        
        return {
            "trade_threshold": analyze_parameter_buckets(
                trades,
                lambda t: t.parameters.trade_threshold_pct,
                0.01  # 0.01% buckets
            ),
            "momentum_timeframe": analyze_parameter_buckets(
                trades,
                lambda t: t.parameters.momentum_timeframe_seconds,
                2  # 2 second buckets
            ),
            "position_size": analyze_parameter_buckets(
                trades,
                lambda t: t.parameters.position_size_pct,
                0.05  # 5% buckets
            ),
        }
    
    def _analyze_temporal_patterns(self, trades: list[TradeRecord]) -> dict:
        """Analyze time-based patterns in trading performance."""
        
        # Group by hour of day
        hourly_performance = {}
        for trade in trades:
            hour = datetime.fromisoformat(trade.timestamp).hour
            if hour not in hourly_performance:
                hourly_performance[hour] = []
            hourly_performance[hour].append(trade)
        
        hourly_stats = []
        for hour, hour_trades in sorted(hourly_performance.items()):
            wins = [t for t in hour_trades if t.pnl_usd > 0]
            hourly_stats.append({
                "hour": hour,
                "trade_count": len(hour_trades),
                "win_rate_pct": (len(wins) / len(hour_trades)) * 100 if hour_trades else 0,
                "avg_pnl_usd": mean([t.pnl_usd for t in hour_trades]) if hour_trades else 0,
            })
        
        # Analyze duration effectiveness
        short_trades = [t for t in trades if t.duration_seconds < 60]  # < 1 min
        medium_trades = [t for t in trades if 60 <= t.duration_seconds < 300]  # 1-5 min
        long_trades = [t for t in trades if t.duration_seconds >= 300]  # 5+ min
        
        def duration_stats(trade_list, label):
            if not trade_list:
                return None
            wins = [t for t in trade_list if t.pnl_usd > 0]
            return {
                "duration_range": label,
                "trade_count": len(trade_list),
                "win_rate_pct": (len(wins) / len(trade_list)) * 100,
                "avg_pnl_usd": mean([t.pnl_usd for t in trade_list]),
            }
        
        return {
            "by_hour": hourly_stats,
            "by_duration": [
                s for s in [
                    duration_stats(short_trades, "<1 min"),
                    duration_stats(medium_trades, "1-5 min"),
                    duration_stats(long_trades, "5+ min"),
                ] if s is not None
            ],
        }
    
    def _generate_suggestions(self, trades: list[TradeRecord]) -> list[dict]:
        """Generate actionable parameter adjustment suggestions."""
        suggestions = []
        
        if len(trades) < 10:
            return [{
                "type": "data_collection",
                "message": "Need more trades (10+) for reliable suggestions",
                "priority": "high",
            }]
        
        # Analyze current parameter performance
        overall = self._calculate_overall_metrics(trades)
        by_condition = self._analyze_by_market_condition(trades)
        by_outcome = self._analyze_by_outcome(trades)
        
        # Current weighted averages (what parameters are being used)
        current_trade_threshold = mean([t.parameters.trade_threshold_pct for t in trades])
        current_timeframe = mean([t.parameters.momentum_timeframe_seconds for t in trades])
        current_position_size = mean([t.parameters.position_size_pct for t in trades])
        current_tp = mean([t.parameters.take_profit_pct for t in trades])
        current_sl = mean([t.parameters.stop_loss_pct for t in trades])
        
        # 1. Analyze win rate and suggest threshold adjustments
        win_rate = overall["win_rate_pct"]
        
        if win_rate < 40:
            suggestions.append(ParameterSuggestion(
                parameter="trade_threshold_pct",
                current_value=current_trade_threshold,
                suggested_value=current_trade_threshold * 1.25,
                direction="increase",
                confidence="high" if win_rate < 30 else "medium",
                reason="Low win rate suggests entries are too aggressive",
                evidence=f"Win rate: {win_rate:.1f}%. Raising threshold filters out weaker signals.",
            ).to_dict())
        elif win_rate > 70:
            suggestions.append(ParameterSuggestion(
                parameter="trade_threshold_pct",
                current_value=current_trade_threshold,
                suggested_value=current_trade_threshold * 0.85,
                direction="decrease",
                confidence="medium",
                reason="High win rate may indicate missed opportunities",
                evidence=f"Win rate: {win_rate:.1f}%. May be too selective - consider lower threshold.",
            ).to_dict())
        
        # 2. Analyze stop loss effectiveness
        if "stop_loss" in by_outcome:
            sl_pct = by_outcome["stop_loss"]["pct_of_total"]
            
            if sl_pct > 50:
                suggestions.append(ParameterSuggestion(
                    parameter="stop_loss_pct",
                    current_value=current_sl,
                    suggested_value=current_sl * 1.2,  # Widen stop
                    direction="decrease",  # More negative = wider
                    confidence="high" if sl_pct > 60 else "medium",
                    reason="Too many stop losses being hit",
                    evidence=f"{sl_pct:.1f}% of trades hit stop loss. Consider widening.",
                ).to_dict())
        
        # 3. Analyze take profit effectiveness
        if "take_profit" in by_outcome:
            tp_pct = by_outcome["take_profit"]["pct_of_total"]
            avg_tp_duration = by_outcome["take_profit"]["avg_duration_seconds"]
            
            if tp_pct < 30 and overall["avg_duration_seconds"] > 300:
                suggestions.append(ParameterSuggestion(
                    parameter="take_profit_pct",
                    current_value=current_tp,
                    suggested_value=current_tp * 0.75,  # Tighter TP
                    direction="decrease",
                    confidence="medium",
                    reason="Take profit rarely reached, positions held too long",
                    evidence=f"Only {tp_pct:.1f}% reach TP. Avg duration: {avg_tp_duration:.0f}s.",
                ).to_dict())
        
        # 4. Analyze market condition performance
        for condition_stats in by_condition:
            if condition_stats["trade_count"] >= 5:
                cond_win_rate = condition_stats["win_rate_pct"]
                condition = condition_stats["condition"]
                
                if cond_win_rate < 35:
                    suggestions.append({
                        "type": "market_condition_warning",
                        "condition": condition,
                        "message": f"Poor performance in {condition} markets",
                        "evidence": f"Win rate: {cond_win_rate:.1f}% across {condition_stats['trade_count']} trades",
                        "suggestion": f"Consider higher thresholds or avoiding trades in {condition} conditions",
                        "priority": "high",
                    })
        
        # 5. Position sizing based on volatility
        if overall["profit_factor"] < 1:
            suggestions.append(ParameterSuggestion(
                parameter="position_size_pct",
                current_value=current_position_size,
                suggested_value=current_position_size * 0.7,
                direction="decrease",
                confidence="high",
                reason="Negative expectancy - reduce risk while tuning",
                evidence=f"Profit factor: {overall['profit_factor']:.2f}. Reduce position size until profitable.",
            ).to_dict())
        elif overall["profit_factor"] > 2 and win_rate > 50:
            suggestions.append(ParameterSuggestion(
                parameter="position_size_pct",
                current_value=current_position_size,
                suggested_value=min(current_position_size * 1.25, 0.25),
                direction="increase",
                confidence="medium",
                reason="Strong performance allows for larger positions",
                evidence=f"Profit factor: {overall['profit_factor']:.2f}, Win rate: {win_rate:.1f}%.",
            ).to_dict())
        
        # 6. Momentum timeframe suggestions based on avg trade duration
        avg_duration = overall["avg_duration_seconds"]
        
        if avg_duration < 30 and current_timeframe > 5:
            suggestions.append(ParameterSuggestion(
                parameter="momentum_timeframe_seconds",
                current_value=current_timeframe,
                suggested_value=max(current_timeframe - 2, 3),
                direction="decrease",
                confidence="medium",
                reason="Very short trade durations suggest faster momentum detection needed",
                evidence=f"Avg trade duration: {avg_duration:.0f}s. Consider shorter lookback.",
            ).to_dict())
        elif avg_duration > 120 and current_timeframe < 10:
            suggestions.append(ParameterSuggestion(
                parameter="momentum_timeframe_seconds",
                current_value=current_timeframe,
                suggested_value=min(current_timeframe + 3, 15),
                direction="increase",
                confidence="medium",
                reason="Long trade durations suggest momentum timeframe may be too short",
                evidence=f"Avg trade duration: {avg_duration:.0f}s. Consider longer lookback for better signals.",
            ).to_dict())
        
        return suggestions
    
    def get_quick_summary(self) -> str:
        """Get a quick text summary of performance."""
        trades = self.collector.trades
        
        if not trades:
            return "No trades recorded yet."
        
        wins = [t for t in trades if t.pnl_usd > 0]
        total_pnl = sum(t.pnl_usd for t in trades)
        
        return (
            f"Trades: {len(trades)} | "
            f"Win Rate: {(len(wins)/len(trades))*100:.1f}% | "
            f"Total P&L: ${total_pnl:+,.2f}"
        )
