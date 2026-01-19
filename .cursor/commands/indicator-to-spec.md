---
name: Indicator to Strategy Spec
description: Analyzes an indicator.pine file and generates a spec.md with positioning strategy guidelines
tags: [strategy, pinescript, specification, indicators]
---

# Indicator to Strategy Spec Command

## Purpose

This command analyzes a Pine Script indicator file and generates a **comprehensive, standalone `spec.md`** document that defines a complete positioning strategy.

### Comprehensive = Everything Needed to Trade

The spec.md should contain **EVERYTHING** a trader needs to execute the strategy:
- ✅ Complete entry/exit rules (no ambiguity)
- ✅ Full risk management system
- ✅ Position sizing logic with examples
- ✅ Quality grading criteria (objective)
- ✅ Market context requirements
- ✅ Visual confirmation checklist
- ✅ Common mistakes and how to avoid them
- ✅ Limitations and when strategy fails
- ✅ Example trades with calculations
- ✅ Implementation guide for coding

**The reader should be able to trade this strategy OR implement it in code with ONLY the spec.md file.**

---

## Prerequisites

Before running, verify the indicator file exists:

1. **Pine Script Indicator File** (`.pine` extension)
   - Should contain an `indicator()` declaration
   - Should have clear signals, zones, or conditions
   - Can be custom or from a library

**If the file is missing, STOP and prompt:**
> "⚠️ Please provide the path to an `indicator.pine` file to analyze.
>
> Example: `strategies/super_trend/indicators.pine`"

---

## Input Parameters

### Required Input
- **Indicator File Path**: Path to the `.pine` indicator file

### Optional Guidelines
User may provide additional preferences:
- Trading style (scalping, swing, position)
- Preferred risk-reward ratio
- Position sizing approach
- Specific entry/exit preferences
- Timeframe focus

---

## Critical: Comprehensive Analysis

**The spec.md must be COMPLETE and SELF-CONTAINED**, regardless of user guidelines.

### Always Include (Even if User Doesn't Mention):

1. **ALL indicator inputs** - Document every configurable parameter
2. **ALL signals** - Every entry/exit signal the indicator generates
3. **ALL visual elements** - Plots, zones, shapes, colors and their meanings
4. **ALL calculations** - Key formulas and how they work
5. **Complete risk management** - Stop loss, take profit, position sizing logic
6. **Market context** - What market conditions favor this strategy
7. **Timeframe recommendations** - Based on indicator design (lookback periods, etc.)
8. **Limitations & warnings** - What the indicator doesn't do well
9. **Quality factors** - How to grade setup quality objectively
10. **Example scenarios** - Multiple real-world examples showing usage

### User Guidelines Are Overlays, Not Limits

- If user says "1:3 R:R" → Use 1:3 as default, but explain alternatives
- If user says "swing trading" → Focus on swing, but mention day trading adaptation
- If user is silent → Extract EVERYTHING and provide complete best-practice defaults

### Default Conservative Approach (When User Provides No Guidelines)

- **Trading Style:** Medium-term swing trading (holds 1-5 days)
- **Risk-Reward:** Minimum 1:2, recommended 1:3
- **Position Sizing:** Quality-based grading (A+/A/B/C system)
- **Risk Per Trade:** 1-2% of account based on setup grade
- **Entry Method:** Confirmation-based (wait for candle close)
- **Exit Method:** Partial profits + trailing remainder

---

## Analysis Process

### Step 1: Extract Indicator Components

Read the `.pine` file and identify:

#### **A. Indicator Metadata**
```
Look for: indicator() declaration
Extract: title, overlay setting, max_labels/boxes/lines
```

#### **B. Input Parameters**
```
Search for: input.* functions
Extract:
  - Parameter name and purpose
  - Default values
  - Groups (if any)
  - Tooltips explaining usage
```

#### **C. Key Calculations**
```
Identify:
  - Trend detection logic (moving averages, supertrend, etc.)
  - Support/Resistance levels
  - Zones (FVG, order blocks, supply/demand)
  - Momentum indicators (RSI, MACD, volume)
  - Custom formulas or algorithms
```

