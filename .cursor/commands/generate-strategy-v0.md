---
name: Indicators to Positioning Strategy
description: Generates a PineScript positioning strategy from indicators.pine and spec.md files
tags: [pinescript, strategy, indicators, automation]
---

# Indicators to Positioning Strategy Command

## What You'll Be Asked

When running this command, you will be prompted for:

1. **📍 Positioning Criteria** - What conditions trigger an entry? (in priority order)
2. **🎯 Take Profit Logic** - How should TP be calculated?
3. **🛑 Stop Loss Logic** - How should SL be calculated?
4. ⚙️ **Additional Settings** (optional) - Trailing stops, filters, position size, etc.

*Note: These prompts are skipped if you already have a `spec.md` file in the strategy folder.*

---

## Purpose

This command creates a complete PineScript v6 positioning strategy by combining:
1. **indicators.pine** (Required) - Technical indicators with calculations and signals
2. **spec.md** (Optional) - Strategy specification with entry/exit rules, OR interactive prompts if spec.md is not present
3. **Output:** `strategy.pine` - Working positioning strategy

**Interactive Mode:** If spec.md is not present, the command will prompt you for:
- **Positioning criteria** (entry conditions in priority order)
- **Take profit method** (how TP should be calculated)
- **Stop loss method** (how SL should be calculated)
- **Additional settings** (trailing stop, filters, position size, etc.)

---

## ⚠️ CRITICAL: Implementation Philosophy

**This command is a PURE TRANSLATOR - it implements ONLY what you specify.**

### Do NOT:
- ❌ Add logic or risk management not explicitly requested
- ❌ Add filters, checks, or conditions not specified by the user
- ❌ Add "smart" features like auto break-even, pyramiding, or hedging
- ❌ Add additional inputs beyond what's in indicators.pine + user specifications
- ❌ Add defensive code or guards not requested
- ❌ Interpret or enhance the user's criteria with additional logic

### DO:
- ✅ Implement EXACTLY what the user specifies
- ✅ Preserve ALL indicator logic from indicators.pine unchanged
- ✅ Use indicator signals exactly as the user describes
- ✅ Calculate TP/SL exactly as the user specifies (no modifications)
- ✅ If the user says "use Pine_Supertrend as SL", use it directly - don't add buffers
- ✅ If something is unclear, ask the user rather than making assumptions

**Example:**
- User says: "Enter long when bull_condition is true"
- Correct: `if bull_condition and barstate.isconfirmed`
- Wrong: `if bull_condition and barstate.isconfirmed and volume > sma(volume, 20)` ← Don't add volume check!

**The user is responsible for strategy logic. You are only the code generator.**

### Handling Minimal Specifications

**If the user provides minimal criteria:**
- Generate minimal code
- Don't fill in gaps with your own assumptions
- Don't add "recommended" features

**Example:**
User says: "Enter long when bull_condition, TP at 2%, SL at Pine_Supertrend"

Generate:
```pinescript
// Entry
longEntry = bull_condition and barstate.isconfirmed

if longEntry
    strategy.entry("Long", strategy.long)
    strategy.exit("Long Exit", "Long",
        limit=close * 1.02,
        stop=Pine_Supertrend)
```

Do NOT generate:
```pinescript
// Entry with added filters
longEntry = bull_condition and barstate.isconfirmed and volume > avgVolume  // ❌ Don't add volume filter!

// Position sizing calculation you weren't asked for
positionSize = (account.equity * riskPercent) / (close - Pine_Supertrend)  // ❌ User didn't ask for this!

if longEntry
    strategy.entry("Long", strategy.long, qty=positionSize)  // ❌ User said 100% equity!
```

---

## Prerequisites Check

Before generating the strategy, verify these files exist in the specified folder:

1. **indicators.pine** (Required)
   - Contains indicator calculations (SuperTrend, FVG, CHOCH, etc.)
   - Has plots, alerts, or signal conditions
   - Uses `//@version=6` indicator declaration

2. **spec.md** (Optional)
   - If present, will be used for strategy rules
   - If missing, user will be prompted interactively

