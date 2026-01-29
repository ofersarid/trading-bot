# Backtest Lab

Interactive lab for running backtests, comparing signal vs AI performance, and making data-driven improvements to the trading system.

**IMPORTANT:** Use the `AskQuestion` tool for all user input prompts to trigger the interactive Ask panel.

---

## Pre-Lab Context (Read First)

Before starting the lab, read these source-of-truth files to understand the current system:

1. **`docs/trading-flow.md`** - Trading system architecture, data flow, file locations
2. **`bot/strategies/README.md`** - Available strategies, their weights, and configurations

These files are the canonical source. Do NOT rely on hardcoded information in this command file.

---

## Architecture Overview

**Action:** Read `docs/trading-flow.md` to understand the current trading system architecture.

This file is the source of truth for:
- **Step 1:** Signal detection - which detectors exist, their files
- **Step 2:** Weighted scoring calculation formula
- **Step 3:** Direction decision logic (threshold check)
- **Step 4:** TP/SL calculation method and file locations
- **Step 5:** Position sizing (AI determines 0.5x-2.0x multiplier)
- **Step 6:** Output format (TradePlan model)

## Testing Modes

All modes use the same weighted scoring (Steps 1-4). The only difference is Step 5 (position sizing).

| Mode | Command | Position Sizing |
|------|---------|-----------------|
| **AI Position Sizing** | `--ai` | AI decides 0.5x-2.0x based on setup quality |
| **AI + Goals** | `--ai --goal 50000 --goal-days 30` | AI sizes based on goal progress |
| **AI Portfolio** | `--ai --portfolio --goal 50000 --goal-days 30` | AI allocates across ALL markets |

## AI Roles Explained

### Position Sizing Strategist (Single Asset)
```
Input:  "BTC LONG signal, score 0.85, you're 15% behind goal with 20 days left"
Output: "POSITION_MULTIPLIER: 1.5x - Behind schedule, strong setup, increase risk"
```
- Direction (LONG/SHORT) is ALREADY DECIDED by weighted scoring
- AI only decides HOW MUCH to risk, not WHETHER to trade
- Uses NEW information: account goals, progress, time pressure

### Portfolio Allocator (Multi-Asset)
```
Input:  [BTC LONG 0.85, ETH LONG 0.72, SOL SHORT 0.68] + portfolio state
Output: "BTC: 40%, ETH: 0% (correlated), SOL: 25%, CASH: 35%"
```
- Sees ALL opportunities at once
- Considers correlation (BTC and ETH move together)
- Can skip opportunities, keep cash reserve
- Manages overall portfolio exposure

## When to Use Each Mode

| Situation | Recommended Mode |
|-----------|------------------|
| Single asset, basic test | AI Position Sizing |
| Single asset with goals | AI + Goals |
| Multiple correlated assets | AI Portfolio |
| Behind on aggressive goal | AI Portfolio (concentrates capital) |

---

## Step 1: Select Historical Data File

List available data files from scenario folders and ask the user to select one.

**Action:** Run this command to find available data files:

```bash
find data/historical -name "*.csv" -type f
```

**Then use the AskQuestion tool to present options:**

Use `AskQuestion` with:
- title: "Backtest Lab - Select Data File"
- question id: "data_file"
- prompt: "Select a historical data file to analyze:"
- options: One option per CSV file found, with id as the relative path and label showing "scenario/filename"

**Wait for user response. Store the selected file path.**

---

## Step 2: Select Strategies to Test

**Action:** Read `bot/strategies/README.md` to get the current "Available Strategies" table.

**Then use the AskQuestion tool with multi-select enabled:**

Use `AskQuestion` with:
- title: "Backtest Lab - Select Strategies"
- question id: "strategies"
- prompt: "Select strategy(s) to test with AI mode:"
- allow_multiple: true
- options: **Build dynamically from the README "Available Strategies" table**
  - One option per strategy found in the table
  - id: the strategy file name without `.py` (e.g., "momentum_based")
  - label: "[Strategy Name] - [Description from table]"
  - Add a final option: id: "all", label: "ALL - Run all strategies for comparison"

