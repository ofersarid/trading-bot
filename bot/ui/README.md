# UI

Textual TUI dashboard for paper trading visualization.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Package exports |
| `dashboard.py` | TradingDashboard - main Textual App |
| `cli.py` | Command-line argument parsing |
| `components/` | Reusable UI components |
| `styles/` | CSS theme files |

## Commands

```bash
# Development mode (recommended) - hot reload enabled
./dev.sh <session_name> [balance]
./dev.sh default              # Start with default session ($10000)
./dev.sh aggressive 5000      # Start "aggressive" session with $5000
./dev.sh --list               # List all saved sessions

# Historical replay mode (visual backtest)
./dev.sh --historical data/historical/BTCUSD_1m_....csv
./dev.sh --historical data/historical/BTCUSD_1m_....csv --speed 0.1

# Direct Python launch (full control)
python bot/ui/dashboard.py --session <name> [options]

# Options:
#   --session, -s    Session name (required)
#   --balance, -b    Starting balance (default: 10000)
#   --coins, -c      Coins to watch (default: BTC ETH SOL)
#   --resume, -r     Resume from saved state
#   --fresh, -f      Clear saved state and start fresh
#   --historical     CSV file for historical replay
#   --speed          Delay between candles (default: 0.5s)
```

## Session Management

```bash
# List all saved sessions
./dev.sh --list
python bot/ui/dashboard.py --list-sessions

# Sessions are stored in data/sessions/<name>/
# Each session saves: balance, positions, fees, trade count
```

## Keybindings

| Key | Action | Description |
|-----|--------|-------------|
| `q` | Quit | Exit dashboard (saves state, closes positions) |
| `r` | Reset | Reset session (clear positions, restore balance) |
| `p` | Pause | Pause/resume trading (market data still streams) |
| `s` | Strategy | Cycle through AI trading strategies |
| `t` | Tuning | Generate performance tuning report |
| `c` | Charts | Toggle charts panel visibility |
| `Ctrl+R` | Restart | Restart with fresh code (hot reload) |
