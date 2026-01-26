# Historical Data - Organized by Scenario

This folder contains historical market data organized by scenario type for backtesting and AI strategy testing.

## Folder Structure

```
data/historical/
├── bullish_momentum/     # Strong upward movement with buyer dominance
├── bearish_momentum/     # Strong downward movement with seller dominance
├── choppy_neutral/       # No clear direction, sideways action
├── extreme_buying/       # Overextended buying - potential reversal setups
├── extreme_selling/      # Panic selling - potential bounce setups
├── uncategorized/        # New data files before classification
└── README.md
```

## File Naming Convention

Files should follow this pattern:
```
{SYMBOL}_{TIMEFRAME}_{START_DATE}_{START_TIME}_to_{END_DATE}_{END_TIME}.csv
```

Example: `BTCUSD_1m_20260120_1328_to_20260120_1428.csv`

## Adding New Data

1. **Fetch data** using the CLI tool:
   ```bash
   ./get-data-set-from --start 20-01-2026:13-28 --end 20-01-2026:14-28
   ```

2. **Review the data** to identify the market condition

3. **Move to appropriate folder**:
   ```bash
   mv data/historical/uncategorized/FILE.csv data/historical/bullish_momentum/
   ```

## Scenario Guidelines

| Scenario | Characteristics |
|----------|-----------------|
| **bullish_momentum** | Price trending up, higher highs/lows, strong buy volume |
| **bearish_momentum** | Price trending down, lower highs/lows, strong sell volume |
| **choppy_neutral** | No clear trend, mixed signals, low conviction moves |
| **extreme_buying** | Extended rally, overbought RSI, potential exhaustion |
| **extreme_selling** | Panic drop, oversold RSI, potential capitulation |

## Usage

### With test_ai.py
```bash
python test_ai.py --list  # Shows available scenarios from folders
python test_ai.py -c bullish_momentum  # Test with data from that scenario
```

### With run_backtest.py
```bash
python3 run_backtest.py --data data/historical/bullish_momentum/FILE.csv
```

### With dashboard replay
```bash
./dev.sh --historical data/historical/bullish_momentum/FILE.csv
```
