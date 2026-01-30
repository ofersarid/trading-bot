# Bot

Main Python package containing all trading bot logic.

## Folders

| Folder | Purpose |
|--------|---------|
| `ai/` | AI-powered analysis, decision making, and position sizing |
| `backtest/` | Backtesting engine and position management |
| `core/` | Core trading logic, models, and unified trading engine |
| `historical/` | Historical data fetching and storage |
| `hyperliquid/` | Hyperliquid exchange API client and WebSocket |
| `indicators/` | Technical indicators (ATR, MACD, RSI, Volume Profile) |
| `live/` | Live trading engine using real-time data |
| `signals/` | Signal detection and aggregation system |
| `simulation/` | Paper trading simulator and state management |
| `strategies/` | Trading strategy definitions and configurations |
| `tuning/` | Parameter tuning and performance analysis |
| `ui/` | Textual TUI dashboard and components |

## Architecture

```mermaid
flowchart TD
    subgraph Data Layer
        HIST[historical/]
        HL[hyperliquid/]
    end

    subgraph Analysis Layer
        IND[indicators/]
        SIG[signals/]
        STRAT[strategies/]
    end

    subgraph Decision Layer
        AI[ai/]
        CORE[core/]
    end

    subgraph Execution Layer
        LIVE[live/]
        BT[backtest/]
        SIM[simulation/]
    end

    subgraph Interface Layer
        UI[ui/]
        TUNE[tuning/]
    end

    HIST --> CORE
    HL --> LIVE

    IND --> SIG
    SIG --> AI
    STRAT --> AI

    AI --> CORE
    CORE --> LIVE
    CORE --> BT

    LIVE --> SIM
    BT --> SIM

    SIM --> UI
    SIM --> TUNE
```

## Trading Flow

The trading system follows a deterministic signal-to-trade pipeline:

```mermaid
sequenceDiagram
    autonumber
    participant Candles as Candles<br/>(OHLCV)
    participant Detectors as Signal Detectors<br/>signals/detectors/*.py
    participant Scoring as Weighted Scoring<br/>ai/signal_brain.py
    participant Decision as Direction Decision<br/>ai/signal_brain.py
    participant TPSL as TP/SL Calculator<br/>core/levels.py
    participant Sizing as Position Sizing<br/>ai/signal_brain.py
    participant Plan as TradePlan<br/>ai/models.py

    Candles->>Detectors: OHLCV data
    Note over Detectors: Momentum, RSI, MACD,<br/>Volume Profile analyze patterns
    Detectors->>Scoring: Signals (direction + strength)

    Note over Scoring: long_score = Σ(weight × strength)<br/>short_score = Σ(weight × strength)
    Scoring->>Decision: long_score, short_score

    alt score >= threshold
        Decision->>TPSL: Direction (LONG/SHORT)
        Note over TPSL: Find nearest support/resistance<br/>from VP levels (VAL, VAH, POC, HVN)
        TPSL->>Sizing: SL price, TP price

        Note over Sizing: AI decides 0.5x-2.0x<br/>based on goal progress

        Sizing->>Plan: Position size %
        Note over Plan: Complete TradePlan<br/>ready for execution
    else score < threshold
        Decision->>Plan: WAIT (no trade)
    end
```

**Key Insight:** The AI never decides direction. Direction is deterministic from weighted scoring. The AI only decides **how much** to risk on a trade that's already been decided.

## Running Modes

| Mode | Command | Behavior |
|------|---------|----------|
| Signals Only | (no --ai flag) | Steps 1-4, no AI sizing |
| AI Sizing | `--ai` | Steps 1-5 with AI position sizing |
| AI + Goals | `--ai --goal X --goal-days Y` | AI sizes based on goal progress |
| Portfolio | `--ai --portfolio --goal X` | Multi-asset allocation |
