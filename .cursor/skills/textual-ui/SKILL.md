---
name: textual-ui
description: Textual TUI framework patterns for the trading dashboard. Use when working on bot/ui/ components, dashboard layout, or Textual widgets.
---

# Textual UI Patterns

Patterns for building the trading dashboard with Textual TUI framework.

## App Class Should Be Thin

The main `App` class should only contain:
1. `CSS_PATH` reference
2. `BINDINGS` definitions
3. `compose()` method for layout
4. `on_mount()` for initialization
5. Action handlers (`action_*` methods)
6. High-level coordination logic

Move everything else to separate component classes, business logic modules, or utility functions.

---

## CSS Separation

**Never embed CSS as Python strings.** Store CSS in separate `.css` files:

```python
class TradingDashboard(App):
    CSS_PATH = "styles/theme.css"
```

CSS files go in `bot/ui/styles/`.

---

## Reactive State Pattern

Use Textual's reactive properties for state that triggers UI updates:

```python
class TradingDashboard(App):
    balance = reactive(10000.0)

    def watch_balance(self, new_value: float) -> None:
        """Called automatically when balance changes."""
        self.update_status_bar()
```

---

## Component Communication

### Parent → Child: Props or Messages

```python
# Via construction
panel = PricesPanel(prices=self.prices)

# Via messages for runtime updates
self.query_one(PricesPanel).post_message(PricesUpdated(self.prices))
```

### Child → Parent: Custom Messages

```python
class TradeRequested(Message):
    def __init__(self, coin: str, direction: str, size: float):
        self.coin = coin
        self.direction = direction
        self.size = size
        super().__init__()

# In parent
def on_trade_requested(self, event: TradeRequested) -> None:
    self.execute_trade(event.coin, event.direction, event.size)
```

---

## Component Design

Components should receive data via props, not reach into parent state:

```python
# Good: Component receives data
class PricesPanel(Static):
    def __init__(self, prices: dict[str, float], momentum: dict[str, float]):
        ...

# Bad: Component reaches into app state
class PricesPanel(Static):
    def update(self):
        prices = self.app.prices  # Don't do this
```

---

## Widget Selection

### RichLog
Use for:
- Streaming data (trades, logs)
- Formatted text with colors
- Variable-length content

### DataTable
Use for:
- Structured tabular data
- Sortable/selectable rows
- Fixed-column layouts

---

## Update Patterns

### Batch Updates

Batch multiple updates to avoid flicker:

```python
def update_all_displays(self) -> None:
    with self.batch_update():
        self.update_prices_display()
        self.update_orderbook_display()
        self.update_positions_display()
```

### Throttled Updates

For high-frequency data, throttle display updates:

```python
def __init__(self):
    self._last_price_update = datetime.min
    self._update_interval = 0.1  # 100ms minimum

async def handle_prices(self, data: dict) -> None:
    self._process_price_data(data)  # Always process

    now = datetime.now()
    if (now - self._last_price_update).total_seconds() >= self._update_interval:
        self.update_prices_display()  # Throttle display
        self._last_price_update = now
```

---

## CSS Classes for State

Use CSS classes to represent component state:

```css
.position.profit {
    color: #00ff88;
    border: solid #00ff88;
}

.position.loss {
    color: #ff4444;
    border: solid #ff4444;
}
```

```python
def update_position_style(self, widget: Widget, pnl: float) -> None:
    widget.remove_class("profit", "loss")
    widget.add_class("profit" if pnl >= 0 else "loss")
```

---

## Key Bindings

Keep bindings simple and documented:

```python
BINDINGS = [
    Binding("q", "quit", "Quit"),
    Binding("r", "reset", "Reset"),
    Binding("space", "toggle_pause", "Pause/Resume"),
    # Threshold adjustments
    Binding("1", "decrease_track", "Track -"),
    Binding("2", "increase_track", "Track +"),
]
```

---

## Notifications

Use built-in notification system for errors and feedback:

```python
def show_error(self, message: str) -> None:
    self.notify(message, severity="error", timeout=5)

def show_success(self, message: str) -> None:
    self.notify(message, severity="information", timeout=3)
```

---

## Related Skills

- For Python code style, see [python-code-style](../python-code-style/SKILL.md)
- For pre-commit compliance, see [python-precommit](../python-precommit/SKILL.md)
