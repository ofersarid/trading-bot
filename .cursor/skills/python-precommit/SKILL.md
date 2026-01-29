---
name: python-precommit
description: Write Python code that passes pre-commit hooks (Ruff, MyPy) on first try. Use when writing or editing Python files in this project to avoid lint errors and type issues.
---

# Python Pre-commit Compliance

This project uses Ruff + MyPy pre-commit hooks. Follow these patterns to pass on first commit.

## Quick Reference

| Issue | Bad | Good |
|-------|-----|------|
| Set comprehension | `set(x for x in items)` | `{x for x in items}` |
| File open | `open(path)` | `Path(path).open()` |
| Unused argument | `def f(unused):` | `def f(unused):  # noqa: ARG002` or `def f(_unused):` |
| Unused loop var | `for k, v in d.items():` (v unused) | `for k in d:` |
| Unused variable | `x = calc()` (never used) | `_ = calc()` or remove |
| Ambiguous char | `f"size × 2"` | `f"size x 2"` |
| Trailing whitespace | Lines ending with spaces | No trailing spaces |

---

## Ruff Rules (Enabled in pyproject.toml)

### ARG - Unused Arguments

```python
# Bad - Ruff ARG002
def callback(event, context):
    return event.data

# Good - Add noqa comment explaining why
def callback(event, context):  # noqa: ARG002 - required by framework
    return event.data

# Good - Prefix with underscore
def callback(event, _context):
    return event.data
```

**When to use each:**
- `# noqa: ARG002` - When signature is required by interface/framework
- `_prefix` - When you might use it later or for clarity

### C4 - Comprehensions

```python
# Bad - C401 unnecessary generator
unique = set(x.name for x in items)
signal_types = sorted(set(s.type for s in signals))

# Good - Set comprehension
unique = {x.name for x in items}
signal_types = sorted({s.type for s in signals})
```

### PTH - Use Pathlib

```python
# Bad - PTH123
with open(path, "w") as f:
    f.write(data)

# Good - Path.open()
from pathlib import Path
with Path(path).open("w") as f:
    f.write(data)
```

### B007 - Unused Loop Variables

```python
# Bad - B007 loop variable 'value' not used
for key, value in mapping.items():
    process(key)

# Good - Just iterate keys
for key in mapping:
    process(key)

# Good - If you need both but use only one
for key, _ in mapping.items():
    process(key)
```

### F841 - Unused Local Variables

```python
# Bad - F841 assigned but never used
result = expensive_calculation()
return True

# Good - Remove or use underscore
_ = expensive_calculation()  # Side effect needed
return True

# Good - Actually use it
result = expensive_calculation()
return result > 0
```

### RUF001 - Ambiguous Characters

```python
# Bad - RUF001 ambiguous '×' (multiplication sign)
logger.debug(f"size={base:.1f}% × {multiplier:.1f}x")

# Good - Use ASCII 'x'
logger.debug(f"size={base:.1f}% x {multiplier:.1f}x")
```

---

## MyPy Rules

### Type Compatibility

```python
# Bad - returns float | None, used where float expected
def get_atr(candles) -> float | None:
    ...

value = get_atr(candles)  # float | None
result = calculate(value)  # Expects float!

# Good - Handle None case
atr_result = get_atr(candles)
value = atr_result if atr_result is not None else 0.0
result = calculate(value)
```

### Literal Types

```python
# Bad - String doesn't match Literal
side: Literal["B", "A"] = "buy"  # Error!

# Good - Use correct literal value
side: Literal["B", "A"] = "B"

# Good - Convert if needed
side: Literal["long", "short"] = "long" if pos.side.value == "LONG" else "short"
```

### Unused type: ignore Comments

```python
# Bad - MyPy warn_unused_ignores is enabled
value = correct_type  # type: ignore[arg-type]  # Error if types now match!

# Good - Remove stale ignores
value = correct_type  # No ignore needed

# Good - Only ignore when actually needed
value = dynamic_value  # type: ignore[arg-type]  # Still needed due to X
```

### Variable Type Narrowing

```python
# Bad - Variable typed as TradePlan in loop, then assigned TradePlan | None
for plan in plans:  # plan: TradePlan
    ...
plan = get_plan()  # Returns TradePlan | None - conflicts!

# Good - Use different variable name
for plan in plans:
    ...
evaluated_plan = get_plan()  # Different name, no conflict
if evaluated_plan:
    ...
```

---

## File Hygiene

### Trailing Whitespace

Lines must not end with spaces. Configure your editor to trim on save.

### End of File

Files must end with a single newline.

### Debug Statements

```python
# Bad - Will fail check
print(f"Debug: {value}")
import pdb; pdb.set_trace()

# Good - Use logging
logger.debug(f"Debug: {value}")
```

---

## Pre-commit Workflow

If commit fails:

1. **Ruff auto-fixes** - Many issues are auto-fixed. Check `git diff` for changes.
2. **Remaining Ruff errors** - Fix manually using patterns above.
3. **MyPy errors** - Check type compatibility and remove stale ignores.
4. **Re-stage** - `git add -A` to include fixes.
5. **Commit again** - Should pass now.

---

## Common Patterns from This Project

### Position Side Conversion

```python
# Model expects lowercase literals
PortfolioPosition(
    side="long" if pos.side.value == "LONG" else "short",
)
```

### Decision ID Tracking

```python
# Dict expects string keys
self._pending_decision_ids[str(id(position))] = decision_id
```

### ATR Calculation

```python
# Handle None return from indicators
from bot.indicators.atr import atr as calculate_atr

atr_result = calculate_atr(candles, period=14)
atr_value = atr_result if atr_result is not None else 0.0
```