#### **D. Signal Generation**
```
Look for:
  - Boolean conditions (bullish/bearish signals)
  - Crossovers/crossunders
  - Zone breaks or validations
  - Alert conditions
  - Plotshape/plotarrow calls (visual signals)
```

#### **E. Visual Elements**
```
Identify:
  - Plot lines (trend, support/resistance)
  - Boxes/rectangles (zones, ranges)
  - Shapes (entry/exit markers)
  - Colors used for states
  - Labels with information
```

---

### Step 2: Determine Strategy Logic

**This is where you INFER and DESIGN, not just extract.**

Based on the indicator analysis, determine:

#### **1. Trend Identification Method**
- How does the indicator show trend direction?
- What confirms a trend change?
- Are there neutral/choppy states?
- What's the lag time? (e.g., "SuperTrend lags by ~5 bars in volatile markets")

#### **2. Entry Signal Requirements**
Map indicator signals to entry conditions:

**For Long Entries:**
- What must be true about trend?
- What signal triggers entry?
- Are there quality filters?
- What confirms the signal?
- **Infer from plotshapes** - If indicator plots triangles/arrows, that's an entry signal
- **Infer from bgcolor** - Background color changes often indicate trade zones
- **Infer from alert conditions** - Alert logic reveals entry rules

**For Short Entries:**
- Mirror logic for bearish setups
- What invalidates the signal?

**Multi-Factor Confirmation:**
- Identify ALL signals the indicator provides
- Design a grading system for setup quality
- Example: "A+ = trend + volume spike + support zone, A = trend + volume, B = trend only"

#### **3. Exit Strategy**
Based on indicator's logic:
- Stop loss placement (below/above zones, levels, etc.)
- **Calculate buffer needed** - Look at ATR usage, volatility measures
- Take profit targets (fixed R:R, indicator-based, or trailing)
- Break-even rules (if indicator shows momentum continuation)
- Trailing stop logic (if indicator is trend-following)
- **Analyze what invalidates the setup** - Often the opposite signal

#### **4. Position Sizing Approach**
Recommend one of:
- **Fixed percentage** - Simple, always same % of equity (good for beginners)
- **Quality-based grading** - Scale position by setup quality (A+/A/B/C) - **recommended default**
- **Volatility-adjusted** - Larger positions in low volatility (advanced)
- **Risk-based** - Size to fixed dollar risk amount (simple risk management)

**Choose based on indicator sophistication:**
- Simple indicator (1-2 signals) → Fixed percentage
- Multi-factor indicator (3+ conditions) → Quality-based grading
- Volatility-aware indicator → Volatility-adjusted

#### **5. Market Context Analysis**

**Infer from indicator design:**
- ATR-based? → Works in trending markets, struggles in chop
- Volume-based? → Needs liquid markets, avoid thin trading
- Mean-reversion? → Best in ranging markets
- Breakout-based? → Best in volatile, trending markets

**Document optimal conditions explicitly:**
```markdown
## Ideal Market Conditions
✅ Strong trends (ADX > 25)
✅ Normal to high volatility
✅ Liquid markets with good volume
❌ Avoid: Choppy/ranging markets
❌ Avoid: Low volume sessions
❌ Avoid: Major news events (whipsaw risk)
```

#### **6. Implicit Quality Factors**

Even if the indicator doesn't explicitly grade setups, YOU should design quality factors:

**Always Consider:**
1. **Trend strength** - Is it a new trend or exhausted?
2. **Volume confirmation** - Is volume supporting the move?
3. **Support/Resistance alignment** - Entry near key levels?
4. **Timeframe confluence** - Higher TF agrees?
5. **Signal clarity** - Clean signal or messy/conflicting?

**Create an objective grading rubric:**
```markdown
### Setup Quality Grading

**A+ Grade (5/5 factors):**
- All 5 quality factors present
- Position size: 80% of risk budget

**A Grade (4/5 factors):**
- 4 quality factors present
- Position size: 60% of risk budget

**B Grade (3/5 factors):**
- 3 quality factors present
- Position size: 40% of risk budget

**C Grade (2/5 factors):**
- Only 2 factors present
- Position size: 20% of risk budget or skip

**Skip (<2 factors):**
- Incomplete setup
- Do not trade
```

