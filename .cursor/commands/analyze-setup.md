---
name: Analyze Setup Execution
description: Analyzes trading setup and execution based on Pine Script logs and chart screenshots
tags: [trading, analysis, pinescript]
---

# Setup & Execution Analysis Command

## Prerequisites Check

Before starting the analysis, verify the following files are attached:

1. **Pine Script Log File** (`.csv` format)
   - Should contain timestamped logs with setup detection, BOS, CHoCH, FVG data
   - File name typically: `pine-logs-*.csv`

2. **Chart Screenshots** (`.png`, `.jpg`, or similar)
   - Should show the setup on the chart
   - Should include visible labels (CHoCH, SETUP, entry markers)
   - Multiple screenshots can show the timeline/progression

**If any required files are missing, STOP and prompt the user:**
> "⚠️ Missing required files for analysis. Please attach:
> - [ ] Pine Script log file (.csv)
> - [ ] Chart screenshot(s) showing the setup
>
> Drag and drop the files into the chat, then run this command again."

---

## Analysis Report Structure

Once all files are confirmed, generate a comprehensive report with the following sections:

### 1. **Setup Identification**
- Extract and display:
  - Exact date and time of setup detection
  - Bar number
  - Setup direction (LONG/SHORT)
  - Setup grade (A/B/C/D) and what it means for position sizing
  - Asset/symbol (if available in logs)

### 2. **Setup Formation Criteria**

#### Minimum Criteria (All Must Pass)
- **Previous Trend BOS Count:** How many BOS in the opposite direction occurred before this setup?
- **CHoCH Detected:** Was a Change of Character identified? At what price level?
- **Valid FVG:** Was a Fair Value Gap formed?
  - FVG size (percentage)
  - FVG top and bottom prices

#### Quality Factors (Grade Determinants)
Based on the screenshot's quality factors section, identify which passed/failed:
- ✓/✗ Strong Move
- ✓/✗ Failed Low (for longs) / Failed High (for shorts)
- ✓/✗ Big FVG
- ✓/✗ Recent BOS
- ✓/✗ FVG Untouched

Explain what the grade means:
- A (5/5): 100% position size
- B (3-4/5): 60-80% position size
- C (2/5): 40% position size
- D (0-1/5): Setup rejected, no trade

### 3. **Entry Strategy Analysis**

Explain why the entry is positioned where it is:
- **Entry Price:** Show the exact entry level
- **Entry Logic:** Explain why it's at the FVG midpoint (or other logic)
- **Wait for Retrace:** Explain the strategy doesn't chase breakouts
  - Time gap between setup detection and entry fill
  - Why waiting for pullback improves R:R ratio
- **Stop Loss:** Where it's placed and why (typically below FVG low for longs)

### 4. **Trade Timeline & Execution**

Create a chronological breakdown:
- **Setup Detection:** When the setup was identified and labeled as PENDING
- **Price Action:** What happened immediately after (did price rally away?)
- **Retrace & Fill:** When/if the entry was filled
  - Search logs for "RETRACE FILLED" or "ORDER PLACED"
  - Note: Some setups never fill if price doesn't return
- **Position Status:** Was the order filled or did it expire?

### 5. **Exit Analysis**

This is crucial - explain what happened to the trade:

**If trade was filled, analyze:**
- Did price move in favor initially?
- Look for exit signals in logs:
  - Stop loss hit
  - Take profit reached
  - Opposite CHoCH (counter-trend CHoCH that would close the position)
  - Opposite BOS accumulation

**Common exit scenarios:**
1. **Stop Loss:** Price moved against position and hit stop
2. **Take Profit:** Price reached target (rare in the data we saw)
3. **CHoCH Exit:** Counter-trend CHoCH invalidated the setup
4. **Strong Counter-Move:** Large FVGs or multiple BOS in opposite direction

**If trade was never filled:**
- Price never retraced to entry level
- Setup expired/invalidated

### 6. **Context & Market Structure**

Provide context from the logs:
- What was happening before the setup? (prior BOS/CHoCH sequence)
- What happened after? (continuation, reversal, consolidation?)
- Were there conflicting signals nearby?

### 7. **Key Insights & Takeaways**

Summarize:
- **Setup Quality:** Was this a high-probability setup based on the grade?
- **Execution Timing:** Did the entry fill at a good vs. bad time?
- **Outcome:** What was the result and why?
- **Lessons:** What can be learned from this specific setup?

---

## Output Format

Structure the report with:
- Clear section headers (##)
- Bullet points for easy scanning
- Code blocks for exact log entries
- Emojis for visual clarity (✓, ✗, ⚠️, 📊, 📈, 📉)
- Price levels formatted consistently

---

## Search Strategy for Logs

1. First, scan screenshots to identify approximate date/time
2. Search logs for that date range
3. Look for key patterns:
   - "SETUP DETECTED"
   - "MINIMUM CRITERIA MET"
   - "CHoCH"
   - "RETRACE FILLED"
   - "ORDER PLACED"
   - BOS events around the time
4. Extract ±20-30 lines of context around the setup
5. Follow the timeline forward to find exit/outcome

---

## Example Questions to Answer

Based on user's actual questions, address:
1. **"Can you identify this specific setup?"** - Full setup breakdown
2. **"What were the criteria for it to be created?"** - Minimum criteria + quality factors
3. **"Why was the entry set so far away?"** - Retrace strategy explanation
4. **"Why didn't we reach take profit?"** - Exit analysis with specific log evidence
5. **"What happened to this trade?"** - Complete timeline from detection to exit

---

## Important Notes

- Always reference specific line numbers or timestamps from logs
- Quote exact log entries when discussing events
- Be honest about missing data - if logs don't show the exit, say so
- Use data to support conclusions, not assumptions
- Highlight timing mismatches (e.g., entry filled during strong counter-move)