**If indicators.pine is missing, STOP and prompt the user:**
> "⚠️ Missing indicators.pine file. Expected structure:
> ```
> strategies/[strategy_name]/
>   ├── indicators.pine    ← Technical indicators (Required)
>   ├── spec.md            ← Strategy specification (Optional)
>   └── strategy.pine      ← Will be generated
> ```
>
> Please specify a valid strategy folder path with indicators.pine file."

---

## Interactive Strategy Criteria Prompting

**If spec.md is NOT present**, prompt the user for these three key pieces of information:

### Prompt 1: Positioning Criteria (Entry Conditions)

First, show available signals from indicators.pine analysis:

```
📊 Available Signals Detected in indicators.pine:

Bullish Signals:
- bullishBreak: SuperTrend bullish crossover
- bull_condition: bullishBreak + KDE threshold passed
- direction == true: Uptrend confirmed

Bearish Signals:
- bearishBreak: SuperTrend bearish crossover
- bear_condition: bearishBreak + KDE threshold passed
- direction == false: Downtrend confirmed

Filters/Values:
- volumeProb: Relative volume percentile (0-1)
- threshold_condition: KDE threshold check
- activationThreshold: Current threshold value
- Pine_Supertrend: SuperTrend line level
```

Then ask:

```
❓ What are your POSITIONING criteria? (Entry conditions in order)

Please list the conditions that must be met to enter a trade, in priority order:

Example format:
1. bull_condition must be true (for longs) / bear_condition must be true (for shorts)
2. volumeProb must be above 0.70
3. Close must be above/below Pine_Supertrend
4. [Any additional filters]

Your positioning criteria:
```

**Wait for user response before continuing.**

---

### Prompt 2: Take Profit Logic

```
❓ How should TAKE PROFIT be calculated?

Choose one or describe your method:

A) Fixed Risk:Reward Ratio
   Example: TP = Entry + (Risk × 2.0) for 2:1 R:R

B) Fixed Points/Percentage
   Example: TP = Entry + 100 points
   Example: TP = Entry × 1.02 (2% profit)

C) Indicator-Based Level
   Example: TP = Next resistance level
   Example: TP = Opposite SuperTrend line

D) Trailing Only (no fixed TP)
   Example: Trail stop, exit only when trailing stop hits

E) Custom Formula
   Example: Describe your calculation

Your take profit method:
```

**Wait for user response before continuing.**

---

### Prompt 3: Stop Loss Logic

```
❓ How should STOP LOSS be calculated?

Choose one or describe your method:

A) Indicator-Based Level
   Example: SL = Pine_Supertrend level
   Example: SL = Recent swing low/high

B) Fixed Points/Percentage
   Example: SL = Entry - 50 points
   Example: SL = Entry × 0.98 (2% loss)

C) ATR-Based
   Example: SL = Entry - (ATR × 1.5)

D) Fixed Risk Amount
   Example: Risk 1% of account per trade

E) Custom Formula
   Example: Describe your calculation

Your stop loss method:
```

**Wait for user response before continuing.**

---

### Prompt 4: Additional Settings (Optional)

```
❓ Any additional settings? (Press Enter to skip)

Optional settings you can specify:
- Position size (leave blank for default 100% of equity)
- Trailing stop logic (describe if needed)
- Break-even logic (describe if needed)  
- Time/session filter (specify times if needed)
- Maximum daily trades (specify number if needed)
- Any other constraints or rules

Your additional settings (or press Enter to skip):
```

**IMPORTANT:** Only implement what the user specifies here. If they press Enter or say "none", don't add any additional features.

**After collecting all responses, show summary:**

```
📋 Strategy Configuration Summary

**Entry Criteria (Positioning):**
1. [User's criterion 1]
2. [User's criterion 2]
3. [User's criterion 3]

**Take Profit:**
[User's TP method]

**Stop Loss:**
[User's SL method]

**Additional Settings:**
[User's settings or "None"]

Is this correct? (y/n/edit)
```

If user confirms, proceed to generation. If "edit", allow them to modify any section.

---

## Generation Process

### Step 1: Read and Analyze Inputs

#### A. Parse indicators.pine

Extract the following:

**1. Indicator Metadata**
- Script name and version
- Overlay setting (true/false)
- Any imported libraries

**2. Input Parameters**
```pinescript
// Identify all input.* declarations:
input.int(), input.float(), input.bool(), input.string(), input.color()
// Note: name, default value, group, tooltip
```

