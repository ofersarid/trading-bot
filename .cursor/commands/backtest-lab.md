# Backtest Lab

Interactive lab for running backtests, comparing signal vs AI performance, and making data-driven improvements to the trading system.

**IMPORTANT:** Use the `AskQuestion` tool for all user input prompts to trigger the interactive Ask panel.

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

**Use the AskQuestion tool with multi-select enabled:**

Use `AskQuestion` with:
- title: "Backtest Lab - Select Strategies"
- question id: "strategies"
- prompt: "Select strategy(s) to test with AI mode:"
- allow_multiple: true
- options:
  - id: "momentum_scalper", label: "Momentum Scalper - Aggressive momentum scalping, quick entries/exits"
  - id: "trend_follower", label: "Trend Follower - Patient trend following, ride the wave"
  - id: "mean_reversion", label: "Mean Reversion - Fade overextended moves, contrarian"
  - id: "conservative", label: "Conservative - High-confidence only, preserve capital"
  - id: "all", label: "ALL - Run all four strategies for comparison"

**Wait for user response. Build list of strategies to test.**
- If user selects "all", use ["momentum_scalper", "trend_follower", "mean_reversion", "conservative"]
- Otherwise, use the specific strategies selected

---

## Step 3: Run Backtests

**Tell the user:**

> **Running backtests...**
>
> This will run:
> - 1x Signals-only mode (baseline)
> - [N]x AI mode with selected strategy(s)
>
> AI mode requires Ollama running. Starting tests...

**Run the following commands sequentially, capturing output:**

### 3.1 Signals-Only Baseline

```bash
cd /Users/ofers/Documents/private/trading-bot && source venv/bin/activate && python3 run_backtest.py --data [SELECTED_FILE] 2>&1
```

**Store results as `signals_only_results`.**

### 3.2 AI Mode for Each Selected Strategy

For each strategy in the selected list, run:

```bash
cd /Users/ofers/Documents/private/trading-bot && source venv/bin/activate && python3 run_backtest.py --data [SELECTED_FILE] --ai --strategy [STRATEGY_NAME] 2>&1
```

**Store results as `ai_[strategy]_results`.**

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
> | Mode | Trades | Win Rate | P&L | P&L % | Sharpe | Profit Factor |
> |------|--------|----------|-----|-------|--------|---------------|
> | Signals-Only | X | X% | $X | X% | X | X |
> | AI (momentum_scalper) | X | X% | $X | X% | X | X |
> | AI (trend_follower) | X | X% | $X | X% | X | X |
> | AI (mean_reversion) | X | X% | $X | X% | X | X |
> | AI (conservative) | X | X% | $X | X% | X | X |
>
> ### Breakout Analysis (from Signals-Only run)
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

## Step 6: Analyze AI Performance

**Compare AI modes against signals-only baseline:**

> **AI Performance Analysis**
>
> ### AI vs Baseline Comparison
>
> | Metric | Signals-Only | Best AI | Improvement |
> |--------|--------------|---------|-------------|
> | Trades | X | X ([strategy]) | X fewer/more |
> | Win Rate | X% | X% ([strategy]) | +X% |
> | P&L | $X | $X ([strategy]) | +$X |
> | Profit Factor | X | X ([strategy]) | +X |
>
> ### AI Value Assessment
>
> **If AI P&L > Signals-Only P&L:**
> - AI is adding value by filtering bad signals
> - Best strategy: [name] - [why it performed best]
>
> **If AI P&L < Signals-Only P&L:**
> - AI is not adding value, may be filtering good signals
> - Check: Are min_signal_strength thresholds filtering out correct (weak) signals?
> - Check: Is prefer_consensus causing missed opportunities?
>
> **If AI trades much fewer but similar P&L:**
> - AI is more selective but not more accurate
> - May need prompt improvements to make better decisions, not just fewer
>
> ### Recommended Strategy Tweaks
>
> | Issue | Current Setting | Suggested Change | Rationale |
> |-------|-----------------|------------------|-----------|
> | [issue] | [current] | [new] | [why] |

---

## Step 7: Generate Improvement Recommendations

**Synthesize findings into actionable recommendations:**

> **Improvement Recommendations**
>
> ### Priority 1: Quick Wins (config changes only)
>
> 1. **[Recommendation]**
>    - File: `[file path]`
>    - Change: `[specific code/config change]`
>    - Expected impact: [what this should improve]
>
> ### Priority 2: Code Changes (indicator/signal logic)
>
> 1. **[Recommendation]**
>    - File: `[file path]`
>    - Change: `[description of code change]`
>    - Expected impact: [what this should improve]
>
> ### Priority 3: Structural Changes (architecture)
>
> 1. **[Recommendation]**
>    - Description: [what needs to change]
>    - Effort: [low/medium/high]
>    - Expected impact: [what this should improve]

---

## Step 8: Offer Next Steps

**Use the AskQuestion tool:**

Use `AskQuestion` with:
- title: "Backtest Lab - Next Steps"
- question id: "next_action"
- prompt: "What would you like to do next?"
- options:
  - id: "implement_quick", label: "Implement Priority 1 recommendations (quick wins)"
  - id: "implement_specific", label: "Implement a specific recommendation"
  - id: "rerun_data", label: "Re-run with different data file"
  - id: "rerun_strategies", label: "Re-run with different strategies"
  - id: "export", label: "Export full report to markdown file"
  - id: "done", label: "Done - end lab session"

**Handle the selected action:**

- **implement_quick**: Implement the quick win changes, then offer to re-run backtests
- **implement_specific**: Ask which recommendation (use AskQuestion), then implement it
- **rerun_data**: Loop back to Step 1
- **rerun_strategies**: Loop back to Step 2
- **export**: Write report to `data/reports/backtest-lab-[timestamp].md`
- **done**: End session with summary

---

## Notes

- AI mode requires Ollama running (`ollama serve`)
- Each AI backtest takes ~45-60 seconds due to LLM calls
- Running all 4 strategies = ~4-5 minutes total
- Results are compared against the same data file for consistency