---

### Step 3: Generate spec.md Structure

Create a comprehensive strategy specification document with these sections:

---

## spec.md Template Structure

```markdown
# [Strategy Name] - Positioning Strategy Specification

Based on: [Indicator Name]
Version: 0.1
Last Updated: [Date]

---

## Overview

[2-3 sentences describing the core strategy concept]

**Strategy Type:** [Scalping / Day Trading / Swing Trading / Position]
**Timeframe:** [Recommended timeframes]
**Market:** [Crypto / Forex / Stocks / Futures]

---

## Indicator Foundation

This strategy is built on the following indicator:

**File:** `indicators.pine`
**Key Components:**
- [Component 1: e.g., SuperTrend with ATR-based bands]
- [Component 2: e.g., Relative Volume KDE analysis]
- [Component 3: e.g., Gaussian kernel smoothing]

**Primary Signals:**
- 🟢 **Bullish Signal:** [Description]
- 🔴 **Bearish Signal:** [Description]

---

## Entry Rules

### Long Entry Conditions

**Required Conditions:**
1. [Primary condition from indicator - e.g., "SuperTrend flips to green"]
2. [Confirmation - e.g., "Relative volume percentile > 70%"]
3. [Filter - e.g., "Price above key support zone"]

**Optional Quality Factors:**
- ✅ [Factor 1 - e.g., "Strong momentum on higher timeframe"]
- ✅ [Factor 2 - e.g., "Entry near support level"]
- ✅ [Factor 3 - e.g., "Volume spike confirmation"]

**Entry Timing:**
- [When exactly to enter - e.g., "On close of confirmation candle"]
- [Or alternative - e.g., "On pullback to 50% of zone"]

### Short Entry Conditions

[Mirror structure for bearish setups]

---

## Exit Rules

### Stop Loss

**Long Positions:**
- **Placement:** [e.g., "Below the SuperTrend line"]
- **Buffer:** [e.g., "Add 0.5% buffer for noise"]
- **Calculation:** `stopLoss = [formula]`

**Short Positions:**
- **Placement:** [e.g., "Above the SuperTrend line"]
- **Buffer:** [e.g., "Add 0.5% buffer for noise"]
- **Calculation:** `stopLoss = [formula]`

### Take Profit

**Target Method:** [Fixed R:R / Multiple targets / Indicator-based]

| Target | Distance | % to Close |
|--------|----------|------------|
| TP1    | [e.g., 1.5R] | [e.g., 50%] |
| TP2    | [e.g., 2.5R] | [e.g., 30%] |
| TP3    | [e.g., 3.5R] | [e.g., 20%] |

**Calculation:**
```
risk = entry - stopLoss
TP1 = entry + (risk × 1.5)
TP2 = entry + (risk × 2.5)
TP3 = entry + (risk × 3.5)
```

### Trailing Stop (Optional)

**Activation:** [e.g., "After TP1 is hit"]
**Method:** [e.g., "Trail stop to break-even, then below each new swing low"]
**Offset:** [e.g., "Trail 1R below current price"]

---

## Position Sizing

**Method:** [Chosen method from analysis]

### [If using Quality-Based Grading]

| Grade | Quality Factors | Position % | Example ($10k) |
|-------|-----------------|------------|----------------|
| A+    | 5/5 or more     | [%]        | $[amount]      |
| A     | 4/5             | [%]        | $[amount]      |
| B     | 3/5             | [%]        | $[amount]      |
| C     | 2/5             | [%]        | $[amount]      |

**Quality Factors:**
1. [Factor 1]
2. [Factor 2]
3. [Factor 3]
4. [Factor 4]
5. [Factor 5]

### [If using Fixed Percentage]

- **Default Position Size:** [%] of equity per trade
- **Max Position Size:** [%] of equity
- **Max Open Trades:** [number]

---

## Risk Management

**Per-Trade Risk:** [e.g., "Risk 1-2% of account per trade based on grade"]
**Daily Loss Limit:** [e.g., "Stop trading if down 3% in a day"]
**Weekly Loss Limit:** [e.g., "Stop trading if down 6% in a week"]

**Risk Per Grade:** [If applicable]
```
A+ setups: Risk up to 2% per trade
A  setups: Risk up to 1.5% per trade
B  setups: Risk up to 1% per trade
C  setups: Risk up to 0.5% per trade
```

---

## Trade Filters (Optional)

**Time Filters:**
- [e.g., "Only trade during main session (9:30 AM - 4:00 PM ET)"]
- [e.g., "Avoid first/last 15 minutes of session"]

**Market Condition Filters:**
- [e.g., "Only trade when ATR > minimum threshold"]
- [e.g., "Avoid ranging markets (ADX < 20)"]

**Correlation Filters:**
- [e.g., "Check higher timeframe alignment"]
- [e.g., "Avoid trading against major support/resistance"]

---

## Key Settings

Settings to use when implementing this strategy:

| Setting | Default | Purpose |
|---------|---------|---------|
| [Setting 1] | [Value] | [Description] |
| [Setting 2] | [Value] | [Description] |
| [Setting 3] | [Value] | [Description] |

*Copy these from the indicator's input parameters*

---

## Visual Setup Checklist

Before entering a trade, verify on the chart:

**Long Setup:**
- [ ] [Visual 1 - e.g., "SuperTrend line is green"]
- [ ] [Visual 2 - e.g., "KDE label shows >70%"]
- [ ] [Visual 3 - e.g., "Price bouncing from support zone"]
- [ ] [Visual 4 - e.g., "Volume spike visible"]

**Short Setup:**
- [ ] [Mirror for bearish setup]

---

## Example Trade Scenarios

### Example Long Trade

**Setup:**
[Describe market context]

**Entry:**
- Price: $[X]
- Signal: [What triggered entry]
- Quality: [Grade assigned]

**Risk Management:**
- Stop Loss: $[X] ([%] away)
- Position Size: [%] of equity
- Risk: $[X] ([%] of account)

**Targets:**
- TP1: $[X] (1.5R) ✅ Hit
- TP2: $[X] (2.5R) ✅ Hit
- TP3: $[X] (3.5R) ⏳ Running

**Outcome:** [Result and lessons]

### Example Short Trade

[Mirror structure]

---

## Limitations & Warnings

**Every strategy has weaknesses. Document them honestly.**

### When This Strategy Struggles

- **[Market Condition]** - [Why it fails] - [How to identify and avoid]
- **[Scenario]** - [What goes wrong] - [Warning signs]
- **[Edge Case]** - [Failure mode] - [Risk mitigation]

**Examples:**
- **Choppy/Ranging Markets** - SuperTrend flips frequently, causing whipsaw losses → Avoid when ADX < 20
- **Low Volume Sessions** - False signals increase → Only trade main session hours
- **News Events** - Volatility spikes invalidate ATR calculations → Stay out 30min before/after major news

### Indicator-Specific Risks

**Based on indicator design:**
- Lagging indicators → Late entries, reduced R:R
- Leading indicators → More false signals, need confirmation
- Volume-based → Doesn't work on low-volume assets
- Zone-based → Subjective interpretation risk
- Machine learning → May overfit to past data

### Known False Signal Patterns

[Analyze indicator code and describe common false signals]

Example:
```markdown
❌ **False Breakout Pattern**
What happens: SuperTrend flips, then immediately flips back
Why: Volatile candles trigger premature signal
Solution: Wait for confirmation candle or use higher timeframe filter
```

---

## Common Mistakes to Avoid

**These are TRADING mistakes, not just indicator misuse:**

1. **Overtrading weak setups** - Trading B/C grade setups too frequently → Only take A+ and A setups until profitable
2. **Ignoring market context** - Trading in unsuitable conditions → Always check if market type matches strategy
3. **Moving stops to break-even too early** - Cutting winners short → Wait for [specific condition] before moving stop
4. **Revenge trading after losses** - Increasing position size after loss → Stick to position sizing rules strictly
5. **Not using alerts** - Missing setups or monitoring too many charts → Set up alerts for entry conditions
6. **Backtesting on too short period** - Overfitting to recent market → Use minimum 6-12 months, various market conditions

---

## Additional Insights

**Go beyond the indicator - add strategic wisdom:**

### Timeframe Selection

**Based on indicator's lookback periods:**
[Calculate: if indicator uses 10-period ATR and 25-bar volume, recommend timeframes]

```markdown
**Recommended Timeframes:**
- Primary: [TF] - Main trading timeframe
- Confirmation: [Higher TF] - Check for alignment
- Precision: [Lower TF] - Fine-tune entries

