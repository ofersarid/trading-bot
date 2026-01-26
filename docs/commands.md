# Trading Bot Commands Reference

Quick reference for all available commands and keybindings.

---

## Prerequisites

Before running any Python commands directly, activate the virtual environment:

```bash
source venv/bin/activate
```

Your prompt will change to show `(venv)` when activated. The shell scripts (`dev.sh`, `start.sh`, `stop.sh`) handle this automatically.

---

## Starting the Bot

### Development Mode (Recommended)
Hot reload enabled - CSS changes instant, Python changes auto-restart.

```bash
./dev.sh <session_name> [balance]

# Examples:
./dev.sh default              # Start with default session ($10000)
./dev.sh aggressive 5000      # Start "aggressive" session with $5000
./dev.sh test_strategy        # Start new "test_strategy" session
./dev.sh --list               # List all saved sessions

# Historical replay mode (see it play out in the UI!)
./dev.sh --historical data/historical/BTCUSD_1m_....csv
./dev.sh --historical data/historical/BTCUSD_1m_....csv --speed 0.1
```

### Production Mode
Simple start without hot reload.

```bash
./start.sh [balance]

# Examples:
./start.sh                    # Start with $10000
./start.sh 5000               # Start with $5000
./start.sh --dev 10000        # Enable CSS hot reload
```

### Stop the Bot
Force stop all running dashboard instances.

```bash
./stop.sh
```

### Direct Python Launch
Full control over all options.

```bash
python bot/ui/dashboard.py --session <name> [options]

# Required:
#   --session, -s    Session name

# Options:
#   --balance, -b    Starting balance (default: 10000)
#   --coins, -c      Coins to watch (default: BTC ETH SOL)
#   --resume, -r     Resume from saved state
#   --fresh, -f      Clear saved state and start fresh

# Examples:
python bot/ui/dashboard.py --session my_strategy
python bot/ui/dashboard.py --session test --balance 5000
python bot/ui/dashboard.py --session my_strategy --resume
python bot/ui/dashboard.py --session old_session --fresh
```

### Paper Trading Simulator

Standalone simulator for testing strategies (without the full dashboard UI).

```bash
# Live mode - connects to Hyperliquid WebSocket
python bot/simulation/run_simulator.py --balance 10000 --coins BTC ETH SOL

# Historical replay mode - replay from CSV file
python bot/simulation/run_simulator.py --historical data/historical/BTCUSDT_1m_....csv

# Historical with slower playback (0.1s between candles)
python bot/simulation/run_simulator.py --historical data/historical/BTCUSDT_1m_....csv --speed 0.1

# Quiet mode (suppress trade-by-trade output)
python bot/simulation/run_simulator.py --historical data/historical/BTCUSDT_1m_....csv --quiet
```

**Simulator Options:**

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--balance` | `-b` | 10000 | Starting balance in USD |
| `--coins` | `-c` | BTC ETH SOL | Coins to watch (live mode only) |
| `--size` | `-s` | 0.1 | Position size as fraction of balance |
| `--historical` | `-H` | - | CSV file for historical replay |
| `--speed` | - | 0 | Delay between candles in seconds |
| `--quiet` | `-q` | - | Suppress trade-by-trade output |

### Dashboard Historical Replay

Run the full dashboard UI with historical data (see trades play out visually):

```bash
# Via dev.sh (recommended)
./dev.sh --historical data/historical/BTCUSD_1m_....csv
./dev.sh --historical data/historical/BTCUSD_1m_....csv --speed 0.1

# Direct Python launch
python bot/ui/dashboard.py --historical data/historical/BTCUSD_1m_....csv --speed 0.5
```

**Dashboard Historical Options:**

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--historical` | `-H` | - | CSV file for historical replay |
| `--speed` | - | 0.5 | Delay between candles in seconds |
| `--balance` | `-b` | 10000 | Starting balance in USD |

### Session Management
```bash
# List all saved sessions
python bot/ui/dashboard.py --list-sessions
./dev.sh --list

# Delete a session
python bot/ui/dashboard.py --delete-session <name>
```

---

## AI Strategy Tester

Interactive tool to experiment with AI trading strategies.

### Prerequisites
```bash
# Start Ollama first (required)
ollama serve
```

### Quick Commands
```bash
# Interactive mode (recommended to start)
python test_ai.py

# List strategies and scenarios
python test_ai.py --list
python test_ai.py -l

# Test specific strategy
python test_ai.py --strategy momentum
python test_ai.py -s momentum

# Test specific strategy + scenario
python test_ai.py -s contrarian -c extreme_buying
python test_ai.py -s conservative -c choppy_neutral

# Compare all strategies on one scenario
python test_ai.py -c bullish_momentum --compare
```

