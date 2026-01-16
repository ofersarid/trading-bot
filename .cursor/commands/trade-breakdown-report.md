---
name: Trade Breakdown Report
description: Generates comprehensive breakdown of trades by quality grade, profit/loss, and weekly statistics from Pine Script logs
tags: [trading, analysis, statistics, pinescript]
---

# Trade Breakdown Report Command

## Prerequisites Check

Before generating the report, verify the following file is attached:

1. **Pine Script Log File** (`.csv` format)
   - Should contain setup detection, retrace fills, and trade execution logs
   - File name typically: `pine-logs-*.csv`

**If the log file is missing, STOP and prompt the user:**
> "⚠️ Missing Pine Script log file. Please attach:
> - [ ] Pine Script log file (.csv) containing trade execution data
>
> Drag and drop the file into the chat, then run this command again."

---

## Report Generation

Once the log file is confirmed, generate a comprehensive trade breakdown report with the following sections:

### 1. **📊 SETUPS DETECTED SUMMARY**

Extract from logs (search for "SETUP DETECTED"):
- **Total setups detected**
- **Breakdown by grade:**
  - Count and percentage for each grade (A+, A, B, C, D)
  - Position size for each grade
  - Direction split (LONG vs SHORT) per grade
- **Overall direction split** (LONG vs SHORT)

**Format as table:**
```
| Grade | Count (%) | Position Size | Longs | Shorts |
|-------|-----------|---------------|-------|--------|
| A+    | X (X%)    | 80%          | X     | X      |
| A     | X (X%)    | 70%          | X     | X      |
| B     | X (X%)    | 60%          | X     | X      |
| C     | X (X%)    | 50%          | X     | X      |
```

**Key Insight:** Explain what the grade distribution suggests about market conditions during the backtest period.

---

### 2. **📈 FILL RATE ANALYSIS**

Compare setups detected vs. trades filled (search for "RETRACE FILLED"):
- **Setups detected:** Total count
- **Trades filled:** Total count (setups that actually entered)
- **Fill rate:** Percentage of setups that filled
- **Never filled:** Count and percentage of setups that expired

**Format:**
```
| Status        | Count | Percentage |
|---------------|-------|------------|
| Filled        | XX    | XX% ✅     |
| Never Filled  | XX    | XX% ❌     |
```

**Explain why setups don't fill:**
- Price never retraced back to entry level
- Strong momentum continued without pullback

---

### 3. **💰 PERFORMANCE OVERVIEW**

Extract equity progression from logs:
- **Starting Capital:** First equity value in logs
- **Ending Equity:** Last equity value in logs
- **Net P&L:** Difference (ending - starting)
- **Return %:** Percentage return
- **Peak Equity:** Highest equity reached during period
- **Drawdown from Peak:** Percentage decline from peak to final equity
- **Time Period:** Date range from logs (first to last date)
- **Total Trades:** Count of filled trades
- **Average Trade Impact:** Average P&L per trade

**Format as clean table**

---

### 4. **📊 WEEKLY TRADING STATISTICS**

Calculate weekly averages:
- **Total weeks:** Calculate from date range in logs (days / 7)
- **Trades per week:** Total filled trades / total weeks
- **Setups per week:** Total detected setups / total weeks
- **Fill rate per week:** Average fills per week

**Display prominently:**
```
📊 Weekly Average: X.X trades/week
```

Compare to optimal trading frequency for the strategy timeframe.

---

### 5. **📉 GRADE PERFORMANCE BREAKDOWN**

For each grade (A+, A, B, C), provide:
- **Setup count**
- **Fill count** and fill rate %
- **Direction distribution**
- **Notable characteristics** (e.g., "Grade A+ setups are rare but filled 100%")

**List specific example trades** for high-quality setups (A+ and A):
- Date, direction, entry price, position size
- Whether it filled or not

---

### 6. **🔍 MONTHLY ACTIVITY BREAKDOWN**

Group trades by month and show:
- **Setups detected** per month
- **Trades filled** per month
- **Fill rate** per month
- **Equity change** per month (starting → ending equity)

**Format as table:**
```
| Month        | Setups | Filled | Fill Rate | Equity Change      |
|--------------|--------|--------|-----------|-------------------|
| Oct 2025     | XX     | XX     | XX%       | $XXX → $XXX (±X%) |
| Nov 2025     | XX     | XX     | XX%       | $XXX → $XXX (±X%) |
...
```

**Identify:**
- Best performing month
- Worst performing month
- Highest activity month

