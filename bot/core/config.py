"""
Trading configuration and thresholds.

Centralizes all magic numbers and adjustable parameters for easy tuning.
"""

from dataclasses import dataclass


@dataclass
class TradingConfig:
    """Configuration for trading behavior and thresholds.
    
    All percentage values are expressed as decimals (e.g., 0.10 = 10%).
    """
    
    # =========================================================
    # Opportunity Detection Thresholds
    # =========================================================
    
    # Minimum momentum to start tracking an opportunity
    track_threshold_pct: float = 0.02
    
    # Minimum momentum to execute a trade
    trade_threshold_pct: float = 0.04
    
    # =========================================================
    # Position Management
    # =========================================================
    
    # Take profit when unrealized P&L reaches this %
    take_profit_pct: float = 0.10
    
    # Stop loss when unrealized P&L drops to this %
    stop_loss_pct: float = -0.05
    
    # Percentage of balance to use per trade
    position_size_pct: float = 0.10
    
    # =========================================================
    # Analysis Parameters
    # =========================================================
    
    # Seconds to look back for momentum calculation
    momentum_lookback_seconds: int = 60
    
    # Seconds between market condition analyses
    market_analysis_interval_seconds: int = 10
    
    # Maximum price history points to retain per coin
    price_history_maxlen: int = 500
    
    # =========================================================
    # Display Limits
    # =========================================================
    
    # Maximum recent trades to keep in memory
    max_trades_history: int = 100
    
    # Order book depth to display (asks and bids)
    orderbook_depth: int = 8
    
    # Maximum trades to show in live trades panel
    max_trades_displayed: int = 15
    
    # =========================================================
    # Market Condition Thresholds
    # =========================================================
    
    # Average momentum thresholds for market condition classification
    market_very_calm_threshold: float = 0.05
    market_calm_threshold: float = 0.10
    market_active_threshold: float = 0.20
    market_volatile_threshold: float = 0.50
    
    # Momentum threshold for individual coin status
    coin_rising_threshold: float = 0.10
    coin_falling_threshold: float = -0.10
    
    # =========================================================
    # Momentum Display Thresholds (for UI labels)
    # =========================================================
    
    # Thresholds for momentum strength labels in prices display
    momentum_flat_threshold: float = 0.10      # Below this = "flat"
    momentum_weak_threshold: float = 0.30      # Below this = "weak"
    momentum_strong_threshold: float = 0.50    # Below this = "strong", above = "aggro"
    
    # =========================================================
    # Logging Intervals
    # =========================================================
    
    # Log price history building every N updates
    price_history_log_interval: int = 50
    
    # Log momentum analysis every N updates
    momentum_analysis_log_interval: int = 100


# Default configuration instance
DEFAULT_CONFIG = TradingConfig()