**Avoid:**
- Too low timeframes → Noise overwhelms signal
- Too high timeframes → Infrequent signals, hard to manage
```

### Position Management Tactics

**Beyond basic entries/exits:**

- **Scaling in** - When and how to add to winners
- **Scaling out** - Multiple profit targets vs. all-out exit
- **Pyramid rules** - Adding to positions (if ever)
- **Correlation management** - How many correlated positions allowed

### Journaling Checklist

**What to track for each trade:**
```markdown
Pre-Trade:
- [ ] Setup grade (A+/A/B/C)
- [ ] All quality factors present? (list them)
- [ ] Market condition suitable?
- [ ] Screenshot of entry setup

Post-Trade:
- [ ] Entry price vs. planned
- [ ] Exit reason (TP/SL/manual)
- [ ] R multiple achieved
- [ ] What went right/wrong
- [ ] Screenshot of full trade
```

### Integration with Other Systems

**If trader uses other strategies:**
```markdown
**Portfolio Considerations:**
- Max % of account in trend-following strategies: [X]%
- Correlation with other strategies: [describe]
- When to reduce size: [conditions]
- When to increase size: [conditions]
```

---

## Optimization & Backtesting

**Recommended Test Period:** [e.g., "Minimum 6 months of data"]

**Key Metrics to Track:**
- Win rate
- Average R multiple
- Profit factor
- Max drawdown
- Sharpe ratio

**Parameters to Optimize:**
- [Parameter 1 and its range]
- [Parameter 2 and its range]
- [Parameter 3 and its range]

**What NOT to optimize:**
- [Things that would cause overfitting]

---

## Implementation Notes

### Converting to strategy.pine

When implementing this spec as a Pine Script strategy:

1. **Import indicator calculations** from `indicators.pine`
2. **Add strategy header** with capital, commission settings
3. **Implement entry conditions** using `strategy.entry()`
4. **Implement exit logic** using `strategy.exit()`
5. **Add position sizing logic** based on quality grading
6. **Include visual markers** for entries/exits
7. **Add alerts** for signal notifications

### Code Structure
```pinescript
//@version=6
strategy("[Strategy Name]", overlay=true)

