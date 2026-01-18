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

## Ollama Commands

Local AI server management.

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
| `bot/ai/strategies.py` | AI strategy prompts |
| `bot/ai/prompts.py` | Default AI prompts |
| `bot/ui/styles/theme.css` | Dashboard visual theme |
| `.env` | API keys (git-ignored) |

---

## Data Locations

| Path | Contents |
|------|----------|
| `data/sessions/<name>/state.json` | Saved session state |
| `data/sessions/<name>/reports/` | Tuning reports |
| `data/feedback/trades.json` | Trade feedback log |
| `trading_bot.log` | Application logs |

---

## Dashboard Keybindings

### General Controls

| Key | Action | Description |
|-----|--------|-------------|
| `q` | Quit | Exit the dashboard (saves state, closes positions) |
| `p` | Pause | Pause/resume trading (market data still streams) |
| `r` | Reset | Reset session (clear positions, restore balance) |
| `Ctrl+S` | Save | Manually save session state |
| `Ctrl+R` | Restart | Restart with fresh code (hot reload) |

### Threshold Adjustments

| Key | Action | Description |
|-----|--------|-------------|
| `1` | Track - | Decrease tracking threshold by 0.01% |
| `2` | Track + | Increase tracking threshold by 0.01% |
| `3` | Trade - | Decrease trading threshold by 0.01% |
| `4` | Trade + | Increase trading threshold by 0.01% |
| `5` | Mom - | Decrease momentum timeframe (5s → 60s) |
| `6` | Mom + | Increase momentum timeframe (5s → 60s) |

### AI & Analysis

| Key | Action | Description |
|-----|--------|-------------|
| `a` | Toggle AI | Switch between Rule-based and AI analysis mode |
| `t` | Tuning | Generate performance tuning report |

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│                    TRADING BOT CONTROLS                      │
├─────────────────────────────────────────────────────────────┤
│  GENERAL           THRESHOLDS          AI & ANALYSIS        │
│  ─────────         ──────────          ──────────────       │
│  q = Quit          1 = Track -         a = Toggle AI        │
│  p = Pause         2 = Track +         t = Tuning Report    │
│  r = Reset         3 = Trade -                              │
│  Ctrl+S = Save     4 = Trade +                              │
│  Ctrl+R = Reload   5 = Momentum -                           │
│                    6 = Momentum +                           │
├─────────────────────────────────────────────────────────────┤
│  START: ./dev.sh <session>    STOP: ./stop.sh               │
│  AI TEST: python test_ai.py   OLLAMA: ollama serve          │
└─────────────────────────────────────────────────────────────┘
```
