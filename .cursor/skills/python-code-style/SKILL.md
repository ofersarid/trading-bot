---
name: python-code-style
description: Python coding standards for this project including file size limits, type hints, docstrings, and code organization. Use when writing, refactoring, or reviewing Python code.
---

# Python Code Style

Standards for Python code in this trading bot project.

## File Size Limits

| Threshold | Lines | Action |
|-----------|-------|--------|
| Target | 300-400 | Ideal file size |
| Warning | 400-500 | Consider extraction |
| Hard Limit | 500+ | Must refactor |

**Exception**: Test files can exceed limits if testing a single module comprehensively.

## When to Extract

Extract code into separate modules when:

1. **File exceeds 400 lines**
2. **Class has multiple responsibilities** (violates SRP)
3. **Related functions form a cohesive concept**
4. **Same pattern appears in multiple places**

## Extraction Patterns

### Pure Functions (no `self` state needed)

```python
# Before: method in large class
class Dashboard:
    def calculate_momentum(self, prices, timeframe):
        # 20 lines of pure calculation

# After: extract to utility module
# utils/calculations.py
def calculate_momentum(prices: list, timeframe: int) -> float:
    # 20 lines of pure calculation
```

### Handler Classes (need limited state)

```python
# Before: handler methods scattered in main class
class Dashboard:
    def handle_price_update(self, data): ...
    def handle_trade_update(self, data): ...

# After: extract to handler module with callbacks
# handlers/messages.py
class MessageHandler:
    def __init__(self, on_price_update, on_trade_update):
        self.on_price_update = on_price_update
        self.on_trade_update = on_trade_update
```

## Module Naming Conventions

| Folder | Purpose |
|--------|---------|
| `handlers/` | Event handlers and callbacks |
| `actions/` | User-triggered actions (keybindings, commands) |
| `utils/` | Pure utility functions with no side effects |
| `services/` | Stateful business logic classes |

---

## Project Structure

```
bot/
├── core/              # Core business logic
│   ├── models.py      # Data classes, enums, types
│   ├── constants.py   # Magic numbers, thresholds, config
│   └── analysis.py    # Market analysis logic
├── ui/
│   ├── dashboard.py   # Main app composition only
│   ├── components/    # Reusable UI components
│   └── styles/        # CSS files
├── simulation/        # Paper trading logic
└── hyperliquid/       # Exchange integration
```

## Separation of Concerns

### UI Layer (ui/)
- Layout composition
- Event handling (key bindings, clicks)
- Display formatting (colors, emojis, layout)
- NO business logic, NO calculations

### Business Logic Layer (core/)
- Market analysis
- Opportunity detection
- Trade decisions
- Price calculations

### Data Layer (core/models.py)
- Dataclasses
- Enums
- Type definitions

---

## Type Hints

**Required everywhere:**

```python
# Good
def calculate_momentum(
    current_price: float,
    history: deque[dict[str, float | datetime]],
    lookback_seconds: int = 60,
) -> float | None:
    ...

# Bad - missing types
def calculate_momentum(current_price, history, lookback_seconds=60):
    ...
```

Use `|` syntax for unions (Python 3.10+).

---

## Method Length

**Maximum: 30 lines** (excluding docstrings)

```python
# Bad: 50+ line method mixing concerns
def analyze_opportunity(self, coin, price, old_price):
    # 50 lines of mixed logic...

# Good: Composed of focused methods
def analyze_opportunity(self, coin: str, price: float, old_price: float) -> None:
    momentum = self._calculate_momentum(coin)
    if momentum is None:
        return

    if self._should_track_opportunity(momentum):
        self._update_or_create_opportunity(coin, price, momentum)
    else:
        self._maybe_remove_opportunity(coin)
```

---

## Constants & Configuration

### No Magic Numbers

```python
# Bad
if momentum > 0.3:  # What is 0.3?
    execute_trade()

# Good
MOMENTUM_TRADE_THRESHOLD = 0.30  # Minimum 60s momentum % to trigger trade

if momentum > MOMENTUM_TRADE_THRESHOLD:
    execute_trade()
```

### Centralized Configuration

```python
@dataclass
class TradingConfig:
    track_threshold: float = 0.10
    trade_threshold: float = 0.30
    take_profit_pct: float = 0.50
    stop_loss_pct: float = -0.30
    position_size_pct: float = 0.10
```

---

## Docstrings

### Module-level (required)

```python
"""
Market analysis module for the trading bot.

Provides functions for:
- Calculating momentum indicators
- Detecting trading opportunities
"""
```

### Public functions (required)

Include: brief description, Args (if not obvious), Returns, Example (for complex functions).

---

## Error Handling

```python
# Bad - bare except, silenced
try:
    result = risky_operation()
except Exception:
    pass

# Good - specific, logged
try:
    result = risky_operation()
except ConnectionError as e:
    logger.error(f"Connection failed: {e}")
    # Retry logic or graceful degradation
```

---

## Async Patterns

### WebSocket Handling

Keep message handlers thin - parse and delegate:

```python
async def process_message(self, data: dict) -> None:
    channel = data.get("channel")
    handlers = {
        "allMids": self.handle_prices,
        "trades": self.handle_trades,
        "l2Book": self.handle_orderbook,
    }
    handler = handlers.get(channel)
    if handler:
        await handler(data)
```

Use `@work` decorator for long-running background tasks.

---

## Related Skills

- For pre-commit compliance (Ruff, MyPy), see [python-precommit](../python-precommit/SKILL.md)
- For Textual UI patterns, see [textual-ui](../textual-ui/SKILL.md)