**3. Calculated Values**
- Core indicator calculations (SuperTrend, MA, RSI, etc.)
- Derived values and conditions
- Arrays, variables that track state

**4. Signals and Conditions**
- Alert conditions (`alertcondition()`)
- Boolean flags (bullishBreak, bearishBreak, etc.)
- Crossovers, crossunders
- Threshold breaches

**5. Visualizations**
- `plot()` calls
- `plotshape()` for signals
- `line.new()`, `box.new()` for zones
- Color schemes and styles

#### B. Get Strategy Rules

**Source 1: spec.md (if present)**

If spec.md exists, extract:

**1. Strategy Overview**
- Strategy name and version
- Brief description
- Target market/timeframe

**2. Entry Rules**
- Long entry conditions (list all criteria)
- Short entry conditions (list all criteria)
- Entry confirmation requirements
- Entry timing/triggers

**3. Exit Rules**
- Stop loss calculation method
- Take profit calculation method
- Trailing stop logic (if any)
- Break-even logic (if any)
- Time-based exits (if any)

**4. Position Sizing**
- Default position size (% of equity)
- Risk per trade
- Position scaling rules
- Maximum positions

**5. Filters**
- Time/session filters
- Volatility filters
- Trend filters
- Volume filters

**6. Risk Management**
- Max daily loss
- Max consecutive losses
- Risk:reward ratios
- Any other constraints

---

**Source 2: Interactive Prompts (if spec.md not present)**

Use the responses collected from the interactive prompting section:

**1. Entry Rules**
- Parse user's positioning criteria list
- Identify which indicator signals to use
- Identify any additional filters
- Separate long vs short entry logic

**2. Take Profit Logic**
- Parse user's TP method
- Identify if it's fixed, indicator-based, or dynamic
- Extract specific values (R:R ratio, percentage, formula)

**3. Stop Loss Logic**
- Parse user's SL method
- Identify if it's fixed, indicator-based, or ATR-based
- Extract specific values (points, percentage, formula, indicator level)

**4. Additional Settings**
- Extract position size if specified
- Note trailing stop preference
- Note break-even preference
- Note any filters or constraints

---

### Step 2: Map Indicator Signals to Strategy Logic

Create a mapping table:

| Indicator Signal | Strategy Use | Implementation |
|-----------------|--------------|----------------|
| `bullishBreak` | Long entry trigger | `if bullishBreak and [filters]` |
| `bearishBreak` | Short entry trigger | `if bearishBreak and [filters]` |
| `volumeProb` | Entry filter | `volumeProb > threshold` |
| `Pine_Supertrend` | Stop loss level | `strategy.exit(..., stop=Pine_Supertrend)` |
| `direction` | Trend filter | `direction == true` for longs |

Document how each indicator component will be used in the strategy.

---

### Step 3: Design Strategy Architecture

#### Script Structure (in order)

```pinescript
//@version=6
strategy("Strategy Name",
    overlay=true,
    initial_capital=10000,
    default_qty_type=strategy.percent_of_equity,
    default_qty_value=100,
    commission_type=strategy.commission.percent,
    commission_value=0.1)

// ══════════════════════════════════════════════════════════════════
// IMPORTS (if needed)
// ══════════════════════════════════════════════════════════════════

// ══════════════════════════════════════════════════════════════════
// INPUTS
// ══════════════════════════════════════════════════════════════════
// Copy from indicators.pine + add strategy-specific inputs

// ══════════════════════════════════════════════════════════════════
// INDICATOR CALCULATIONS
// ══════════════════════════════════════════════════════════════════
// Copy calculation logic from indicators.pine

// ══════════════════════════════════════════════════════════════════
// STRATEGY FILTERS
// ══════════════════════════════════════════════════════════════════
// Implement filters from spec.md

// ══════════════════════════════════════════════════════════════════
// ENTRY CONDITIONS
// ══════════════════════════════════════════════════════════════════
// Map indicator signals to entry rules from spec.md

// ══════════════════════════════════════════════════════════════════
// EXIT LOGIC
// ══════════════════════════════════════════════════════════════════
// Calculate TP/SL based on spec.md

// ══════════════════════════════════════════════════════════════════
// STRATEGY EXECUTION
// ══════════════════════════════════════════════════════════════════
// strategy.entry() and strategy.exit() calls

// ══════════════════════════════════════════════════════════════════
// VISUALIZATIONS
// ══════════════════════════════════════════════════════════════════
// Copy plots from indicators.pine + add entry/exit markers
```

