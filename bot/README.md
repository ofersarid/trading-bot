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
    participant Factory as SignalsFactory<br/>signals/factory.py
    participant Sizer as GoalBasedSizer<br/>ai/goal_sizer.py
    participant Plan as TradePlan<br/>ai/models.py

    Candles->>Detectors: OHLCV data
    Note over Detectors: Momentum, RSI, MACD,<br/>Volume Profile analyze patterns
    Detectors->>Factory: Raw Signals (direction + strength)

    Note over Factory: Filters by strategy weights<br/>Calculates weighted scores<br/>Enriches with TP/SL

    alt score >= threshold
        Factory->>Sizer: FactoryOutput (signals + TP/SL)
        Note over Sizer: AI decides position size<br/>based on goal progress

        Sizer->>Plan: SizingDecision
        Note over Plan: Complete TradePlan<br/>ready for execution
    else score < threshold
        Factory->>Plan: WAIT (no trade)
    end
```

**Key Insight:** The AI never decides direction. Direction is determined by SignalsFactory through weighted scoring. The AI (GoalBasedSizer) only decides **how much** to risk on a trade that's already been decided.

## Running Modes

| Mode | Command | Behavior |
|------|---------|----------|
| Signals Only | (no --ai flag) | Steps 1-4, no AI sizing |
| AI Sizing | `--ai` | Steps 1-5 with AI position sizing |
| AI + Goals | `--ai --goal X --goal-days Y` | AI sizes based on goal progress |
| Portfolio | `--ai --portfolio --goal X` | Multi-asset allocation |