**Wait for user response. Build list of strategies to test.**
- If user selects "all", use all strategy IDs found in the README table
- Otherwise, use the specific strategies selected

---

## Step 3: Run Backtests

**Tell the user:**

> **Running backtests...**
>
> This will run [N] AI mode backtest(s) with selected strategy(s) + decision logging.
>
> AI mode requires Ollama running. Starting tests...

**Run the following commands sequentially, capturing output:**

### 3.1 AI Mode for Each Selected Strategy (with Decision Logging)

For each strategy in the selected list, run with `--log-decisions` to enable AI analysis:

```bash
cd /Users/ofers/Documents/trading-bot && python3 run_backtest.py --data [SELECTED_FILE] --ai --log-decisions --strategy [STRATEGY_NAME] 2>&1
```

**Store results as `ai_[strategy]_results`.**

**Note:** The `--log-decisions` flag captures every AI decision for post-backtest analysis.

---

## Step 4: Build Comparison Report

**After all backtests complete, build a comparison table:**

> **Backtest Results Comparison**
>
> **Data:** [selected file]
> **Period:** [start] to [end]
> **Candles:** [count]
>
> ### Performance Comparison
>
> | Strategy | Trades | Win Rate | P&L | P&L % | Sharpe | Profit Factor |
> |----------|--------|----------|-----|-------|--------|---------------|
> | [strategy_1] | X | X% | $X | X% | X | X |
> | [strategy_2] | X | X% | $X | X% | X | X |
> | ... | ... | ... | ... | ... | ... | ... |
>
> ### Best Performing Strategy
>
> | Metric | Winner | Value |
> |--------|--------|-------|
> | Highest P&L | [strategy] | $X |
> | Best Win Rate | [strategy] | X% |
> | Best Sharpe | [strategy] | X |
>
> ### Breakout Analysis
>
> - Total breakouts: X
> - Breakouts with pre-signals: X/X (X%)
> - Breakouts with CORRECT signal: X/X (X%)
> - Correct signals avg strength: X
> - Wrong signals avg strength: X
> - **Correlation:** [positive/negative/neutral]

---

## Step 5: Analyze Signal Performance

**Based on the breakout analysis data, evaluate:**

> **Signal Performance Analysis**
>
> ### Key Metrics
> - Signal-to-breakout coverage: [X]% of breakouts had preceding signals
> - Signal accuracy: [X]% of signals predicted correct direction
> - Strength correlation: [positive/negative/neutral]
>
> ### Diagnosis
>
> **If correlation is NEGATIVE (stronger signals are wrong):**
> - Problem: Signal strength formula rewards lagging indicators
> - RSI fires strongest AFTER price has already moved
> - MACD crossovers confirm trends that are nearly exhausted
>
> **If win rate < 30%:**
> - Problem: Signals are not predictive enough
> - Too many false positives
>
> **If breakout coverage < 50%:**
> - Problem: Missing breakouts entirely
> - Indicator thresholds may be too strict
>
> ### Recommended Indicator Tweaks
>
> Based on the data, suggest specific changes:
>
> | Issue | Current Value | Suggested Change | Rationale |
> |-------|---------------|------------------|-----------|
> | [issue] | [current] | [new] | [why] |

---

## Step 5.5: AI Decision Analysis (NEW)

**Parse the AI decision analysis from the backtest output. Look for the "AI DECISION ANALYSIS" section.**

