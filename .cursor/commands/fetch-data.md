# Fetch Data

Fetch OHLCV and trade data for NY trading session, then **analyze price action to identify optimal trades**.

**Includes previous day's data** for Volume Profile context (POC, VAH, VAL levels).

**Generates `scenarios.md`** with:
- Session summary (open/high/low/close/range)
- Optimal single trade (maximum profit with one trade)
- Optimal two trades (maximum combined profit)
- Scenario breakdown with entry/exit points for training

---

## NY Trading Hours

**NY Stock Market Hours:** 9:30 AM - 4:00 PM Eastern Time

| Timezone | Open | Close |
|----------|------|-------|
| New York (ET) | 09:30 | 16:00 |
| UTC | 14:30 | 21:00 |
| Israel (Asia/Jerusalem) | 16:30 | 23:00 |

---

## Step 1: Gather Input

**Ask the user for the details:**

> **Let's fetch trading data for a session.**
>
> Please provide:
> 1. **Date:** (format: DD-MM-YYYY, e.g., 21-01-2026)
> 2. **Coin:** (e.g., BTC, ETH)

**Wait for the user's response.**

**Parse and confirm the input:**

Calculate the previous day's date for VP context.

> **Confirm details:**
>
> | Field | Value |
> |-------|-------|
> | Trading Date | [DATE] |
> | Previous Day (VP context) | [PREV_DATE] |
> | Coin | [COIN] |
> | Session | NY Trading Hours (16:30-23:00 Israel / 09:30-16:00 NY) |
>
> **Folder name:** `[COIN]_[YYYYMMDD]`
> **Location:** `data/historical/[FOLDER_NAME]/`

Use AskQuestion to confirm before proceeding.

---

## Step 2: Create Data Folder

Create the data folder with the naming convention:

```
[COIN]_[YYYYMMDD]
```

Example: `BTC_20260121`

```bash
mkdir -p "data/historical/[FOLDER_NAME]"
```

---

## Step 3: Fetch OHLCV Data (Trading Day)

Convert to UTC for the fetch command:
- Start: 14:30 UTC on [DATE]
- End: 21:00 UTC on [DATE]

```bash
./get-data-set-from --start [DD-MM-YYYY]:14-30 --end [DD-MM-YYYY]:21-00 -o "data/historical/[FOLDER_NAME]"
```

Report the result:
> **OHLCV data (trading day) fetched:** `[FILENAME]`

If the command fails, report the error and stop.

---

## Step 4: Fetch OHLCV Data (Previous Day for VP)

Fetch the previous day's OHLCV data for Volume Profile context:
- Start: 14:30 UTC on [PREV_DATE]
- End: 21:00 UTC on [PREV_DATE]

```bash
./get-data-set-from --start [PREV_DD-MM-YYYY]:14-30 --end [PREV_DD-MM-YYYY]:21-00 -o "data/historical/[FOLDER_NAME]"
```

Rename the file to indicate it's the previous day:
```bash
mv "data/historical/[FOLDER_NAME]/[PREV_OHLCV_FILE]" "data/historical/[FOLDER_NAME]/prev_day_[PREV_OHLCV_FILE]"
```

Report the result:
> **OHLCV data (previous day) fetched:** `prev_day_[FILENAME]`

If the command fails, warn but continue (previous day data is optional but recommended).

---

## Step 5: Fetch Trade Data (Trading Day)

Trade data is fetched by date:

```bash
./get-trades-from fetch --start [DD-MM-YYYY] --coin [COIN] -o "data/historical/[FOLDER_NAME]"
```

Report the result:
> **Trade data (trading day) fetched:** `[FILENAME]`

If the command fails, report the error but continue (trade data is optional for basic backtesting).

---

## Step 6: Fetch Trade Data (Previous Day for VP)

Fetch the previous day's trade data for Volume Profile context:

```bash
./get-trades-from fetch --start [PREV_DD-MM-YYYY] --coin [COIN] -o "data/historical/[FOLDER_NAME]"
```