// 1. Import or copy indicator calculations

// 2. Add position sizing logic

// 3. Detect entry signals

// 4. Execute trades
if longCondition
    strategy.entry("Long", strategy.long, qty=positionSize)
    strategy.exit("Exit Long", "Long", stop=stopLoss, limit=takeProfit)

// 5. Visualizations
```

---

## Changelog

### v0.1 - [Date]
- Initial strategy specification
- Based on [indicator name] analysis
- [Key decisions or notes]
```

---

## Generation Rules

### Comprehensive Extraction Mandate

**Extract and document EVERYTHING from the indicator**, including:

✅ **Every input parameter** - Even if it seems minor (styling, labels, etc.)
✅ **Every signal condition** - All bullish and bearish triggers
✅ **Every visualization** - What colors, shapes, lines, boxes mean
✅ **Every calculation detail** - How zones, levels, scores are computed
✅ **Every alert condition** - What triggers notifications
✅ **Implicit logic** - Infer entry/exit rules from plotshapes and bgcolors
✅ **Dependencies** - External libraries, imported functions, custom types
✅ **Edge cases** - What happens in choppy markets, gaps, low volume
✅ **Optimal conditions** - When does this indicator work best/worst

### Writing Style
- **Clear and actionable** - No ambiguity in rules
- **Specific numbers** - Provide defaults, not ranges (user can adjust later)
- **Visual language** - Describe what trader sees on chart
- **Example-driven** - Include concrete examples
- **Complete** - Assume the reader has ONLY the spec.md to work from