> **AI Decision Analysis**
>
> ### Confidence Calibration
>
> | Confidence Band | Trades | Actual Win Rate | Expected Win Rate | Status |
> |-----------------|--------|-----------------|-------------------|--------|
> | 8-10 (High) | X | X% | ~75% | [CALIBRATED/OVERCONFIDENT/UNDERCONFIDENT] |
> | 6-7 (Medium) | X | X% | ~55% | [CALIBRATED/OVERCONFIDENT/UNDERCONFIDENT] |
> | 4-5 (Low) | X | X% | ~45% | [CALIBRATED/OVERCONFIDENT/UNDERCONFIDENT] |
> | 1-3 (Very Low) | X | X% | ~30% | [CALIBRATED/OVERCONFIDENT/UNDERCONFIDENT] |
>
> **Diagnosis:**
> - If OVERCONFIDENT: AI thinks setups are better than they are
> - If UNDERCONFIDENT: AI is being too conservative
>
> ### Signal Pattern Analysis
>
> **Best Patterns (Trust These):**
> | Pattern | Trades | Win Rate | Recommendation |
> |---------|--------|----------|----------------|
> | MOMENTUM+VOLUME_PROFILE | X | X% | TRUST - confirm readily |
> | [pattern] | X | X% | [recommendation] |
>
> **Worst Patterns (Be Skeptical):**
> | Pattern | Trades | Win Rate | Recommendation |
> |---------|--------|----------|----------------|
> | MOMENTUM+RSI | X | X% | AVOID - add skepticism to prompt |
> | [pattern] | X | X% | [recommendation] |
>
> ### Rejection Analysis
>
> - Total Rejected Trades: X
> - Would Have Won: X (X%)
> - Would Have Lost: X (X%)
> - **Assessment:** [AI is rejecting good trades / AI rejections are correct]
>
> ### Generated Few-Shot Examples
>
> **Good Example (WON):**
> ```
> Signals: MOMENTUM LONG (0.85), VOLUME_PROFILE LONG (0.70)
> Decision: CONFIRM (confidence 8)
> Outcome: +0.45% profit
> Lesson: Aligned signals in same direction led to profit
> ```
>
> **Bad Example (LOST - Mistake to Avoid):**
> ```
> Signals: MOMENTUM LONG (0.65), RSI SHORT (0.80)
> Decision: CONFIRM (confidence 6) ← MISTAKE
> Outcome: -0.28% loss
> Lesson: Conflicting signals were a warning sign
> ```

---

## Step 6: Analyze AI Performance

**Analyze AI position sizing behavior across strategies:**

> **AI Performance Analysis**
>
> ### Strategy Comparison
>
> | Strategy | Trades | Win Rate | P&L | Sharpe | Best For |
> |----------|--------|----------|-----|--------|----------|
> | [strategy_1] | X | X% | $X | X | [assessment] |
> | [strategy_2] | X | X% | $X | X | [assessment] |
>
> ### Position Sizing Distribution
>
> | Multiplier Range | Count | Win Rate | Assessment |
> |------------------|-------|----------|------------|
> | 0.5x or less | X | X% | Conservative sizing |
> | 0.5x - 1.0x | X | X% | Moderate sizing |
> | 1.0x - 1.5x | X | X% | Aggressive sizing |
> | 1.5x or more | X | X% | Very aggressive |
>
> **Ideal distribution depends on goal progress:**
> - **Ahead of goal**: Should see more 0.5x-1.0x (protecting gains)
> - **Behind goal**: Should see more 1.0x-1.5x (catching up)
> - **On track**: Should see balanced distribution
>
> ### Goal Calibration Check
>
> | Symptom | Likely Cause | Fix |
> |---------|--------------|-----|
> | AI always outputs ~1.0x | No goal set | Add `--goal X --goal-days Y` |
> | AI over-aggressive (big losses) | Unrealistic goal | Lower goal or extend timeframe |
> | AI too conservative | Already ahead of goal | Set new, higher goal |

---

## Step 7: Generate Improvement Recommendations

**Based on strategy comparison AND AI decision analysis, identify bottlenecks:**

### The Architecture

**Reference `docs/trading-flow.md` for the complete flow diagram.**

Key insight: Steps 1-4 are IDENTICAL for all strategies. Only Step 5 (position sizing) varies based on AI's assessment of setup quality and goal progress.

### Decision Tree for Recommendations