Rename the file to indicate it's the previous day:
```bash
mv "data/historical/[FOLDER_NAME]/[PREV_TRADE_FILE]" "data/historical/[FOLDER_NAME]/prev_day_[PREV_TRADE_FILE]"
```

Report the result:
> **Trade data (previous day) fetched:** `prev_day_[FILENAME]`

If the command fails, warn but continue.

---

## Step 7: Analyze Session and Create Scenarios File

**Read the OHLCV CSV file** and perform hindsight optimal trade analysis.

### 7.1 Load and Parse Data

Read the trading day OHLCV file: `data/historical/[FOLDER_NAME]/[OHLCV_FILE]`

Extract from the CSV:
- All candle data (timestamp, open, high, low, close, volume)
- Session open price (first candle open)
- Session high (maximum high across all candles, with timestamp)
- Session low (minimum low across all candles, with timestamp)
- Session close (last candle close)

### 7.2 Calculate Optimal Trades

**Single Optimal Trade:**
Find the largest price swing in the session:
1. If session low occurs BEFORE session high: Optimal trade is LONG from low to high
2. If session high occurs BEFORE session low: Optimal trade is SHORT from high to low
3. Calculate profit percentage: `((exit - entry) / entry) * 100`

**Two Optimal Trades:**
Find the best combination of two non-overlapping trades:
1. Scan all significant swing points (local highs/lows with >0.2% moves)
2. Find the two best non-overlapping trades that maximize combined profit
3. Consider all combinations: LONG+LONG, SHORT+SHORT, LONG+SHORT, SHORT+LONG

### 7.3 Identify Scenario Types

For each significant price move, classify as:
- `bullish_breakout` - Price breaks above resistance with momentum (>0.3% move up)
- `bearish_breakdown` - Price breaks below support with momentum (>0.3% move down)
- `bullish_rejection` - Price tests low and reverses up sharply
- `bearish_rejection` - Price tests high and reverses down sharply
- `consolidation` - Sideways movement (<0.2% range over >30 minutes)
- `trend_continuation` - Move in same direction as previous scenario

### 7.4 Generate scenarios.md

Write the analysis to `data/historical/[FOLDER_NAME]/scenarios.md` with this structure:

```markdown
# [COIN] - [DATE] - Optimal Trade Analysis

NY Session (09:30-16:00 ET / 16:30-23:00 Israel)

## Session Summary

| Metric | Value |
|--------|-------|
| Open | $[OPEN] |
| High | $[HIGH] (at [HIGH_TIME] Israel) |
| Low | $[LOW] (at [LOW_TIME] Israel) |
| Close | $[CLOSE] |
| Range | [RANGE]% |
| Direction | [BULLISH/BEARISH/NEUTRAL] |

---

## Optimal Trades (Hindsight Analysis)

### Single Trade (Maximum Profit)

| Direction | Entry | Exit | Profit |
|-----------|-------|------|--------|
| [LONG/SHORT] | $[ENTRY] @ [TIME] | $[EXIT] @ [TIME] | **+[PROFIT]%** |

**Setup**: [Describe the price action that led to this optimal entry]

---

### Two Trades (Maximum Combined Profit)

| # | Direction | Entry | Exit | Profit |
|---|-----------|-------|------|--------|
| 1 | [LONG/SHORT] | $[ENTRY] @ [TIME] | $[EXIT] @ [TIME] | +[PROFIT]% |
| 2 | [LONG/SHORT] | $[ENTRY] @ [TIME] | $[EXIT] @ [TIME] | +[PROFIT]% |
| | | | **Total** | **+[TOTAL]%** |

---

## Session Scenarios

| # | Time (Israel) | Type | Description |
|---|---------------|------|-------------|
| 1 | [START] - [END] | [TYPE] | [DESCRIPTION] |
| 2 | [START] - [END] | [TYPE] | [DESCRIPTION] |
| ... | ... | ... | ... |

---

## Scenario Details

### Scenario 1: [TIME_RANGE] - [TYPE]

**Price Action**: [Describe what happened]

**Optimal Trade**:
- Direction: [LONG/SHORT]
- Entry: $[PRICE] @ [TIME] - [Why this is the optimal entry]
- Exit: $[PRICE] @ [TIME] - [Why this is the optimal exit]
- Profit: +[X]%

---

### Scenario 2: [TIME_RANGE] - [TYPE]

[Same structure as above]

---

## Training Data Summary

These optimal trades can be used to train the system:

| Scenario | Signal Type | Entry Trigger | Exit Trigger | Profit |
|----------|-------------|---------------|--------------|--------|
| 1 | [TYPE] | [CONDITION] | [CONDITION] | +[X]% |
| 2 | [TYPE] | [CONDITION] | [CONDITION] | +[X]% |

---

## Types Reference

- `bullish_breakout` - Strong move up through resistance
- `bearish_breakdown` - Strong move down through support
- `bullish_rejection` - Failed breakdown, reversal up
- `bearish_rejection` - Failed breakout, reversal down
- `consolidation` - Sideways, no clear direction
- `trend_continuation` - Continuation of previous move
```

