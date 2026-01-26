"""
Trading Strategies Module.

This module provides trading strategy definitions that control how the AI trades.
Each strategy combines a trading prompt (mindset/style) with risk parameters
and signal filtering rules.

Available strategies:
- momentum_scalper: Aggressive momentum scalping - quick entries/exits
- trend_follower: Patient trend following - ride the wave
- mean_reversion: Fade overextended moves - contrarian
- conservative: High-confidence only - preserve capital

Usage:
    from bot.strategies import get_strategy, Strategy

    strategy = get_strategy("momentum_scalper")
    print(strategy.name)  # "Momentum Scalper"
    print(strategy.prompt)  # The AI trading prompt
    print(strategy.risk.max_position_pct)  # 15.0
"""

from bot.strategies.base import RiskConfig, Strategy, StrategyType, TradingStrategy
from bot.strategies.conservative import CONSERVATIVE
from bot.strategies.mean_reversion import MEAN_REVERSION
from bot.strategies.momentum_scalper import MOMENTUM_SCALPER
from bot.strategies.trend_follower import TREND_FOLLOWER

# Registry of all strategies
_STRATEGIES: dict[str, Strategy] = {
    "momentum_scalper": MOMENTUM_SCALPER,
    "trend_follower": TREND_FOLLOWER,
    "mean_reversion": MEAN_REVERSION,
    "conservative": CONSERVATIVE,
}


def get_strategy(name: str) -> Strategy:
    """
    Get a pre-defined strategy by name.

    Args:
        name: Strategy name (case-insensitive, underscores/hyphens/spaces accepted)

    Returns:
        Strategy instance

    Raises:
        ValueError: If strategy not found

    Example:
        >>> strategy = get_strategy("momentum_scalper")
        >>> strategy = get_strategy("Momentum Scalper")  # Also works
        >>> strategy = get_strategy("momentum-scalper")  # Also works
    """
    key = name.lower().replace(" ", "_").replace("-", "_")
    if key not in _STRATEGIES:
        available = ", ".join(_STRATEGIES.keys())
        raise ValueError(f"Unknown strategy '{name}'. Available: {available}")

    return _STRATEGIES[key]


def list_strategies() -> list[tuple[str, str]]:
    """
    List available strategies with descriptions.

    Returns:
        List of (name, description) tuples
    """
    return [
        ("momentum_scalper", "Aggressive momentum scalping - quick entries/exits"),
        ("trend_follower", "Patient trend following - ride the wave"),
        ("mean_reversion", "Fade overextended moves - contrarian"),
        ("conservative", "High-confidence only - preserve capital"),
    ]


def register_strategy(name: str, strategy: Strategy) -> None:
    """
    Register a custom strategy.

    Args:
        name: Name to register the strategy under
        strategy: Strategy instance

    Example:
        >>> from bot.strategies import register_strategy, Strategy, RiskConfig
        >>> my_strategy = Strategy(
        ...     name="My Strategy",
        ...     strategy_type=StrategyType.MOMENTUM_SCALPER,
        ...     prompt="...",
        ...     risk=RiskConfig(max_position_pct=10.0),
        ... )
        >>> register_strategy("my_strategy", my_strategy)
    """
    _STRATEGIES[name.lower().replace(" ", "_").replace("-", "_")] = strategy


__all__ = [
    # Base classes
    "RiskConfig",
    "Strategy",
    "StrategyType",
    "TradingStrategy",
    # Registry functions
    "get_strategy",
    "list_strategies",
    "register_strategy",
    # Pre-defined strategies
    "MOMENTUM_SCALPER",
    "TREND_FOLLOWER",
    "MEAN_REVERSION",
    "CONSERVATIVE",
]