---

### Step 4: Generate strategy.pine

#### A. Transform Header

**FROM indicators.pine:**
```pinescript
//@version=6
indicator("Indicator Name", overlay=true)
```

**TO strategy.pine:**
```pinescript
//@version=6
strategy("Strategy Name v1.0",
    overlay=true,
    initial_capital=10000,
    default_qty_type=strategy.percent_of_equity,
    default_qty_value=100)
    
// ONLY add these if user explicitly requests:
// commission_type=strategy.commission.percent,
// commission_value=0.1,
// pyramiding=1,
// etc.
```

#### B. Preserve All Indicator Logic

**Copy these sections directly from indicators.pine:**
- All imports
- All input declarations
- All calculation logic
- All helper functions
- All visualization code

**Keep variable names and logic identical** to avoid introducing bugs.

#### C. Add Strategy-Specific Inputs (ONLY if needed)

**CRITICAL: Only add inputs that are actually used in the user's criteria.**

Based on user specifications, add ONLY what's needed:

```pinescript
// ══════════════════════════════════════════════════════════════════
// STRATEGY INPUTS (only if user specified these)
// ══════════════════════════════════════════════════════════════════

// Example: ONLY add if user said "position size" or different from 100%
// positionSize = input.float(100, "Position Size (% of Equity)", 
//     minval=1, maxval=100, step=1, 
//     group="Strategy")

// Example: ONLY add if user specified R:R ratio in their TP method
// riskRewardRatio = input.float(2.0, "Risk:Reward Ratio", 
//     minval=0.5, maxval=10, step=0.5,
//     group="Strategy")

// Example: ONLY add if user said "use trailing stop"
// useTrailingStop = input.bool(false, "Use Trailing Stop", 
//     group="Strategy")

// Example: ONLY add if user requested time filter
// useTimeFilter = input.bool(false, "Enable Time Filter", 
//     group="Filters")
```

**Rule:** If the user's criteria don't mention it, don't add it.

#### D. Implement Entry Conditions

Map indicator signals to spec.md entry rules:

```pinescript
// ══════════════════════════════════════════════════════════════════
// ENTRY CONDITIONS
// ══════════════════════════════════════════════════════════════════

// Long Entry: [describe logic from spec.md]
longEntry = false
if [indicator_signal] and [filter1] and [filter2]
    longEntry := true

// Short Entry: [describe logic from spec.md]
shortEntry = false
if [indicator_signal] and [filter1] and [filter2]
    shortEntry := true
```

#### E. Implement Exit Logic

Based on spec.md:

```pinescript
// ══════════════════════════════════════════════════════════════════
// EXIT LOGIC
// ══════════════════════════════════════════════════════════════════

// Calculate stop loss and take profit levels
var float longStopLoss = na
var float longTakeProfit = na
var float shortStopLoss = na
var float shortTakeProfit = na

if longEntry
    longStopLoss := [calculation from spec]
    longTakeProfit := [calculation from spec]

if shortEntry
    shortStopLoss := [calculation from spec]
    shortTakeProfit := [calculation from spec]
```

#### F. Execute Strategy Orders

```pinescript
// ══════════════════════════════════════════════════════════════════
// STRATEGY EXECUTION
// ══════════════════════════════════════════════════════════════════

if longEntry and barstate.isconfirmed
    strategy.entry("Long", strategy.long)
    strategy.exit("Long Exit", "Long", 
        stop=longStopLoss, 
        limit=longTakeProfit)

if shortEntry and barstate.isconfirmed
    strategy.entry("Short", strategy.short)
    strategy.exit("Short Exit", "Short", 
        stop=shortStopLoss, 
        limit=shortTakeProfit)
```

#### G. Add Entry/Exit Visualizations