---

### 7. **📊 DIRECTIONAL BIAS ANALYSIS**

Compare long vs. short distribution:
- **Setups detected:** LONG vs SHORT counts and %
- **Trades filled:** LONG vs SHORT counts and %
- **Market bias interpretation:** What does the directional split suggest about market conditions?

**Example insights:**
- "62% SHORT setups suggests bearish market conditions during this period"
- "Higher fill rate for longs (75%) vs shorts (60%) suggests long setups had better retrace opportunities"

---

### 8. **💡 KEY FINDINGS & INSIGHTS**

Synthesize the data into actionable insights:

1. **Quality Distribution:** What does the grade distribution tell us?
   - Many Grade B setups = market conditions didn't produce optimal setups
   - Rare Grade A+ = exceptional setups are truly exceptional

2. **Fill Rate Challenge:** If <70% fill rate
   - Consider: Are entries too aggressive?
   - Or: Strong momentum markets with fewer pullbacks?

3. **Performance Analysis:**
   - Is strategy profitable?
   - Where did major gains/losses occur?
   - Consistency across months?

4. **Activity Consistency:**
   - Is weekly average sustainable?
   - Too many or too few trades for the strategy?

5. **Optimization Opportunities:**
   - What grades are most profitable?
   - Should minimum grade threshold be adjusted?
   - Are certain market conditions more favorable?

---

### 9. **🎯 TRADE OUTCOMES ESTIMATE**

Based on equity progression through the logs:
- **Peak drawdown:** Maximum decline from any equity high
- **Largest equity gain:** Biggest single-day or single-week gain
- **Largest equity drop:** Biggest single-day or single-week loss
- **Consistency:** How stable is equity growth?

**Note:** Logs may not show individual trade exits (TP/SL), so win rate may not be calculable. State this clearly if exits aren't logged.

---

### 10. **📋 SUMMARY TABLE**

Create a one-page summary:

```
═══════════════════════════════════════════════════════════
                    STRATEGY PERFORMANCE SUMMARY
═══════════════════════════════════════════════════════════

Period:                 [Start Date] → [End Date] (XX days)
Starting Capital:       $XXX.XX
Ending Equity:          $XXX.XX
Return:                 ±XX.XX%

Setups Detected:        XX total
  - Grade A+:          XX (XX%)
  - Grade A:           XX (XX%)
  - Grade B:           XX (XX%)
  - Grade C:           XX (XX%)

Trades Filled:          XX (XX% fill rate)
  - LONG:              XX (XX%)
  - SHORT:             XX (XX%)

Weekly Average:         X.X trades/week
Best Month:             [Month] (+XX%)
Worst Month:            [Month] (-XX%)

Key Insight:            [One-sentence takeaway]
═══════════════════════════════════════════════════════════
```

---

## Search Strategy for Logs

1. **Setup Detection:**
   - Search for: "SETUP DETECTED"
   - Extract: Bar number, Grade, Direction, Entry price, Stop, Position %

2. **Trade Fills:**
   - Search for: "RETRACE FILLED"
   - Extract: Date, Entry price, Position size, Equity

3. **Equity Tracking:**
   - Track equity values throughout logs
   - Note: Each log entry with "Equity: $" shows current equity

4. **Date Range:**
   - First log entry date = Start date
   - Last log entry date = End date
   - Calculate total days, divide by 7 for weeks

---

## Output Guidelines

- Use clear section headers with emojis for visual clarity
- Format numbers consistently (decimals, percentages)
- Include tables for easy comparison
- Provide both raw data AND interpretation
- Highlight key insights in bold
- Use ✅ ❌ for visual indicators
- Keep explanations concise but informative

---

## Example Key Questions to Answer

Based on user's needs, ensure the report addresses:
1. **"How many trades per week?"** → Weekly average calculation
2. **"What's the grade distribution?"** → Grade breakdown table
3. **"Which grades perform best?"** → Grade performance analysis
4. **"Is the strategy profitable?"** → Performance overview
5. **"What's the fill rate?"** → Fill rate analysis
6. **"Long or short bias?"** → Directional bias section
7. **"Monthly consistency?"** → Monthly breakdown table

---

## Notes

- If specific data is missing from logs, state it clearly
- Don't make assumptions - work only with available log data
- If logs show setup detection but not exits, note that win rate can't be calculated
- Focus on actionable insights, not just raw statistics
- Compare metrics to strategy goals (e.g., "2 trades/week is within optimal range for 15min strategy")