```
STEP 1: Are the base signals profitable?
────────────────────────────────────────
IF win_rate < 40%:
    → PROBLEM: Base signals/weights are not predictive
    → FIX: Tune signal_weights and signal_threshold
    → LOCATION: See bot/strategies/README.md for weight config
    → OR: Improve indicator parameters (RSI thresholds, MACD periods)
    → LOCATION: See Step 1 files in docs/trading-flow.md

STEP 2: Is AI sizing appropriately?
───────────────────────────────────
IF AI always outputs ~1.0x:
    → QUESTION: Do you have an account goal set?
    → FIX: Add --goal 50000 --goal-days 30
    → Without a goal, AI has limited context for sizing

IF AI is over-aggressive (big losses on 1.5x+ trades):
    → CHECK: Is goal realistic? Unrealistic goals → desperate sizing
    → FIX: Lower goal or extend timeframe

IF AI is too conservative (always 0.5x-0.8x):
    → CHECK: Is goal already achieved? AI protects gains
    → FIX: Set new, higher goal to encourage larger sizing

STEP 3: Compare strategies
──────────────────────────
→ Identify which strategy performs best on this data
→ Consider: Does the data match the strategy's assumptions?
→ OPTIMIZE: Fine-tune weights for winning strategy, consider portfolio mode
```

### Understanding AI Position Sizing Issues

**Diagnosing poor AI sizing:**

| Symptom | Cause | Fix |
|---------|-------|-----|
| AI sizing up on losers | Unrealistic goal causing desperation | Lower goal or extend timeframe |
| AI sizing down on winners | Too conservative, goal already met | Set new, higher goal |
| AI always outputs 1.0x | No goal set, AI has no context | Add `--goal X --goal-days Y` |
| Erratic sizing | Prompt confusion | Check AI response logs |

**Signs AI is working well:**

| Pattern | What AI Is Doing | Next Step |
|---------|------------------|-----------|
| Higher win rate | Sizing up on quality setups | Increase goal aggressiveness |
| Lower drawdown | Sizing down on weak setups | Working as designed |
| Higher profit factor | Better risk-adjusted returns | Consider portfolio mode |

**Generate recommendations based on the analysis:**