```pinescript
// ══════════════════════════════════════════════════════════════════
// STRATEGY MARKERS
// ══════════════════════════════════════════════════════════════════

// Plot entry signals
plotshape(longEntry and barstate.isconfirmed, 
    "Long Entry", 
    style=shape.triangleup, 
    location=location.belowbar, 
    color=color.green, 
    size=size.small)

plotshape(shortEntry and barstate.isconfirmed, 
    "Short Entry", 
    style=shape.triangledown, 
    location=location.abovebar, 
    color=color.red, 
    size=size.small)

// Plot stop loss and take profit levels
plot(strategy.position_size > 0 ? longStopLoss : na, 
    "Long SL", 
    color=color.red, 
    style=plot.style_linebr, 
    linewidth=2)

plot(strategy.position_size > 0 ? longTakeProfit : na, 
    "Long TP", 
    color=color.green, 
    style=plot.style_linebr, 
    linewidth=2)
```

---

### Step 5: Validate Generated Strategy

Before saving, check:

- [ ] All indicator calculations are preserved exactly
- [ ] All input parameters from indicators.pine are included
- [ ] Strategy-specific inputs are added
- [ ] Entry conditions implement spec.md requirements
- [ ] Exit logic matches spec.md rules
- [ ] Position sizing is implemented
- [ ] Filters from spec.md are applied
- [ ] Visualizations show entry/exit points clearly
- [ ] Code follows PineScript v6 syntax
- [ ] All variables are properly declared
- [ ] No syntax errors

---

## Required Documentation Files

**Always consult these before writing code:**

| What You Need | File to Read |
|--------------|--------------|
| Strategy functions | `pinescriptv6/reference/functions/strategy.md` |
| Technical indicators | `pinescriptv6/reference/functions/ta.md` |
| Drawing & visuals | `pinescriptv6/reference/functions/drawing.md` |
| User inputs | `pinescriptv6/reference/functions/general.md` |
| Built-in variables | `pinescriptv6/reference/variables.md` |
| Constants | `pinescriptv6/reference/constants.md` |
| Execution model | `pinescriptv6/concepts/execution_model.md` |
| Common errors | `pinescriptv6/concepts/common_errors.md` |

---

## Output Format

### 1. Analysis Report

Before generating, show:

```markdown
## 📊 Strategy Generation Analysis

### Input Files
- **Indicators:** strategies/[name]/indicators.pine
- **Specification:** [spec.md OR Interactive Prompts]
- **Output:** strategies/[name]/strategy.pine

### Indicators Found
- SuperTrend (ATR: 10, Multiplier: 3)
- Volume KDE (Threshold: 70%)
- Trend Direction
- Relative Volume

### Signals Detected
- `bullishBreak` → Long entry trigger
- `bearishBreak` → Short entry trigger
- `volumeProb` → Entry filter
- `threshold_condition` → Confirmation filter

### Strategy Configuration
**Entry Criteria (Positioning):**
1. [Criterion 1 from spec.md OR user prompt]
2. [Criterion 2 from spec.md OR user prompt]
3. [...]

**Take Profit:**
[TP method from spec.md OR user prompt]

**Stop Loss:**
[SL method from spec.md OR user prompt]

**Position Sizing:**
[Position sizing from spec.md OR user prompt OR default]

**Additional Filters:**
[Filters from spec.md OR user prompt OR none]

### Implementation Plan
1. Copy all indicator logic to strategy
2. Add strategy inputs (position size, R:R, filters)
3. Map detected signals to entry criteria
4. Implement TP/SL based on specified methods
5. Add any filters or constraints
6. Add entry/exit visualizations
```

### 2. Confirmation Prompt

```
📋 Ready to generate strategy with:
- [N] indicator inputs preserved
- [N] new strategy inputs added
- [N] entry conditions implemented
- [N] exit conditions implemented

Proceed with generation? (y/n)
```

### 3. Success Message

```
✅ Strategy generated successfully!

Created: strategies/[name]/strategy.pine

📝 Next Steps:
1. Copy the strategy code to TradingView
2. Test on your chart
3. Review the Strategy Tester results
4. Adjust inputs as needed

💡 The strategy preserves all indicator logic and adds:
- Position sizing controls
- Risk:reward management
- Entry/exit execution
- Stop loss and take profit levels
```

---

## Common Strategy Patterns

### Pattern 1: Signal + Filter Entry