### Quality Standards
- Every section must be complete (no "TODO" or placeholders)
- Rules must be implementable without interpretation
- Numbers must be realistic and testable
- Avoid contradictory logic
- **Document more than asked** - User guidelines are minimums, not limits
- Include warnings about overfitting, false signals, market conditions

### Customization Based on Indicator Type

**If indicator is trend-following (SuperTrend, MA, etc.):**
- Focus on breakout/breakdown entries
- Use indicator line as dynamic stop
- Suggest trailing stops

**If indicator is mean-reversion (RSI, Bollinger, etc.):**
- Focus on overbought/oversold entries
- Use fixed targets
- Suggest quick exits

**If indicator shows zones (FVG, order blocks, etc.):**
- Focus on zone retests
- Use zone boundaries for stops
- Suggest layered entries

**If indicator uses volume:**
- Add volume confirmation to entry rules
- Use volume spikes as quality factor
- Suggest avoiding low-volume setups

---

## Output

### Save Location
Write `spec.md` to the same folder as the indicator file:
```
strategies/[strategy_name]/
  ├── indicators.pine
  └── spec.md (← generated here)
```

### Confirmation Message
```
✅ Strategy specification generated successfully!

Created: [path/to/spec.md]
Based on: [path/to/indicators.pine]

📊 Strategy Summary:
  Type: [Swing Trading / Day Trading / etc.]
  Entry Signals: [Number] conditions
  Position Sizing: [Method]
  Risk-Reward: [Ratio]

💡 Next Steps:
  1. Review the spec.md and adjust defaults if needed
  2. Use the "Skeleton to PineScript Strategy" command to implement
  3. Backtest with at least 6 months of data
  4. Paper trade before going live
```

---

## Example Execution Flow

**User provides:**
```
Indicator: strategies/super_trend/indicators.pine
Guidelines: Conservative swing trading, 1:3 R:R minimum
```

**Command execution:**

### Phase 1: Deep Analysis (Extract Everything)
1. 🔍 Reads `indicators.pine` (245 lines)
2. 📊 Identifies components:
   - SuperTrend (ATR length=10, multiplier=3)
   - Relative Volume KDE (Gaussian kernel, 25-bar lookback)
   - Opacity gradient based on volume percentile
   - Trend color visualization
   - KDE labels with percentages
3. 🎯 Extracts ALL inputs:
   - 10 input parameters across 3 groups
   - Default values, tooltips, ranges
4. 📐 Maps signal logic:
   - Primary: SuperTrend direction flip
   - Quality filter: KDE percentile threshold (70%)
   - Confirmation: Volume spike vs. 25-bar average
5. 🎨 Documents visuals:
   - Green line = bullish trend
   - Red line = bearish trend
   - Background gradient = volume strength
   - Labels = KDE percentage values

### Phase 2: Strategy Design (Infer & Create)
6. 🧠 Infers entry rules:
   - LONG: Green flip + KDE >70% + volume spike
   - SHORT: Red flip + KDE >70% + volume spike
7. 🎯 Designs quality grading:
   - A+ (5/5): Trend flip + KDE >80% + volume >150% + higher TF aligned + near support
   - A (4/5): 4 factors present
   - B (3/5): 3 factors present
   - C (2/5): Only trend + volume
8. 📏 Calculates stop loss:
   - LONG: Below SuperTrend line + (0.5% buffer for ATR noise)
   - SHORT: Above SuperTrend line + (0.5% buffer)
9. 🎯 Defines take profit:
   - User wants 1:3 minimum → Use 1.5R, 2.5R, 3.5R scaled exits
   - Alternative: Trail stop after 1.5R hit
10. ⚠️ Identifies limitations:
    - Lagging in sideways markets (SuperTrend nature)
    - False signals when ADX < 20 (choppy)
    - Volume analysis needs liquid markets

### Phase 3: Complete Documentation
11. 📝 Generates comprehensive spec.md with:
    - **Overview** - Strategy concept and type
    - **Indicator Foundation** - All components explained
    - **Entry Rules** - Long/short conditions + quality factors (5 factors defined)
    - **Exit Rules** - Stop loss formulas, TP targets, trailing logic
    - **Position Sizing** - Quality-based grading table with examples
    - **Risk Management** - Per-trade risk by grade, daily/weekly limits
    - **Trade Filters** - Session times, ADX threshold, volume minimums
    - **Key Settings** - All 10 inputs documented
    - **Visual Checklist** - What to see on chart before entry
    - **Example Trades** - 2 long, 2 short scenarios with calculations
    - **Limitations** - Choppy markets, low volume, news events
    - **Common Mistakes** - 6 mistakes with solutions
    - **Additional Insights** - Timeframe selection, journaling, integration
    - **Implementation Notes** - How to convert to strategy.pine
