# Trading Strategies

This folder contains trading strategy definitions for the AI trader. Each strategy defines:

1. **Prompt**: The AI's trading mindset and rules
2. **Risk Config**: Position sizing, stop-loss, take-profit parameters
3. **Signal Filtering**: Minimum strength, confidence thresholds

## Available Strategies

| Strategy | File | Description |
|----------|------|-------------|
| Momentum Scalper | `momentum_scalper.py` | Aggressive quick trades, small profits |
| Trend Follower | `trend_follower.py` | Patient, rides trends until exhaustion |
| Mean Reversion | `mean_reversion.py` | Contrarian, fades overextended moves |
| Conservative | `conservative.py` | High-confidence only, preserves capital |

## Usage

```python
from bot.strategies import get_strategy, list_strategies

# Get a strategy by name
strategy = get_strategy("momentum_scalper")
print(strategy.name)  # "Momentum Scalper"
print(strategy.prompt)  # The AI trading prompt
print(strategy.risk.max_position_pct)  # 15.0

# List all available strategies
for name, description in list_strategies():
    print(f"{name}: {description}")
```

## Adding a Custom Strategy

1. Create a new file in this folder (e.g., `my_strategy.py`)
2. Define the prompt and strategy:

```python
from bot.strategies.base import RiskConfig, Strategy, StrategyType

PROMPT = """You are a [describe trading style]...

YOUR TRADING STYLE:
- [Rule 1]
- [Rule 2]

ENTRY CRITERIA:
- [Criterion 1]
- [Criterion 2]

EXIT CRITERIA:
- [Criterion 1]
- [Criterion 2]

RISK RULES:
- [Rule 1]
- [Rule 2]
"""

MY_STRATEGY = Strategy(
    name="My Strategy",
    strategy_type=StrategyType.MOMENTUM_SCALPER,  # Pick closest type
    prompt=PROMPT,
    risk=RiskConfig(
        max_position_pct=10.0,
        stop_loss_atr_multiplier=1.5,
        take_profit_atr_multiplier=2.0,
        trail_activation_pct=0.5,
        trail_distance_pct=0.3,
    ),
    min_signal_strength=0.5,
    min_confidence=6,
    prefer_consensus=True,
)
```

3. Register it at runtime:

```python
from bot.strategies import register_strategy
from my_strategy import MY_STRATEGY

register_strategy("my_strategy", MY_STRATEGY)
```

Or add it to `__init__.py` to make it available by default.

## Strategy Components

### RiskConfig

| Parameter | Description | Default |
|-----------|-------------|---------|
| `max_position_pct` | Maximum position size (% of balance) | 10.0 |
| `stop_loss_atr_multiplier` | Stop loss = entry ± ATR × multiplier | 1.5 |
| `take_profit_atr_multiplier` | Take profit = entry ± ATR × multiplier | 2.0 |
| `trail_activation_pct` | Profit % to activate trailing stop | 0.5 |
| `trail_distance_pct` | Trailing stop distance as % of price | 0.3 |

### Signal Filtering

| Parameter | Description | Default |
|-----------|-------------|---------|
| `min_signal_strength` | Minimum signal strength (0-1) to consider | 0.3 |
| `min_confidence` | Minimum AI confidence (1-10) to act | 6 |
| `prefer_consensus` | Wait for multiple signals to agree | True |

## File Structure

```
bot/strategies/
├── __init__.py          # Registry and exports
├── base.py              # Strategy, RiskConfig, StrategyType classes
├── momentum_scalper.py  # Momentum scalper strategy
├── trend_follower.py    # Trend follower strategy
├── mean_reversion.py    # Mean reversion strategy
├── conservative.py      # Conservative strategy
└── README.md            # This file
```
