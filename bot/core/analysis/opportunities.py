"""
Opportunity detection and validation.

Provides logic for detecting trading opportunities based on momentum
and validating conditions for trade execution.
"""

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from bot.core.config import TradingConfig
from bot.core.models import OpportunityCondition, PendingOpportunity
from bot.core.analysis.momentum import calculate_momentum


class OpportunityAction(Enum):
    """Actions to take based on opportunity analysis."""
    NO_ACTION = "no_action"           # Not enough history or no signal
    START_TRACKING = "start_tracking"  # Momentum above track threshold
    KEEP_TRACKING = "keep_tracking"    # Already tracking, momentum still valid
    STOP_TRACKING = "stop_tracking"    # Momentum dropped below threshold
    READY_TO_EXECUTE = "ready"         # All conditions met


@dataclass
class OpportunityAnalysisResult:
    """Result of opportunity analysis for a coin."""
    coin: str
    action: OpportunityAction
    momentum_pct: float | None = None
    direction: str | None = None  # "LONG" or "SHORT"
    current_price: float = 0.0
    
    @property
    def is_trackable(self) -> bool:
        """Whether this opportunity should be tracked."""
        return self.action in (
            OpportunityAction.START_TRACKING,
            OpportunityAction.KEEP_TRACKING,
            OpportunityAction.READY_TO_EXECUTE,
        )


class OpportunityAnalyzer:
    """
    Analyzes price movements to detect trading opportunities.
    
    Separates the detection logic from UI and execution concerns.
    """
    
    def __init__(self, config: TradingConfig):
        self.config = config
    
    def analyze(
        self,
        coin: str,
        current_price: float,
        price_history: deque[dict],
        momentum_timeframe: int,
        track_threshold: float,
        trade_threshold: float,
        is_currently_tracking: bool = False,
    ) -> OpportunityAnalysisResult:
        """
        Analyze a coin for trading opportunity.
        
        Args:
            coin: Coin symbol
            current_price: Current price
            price_history: Price history deque
            momentum_timeframe: Lookback period in seconds
            track_threshold: Minimum momentum % to start tracking
            trade_threshold: Minimum momentum % to execute trade
            is_currently_tracking: Whether we're already tracking this coin
        
        Returns:
            Analysis result with recommended action
        """
        momentum = calculate_momentum(current_price, price_history, momentum_timeframe)
        
        if momentum is None:
            return OpportunityAnalysisResult(
                coin=coin,
                action=OpportunityAction.NO_ACTION,
                current_price=current_price,
            )
        
        momentum_pct = momentum  # Already in percentage from calculate_momentum
        abs_momentum = abs(momentum_pct)
        direction = "LONG" if momentum_pct > 0 else "SHORT"
        
        # Determine action based on momentum vs thresholds
        if abs_momentum < track_threshold:
            if is_currently_tracking:
                action = OpportunityAction.STOP_TRACKING
            else:
                action = OpportunityAction.NO_ACTION
        elif abs_momentum >= trade_threshold:
            action = OpportunityAction.READY_TO_EXECUTE
        elif is_currently_tracking:
            action = OpportunityAction.KEEP_TRACKING
        else:
            action = OpportunityAction.START_TRACKING
        
        return OpportunityAnalysisResult(
            coin=coin,
            action=action,
            momentum_pct=momentum_pct,
            direction=direction,
            current_price=current_price,
        )
    
    def create_opportunity(
        self,
        coin: str,
        direction: str,
        price: float,
        trade_threshold: float,
        momentum_timeframe: int,
    ) -> PendingOpportunity:
        """
        Create a new pending opportunity with standard conditions.
        
        Args:
            coin: Coin symbol
            direction: "LONG" or "SHORT"
            price: Current price
            trade_threshold: The threshold for trading
            momentum_timeframe: The momentum timeframe in seconds
        
        Returns:
            New PendingOpportunity instance
        """
        return PendingOpportunity(
            coin=coin,
            direction=direction,
            current_price=price,
            conditions=[
                OpportunityCondition(
                    "Momentum",
                    f">{trade_threshold:.2f}% move in {momentum_timeframe}s"
                ),
                OpportunityCondition("No Position", "Not already in position"),
                OpportunityCondition("Cooldown", "30s since last trade"),
                OpportunityCondition("Balance", "Sufficient margin"),
            ]
        )
    
    def validate_conditions(
        self,
        opp: PendingOpportunity,
        momentum_pct: float,
        trade_threshold: float,
        has_position: bool,
        balance: float,
        position_size_pct: float,
    ) -> bool:
        """
        Validate opportunity conditions and update their status.
        
        Args:
            opp: The pending opportunity to validate
            momentum_pct: Current momentum percentage
            trade_threshold: Required momentum threshold
            has_position: Whether already in position for this coin
            balance: Current available balance
            position_size_pct: Percentage of balance per position
        
        Returns:
            True if all conditions are met
        """
        # 1. Momentum threshold
        opp.conditions[0].met = abs(momentum_pct) >= trade_threshold
        opp.conditions[0].value = f"{momentum_pct:+.2f}% (need ±{trade_threshold:.2f}%)"
        
        # 2. No existing position
        opp.conditions[1].met = not has_position
        opp.conditions[1].value = "✓" if not has_position else "In position"
        
        # 3. Cooldown (simplified - always true for now)
        opp.conditions[2].met = True
        opp.conditions[2].value = "✓"
        
        # 4. Balance check
        position_value = balance * position_size_pct
        opp.conditions[3].met = position_value > 0
        opp.conditions[3].value = f"${balance:,.0f}"
        
        return opp.is_valid