```pinescript
// Entry when indicator triggers AND filters pass
longEntry = indicatorSignal and filter1 and filter2 and barstate.isconfirmed
if longEntry
    strategy.entry("Long", strategy.long)
```

### Pattern 2: Dynamic Stop Loss

```pinescript
// Stop loss based on indicator level
var float stopLevel = na
if longEntry
    stopLevel := indicatorSupportLevel  // e.g., Pine_Supertrend
    strategy.exit("Long Exit", "Long", stop=stopLevel, limit=takeProfitLevel)
```

### Pattern 3: Risk:Reward Based TP

```pinescript
// Take profit calculated from stop distance
risk = close - stopLoss
takeProfit = close + (risk * riskRewardRatio)
```

### Pattern 4: Trailing Stop

```pinescript
// Trailing stop using strategy.exit()
if strategy.position_size > 0
    trailOffset = (close - strategy.position_avg_price) * trailPercent
    strategy.exit("Long Exit", "Long", 
        trail_points=trailOffset, 
        trail_offset=trailOffset)
```

### Pattern 5: Break-Even Logic

```pinescript
// Move SL to entry after reaching profit threshold
if strategy.position_size > 0
    profitPercent = (close - strategy.position_avg_price) / strategy.position_avg_price
    if profitPercent > breakEvenThreshold
        strategy.exit("Long Exit", "Long", 
            stop=strategy.position_avg_price, 
            limit=takeProfit)
```

---

## Edge Cases to Handle

### 1. indicators.pine has no clear signals

- Scan for potential signal patterns (crossovers, threshold breaches)
- If none found, ask user to specify which indicator values trigger entries
- Suggest adding alert conditions to indicators.pine first

### 2. spec.md is vague or incomplete

- Generate strategy with best-effort interpretation
- Add TODO comments for unclear sections
- Prompt user for clarification on critical missing info

### 3. Conflicting logic between indicator and spec

- **Indicator is source of truth for calculations**
- **Spec is source of truth for strategy rules**
- Note conflicts in generation report
- Ask user which should take precedence

### 4. Complex position sizing in spec

- Implement as separate function if logic is complex
- Add extensive comments explaining the calculation
- Provide example values in tooltips

### 5. Multiple entry conditions in spec

- Combine with `and` logic by default
- Add input toggle for each optional condition
- Document the logic clearly

---

## Example Usage Flow

### Scenario A: With spec.md

**User provides folder:**
```
strategies/super_trend/
```

**Command execution:**
1. ✅ Finds `indicators.pine`
2. ✅ Finds `spec.md`
3. 🔍 Analyzes indicator (extracts signals, inputs, calculations)
4. 🔍 Analyzes spec (extracts entry/exit rules, risk management)
5. 📊 Shows analysis report with implementation plan
6. ⚠️  Asks: "Proceed with generation?"
7. ✅ User confirms
8. ⚡ Generates `strategy.pine` with all logic integrated
9. ✅ Shows success message with next steps

---

### Scenario B: Without spec.md (Interactive)

**User provides folder:**
```
strategies/super_trend/
```

**Command execution:**
1. ✅ Finds `indicators.pine`
2. ❌ No spec.md found
3. 🔍 Analyzes indicator (extracts signals, inputs, calculations)
4. 📊 Shows detected signals and available conditions
5. ❓ **Prompt 1:** "What are your POSITIONING criteria?"
   - User responds: "1. bull_condition for longs, 2. volumeProb > 0.70"
6. ❓ **Prompt 2:** "How should TAKE PROFIT be calculated?"
   - User responds: "A) Fixed R:R of 2:1"
7. ❓ **Prompt 3:** "How should STOP LOSS be calculated?"
   - User responds: "A) Use Pine_Supertrend level"
8. ❓ **Prompt 4:** "Any additional settings?"
   - User responds: "Use trailing stop: yes"
9. 📋 Shows configuration summary
10. ⚠️  Asks: "Is this correct? (y/n/edit)"
11. ✅ User confirms
12. ⚡ Generates `strategy.pine` with specified logic
13. ✅ Shows success message with next steps

---

## Important Notes

