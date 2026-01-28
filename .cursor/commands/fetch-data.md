# Fetch Data

Fetch OHLCV and trade data for NY trading session and create a data folder with a scenarios template.

**Includes previous day's data** for Volume Profile context (POC, VAH, VAL levels).

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

## Step 7: Create Scenarios File

Create a `scenarios.md` file in the folder to break down the session into specific scenarios:

```markdown
# [COIN] - [DATE]

NY Session (09:30-16:00 ET / 16:30-23:00 Israel)

## Previous Day VP Context

| Level | Price | Notes |
|-------|-------|-------|
| VAH | $XX,XXX | Value Area High |
| POC | $XX,XXX | Point of Control - highest volume |
| VAL | $XX,XXX | Value Area Low |

---

## Scenarios

| # | Time (Israel) | Type | Description |
|---|---------------|------|-------------|
| 1 | HH:MM - HH:MM | | |
| 2 | HH:MM - HH:MM | | |
| 3 | HH:MM - HH:MM | | |

---

## Scenario Details

### 1. [Time] - [Type]



### 2. [Time] - [Type]



### 3. [Time] - [Type]



---

## Types Reference

- `bullish_breakout` - Strong move up through resistance
- `bearish_breakdown` - Strong move down through support
- `bullish_rejection` - Failed breakdown, reversal up
- `bearish_rejection` - Failed breakout, reversal down
- `choppy` - No clear direction, sideways
- `extreme_buying` - Overextended rally
- `extreme_selling` - Panic drop

## VP Trading Rules

- **Price above VAH**: Bullish bias, look for longs on pullbacks to VAH
- **Price below VAL**: Bearish bias, look for shorts on rallies to VAL
- **Price inside VA**: Range-bound, expect mean reversion to POC
- **POC acts as magnet**: Price tends to revisit POC during the session
```

Write this template to `data/historical/[FOLDER_NAME]/scenarios.md`

---

## Step 8: Report Summary

> **Data Folder Created Successfully**
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
> **Files in folder:**
> ```
> data/historical/[COIN]_[YYYYMMDD]/
> ├── [OHLCV_FILE]              # Trading day
> ├── [TRADE_FILE]              # Trading day
> ├── prev_day_[OHLCV_FILE]     # Previous day (VP context)
> ├── prev_day_[TRADE_FILE]     # Previous day (VP context)
> └── scenarios.md
> ```
>
> **Next steps:**
> 1. Review the session in TradingView
> 2. Calculate previous day's VP levels (POC, VAH, VAL) and add to `scenarios.md`
> 3. Edit `scenarios.md` to break down into specific scenarios
> 4. Run backtest: `python run_backtest.py --data "data/historical/[COIN]_[YYYYMMDD]/*.csv" --vp`

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
