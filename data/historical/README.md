# Historical Data - Organized by Scenario

This folder contains historical market data organized by specific trading scenarios for backtesting.

## Folder Structure

Each scenario is a self-contained folder with both OHLCV and trade data:

```
data/historical/
├── BTC_20260120_1645_to_1721_bullish_breakout/
│   ├── BTCUSD_1m_20260120_1645_to_20260120_1721.csv   # OHLCV candles
│   └── BTC_trades_20260120.parquet                     # Tick data for Volume Profile
├── BTC_20260121_0830_to_0915_bearish_rejection/
│   ├── BTCUSD_1m_...csv
│   └── BTC_trades_...parquet
├── uncategorized/              # New data lands here before classification
│   ├── BTCUSD_1m_...csv
│   └── BTC_trades_...parquet
└── README.md
```

## Folder Naming Convention

```
{COIN}_{DATE}_{START_TIME}_to_{END_TIME}_{scenario_description}
```

Examples:
- `BTC_20260120_1645_to_1721_bullish_breakout`
- `BTC_20260121_0830_to_0915_bearish_rejection`
- `ETH_20260122_1400_to_1530_choppy_consolidation`

## Scenario Descriptions

Use descriptive names that capture the market behavior:

| Pattern | Description |
|---------|-------------|
| `bullish_breakout` | Strong move up through resistance |
| `bearish_breakdown` | Strong move down through support |
| `bullish_rejection` | Failed breakdown, reversal up |
| `bearish_rejection` | Failed breakout, reversal down |
| `choppy_consolidation` | Sideways, no clear direction |
| `extreme_buying` | Overextended rally, potential reversal |
| `extreme_selling` | Panic drop, potential bounce |
| `range_bound` | Clear support/resistance, mean reversion |

## Data Types

| File Type | Format | Used For |
|-----------|--------|----------|
| `*.csv` | OHLCV | Candlestick charts, price indicators (RSI, MACD, momentum) |
| `*.parquet` | Trades | Volume Profile analysis (POC, Value Area, delta) |

## Workflow

### Step 1: Fetch OHLCV Data
```bash
./get-data-set-from --start 20-01-2026:16-45 --end 20-01-2026:17-21
# Output: data/historical/uncategorized/BTCUSD_1m_20260120_1645_to_20260120_1721.csv
```

### Step 2: Fetch Matching Trade Data
```bash
./get-trades-from fetch --start 20-01-2026 --coin BTC
# Output: data/historical/uncategorized/BTC_trades_20260120.parquet
```

### Step 3: Review and Classify
Analyze the data to identify the market scenario, then create a named folder:
```bash
mkdir -p "data/historical/BTC_20260120_1645_to_1721_bullish_breakout"
mv data/historical/uncategorized/BTCUSD_1m_20260120_1645*.csv \
   "data/historical/BTC_20260120_1645_to_1721_bullish_breakout/"
mv data/historical/uncategorized/BTC_trades_20260120.parquet \
   "data/historical/BTC_20260120_1645_to_1721_bullish_breakout/"
```

## Usage

### Run Backtest with Volume Profile
```bash
# Auto-detect matching trade data in the same folder
python run_backtest.py \
    --data "data/historical/BTC_20260120_1645_to_1721_bullish_breakout/BTCUSD_1m_*.csv" \
    --vp

# Or explicitly specify both files
python run_backtest.py \
    --data "data/historical/BTC_20260120_1645_to_1721_bullish_breakout/BTCUSD_1m_*.csv" \
    --trade-data "data/historical/BTC_20260120_1645_to_1721_bullish_breakout/BTC_trades_*.parquet"
```

### Dashboard Replay
```bash
./dev.sh --historical "data/historical/BTC_20260120_1645_to_1721_bullish_breakout/BTCUSD_1m_*.csv"
```
