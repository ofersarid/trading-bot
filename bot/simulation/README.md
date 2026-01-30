# Simulation

Paper trading simulator and state management.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Package exports |
| `paper_trader.py` | PaperTrader - simulates trading with fake money |
| `models.py` | Position, Trade, Side, FeeStructure, SimulatorState |
| `historical_source.py` | HistoricalDataSource - streams candles from CSV |
| `state_manager.py` | SessionStateManager - persists session state to disk |
| `opportunity_seeker.py` | Scans for trading opportunities |
| `run_simulator.py` | Standalone simulator runner |

## Commands

Standalone simulator (without full dashboard UI):

```bash
# Live mode - connects to Hyperliquid WebSocket
python bot/simulation/run_simulator.py --balance 10000 --coins BTC ETH SOL

# Historical replay mode
python bot/simulation/run_simulator.py --historical data/historical/BTCUSD_1m_....csv

# Slower playback for visualization
python bot/simulation/run_simulator.py --historical data/historical/BTCUSD_1m_....csv --speed 0.1

# Quiet mode (just final results)
python bot/simulation/run_simulator.py --historical data/historical/BTCUSD_1m_....csv --quiet
```

## Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--balance` | `-b` | 10000 | Starting balance in USD |
| `--coins` | `-c` | BTC ETH SOL | Coins to watch (live mode only) |
| `--size` | `-s` | 0.1 | Position size as fraction of balance |
| `--historical` | `-H` | - | CSV file for historical replay |
| `--speed` | - | 0 | Delay between candles in seconds |
| `--quiet` | `-q` | - | Suppress trade-by-trade output |

## Python API

```python
from bot.simulation.paper_trader import PaperTrader
from bot.simulation.models import HYPERLIQUID_FEES

trader = PaperTrader(starting_balance=10000, fees=HYPERLIQUID_FEES)

# Open positions
trader.open_long("BTC", size=0.1, price=95000)
trader.open_short("ETH", size=1.0, price=3200)

# Close positions
trader.close_position("BTC", price=96000)

# Get state
state = trader.get_state({"BTC": 95500, "ETH": 3150})
print(f"Equity: ${state.equity:,.2f}")
```

## Session Persistence

Sessions are saved to `data/sessions/<name>/state.json` and can be resumed:

```bash
./dev.sh my_session --resume
```