> **Improvement Recommendations**
>
> ### Results Summary
>
> | Strategy | P&L | Win Rate | Assessment |
> |----------|-----|----------|------------|
> | [best_strategy] | $X | X% | Best overall |
> | [other_strategy] | $X | X% | [assessment] |
>
> ---
>
> ### Level 1: Fix Base Strategy (if win rate < 40%)
>
> **Before adding AI sizing, the base strategy must be profitable.**
>
> **Reference `docs/trading-flow.md` for correct file locations:**
>
> | Component | Issue | File (see trading-flow.md) | Suggested Change |
> |-----------|-------|---------------------------|------------------|
> | Signal Weights | Wrong weighting | Step 2 files | Adjust `signal_weights` dict - which signals actually predict well? |
> | Threshold | Too strict/loose | Step 3 files | Tune `signal_threshold` - lower = more trades |
> | Min Strength | Filtering good signals | Strategy files | Lower `min_signal_strength` |
> | TP/SL Levels | Stops too tight/wide | Step 4 files | Adjust level lookup or ATR multipliers |
> | Detectors | Fire too late | Step 1 files | Adjust detector thresholds/periods |
>
> **How to tune weights:**
> - Look at signal accuracy from breakout analysis
> - Signals with higher accuracy should have higher weights
> - If RSI is 60% accurate and MACD is 45%, weight RSI higher
>
> ---
>
> ### Level 2: Tune AI Position Sizing
>
> **Ensure AI has proper context for sizing decisions:**
>
> | Symptom | Likely Cause | Fix |
> |---------|--------------|-----|
> | AI always outputs ~1.0x | No goal set | Add `--goal X --goal-days Y` to command |
> | AI over-aggressive (big losses) | Unrealistic goal | Lower goal or extend timeframe |
> | AI too conservative | Already ahead of goal | Set new, higher goal |
> | AI sizing down on winners | Prompt misunderstanding | Check AI prompt (see Step 5 in trading-flow.md) |
>
> **Questions to ask:**
> 1. Did you set an account goal? Without `--goal`, AI has limited sizing context
> 2. Is the goal realistic? $1,000 → $50,000 in 7 days will cause desperate sizing
> 3. Is the goal too easy? If already achieved, AI will size down to protect gains
>
> ---
>
> ### Level 3: Fine-Tune AI Position Sizing
>
> **If AI is adding value but could be better, tune these:**
>
> #### Goal Calibration
> | Current Result | Interpretation | Adjustment |
> |----------------|----------------|------------|
> | AI always 0.5x-0.8x | Too conservative | Make goal more aggressive |
> | AI always 1.5x-2.0x | Too aggressive | Extend timeframe or lower goal |
> | AI varies well (0.5x-1.5x) | Working as designed | Keep current goal |
>
> #### When to Use Portfolio Mode
> | Situation | Use Portfolio Mode? |
> |-----------|---------------------|
> | Single asset (BTC only) | No - Position Sizing is enough |
> | Multiple uncorrelated assets | Maybe - Portfolio can optimize allocation |
> | Multiple correlated assets (BTC, ETH) | Yes - Portfolio avoids double exposure |
> | Behind on aggressive goal | Yes - Portfolio can concentrate on best opportunity |
>
> #### Portfolio Mode Specific Issues
> | Symptom | Cause | Fix |
> |---------|-------|-----|
> | Portfolio always picks one asset | Other assets have weaker signals | Tune individual signal weights |
> | Portfolio keeps 80% cash | Too conservative, signals weak | Lower signal thresholds |
> | Portfolio overallocates | Ignoring correlation | Check prompt, AI should know BTC≈ETH |
>
> ### Level 4: Consider Portfolio Mode
>
> **If Position Sizing works but you want more:**
>
> ```bash
> # Upgrade to portfolio mode
> python run_backtest.py --ai --portfolio --goal 50000 --goal-days 30 --data X.csv
> ```
>
> **Portfolio mode is better when:**
> - You trade multiple assets simultaneously
> - Assets are correlated (BTC and ETH move together)
> - You want AI to choose WHICH opportunity is best, not just size each one
> - You're behind on goal and need to concentrate capital
>
> **Portfolio mode adds value by:**
> - Avoiding double-exposure to correlated assets
> - Keeping cash reserve for better opportunities
> - Concentrating on highest-conviction plays when behind
> - Hedging with opposite positions (long BTC, short SOL)
>
> ---
>
> ### All Layers Working (both improvements positive)
>
> **Great! Focus on fine-tuning:**
>
> | Opportunity | Where (see trading-flow.md) | Expected Gain |
> |-------------|----------------------------|---------------|
> | Add pattern warnings to prompt | AI prompt files | +2-5% win rate |
> | Add few-shot examples | AI prompt files | +2-3% win rate |
> | Adjust TP/SL logic | Step 4 files | +2-5% P&L |
> | Add new signal detector | Step 1 files | +5-10% coverage |

---

## Step 7.5: Show Quick Summary

**After analysis, display a clear summary using the architecture layers:**

