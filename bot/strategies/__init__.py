"""
Trading Strategies Module.

This module provides trading strategy definitions that control signal weighting
and risk parameters. Each strategy defines which signals to prioritize and
how aggressively to trade.

Available strategies:
- momentum_based: Primary MOMENTUM signal with VP support
- momentum_macd: MOMENTUM + MACD confirmation required
- rsi_based: Primary RSI signal with VP support
- multi_signal: Multiple signals must align (balanced weights)

Usage:
    from bot.strategies import get_strategy, Strategy

    strategy = get_strategy("momentum_based")
    print(strategy.name)  # "Momentum Based"
    print(strategy.signal_weights)  # {MOMENTUM: 1.0, VOLUME_PROFILE: 0.5}
    print(strategy.risk.max_position_pct)  # 15.0
"""

from bot.signals.base import SignalType
from bot.strategies.base import RiskConfig, Strategy, StrategyType, TradingStrategy
from bot.strategies.momentum_based import MOMENTUM_BASED
from bot.strategies.momentum_macd import MOMENTUM_MACD
from bot.strategies.multi_signal import MULTI_SIGNAL
from bot.strategies.rsi_based import RSI_BASED

# Registry of all strategies
_STRATEGIES: dict[str, Strategy] = {
    "momentum_based": MOMENTUM_BASED,
    "momentum_macd": MOMENTUM_MACD,
    "rsi_based": RSI_BASED,
    "multi_signal": MULTI_SIGNAL,
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
        >>> strategy = get_strategy("momentum_based")
        >>> strategy = get_strategy("Momentum Based")  # Also works
        >>> strategy = get_strategy("momentum-based")  # Also works
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
        ("momentum_based", "Primary: MOMENTUM (1.0) + VP (0.5)"),
        ("momentum_macd", "Primary: MOMENTUM (0.6) + MACD (0.4)"),
        ("rsi_based", "Primary: RSI (1.0) + VP (0.3)"),
        ("multi_signal", "Balanced: MOMENTUM (0.4) + RSI (0.3) + MACD (0.3)"),
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
        ...     strategy_type=StrategyType.MOMENTUM_BASED,
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
    # Signal types for custom strategy creation
    "SignalType",
    # Registry functions
    "get_strategy",
    "list_strategies",
    "register_strategy",
    # Pre-defined strategies
    "MOMENTUM_BASED",
    "MOMENTUM_MACD",
    "RSI_BASED",
    "MULTI_SIGNAL",
]
