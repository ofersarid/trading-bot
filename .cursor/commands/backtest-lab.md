# Backtest Lab

Interactive lab for running backtests, comparing signal vs AI performance, and making data-driven improvements to the trading system.

**IMPORTANT:** Use the `AskQuestion` tool for all user input prompts to trigger the interactive Ask panel.

---

## Step 1: Select Historical Data File

List available data files and ask the user to select one.

**Action:** Run this command to find available data files:

```bash
ls -la data/historical/*.csv
```

**Then use the AskQuestion tool to present options:**

Use `AskQuestion` with:
- title: "Backtest Lab - Select Data File"
- question id: "data_file"
- prompt: "Select a historical data file to analyze:"
- options: One option per CSV file found, with id as the filename and label showing "filename (size, date range)"

**Wait for user response. Store the selected file path.**

---

## Step 2: Select Personas to Test

**Use the AskQuestion tool with multi-select enabled:**

Use `AskQuestion` with:
- title: "Backtest Lab - Select Personas"
- question id: "personas"
- prompt: "Select persona(s) to test with AI mode:"
- allow_multiple: true
- options:
  - id: "scalper", label: "Scalper - Aggressive, quick trades, tight stops"
  - id: "balanced", label: "Balanced - Moderate risk, waits for consensus"
  - id: "conservative", label: "Conservative - Capital preservation, wide stops"
  - id: "all", label: "ALL - Run all three personas for comparison"

**Wait for user response. Build list of personas to test.**
- If user selects "all", use ["scalper", "balanced", "conservative"]
- Otherwise, use the specific personas selected

---

## Step 3: Run Backtests

**Tell the user:**

> **Running backtests...**
>
> This will run:
> - 1x Signals-only mode (baseline)
> - [N]x AI mode with selected persona(s)
>
> AI mode requires Ollama running. Starting tests...

**Run the following commands sequentially, capturing output:**

### 3.1 Signals-Only Baseline

```bash
cd /Users/ofers/Documents/private/trading-bot && source venv/bin/activate && python3 run_backtest.py --data [SELECTED_FILE] 2>&1
```

**Store results as `signals_only_results`.**

### 3.2 AI Mode for Each Selected Persona

For each persona in the selected list, run:

```bash
cd /Users/ofers/Documents/private/trading-bot && source venv/bin/activate && python3 run_backtest.py --data [SELECTED_FILE] --ai --persona [PERSONA_NAME] 2>&1
```

**Store results as `ai_[persona]_results`.**

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
> | AI (scalper) | X | X% | $X | X% | X | X |
> | AI (balanced) | X | X% | $X | X% | X | X |
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
> | Trades | X | X ([persona]) | X fewer/more |
> | Win Rate | X% | X% ([persona]) | +X% |
> | P&L | $X | $X ([persona]) | +$X |
> | Profit Factor | X | X ([persona]) | +X |
>
> ### AI Value Assessment
>
> **If AI P&L > Signals-Only P&L:**
> - AI is adding value by filtering bad signals
> - Best persona: [name] - [why it performed best]
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
> ### Recommended AI/Persona Tweaks
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
  - id: "rerun_personas", label: "Re-run with different personas"
  - id: "export", label: "Export full report to markdown file"
  - id: "done", label: "Done - end lab session"

**Handle the selected action:**

- **implement_quick**: Implement the quick win changes, then offer to re-run backtests
- **implement_specific**: Ask which recommendation (use AskQuestion), then implement it
- **rerun_data**: Loop back to Step 1
- **rerun_personas**: Loop back to Step 2
- **export**: Write report to `data/reports/backtest-lab-[timestamp].md`
- **done**: End session with summary

---

## Notes

- AI mode requires Ollama running (`ollama serve`)
- Each AI backtest takes ~45-60 seconds due to LLM calls
- Running all 3 personas = ~3-4 minutes total
- Results are compared against the same data file for consistency