12. ✅ Saves to `strategies/super_trend/spec.md`

### What User Gets

A **48-section, complete specification** including everything from the indicator PLUS:
- Quality grading system (not in indicator)
- Multiple profit targets (not in indicator)
- Market condition filters (inferred from design)
- Timeframe recommendations (calculated from lookback periods)
- False signal patterns (analyzed from logic)
- Trade journaling template (strategic addition)
- Example calculations with real numbers

**Total: ~2000 words of actionable, implementation-ready documentation**

---

## Edge Cases

### 1. Complex Multi-Indicator Script
- Break down each indicator's role
- Prioritize primary entry signal
- Use secondary indicators as filters

### 2. Indicator Without Clear Signals
- Ask user for guidance on how they interpret it
- Suggest entry rules based on common patterns
- Note uncertainty in spec.md

### 3. Indicator Is Purely Visual (no calculations)
- Explain that manual interpretation is needed
- Create spec based on visual pattern rules
- Note subjective nature of entries

### 4. User Provides Conflicting Guidelines
- Point out the conflict
- Ask for clarification
- Proceed with most conservative interpretation

---

## Important Notes

### Completeness Is Non-Negotiable

- **Extract EVERYTHING** - Every input, signal, calculation, visual element
- **Infer intelligently** - If indicator has plotshapes but no alert conditions, infer entry rules from shapes
- **Design thoroughly** - Create quality grading system even if indicator doesn't have one
- **Document honestly** - Include limitations, false signals, and failure modes
- **Provide examples** - Multiple concrete scenarios with real numbers
- **Think strategically** - Go beyond mechanical extraction to strategy design

### User Guidelines Are Enhancements, Not Limits

- If user says "day trading" → Focus on day trading BUT still document swing trading adaptation
- If user says nothing → Provide complete conservative defaults for everything
- Never leave sections incomplete because user didn't mention them
- The spec must be **publication-ready and actionable**

### Quality Checklist

Before generating the spec, verify you've addressed:
- [ ] **ALL** indicator inputs documented?
- [ ] **ALL** signals explained with entry rules?
- [ ] **ALL** visual elements described?
- [ ] Position sizing system designed (with grading)?
- [ ] Stop loss placement rules clear?
- [ ] Take profit system defined?
- [ ] Quality factors objective and measurable?
- [ ] Limitations and failure modes documented?
- [ ] Multiple example trades included?
- [ ] Optimal market conditions specified?
- [ ] Common mistakes listed with solutions?
- [ ] Implementation notes for coding provided?

**If ANY of these is incomplete, the spec is not done.**

### Trading Wisdom

- **Backtest before live trading** - Minimum 6-12 months of data
- **Market conditions change** - Strategy may need adjustments over time
- **Risk management is critical** - Never risk more than you can afford to lose
- **Start small** - Paper trade first, then micro positions, then full size
- **Keep a journal** - Track every trade to identify patterns in your execution

---

## Search Patterns for Indicator Analysis

### Trend Detection
```
grep for: "trend", "direction", "bullish", "bearish", "up", "down"
look for: state variables, boolean conditions
```

### Support/Resistance
```
grep for: "support", "resistance", "level", "zone", "high", "low", "pivot"
look for: horizontal lines, zone boxes
```

### Signals
```
grep for: "signal", "alert", "entry", "exit", "buy", "sell"
look for: plotshape, plotarrow, bgcolor, alert() calls
```

### Volume Analysis
```
grep for: "volume", "vol", "relative", "spike"
look for: volume comparisons, volume arrays
```

### Momentum
```
grep for: "rsi", "macd", "momentum", "strength", "stoch"
look for: ta.rsi, ta.macd, custom momentum calcs
```
