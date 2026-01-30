# Historical

Historical data fetching, parsing, and storage for backtesting.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Package exports |
| `cli.py` | CLI for fetching historical candle data |
| `fetcher.py` | Data fetcher from exchange APIs |
| `fill_parser.py` | Parse fill/trade data from exchange exports |
| `models.py` | Data models for historical data |
| `s3_fetcher.py` | Fetch data from S3 storage |
| `trade_storage.py` | Load/save trade data in Parquet format |
| `trades_cli.py` | CLI for managing trade data files |

## Commands

```bash
# Fetch historical data (convenience script)
./get-data-set-from                                    # Last 1 hour of BTC
./get-data-set-from --start 12-01-2026:10-15 --end 12-01-2026:11-15
./get-data-set-from --symbol ETHUSDT                   # Different symbol
./get-data-set-from --interval 5                       # 5-minute candles

# Direct Python usage
python -m bot.historical.cli --start 12-01-2026:10-15 --end 12-01-2026:11-15

# Manage trade data (Parquet files)
python -m bot.historical.trades_cli --help
```

## Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--start` | `-s` | 1 hour ago | Start time `dd-mm-yyyy:hh-mm` |
| `--end` | `-e` | now | End time `dd-mm-yyyy:hh-mm` |
| `--symbol` | `-S` | `BTCUSDT` | Trading pair |
| `--interval` | `-i` | `1` | Candle interval (1, 5, 15, 60, 240, D) |
| `--category` | `-c` | `linear` | Market type (linear, spot, inverse) |
| `--output` | `-o` | `data/historical/` | Output directory |

## Output Format

Data is saved as CSV to `data/historical/`:

```csv
timestamp,open,high,low,close,volume,turnover
2026-01-12T10:15:00,95000.5,95050.0,94980.0,95020.0,1.523,144640.46
```
