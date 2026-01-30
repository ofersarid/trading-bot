# Trading Bot

AI-powered crypto trading bot for Hyperliquid with paper trading simulation and backtesting.

## Quick Start

**No API keys needed for paper trading!**

```bash
# 1. Setup (first time only)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Start Ollama for AI mode (optional)
ollama serve
ollama pull mistral

# 3. Run the dashboard
./dev.sh default              # Start with $10000
./dev.sh my_strategy 5000     # Custom session with $5000
```

## Prerequisites

- Python 3.11+
- Ollama (for AI mode) - `brew install ollama` or https://ollama.ai

## Files

| File | Purpose |
|------|---------|
| `dev.sh` | Development mode with hot reload (CSS + Python auto-restart) |
| `start.sh` | Start paper trading simulator |
| `stop.sh` | Stop the trading bot |
| `run_backtest.py` | Run backtests on historical data |
| `pyproject.toml` | Python project config (dependencies, Ruff, MyPy settings) |
| `requirements.txt` | Python dependencies |
| `test_ai.py` | AI integration tests |
| `test_ui.py` | UI component tests |

## Commands

```bash
# Development mode with hot reload
./dev.sh <session_name> [balance]
./dev.sh my_strategy           # Load/create session with $10000
./dev.sh aggressive 5000       # Load/create session with $5000

# Historical replay mode
./dev.sh --historical data/historical/BTCUSD_1m_....csv
./dev.sh --historical data/historical/BTCUSD_1m_....csv --speed 0.1

# List sessions
./dev.sh --list

# Run backtests
python run_backtest.py --help

# Run tests
python -m pytest tests/
```

## Architecture

```mermaid
flowchart TD
    subgraph Data Sources
        WS[WebSocket<br/>Live Prices]
        CSV[CSV Files<br/>Historical]
        PARQUET[Parquet Files<br/>Trade Data]
    end

    subgraph Core Engine
        CORE[TradingCore<br/>Unified Logic]
        SIGNALS[Signal Detectors<br/>Momentum, RSI, MACD, VP]
        BRAIN[SignalBrain<br/>Weighted Scoring]
    end

    subgraph AI Layer
        OLLAMA[Ollama Client<br/>Local LLM]
        ANALYZER[Market Analyzer]
        ALLOCATOR[Portfolio Allocator]
    end

    subgraph Execution
        PAPER[Paper Trader<br/>Simulation]
        LIVE[Live Engine<br/>Real Trading]
        BACKTEST[Backtest Engine<br/>Historical]
    end

    subgraph UI
        DASHBOARD[TUI Dashboard<br/>Textual]
        CHARTS[Charts Panel]
        AI_PANEL[AI Panel]
    end

    WS --> LIVE
    CSV --> BACKTEST
    PARQUET --> SIGNALS

    LIVE --> CORE
    BACKTEST --> CORE

    CORE --> SIGNALS
    SIGNALS --> BRAIN
    BRAIN --> OLLAMA
    OLLAMA --> ANALYZER
    ANALYZER --> ALLOCATOR

    CORE --> PAPER
    PAPER --> DASHBOARD
    DASHBOARD --> CHARTS
    DASHBOARD --> AI_PANEL
```

## Folders

| Folder | Purpose |
|--------|---------|
| `bot/` | Main Python package with trading logic |
| `data/` | Historical data, sessions, and feedback |
| `docs/` | Documentation and architecture decisions |
| `tests/` | Unit and integration tests |