**Important**: Fill in ALL values from the actual data. Do not leave placeholders.

---

## Step 8: Report Summary

> **Data Folder Created and Analyzed**
>
> | Item | Value |
> |------|-------|
> | Folder | `data/historical/[COIN]_[YYYYMMDD]/` |
> | Trading Date | [DATE] |
> | Previous Day | [PREV_DATE] |
> | Session | NY Trading Hours (09:30-16:00 ET) |
>
> **Trading Day Files:**
> | File | Status |
> |------|--------|
> | OHLCV | `[OHLCV_FILENAME]` |
> | Trades | `[TRADE_FILENAME]` (or "Not fetched") |
>
> **Previous Day Files (VP Context):**
> | File | Status |
> |------|--------|
> | OHLCV | `prev_day_[OHLCV_FILENAME]` |
> | Trades | `prev_day_[TRADE_FILENAME]` (or "Not fetched") |
>
> **Scenario Analysis:**
> | Metric | Value |
> |--------|-------|
> | Session Range | [RANGE]% |
> | Optimal Single Trade | [DIRECTION] +[PROFIT]% |
> | Optimal Two Trades | +[TOTAL_PROFIT]% combined |
> | Scenarios Identified | [COUNT] |
>
> **Files in folder:**
> ```
> data/historical/[COIN]_[YYYYMMDD]/
> ├── [OHLCV_FILE]              # Trading day
> ├── [TRADE_FILE]              # Trading day
> ├── prev_day_[OHLCV_FILE]     # Previous day (VP context)
> ├── prev_day_[TRADE_FILE]     # Previous day (VP context)
> └── scenarios.md              # Optimal trade analysis (generated)
> ```
>
> **Next steps:**
> 1. Review `scenarios.md` for optimal entry/exit points
> 2. Use the training data to configure signal detection
> 3. Run backtest: `python run_backtest.py --data "data/historical/[COIN]_[YYYYMMDD]/*.csv" --vp`

---

## Error Handling

**If OHLCV fetch fails:**
> **Error:** Failed to fetch OHLCV data.
> [Error message]
>
> Please check:
> - Is the date format correct? (DD-MM-YYYY)
> - Is the date in the past?
> - Is the data source accessible?

**If trade fetch fails:**
> **Warning:** Failed to fetch trade data. Continuing without Volume Profile data.
> [Error message]
>
> You can still run backtests with OHLCV data only (no Volume Profile).

**If previous day fetch fails:**
> **Warning:** Failed to fetch previous day data. Continuing without VP context.
> [Error message]
>
> You can still run backtests but won't have previous day's VP levels for reference.

**If folder already exists:**
> **Warning:** Folder `[FOLDER_NAME]` already exists.

Ask user whether to overwrite, rename, or cancel.