> ### Quick Summary
>
> ```
> ┌─────────────────────────────────────────────────────────────┐
> │  ARCHITECTURE LAYER RESULTS                                 │
> ├─────────────────────────────────────────────────────────────┤
> │                                                             │
> │  LAYER 1: SIGNALS-ONLY (raw pattern detection)              │
> │     P&L: $X,XXX | Win Rate: XX% | Trades: XX                │
> │                        │                                    │
> │                        ▼  weighted_improvement: +$XXX       │
> │                                                             │
> │  LAYER 2: AI BYPASS (weighted scoring + risk mgmt)          │
> │     P&L: $X,XXX | Win Rate: XX% | [✓/✗ vs Layer 1]         │
> │                        │                                    │
> │                        ▼  ai_improvement: +$XXX             │
> │                                                             │
> │  LAYER 3: AI POSITION SIZING (goal-aware sizing)            │
> │     P&L: $X,XXX | Win Rate: XX% | [✓/✗ vs Layer 2]         │
> │                                                             │
> ├─────────────────────────────────────────────────────────────┤
> │  AI POSITION SIZING ANALYSIS                                │
> │  Goal: $XX,XXX in XX days | Progress: XX%                   │
> │  Avg Multiplier: X.Xx | Range: X.Xx - X.Xx                  │
> ├─────────────────────────────────────────────────────────────┤
> │  FIX THIS FIRST: [LAYER 1/2/3]                              │
> │  RECOMMENDATION: [specific action]                          │
> └─────────────────────────────────────────────────────────────┘
> ```
>
> **Example outputs:**
>
> If base signals are bad (Layer 1):
> ```
> FIX THIS FIRST: LAYER 1 - SIGNALS (38% win rate)
> RECOMMENDATION: Improve detector timing before tuning weights
> LOCATION: See Step 1 files in docs/trading-flow.md
> ```
>
> If weighted strategy doesn't beat baseline (Layer 2):
> ```
> FIX THIS FIRST: LAYER 2 - WEIGHTED STRATEGY (-$50 vs baseline)
> RECOMMENDATION: Tune signal_weights (see bot/strategies/README.md for config)
> ```
>
> If AI position sizing seems off (Layer 5):
> ```
> FIX THIS FIRST: LAYER 5 - AI POSITION SIZING
> POSSIBLE CAUSES:
>   - No goal set? Add --goal 50000 --goal-days 30
>   - Goal unrealistic? AI may be over-aggressive
>   - Goal already met? AI sizes down to protect gains
> RECOMMENDATION: Tune goal settings based on position sizing distribution
> ```
>
> If AI is helping but could be better:
> ```
> FIX THIS FIRST: LAYER 3.5 - AI CALIBRATION
> AI sizing is +$XXX vs bypass, but:
>   - Avg multiplier 0.7x suggests too conservative
>   - RECOMMENDATION: Make goal more aggressive to encourage larger sizing
>   - OR: Try --portfolio mode for multi-asset allocation
> ```
>
> If all layers pass:
> ```
> FIX THIS FIRST: NONE - All layers add value!
> LAYER 1 → LAYER 2: +$XXX (weighted scoring helps)
> LAYER 2 → LAYER 3: +$XXX (AI sizing helps)
> RECOMMENDATION: Consider --portfolio mode or test on different data
> ```

---

## Step 8: Offer Next Steps

**Use the AskQuestion tool:**

Use `AskQuestion` with:
- title: "Backtest Lab - Next Steps"
- question id: "next_action"
- prompt: "Based on the analysis, what would you like to do?"
- options:
  - id: "fix_bottleneck", label: "Fix the identified bottleneck (recommended)"
  - id: "try_portfolio_mode", label: "Try Portfolio Mode (multi-asset allocation)"
  - id: "adjust_goal", label: "Adjust account goal settings"
  - id: "tune_weights", label: "Tune signal weights for the strategy"
  - id: "implement_specific", label: "Implement a specific recommendation"
  - id: "explore_code", label: "Show me the relevant code to understand the issue"
  - id: "view_sizing_log", label: "View AI position sizing decisions"
  - id: "rerun_data", label: "Re-run with different data file"
  - id: "rerun_strategies", label: "Re-run with different strategies"
  - id: "export", label: "Export full report to markdown file"
  - id: "done", label: "Done - end lab session"

**Handle the selected action:**

- **fix_bottleneck**: Based on the diagnosed layer, implement the top recommendation:
  - First read `docs/trading-flow.md` to find the correct files for the layer
  - If LAYER 1 (Signals): Adjust detector parameters (see Step 1 files)
  - If LAYER 2 (Weights): Adjust `signal_weights` (see Step 2 files + `bot/strategies/README.md`)
  - If LAYER 4 (TP/SL): Adjust level calculation (see Step 4 files)
  - If LAYER 5 (AI Sizing): Check goal settings, adjust if unrealistic
  - Then offer to re-run backtests to validate the fix

- **try_portfolio_mode**:
  1. Explain what portfolio mode does differently
  2. Re-run backtest with `--portfolio` flag added
  3. Compare results to position sizing mode
  4. Recommend which mode to use going forward

- **adjust_goal**:
  1. Show current goal settings (or note if missing)
  2. Use AskQuestion to get new goal:
     - "What's your target balance?"
     - "How many days to reach it?"
  3. Re-run backtest with new goal
  4. Compare position sizing distribution before/after