### Available Strategies

| Strategy | Flag | Description |
|----------|------|-------------|
| Generic | `-s generic` | Balanced analysis without specific rules |
| Momentum | `-s momentum` | Ride strong trends and breakouts |
| Contrarian | `-s contrarian` | Bet against extreme market sentiment |
| Conservative | `-s conservative` | Only high-probability setups |
| Scalper | `-s scalper` | Quick in-and-out on fresh moves |

### Available Scenarios

| Scenario | Flag | Description |
|----------|------|-------------|
| Bullish Momentum | `-c bullish_momentum` | Strong upward movement |
| Bearish Momentum | `-c bearish_momentum` | Strong downward movement |
| Choppy/Neutral | `-c choppy_neutral` | No clear direction |
| Extreme Buying | `-c extreme_buying` | Overextended, reversal setup |
| Extreme Selling | `-c extreme_selling` | Panic selling, bounce setup |

---

## Historical Data Commands

Fetch historical kline (candlestick) data from Bybit for backtesting and case studies.

### Fetch Historical Data

```bash
./get-data-set-from [options]

# No arguments - fetch last 1 hour of BTC data
./get-data-set-from

# Fetch specific time range
./get-data-set-from --start 12-01-2026:10-15 --end 12-01-2026:11-15

# Fetch different symbol
./get-data-set-from --symbol ETHUSDT

# Fetch with 5-minute candles
./get-data-set-from --start 12-01-2026:10-00 --end 12-01-2026:14-00 --interval 5

# Fetch spot market (instead of perpetuals)
./get-data-set-from --start 12-01-2026:10-00 --end 12-01-2026:11-00 --category spot
```

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--start` | `-s` | 1 hour ago | Start time `dd-mm-yyyy:hh-mm` |
| `--end` | `-e` | now | End time `dd-mm-yyyy:hh-mm` |
| `--symbol` | `-S` | `BTCUSDT` | Trading pair |
| `--interval` | `-i` | `1` | Candle interval (1, 3, 5, 15, 30, 60, 120, 240, 360, 720, D, W) |
| `--category` | `-c` | `linear` | Market type (linear=USDT perps, spot, inverse) |
| `--output` | `-o` | `data/historical/` | Output directory |
| `--filename` | `-f` | auto | Custom filename |

### Output

Data is saved as CSV to `data/historical/`. Files are organized by scenario type:

```
data/historical/
├── bullish_momentum/      # Strong upward movement
├── bearish_momentum/      # Strong downward movement
├── choppy_neutral/        # No clear direction
├── extreme_buying/        # Overextended - reversal setup
├── extreme_selling/       # Panic selling - bounce setup
├── uncategorized/         # New data before classification
│   ├── BTCUSDT_1m_20260112_1015_to_20260112_1115.csv
│   └── ETHUSDT_5m_20260112_1000_to_20260112_1400.csv
└── README.md
```

After fetching data, move it to the appropriate scenario folder based on market conditions.

CSV format:
```csv
timestamp,open,high,low,close,volume,turnover
2026-01-12T10:15:00,95000.5,95050.0,94980.0,95020.0,1.523,144640.46
```

### Direct Python Usage

```bash
# Activate venv first
source venv/bin/activate

# Run the CLI module
python -m bot.historical.cli --start 12-01-2026:10-15 --end 12-01-2026:11-15

# Or use the fetcher programmatically
python -c "
from bot.historical import BybitHistoricalFetcher
from datetime import datetime

with BybitHistoricalFetcher() as fetcher:
    candles = fetcher.fetch('BTCUSDT', datetime(2026,1,12,10,15), datetime(2026,1,12,11,15))
    fetcher.save_csv(candles, 'data/historical/my_data.csv')
"
```

---

## Backtesting Workflow

Complete workflow from fetching data to running backtests.

### 1. Fetch Historical Data

```bash
# Default: Last 1 hour of BTCUSDT 1-minute candles
./get-data-set-from

# Specific time range
./get-data-set-from --start 12-01-2026:10-00 --end 12-01-2026:14-00

# Different symbol
./get-data-set-from --symbol ETHUSDT --start 12-01-2026:10-00 --end 12-01-2026:14-00
```

### 2. Run Backtest

**Option A: Full Dashboard UI (recommended for case studies)**

See trades play out visually with charts, AI reasoning, and P&L tracking:

```bash
./dev.sh --historical data/historical/BTCUSD_1m_20260120_1328_to_20260126_0847.csv

