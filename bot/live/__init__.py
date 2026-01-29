"""
Live Trading Module - Real-time trading using unified architecture.

This module provides live trading capabilities that use the SAME logic
as the backtest system. Backtest results are predictive of live performance.

Usage:
    # Run from command line
    python -m bot.live.engine --balance 10000 --ai --goal 50000 --goal-days 30

    # Or import and use programmatically
    from bot.live import LiveEngine

    engine = LiveEngine(
        coins=["BTC", "ETH"],
        strategy_name="momentum_based",
        ai_enabled=True,
        account_goal=50000,
        goal_timeframe_days=30,
    )
    await engine.run()
"""

from bot.live.engine import LiveEngine

__all__ = ["LiveEngine"]