### Do's
- ✅ Preserve ALL indicator logic exactly as-is
- ✅ Keep all indicator inputs and settings
- ✅ Maintain indicator visualizations
- ✅ Implement ONLY what the user specifies - nothing more
- ✅ Use `barstate.isconfirmed` for entry execution
- ✅ Add comments explaining what the code does (not why - that's the user's strategy)
- ✅ Ask for clarification if user's criteria are unclear

### Don'ts
- ❌ Don't modify indicator calculations
- ❌ Don't remove any indicator functionality
- ❌ Don't invent functions not in PineScript docs
- ❌ Don't use deprecated PineScript syntax
- ❌ Don't execute entries on unconfirmed bars (without explicit user request)
- ❌ **Don't add ANY logic, filters, or risk management not explicitly requested**
- ❌ **Don't add "smart" features or safety nets on your own**
- ❌ **Don't add inputs for features the user didn't ask for**
- ❌ **Don't enhance or improve the user's criteria - implement them exactly**
- ❌ **Don't add buffers, offsets, or adjustments to levels unless specified**

---

## Coding Standards

### 1. Variable Naming
```pinescript
// Good
longEntryCondition = bullishBreak and volumeFilter
stopLossLevel = Pine_Supertrend

// Bad
lec = bb and vf
sl = st
```

### 2. Comments
```pinescript
// Good - explains WHY
// Wait for volume confirmation above 70th percentile to filter false breakouts
if volumeProb > 0.70 and bullishBreak

// Bad - explains WHAT (already obvious)
// Check if volume probability is greater than 0.70
```

### 3. Input Organization
```pinescript
// Group related inputs
positionSize = input.float(100, "Position Size", group="Position Sizing")
riskPercent = input.float(1, "Risk Per Trade %", group="Position Sizing")

useTimeFilter = input.bool(false, "Enable Time Filter", group="Filters")
tradingSession = input.session("0930-1600", "Session", group="Filters")
```

### 4. Strategy Execution
```pinescript
// Always check barstate.isconfirmed before entries
if longEntry and barstate.isconfirmed
    strategy.entry("Long", strategy.long)

// Set exits immediately after entries
if longEntry
    strategy.exit("Long Exit", "Long", 
        stop=stopLoss, 
        limit=takeProfit)
```

---

## Validation Checklist

Before saving strategy.pine:

- [ ] Consulted required PineScript documentation
- [ ] All indicator logic preserved from indicators.pine (unchanged)
- [ ] All inputs from indicators.pine included (unchanged)
- [ ] **NO additional logic or features added beyond user specifications**
- [ ] **NO filters added that user didn't request**
- [ ] **NO risk management added that user didn't specify**
- [ ] Entry conditions implement EXACTLY what user specified (nothing more)
- [ ] Exit logic implements EXACTLY what user specified (nothing more)
- [ ] Position sizing implemented as specified (or default 100% if not specified)
- [ ] Strategy inputs ONLY added if needed for user's criteria
- [ ] Visualizations show entry/exit markers (if appropriate)
- [ ] Stop loss and take profit levels plotted (if specified by user)
- [ ] Code follows PineScript v6 syntax
- [ ] No syntax errors
- [ ] All variables properly declared with types
- [ ] Uses `barstate.isconfirmed` for entries (unless user said otherwise)
- [ ] Comments explain what code does, not strategy reasoning
- [ ] **Verified no "smart" enhancements or assumptions were made**

---

## Post-Generation Recommendations

After generating strategy.pine, suggest to user:

1. **Test on Historical Data**
   - Copy to TradingView
   - Run Strategy Tester
   - Check win rate, profit factor, drawdown
   - Verify the strategy behaves as you intended

2. **Validate Implementation**
   - Review generated code to ensure it matches your specifications
   - Check that entry conditions are correct
   - Verify TP/SL calculations match your criteria
   - Manually review a few trades to confirm they match your intent

3. **Iterate on Your Strategy**
   - If results aren't as expected, modify YOUR criteria (not the code)
   - Run the command again with updated specifications
   - Test different positioning criteria
   - Adjust your TP/SL methods

4. **Optimize Your Parameters**
   - Adjust indicator settings (from indicators.pine)
   - Tune your R:R ratio if using one
   - Test different positioning criteria
   - Modify your filters if needed

**Note:** The generated strategy implements exactly what you specified. If you want to improve it, update your specifications and re-run the command.