# Faster replay (0.1s per candle instead of default 0.5s)
./dev.sh --historical data/historical/BTCUSD_1m_20260120_1328_to_20260126_0847.csv --speed 0.1
```

**Option B: CLI Simulator (fast batch testing)**

Quick results without the UI - good for parameter sweeps:

```bash
# Run backtest with that data
python bot/simulation/run_simulator.py \
    --historical data/historical/BTCUSD_1m_20260120_1328_to_20260126_0847.csv \
    --balance 10000

# Quiet mode (just final results)
python bot/simulation/run_simulator.py \
    --historical data/historical/BTCUSD_1m_20260120_1328_to_20260126_0847.csv \
    --quiet

# Slow playback for visualization (0.1s between candles)
python bot/simulation/run_simulator.py \
    --historical data/historical/BTCUSD_1m_20260120_1328_to_20260126_0847.csv \
    --speed 0.1
```

---

## 3-Layer Backtest Engine

Advanced backtesting with the Indicators → Signals → AI Brain architecture.

### Quick Start

```bash
# Signals-only mode (fast, no AI required)
python3 run_backtest.py

# With AI decisions (requires Ollama running)
python3 run_backtest.py --ai

# Specific persona
python3 run_backtest.py --persona scalper
python3 run_backtest.py --persona conservative
python3 run_backtest.py --persona balanced

# Custom data file
python3 run_backtest.py --data data/historical/BTCUSD_1m_20260120_1328_to_20260126_0847.csv
```

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--data` | `-d` | latest CSV | Path to historical data CSV |
| `--ai` | - | disabled | Enable AI decisions (requires Ollama) |
| `--persona` | `-p` | balanced | Trading persona (scalper/conservative/balanced) |
| `--balance` | `-b` | 10000 | Starting balance in USD |
| `--signals` | `-s` | all | Signal detectors to use (momentum rsi macd) |

### Personas

| Persona | Style | Description |
|---------|-------|-------------|
| `scalper` | Aggressive | Quick trades, tight stops, acts on single strong signals |
| `conservative` | Cautious | Waits for consensus, wider stops, higher confidence threshold |
| `balanced` | Moderate | Weighs risk/reward, reasonable stops, adaptable |

### Signal Detectors

| Detector | Description |
|----------|-------------|
| `momentum` | EMA crossover (9/21 period) |
| `rsi` | Oversold (<30) / Overbought (>70) |
| `macd` | MACD/Signal line crossover |

### Example Output

```
🚀 BACKTEST CONFIGURATION
============================================================
  Data:      data/historical/BTCUSD_1m_20260120_1328_to_20260126_0847.csv
  Persona:   balanced
  Balance:   $10,000.00
  Signals:   momentum, rsi, macd
  AI Mode:   Disabled (signals-only)
============================================================

📊 BACKTEST RESULTS
============================================================
💰 PERFORMANCE
  Initial Balance: $10,000.00
  Final Balance:   $10,245.32
  Total P&L:       +$245.32 (+2.45%)

📊 RISK METRICS
  Win Rate:        62.5%
  Max Drawdown:    1.23%
  Sharpe Ratio:    1.45

🔄 TRADE STATISTICS
  Total Trades:    24
  Winning:         15
  Losing:          9
```

### Running Unit Tests

```bash
# Test indicators (SMA, EMA, RSI, MACD, ATR)
python3 tests/test_indicators.py

# Test signal detectors
python3 tests/test_signals.py

# Test backtest components
python3 tests/test_backtest.py
```

### Architecture Overview

```
Historical CSV → Indicators (pure math) → Signals (pattern detection) → AI Brain → Position Manager
                     │                        │                           │              │
                 SMA/EMA/RSI              Momentum                    TradePlan      Trailing
                 MACD/ATR                 RSI/MACD                    Execution      Stops
```

---

## Ollama Commands

Local AI server management.

> **Note:** Ollama runs as a separate background server on `localhost:11434`. It persists independently of the trading bot - closing the bot does NOT stop Ollama. If configured, Ollama may also start automatically on system boot.

```bash
# Start Ollama server (required for AI mode)
ollama serve

# List installed models
ollama list

# Download a model
ollama pull mistral          # Recommended for 8GB RAM
ollama pull llama3.2         # Best quality
ollama pull phi3             # Lightweight option

# Test a model directly
ollama run mistral "Hello, are you working?"

# Check if Ollama is running
curl http://localhost:11434/api/tags
```

