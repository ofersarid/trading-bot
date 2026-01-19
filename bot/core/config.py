"""
Trading configuration and thresholds.

Centralizes all magic numbers and adjustable parameters for easy tuning.
"""

from dataclasses import dataclass


@dataclass
class TradingConfig:
    """Configuration for trading behavior and thresholds.

    All percentage values are expressed as decimals (e.g., 0.10 = 10%).

    TUNABLE PARAMETERS (for feedback loop optimization):
    - Entry: track_threshold_pct, trade_threshold_pct, momentum_timeframe_seconds
    - Exit: take_profit_pct, stop_loss_pct
    - Position: position_size_pct, cooldown_seconds, max_concurrent_positions
    """

    # =========================================================
    # Opportunity Detection Thresholds (TUNABLE)
    # =========================================================

    # Minimum momentum to start tracking an opportunity
    # Range: 0.01% - 0.10% | Lower = more sensitive, more signals
    track_threshold_pct: float = 0.02

    # Minimum momentum to execute a trade
    # Range: 0.02% - 0.20% | Lower = more trades, potentially lower quality
    trade_threshold_pct: float = 0.04

    # Lookback period for momentum calculation (TUNABLE)
    # Range: 1-30 seconds | Lower = more responsive, more noise
    momentum_timeframe_seconds: int = 5

    # =========================================================
    # Position Management (TUNABLE)
    # =========================================================

    # Take profit when unrealized P&L reaches this %
    # Range: 1% - 20% | Higher = larger wins but fewer exits
    take_profit_pct: float = 0.10

    # Stop loss when unrealized P&L drops to this %
    # Range: -2% to -10% | Tighter = smaller losses but more stops
    stop_loss_pct: float = -0.05

    # Percentage of balance to use per trade (TUNABLE)
    # Range: 5% - 25% | Higher = larger positions, more risk
    position_size_pct: float = 0.10

    # Seconds to wait between trades on the same coin (TUNABLE)
    # Range: 10-120 seconds | Lower = more trades, potential overtrading
    cooldown_seconds: float = 30.0

    # Maximum concurrent positions across all coins (TUNABLE)
    # Range: 1-5 | Higher = more diversification but more capital needed
    max_concurrent_positions: int = 2

    # =========================================================
    # Analysis Parameters
    # =========================================================

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
    # Logging Intervals
    # =========================================================

    # Log price history building every N updates
    price_history_log_interval: int = 50

    # Log momentum analysis every N updates
    momentum_analysis_log_interval: int = 100


# Default configuration instance
DEFAULT_CONFIG = TradingConfig()