- **tune_weights**:
  1. Read `bot/strategies/README.md` to understand weight configuration
  2. Read the current strategy file (from README's file structure section)
  3. Show signal accuracy from breakout analysis
  4. Suggest new weights based on accuracy (higher accuracy → higher weight)
  5. Implement changes and offer to re-run

- **implement_specific**: Ask which recommendation (use AskQuestion), then implement it

- **explore_code**: Read `docs/trading-flow.md` first to find correct file locations, then read the relevant files for the bottleneck:
  - LAYER 1 (Signals): Files listed under "Step 1" in trading-flow.md
  - LAYER 2 (Weights): Files listed under "Step 2" in trading-flow.md
  - LAYER 3 (Direction): Files listed under "Step 3" in trading-flow.md
  - LAYER 4 (TP/SL): Files listed under "Step 4" in trading-flow.md
  - LAYER 5 (Sizing): Files listed under "Step 5" in trading-flow.md

- **view_sizing_log**:
  1. Find the latest decision log in `data/logs/`
  2. Read and summarize:
     - Position multiplier distribution (how often 0.5x, 1.0x, 1.5x, 2.0x)
     - Correlation: high multiplier → win or loss?
     - When AI sized down: were those actually bad setups?
     - When AI sized up: were those actually good setups?

- **rerun_data**: Loop back to Step 1
- **rerun_strategies**: Loop back to Step 2
- **export**: Write report to `data/reports/backtest-lab-[timestamp].md`
- **done**: End session with summary

---

## Notes

- AI mode requires Ollama running (`ollama serve`)
- AI works best with a goal set (`--goal 50000 --goal-days 30`)
- Portfolio mode adds ~100ms per decision vs single-asset Position Sizing (~50ms)
- Results are compared against the same data file for consistency
- Decision logs are saved to `data/logs/` for future analysis

### The Architecture Philosophy

**See `docs/trading-flow.md` for the complete architecture diagram.**

```
SIGNALS → WEIGHTED SCORING → DIRECTION → TP/SL → POSITION SIZE
(Layer 1)    (Layer 2)       (Layer 3)  (Layer 4)   (Layer 5)
```

| Layer | What It Does | Where to Fix (see trading-flow.md) |
|-------|--------------|-----------------------------------|
| 1 - Signals | Detect patterns | Step 1 files |
| 2 - Weighted | Combine signals | Step 2 files |
| 3 - Direction | Threshold check | Step 3 files |
| 4 - TP/SL | Structure-aware stops | Step 4 files |
| 5 - Sizing | AI or fixed 1.0x | Step 5 files |

### Improvement Priority

**Fix issues in order:**

1. **If win rate < 40%** → Fix weights/threshold or indicators first
2. **If AI sizing is flat (~1.0x)** → Set proper goals with `--goal`
3. **If AI sizing varies well** → Consider Portfolio mode or fine-tune goals

**You can't fix bad signals with good weights. You can't fix bad weights with AI sizing.**

### AI Role Summary

| Old Role (Deprecated) | New Role |
|----------------------|----------|
| "Should I take this trade?" | Direction already decided by weighted scoring |
| "What stop-loss should I use?" | Stops calculated by ATR-based risk management |
| N/A | **"How much should I risk given my goals?"** |
| N/A | **"Which of these opportunities is best?"** (Portfolio) |

### When AI Adds Value

AI position sizing adds value when:
- You have an account goal to optimize toward
- The goal creates pressure to size differently (ahead = conservative, behind = aggressive)
- Signals are already good (Layer 1 and 2 work)

AI does NOT add value when:
- No goal is set (AI defaults to ~1.0x anyway)
- Goal is trivial (already achieved, no pressure)
- Lower layers are broken (garbage in = garbage out)

### Portfolio Mode Decision Guide

| Situation | Use Position Sizing | Use Portfolio |
|-----------|--------------------:|:--------------|
| Single asset | ✓ | |
| Multiple independent assets | ✓ | Maybe |
| Correlated assets (BTC+ETH) | | ✓ |
| Behind on aggressive goal | | ✓ (concentrates capital) |
| Want simplicity | ✓ | |
| Want AI to choose between opportunities | | ✓ |