### Checking Ollama Status

```bash
# Quick check - returns model list if running, error if not
curl -s http://localhost:11434/api/tags > /dev/null && echo "Ollama is RUNNING" || echo "Ollama is STOPPED"

# Check if Ollama process exists
pgrep -x ollama && echo "Ollama process found" || echo "No Ollama process"

# See Ollama process details
ps aux | grep -i ollama | grep -v grep
```

### Stopping Ollama

```bash
# Graceful stop (if running in foreground, just Ctrl+C)

# Kill Ollama process
pkill ollama

# Force kill if needed
pkill -9 ollama

# Verify it's stopped
pgrep -x ollama || echo "Ollama is stopped"
```

### Disable Ollama Auto-Start (macOS)

If Ollama starts automatically on boot and you want to disable that:

```bash
# Unload the launch agent
launchctl unload ~/Library/LaunchAgents/com.ollama.ollama.plist 2>/dev/null

# Or remove it entirely
rm ~/Library/LaunchAgents/com.ollama.ollama.plist 2>/dev/null
```

---

## Development Commands

### Running Tests
```bash
# Test UI layout (no data connection)
python test_ui.py

# Test AI connection and strategies
python test_ai.py -l
```

### Log Monitoring
```bash
# Watch live logs
tail -f trading_bot.log

# Search logs for errors
grep -i error trading_bot.log

# Search logs for trades
grep -i "trade\|position" trading_bot.log
```

### Git Shortcuts
```bash
# Check status
git status

# View recent changes
git diff

# Commit changes
git add . && git commit -m "message"
```

---

## Configuration Files

| File | Purpose |
|------|---------|
| `bot/core/config.py` | Trading parameters (thresholds, position size) |
| `bot/strategies/` | Trading strategy definitions (one file per strategy) |
| `bot/ai/prompts.py` | AI prompt templates |
| `bot/ui/styles/theme.css` | Dashboard visual theme |
| `.env` | API keys (git-ignored) |

---

## Data Locations

| Path | Contents |
|------|----------|
| `data/sessions/<name>/state.json` | Saved session state |
| `data/sessions/<name>/reports/` | Tuning reports |
| `data/feedback/trades.json` | Trade feedback log |
| `data/historical/<scenario>/*.csv` | Historical data organized by scenario |
| `trading_bot.log` | Application logs |

---

## Dashboard Keybindings

| Key | Action | Description |
|-----|--------|-------------|
| `q` | Quit | Exit the dashboard (saves state, closes positions) |
| `r` | Reset | Reset session (clear positions, restore balance) |
| `p` | Pause | Pause/resume trading (market data still streams) |
| `Ctrl+R` | Restart | Restart with fresh code (hot reload) |
| `s` | Strategy | Cycle through AI trading strategies |
| `t` | Tuning | Generate performance tuning report |

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│                    TRADING BOT CONTROLS                      │
├─────────────────────────────────────────────────────────────┤
│  q = Quit           r = Reset           p = Pause           │
│  Ctrl+R = Restart   s = Strategy        t = Tuning Report   │
├─────────────────────────────────────────────────────────────┤
│  LIVE MODE                                                  │
│  ──────────                                                 │
│  START:      ./dev.sh <session>                             │
│  STOP:       ./stop.sh                                      │
├─────────────────────────────────────────────────────────────┤
│  HISTORICAL REPLAY (Visual)                                 │
│  ──────────────────────────                                 │
│  FETCH DATA: ./get-data-set-from                            │
│              ./get-data-set-from --start dd-mm-yyyy:hh-mm   │
│                                                             │
│  DASHBOARD:  ./dev.sh --historical data/historical/FILE.csv │
│              ./dev.sh --historical FILE.csv --speed 0.1     │
├─────────────────────────────────────────────────────────────┤
│  3-LAYER BACKTEST (Fast)                                    │
│  ───────────────────────                                    │
│  SIGNALS:    python3 run_backtest.py                        │
│  WITH AI:    python3 run_backtest.py --ai                   │
│  PERSONA:    python3 run_backtest.py --persona scalper      │
│  DATA:       python3 run_backtest.py --data FILE.csv        │
├─────────────────────────────────────────────────────────────┤
│  AI & TOOLS                                                 │
│  ──────────                                                 │
│  OLLAMA:     ollama serve                                   │
│  AI TEST:    python test_ai.py                              │
│  UNIT TESTS: python3 tests/test_indicators.py               │
└─────────────────────────────────────────────────────────────┘
```
