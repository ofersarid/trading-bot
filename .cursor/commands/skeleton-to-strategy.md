# Skeleton to PineScript Strategy

Convert a strategy skeleton into a working PineScript v6 strategy for TradingView.

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| `skeleton.md` | ✅ Yes | Strategy skeleton with entry/exit rules |
| `indicator.pine` | ❌ Optional | Existing indicator to convert and integrate |

## Instructions

Read the provided `skeleton.md` and implement it as a PineScript v6 strategy.

**If an `indicator.pine` file is provided:**
- Use it as the foundation for calculations
- Extract and reuse its indicator logic, inputs, and visualizations
- Map the skeleton's entry/exit rules to the indicator's signals/conditions

### Before You Start

1. **Read the documentation manifest** - Check `pinescriptv6/LLM_MANIFEST.md` to understand the documentation structure
2. **Understand the strategy** - Make sure Entry/Exit rules are clear before coding
3. **Identify required indicators** - List what built-in or custom indicators you'll need
4. **If indicator provided** - Read it first and identify which signals map to entry/exit conditions

### Converting an Indicator to Strategy

When an `indicator.pine` file is provided, follow this process:

#### Step 1: Analyze the Indicator
- Identify all **inputs** (keep them, add strategy-specific ones)
- Identify **calculated values** (levels, zones, signals)
- Identify **visual elements** (plots, shapes, lines, boxes)
- Note any **alert conditions** (these often map to entry signals)

#### Step 2: Transform the Header
```pinescript
// FROM indicator:
//@version=6
indicator("Indicator Name", overlay=true)

// TO strategy:
//@version=6
strategy("Strategy Name v0.1", 
    overlay=true,
    initial_capital=10000,
    default_qty_type=strategy.percent_of_equity,
    default_qty_value=100)
```

#### Step 3: Map Signals to Strategy Actions
| Indicator Signal | Strategy Action |
|-----------------|-----------------|
| Bullish signal/alert | `strategy.entry("Long", strategy.long)` |
| Bearish signal/alert | `strategy.entry("Short", strategy.short)` |
| Exit signal | `strategy.close()` or `strategy.exit()` |
| Zone/level reached | Entry or exit condition |

#### Step 4: Add Strategy-Specific Logic
- Take profit / stop loss levels (if in skeleton)
- Position sizing (if different from default)
- Trade filters (time, volatility, etc.)

### Required Documentation Files

**Always consult these files before writing code:**

| What You Need | File to Read |
|--------------|--------------|
| Strategy functions (`strategy.entry`, `strategy.exit`, `strategy.close`) | `pinescriptv6/reference/functions/strategy.md` |
| Technical indicators (`ta.rsi`, `ta.sma`, `ta.crossover`) | `pinescriptv6/reference/functions/ta.md` |
| Plotting & visuals (`plot`, `plotshape`, `line.new`, `box.new`) | `pinescriptv6/reference/functions/drawing.md` |
| User inputs (`input.int`, `input.float`, `input.bool`) | `pinescriptv6/reference/functions/general.md` |
| Built-in variables (`open`, `close`, `high`, `low`, `volume`) | `pinescriptv6/reference/variables.md` |
| Constants (`color.red`, `shape.triangleup`) | `pinescriptv6/reference/constants.md` |
| `var`/`varip` and execution model | `pinescriptv6/concepts/execution_model.md` |
| Common errors & fixes | `pinescriptv6/concepts/common_errors.md` |

**Routing Examples:**
- Building entry/exit logic → Read `strategy.md` + `ta.md`
- Drawing zones or boxes → Read `drawing.md`
- Multi-timeframe data → Read `pinescriptv6/reference/functions/request.md`
- Arrays for tracking levels → Read `pinescriptv6/reference/functions/collections.md`

### Implementation Requirements

#### Script Header
```pinescript
//@version=6
strategy("[Strategy Name]", 
    overlay=true, 
    initial_capital=10000,
    default_qty_type=strategy.percent_of_equity,
    default_qty_value=100,
    commission_type=strategy.commission.percent,
    commission_value=0.1)
```

#### Required Sections (in order)

1. **Inputs** - User-configurable parameters
2. **Calculations** - Indicators, levels, conditions
3. **Entry Conditions** - Long and short entry logic
4. **Exit Conditions** - Take profit, stop loss logic
5. **Strategy Execution** - `strategy.entry()` and `strategy.exit()` calls
6. **Visualizations** - Plot indicators, entry/exit markers, zones

#### Coding Standards

- Use descriptive variable names (`bullishEngulfing` not `be`)
- Group related inputs with `group` parameter
- Add tooltips to inputs explaining their purpose
- Use `var` for variables that persist across bars (see `concepts/execution_model.md`)
- Prefer `ta.*` namespace functions over manual calculations
- Comment each logical section
- **Do not invent functions** - if not found in the docs, it doesn't exist

### Output

Write to the appropriate version file in `strategies/{strategy_name}/`:
- New strategy → `0.1.pine`
- Iteration → increment version (`0.2.pine`, `0.3.pine`, etc.)

### Strategy Template

```pinescript
//@version=6
strategy("[Strategy Name] v0.1", 
    overlay=true,
    initial_capital=10000,
    default_qty_type=strategy.percent_of_equity,
    default_qty_value=100)

// ══════════════════════════════════════════════════════════════════════════════
// INPUTS
// ══════════════════════════════════════════════════════════════════════════════

// Entry Parameters
// ...

// Exit Parameters  
// ...

// ══════════════════════════════════════════════════════════════════════════════
// CALCULATIONS
// ══════════════════════════════════════════════════════════════════════════════

// Indicator calculations
// ...

// ══════════════════════════════════════════════════════════════════════════════
// CONDITIONS
// ══════════════════════════════════════════════════════════════════════════════

// Entry conditions
longCondition = false  // TODO: implement
shortCondition = false // TODO: implement

// ══════════════════════════════════════════════════════════════════════════════
// STRATEGY EXECUTION
// ══════════════════════════════════════════════════════════════════════════════

if longCondition
    strategy.entry("Long", strategy.long)

if shortCondition
    strategy.entry("Short", strategy.short)

// Exit logic
// strategy.exit(...)

// ══════════════════════════════════════════════════════════════════════════════
// VISUALIZATIONS
// ══════════════════════════════════════════════════════════════════════════════

// Plot indicators, zones, signals
// ...
```

### Common Patterns

#### Order Block Detection
```pinescript
// Bearish OB: last bearish candle before bullish impulse
// Bullish OB: last bullish candle before bearish impulse
```

#### Candle Patterns
```pinescript
bullishEngulfing = close[1] < open[1] and close > open and close > open[1] and open < close[1]
bearishEngulfing = close[1] > open[1] and close < open and close < open[1] and open > close[1]
```

#### Zone Management
```pinescript
var float zoneTop = na
var float zoneBottom = na
inZone = close >= zoneBottom and close <= zoneTop
```

### Checklist Before Saving

- [ ] Consulted required documentation files (strategy.md, ta.md, drawing.md)
- [ ] If indicator provided: all its logic is integrated
- [ ] Script compiles without errors
- [ ] All skeleton entry rules are implemented
- [ ] All skeleton exit rules are implemented
- [ ] Inputs have sensible defaults matching skeleton
- [ ] Key levels/zones are visualized
- [ ] Entry/exit signals are plotted
