# Fetch Data

Fetch OHLCV and trade data for NY trading session and create a data folder with a scenarios template.

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

> **Confirm details:**
>
> | Field | Value |
> |-------|-------|
> | Date | [DATE] |
> | Coin | [COIN] |
> | Session | NY Trading Hours (16:30-23:00 Israel / 09:30-16:00 NY) |
>
> **Folder name:** `[COIN]_[YYYY-MM-DD]`
> **Location:** `data/historical/[FOLDER_NAME]/`

Use AskQuestion to confirm before proceeding.

---

## Step 2: Create Data Folder

Create the data folder with the naming convention:

```
[COIN]_[YYYYMMDD]
```

Example: `BTC_2026-01-21`

```bash
mkdir -p "data/historical/[FOLDER_NAME]"
```

---

## Step 3: Fetch OHLCV Data

Convert to UTC for the fetch command:
- Start: 14:30 UTC on [DATE]
- End: 21:00 UTC on [DATE]

```bash
./get-data-set-from --start [DD-MM-YYYY]:14-30 --end [DD-MM-YYYY]:21-00 -o "data/historical/[FOLDER_NAME]"
```

Report the result:
> **OHLCV data fetched:** `[FILENAME]`

If the command fails, report the error and stop.

---

## Step 4: Fetch Trade Data

Trade data is fetched by date:

```bash
./get-trades-from fetch --start [DD-MM-YYYY] --coin [COIN] -o "data/historical/[FOLDER_NAME]"
```

Report the result:
> **Trade data fetched:** `[FILENAME]`

If the command fails, report the error but continue (trade data is optional for basic backtesting).

---

## Step 5: Create Scenarios File

Create a `scenarios.md` file in the folder to break down the session into specific scenarios:

```markdown
# [COIN] - [DATE]

NY Session (09:30-16:00 ET / 16:30-23:00 Israel)

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
```

Write this template to `data/historical/[FOLDER_NAME]/scenarios.md`

---

## Step 6: Report Summary

> **Data Folder Created Successfully**
>
> | Item | Value |
> |------|-------|
> | Folder | `data/historical/[COIN]_[YYYY-MM-DD]/` |
> | Session | NY Trading Hours (09:30-16:00 ET) |
> | OHLCV | `[OHLCV_FILENAME]` |
> | Trades | `[TRADE_FILENAME]` (or "Not fetched" if failed) |
> | Scenarios | `scenarios.md` (ready to break down) |
>
> **Files in folder:**
> ```
> data/historical/[COIN]_[YYYY-MM-DD]/
> ├── [OHLCV_FILE]
> ├── [TRADE_FILE]
> └── scenarios.md
> ```
>
> **Next steps:**
> 1. Review the session in TradingView
> 2. Edit `scenarios.md` to break down into specific scenarios
> 3. Run backtest: `python run_backtest.py --data "data/historical/[COIN]_[YYYY-MM-DD]/*.csv" --vp`

---

## Error Handling

**If OHLCV fetch fails:**
> **Error:** Failed to fetch OHLCV data.
> [Error message]
>
> Please check:
> - Is the date format correct? (YYYY-MM-DD)
> - Is the date in the past?
> - Is the data source accessible?

**If trade fetch fails:**
> **Warning:** Failed to fetch trade data. Continuing without Volume Profile data.
> [Error message]
>
> You can still run backtests with OHLCV data only (no Volume Profile).

**If folder already exists:**
> **Warning:** Folder `[FOLDER_NAME]` already exists.

Ask user whether to overwrite, rename, or cancel.
