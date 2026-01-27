# Historical Trade Data

This directory stores tick-level trade data for Volume Profile analysis.

## Data Source

Trade data is fetched from Hyperliquid's public S3 archives:
- Bucket: `s3://hl-mainnet-node-data/node_fills_by_block/`
- Format: LZ4-compressed JSON files, organized by date
- Cost: ~$0.09/GB (requester pays for data transfer)

## File Format

Trade data is stored in **Parquet format** for efficiency:
- ~10x smaller than CSV
- Fast columnar reads
- Efficient filtering by coin/time

### File Naming Convention

```
{COIN}_trades_{START_DATE}_to_{END_DATE}.parquet
{COIN}_trades_{DATE}.parquet
```

Examples:
- `BTC_trades_20260120.parquet` - Single day
- `BTC_trades_20260120_to_20260125.parquet` - Date range

### Columns

| Column | Type | Description |
|--------|------|-------------|
| timestamp | datetime | Trade execution time (microsecond precision) |
| price | float64 | Trade price |
| size | float64 | Trade size |
| side | string | Aggressor side: "B" (buy) or "A" (sell) |
| coin | string | Asset symbol (e.g., "BTC", "ETH") |

## Usage

### Fetching Trade Data

Use the `get-trades-from` CLI script:

```bash
# Fetch single day
./get-trades-from fetch --start 20-01-2026 --coin BTC

# Fetch date range
./get-trades-from fetch --start 20-01-2026 --end 25-01-2026 --coin BTC

# List available dates in S3
./get-trades-from list
```

### Loading in Python

```python
from bot.historical.trade_storage import TradeStorage

storage = TradeStorage()

# Load all trades
for trade in storage.load_trades("data/historical/trades/BTC_trades_20260120.parquet"):
    print(f"{trade.timestamp}: {trade.price} x {trade.size} ({trade.side})")

# Load with filters
from datetime import datetime
for trade in storage.load_trades(
    "data/historical/trades/BTC_trades_20260120.parquet",
    start_time=datetime(2026, 1, 20, 10, 0),
    end_time=datetime(2026, 1, 20, 11, 0),
):
    process(trade)
```

### Building Volume Profile

```python
from bot.indicators.volume_profile import VolumeProfileBuilder, get_poc, get_value_area

builder = VolumeProfileBuilder(tick_size=10.0, coin="BTC")

for trade in storage.load_trades("BTC_trades_20260120.parquet"):
    builder.add_trade(trade)

profile = builder.get_profile()
print(f"POC: ${get_poc(profile):,.2f}")
print(f"Value Area: {get_value_area(profile)}")
```

## File Info

Get information about a trade data file:

```bash
./get-trades-from info data/historical/trades/BTC_trades_20260120.parquet --sample 10
```

## Requirements

- AWS CLI (`brew install awscli`)
- LZ4 (`brew install lz4`)
- pyarrow (`pip install pyarrow`)

## Directory Structure

```
data/historical/trades/
├── README.md
├── raw/                    # Raw downloads from S3 (temporary)
│   └── 20260120/
├── BTC_trades_20260120.parquet
├── BTC_trades_20260121.parquet
└── ...
```
