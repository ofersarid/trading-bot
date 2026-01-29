# Trading Strategies

This folder contains trading strategy definitions for the AI trader. Each strategy defines:

1. **Signal Weights**: How important each signal type is to the strategy
2. **Signal Threshold**: Minimum weighted score to consider a trade
3. **Risk Config**: Position sizing, stop-loss, take-profit parameters
4. **Prompt**: The AI's trading mindset and rules (used when AI mode enabled)

## Available Strategies

| Strategy | File | Primary Signals | Description |
|----------|------|-----------------|-------------|
| Momentum Based | `momentum_based.py` | MOMENTUM (1.0) + VP (0.5) | Primary momentum with VP support |
| Momentum + MACD | `momentum_macd.py` | MOMENTUM (0.6) + MACD (0.4) | Requires MACD confirmation |
| RSI Based | `rsi_based.py` | RSI (1.0) + VP (0.3) | Primary RSI with VP support |
| Multi-Signal | `multi_signal.py` | MOM (0.4) + RSI (0.3) + MACD (0.3) | Multiple signals must align |

## Usage

```python
from bot.strategies import get_strategy, list_strategies

# Get a strategy by name
strategy = get_strategy("momentum_based")
print(strategy.name)  # "Momentum Based"
print(strategy.signal_weights)  # {SignalType.MOMENTUM: 1.0, SignalType.VOLUME_PROFILE: 0.5}
print(strategy.signal_threshold)  # 0.7

# List all available strategies
for name, description in list_strategies():
    print(f"{name}: {description}")
```

## How Signal Weighting Works

Each signal type has a **weight** (0.0-1.0) that determines its importance to the strategy.

**Weighted Score Calculation:**
```
For each signal: contribution = weight * signal_strength
Total score per direction = sum of all contributions for LONG or SHORT
```

**Example:**
```
Momentum Based receives:
- MOMENTUM LONG, strength=0.85, weight=1.0 → contribution: 0.85
- VOLUME_PROFILE LONG, strength=0.60, weight=0.5 → contribution: 0.30

Total LONG score = 0.85 + 0.30 = 1.15
Threshold = 0.7
Result: 1.15 >= 0.7 → Proceed with trade
```

## Adding a Custom Strategy

1. Create a new file in this folder (e.g., `my_strategy.py`)
2. Define the prompt and strategy:

```python
from bot.signals.base import SignalType
from bot.strategies.base import RiskConfig, Strategy, StrategyType

PROMPT = """You are a [describe trading style]...

SIGNAL WEIGHTS:
- SIGNAL_TYPE_1: [weight] (primary/supporting signal)
- SIGNAL_TYPE_2: [weight] (primary/supporting signal)

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
    strategy_type=StrategyType.MOMENTUM_BASED,  # Pick closest type
    prompt=PROMPT,
    risk=RiskConfig(
        max_position_pct=10.0,
        stop_loss_atr_multiplier=1.5,
        take_profit_atr_multiplier=2.0,
        trail_activation_pct=0.5,
        trail_distance_pct=0.3,
    ),
    signal_weights={
        SignalType.MOMENTUM: 1.0,  # Primary signal - full weight
        SignalType.RSI: 0.5,  # Supporting signal - half weight
    },
    signal_threshold=0.7,  # Minimum weighted score to trade
    min_signal_strength=0.3,  # Noise filter for weak signals
    min_confidence=6,
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
| `stop_loss_atr_multiplier` | Stop loss = entry +/- ATR * multiplier | 1.5 |
| `take_profit_atr_multiplier` | Take profit = entry +/- ATR * multiplier | 2.0 |
| `trail_activation_pct` | Profit % to activate trailing stop | 0.5 |
| `trail_distance_pct` | Trailing stop distance as % of price | 0.3 |

### Signal Weighting

| Parameter | Description | Default |
|-----------|-------------|---------|
| `signal_weights` | Dict mapping SignalType to weight (0.0-1.0) | `{}` (empty) |
| `signal_threshold` | Minimum weighted score to consider a trade | 0.5 |
| `min_signal_strength` | Noise filter - ignore signals below this strength | 0.2 |
| `min_confidence` | Minimum AI confidence (1-10) to act | 6 |

### Signal Weight Configuration

Each strategy defines weights for the signal types it uses:

| Strategy | MOMENTUM | RSI | MACD | VOLUME_PROFILE | Threshold |
|----------|----------|-----|------|----------------|-----------|
| Momentum Based | 1.0 | - | - | 0.5 | 0.7 |
| Momentum + MACD | 0.6 | - | 0.4 | - | 0.6 |
| RSI Based | - | 1.0 | - | 0.3 | 0.8 |
| Multi-Signal | 0.4 | 0.3 | 0.3 | - | 0.8 |

**Note:** `-` means the signal type is not used by that strategy.

Available signal types: `MOMENTUM`, `RSI`, `MACD`, `VOLUME_PROFILE`

## File Structure

```
bot/strategies/
├── __init__.py          # Registry and exports
├── base.py              # Strategy, RiskConfig, StrategyType classes
├── momentum_based.py    # Primary MOMENTUM signal
├── momentum_macd.py     # MOMENTUM + MACD confirmation
├── rsi_based.py         # Primary RSI signal
├── multi_signal.py      # Multiple signals required
└── README.md            # This file
```
