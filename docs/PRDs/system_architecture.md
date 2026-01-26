# System Architecture - Crypto AI Trading Bot

> **Version:** 2.0
> **Last Updated:** January 25, 2026
> **Status:** Draft

---

## 1. Overview

### 1.1 Purpose
A locally-run AI-powered trading bot that connects to Hyperliquid exchange for crypto futures scalping, using a 3-layer architecture: technical indicators, rule-based signal detectors, and an AI decision layer (Ollama).

### 1.2 Key Design Principles
- **Local-first**: Runs entirely on user's machine (AI via Ollama, no cloud dependency)
- **3-Layer Architecture**: Separates calculations (indicators), pattern detection (signals), and decision-making (AI)
- **Event-driven**: Reacts to market data streams in real-time
- **AI-augmented**: Local LLM evaluates signals and decides trade execution
- **Risk-managed**: Hard limits prevent catastrophic losses

### 1.3 Target User
- Scalp trader on 1-minute timeframe
- Small account (fee-sensitive)
- Based in Israel
- Using Cursor IDE for development

---

## 2. System Architecture

### 2.1 High-Level Diagram

```mermaid
flowchart TB
    subgraph LOCAL["LOCAL MACHINE (Cursor IDE)"]
        subgraph BOT["TRADING BOT (Python)"]
            WS[WebSocket Manager] --> CA[Candle Aggregator]

            subgraph LAYERS["3-LAYER ARCHITECTURE"]
                CA --> IND[Layer 1: Indicators<br/>RSI, MACD, ATR, EMA]
                IND --> SIG[Layer 2: Signal Detectors<br/>Pattern Recognition]
                SIG --> BRAIN[Layer 3: Signal Brain<br/>AI Decision Maker]
            end

            BRAIN --> PM[Position Manager]
            PM --> PT[Paper Trader]

            WS -->|Market Data| SS[(Session State<br/>JSON)]
            PT -->|Positions| TC[Trading Config]

            subgraph UI["TERMINAL UI (Textual)"]
                P1[Prices]
                P2[Order Book]
                P3[Trades Feed]
                P4[AI Panel]
                P5[Opportunities]
                P6[Positions]
                P7[History]
                P8[Status Bar]
            end
        end
    end

    HL_WS[("Hyperliquid<br/>WebSocket API<br/>(Market Data)")] -->|WebSocket<br/>Public - No Auth| WS
    OLLAMA[("Ollama<br/>Local AI<br/>localhost:11434")] <-->|HTTP<br/>Local - No Auth| BRAIN
    HL_REST[("Hyperliquid<br/>REST API<br/>(Testnet/Mainnet)")] <-.->|HTTPS<br/>Auth Required| PT

    style LOCAL fill:#1a1a2e,stroke:#16213e,color:#fff
    style BOT fill:#16213e,stroke:#0f3460,color:#fff
    style LAYERS fill:#0f3460,stroke:#00ff88,color:#fff
    style UI fill:#0f3460,stroke:#e94560,color:#fff
    style HL_WS fill:#0f3460,stroke:#e94560,color:#fff
    style OLLAMA fill:#0f3460,stroke:#00ff88,color:#fff
    style HL_REST fill:#0f3460,stroke:#e94560,color:#fff
```

### 2.2 Operating Modes

The bot supports three operating modes, allowing progression from safe testing to live trading:

| Mode | Market Data | Order Execution | Funds at Risk | Use Case |
|------|-------------|-----------------|---------------|----------|
| **Simulation** | Live from Hyperliquid | Local (simulated) | None | Strategy development, unlimited testing |
| **Testnet** | Live from testnet | Real orders on testnet | None (mock USDC) | API integration testing, order flow testing |
| **Live** | Live from mainnet | Real orders on mainnet | Real funds | Production trading |

**Mode Selection:**
```python
# config/settings.py
TRADING_MODE = "simulation"  # "simulation" | "testnet" | "live"
```

**Key Insight:** Simulation mode only requires public market data (no API keys needed). This enables unlimited paper trading with full control over starting balance and resets.

### 2.3 Data Flow (3-Layer Architecture)

```mermaid
flowchart TD
    subgraph STEP1["1. MARKET DATA STREAM"]
        HL[Hyperliquid] -->|WebSocket<br/>Public - No Auth| DM[Data Manager]
        DM --> BUF[(Candle Buffer<br/>last 100 candles)]
    end

    subgraph STEP2["2. INDICATORS (Layer 1 - Pure Math)"]
        BUF --> RSI[RSI Calculator]
        BUF --> MACD[MACD Calculator]
        BUF --> ATR[ATR Calculator]
        BUF --> EMA[Moving Averages]
        RSI --> VALUES[Indicator Values<br/>RSI=28.5, MACD=-0.3]
    end

    subgraph STEP3["3. SIGNAL DETECTORS (Layer 2 - Rules)"]
        VALUES --> DET{Detectors}
        DET --> RSI_DET[RSI Detector<br/>Oversold/Overbought]
        DET --> MOM_DET[Momentum Detector<br/>Pressure Analysis]
        DET --> MACD_DET[MACD Detector<br/>Crossovers]
        RSI_DET --> AGG[Signal Aggregator]
        MOM_DET --> AGG
        MACD_DET --> AGG
        AGG --> SIG[Signals<br/>LONG strength=0.8]
    end

    subgraph STEP4["4. SIGNAL BRAIN (Layer 3 - AI)"]
        SIG --> BRAIN[Signal Brain]
        BRAIN -->|HTTP| OLLAMA[Ollama<br/>Local AI]
        OLLAMA --> PLAN[TradePlan<br/>Action + SL + TP + Size]
    end

    subgraph STEP5["5. EXECUTION"]
        PLAN --> PM[Position Manager]
        PM --> ER{Execution Router}

        ER -->|Simulation| SIM[Paper Trader]
        SIM --> LOCAL[(Local tracking<br/>P&L calc<br/>JSON history)]

        ER -.->|Testnet| TEST[Order Manager]
        TEST -.-> HL_TEST[Hyperliquid Testnet]

        ER -.->|Live| LIVE[Order Manager]
        LIVE -.-> HL_LIVE[Hyperliquid Mainnet]
    end

    style STEP1 fill:#1a1a2e,stroke:#16213e,color:#fff
    style STEP2 fill:#16213e,stroke:#0f3460,color:#fff
    style STEP3 fill:#0f3460,stroke:#e94560,color:#fff
    style STEP4 fill:#1a1a2e,stroke:#00ff88,color:#fff
    style STEP5 fill:#16213e,stroke:#e94560,color:#fff
```

### 2.4 Layer Responsibilities

| Layer | Component | Input | Output | Uses AI? |
|-------|-----------|-------|--------|----------|
| **Layer 1** | Indicators | Prices (floats) | Calculated values (RSI=28.5) | No |
| **Layer 2** | Signal Detectors | Candles (OHLCV) | Signal (direction + strength) | No |
| **Layer 3** | Signal Brain | Signals + Context | TradePlan (action + parameters) | **Yes** |

**Why This Separation?**

1. **Indicators** are pure math - reusable, testable, no side effects
2. **Signal Detectors** apply trading rules - deterministic, backtestable without AI costs
3. **Signal Brain** makes final decisions - uses AI for nuanced judgment, considers multiple signals and market context

---

## 3. Component Specifications

### 3.1 Indicators (Layer 1)

**Responsibility:** Pure mathematical calculations that compute technical analysis values from raw price data.

**Location:** `bot/indicators/`

| Indicator | File | Purpose |
|-----------|------|---------|
| RSI | `rsi.py` | Relative Strength Index - overbought/oversold levels |
| MACD | `macd.py` | Moving Average Convergence Divergence - trend momentum |
| ATR | `atr.py` | Average True Range - volatility measurement |
| Moving Averages | `moving_averages.py` | SMA, EMA calculations |

**Key Characteristics:**
- **Stateless**: No memory between calls
- **Pure functions**: Same input always produces same output
- **No trading logic**: Just mathematical formulas

**Example:**
```python
# bot/indicators/rsi.py
def rsi(prices: list[float], period: int = 14) -> float | None:
    """
    Calculate RSI = 100 - (100 / (1 + RS))
    where RS = Average Gain / Average Loss
    """
```

---

### 3.2 Signal Detectors (Layer 2)

**Responsibility:** Apply trading rules to indicator values to generate actionable signals.

**Location:** `bot/signals/detectors/`

| Detector | File | Signal Logic |
|----------|------|--------------|
| RSI | `detectors/rsi.py` | Oversold (<30) → LONG, Overbought (>70) → SHORT, plus divergence detection |
| Momentum | `detectors/momentum.py` | Buy/sell pressure analysis from price action |
| MACD | `detectors/macd.py` | Crossover detection (histogram sign changes) |

**Key Classes:**

```python
# bot/signals/base.py
@dataclass
class Signal:
    coin: str
    signal_type: SignalType  # MOMENTUM, RSI, MACD
    direction: Literal["LONG", "SHORT"]
    strength: float  # 0.0-1.0
    timestamp: datetime
    metadata: dict[str, Any]

class SignalDetector(Protocol):
    def detect(self, coin: str, candles: list[Candle]) -> Signal | None: ...
```

**Signal Aggregator:**
```python
# bot/signals/aggregator.py
class SignalAggregator:
    """Collects signals from multiple detectors."""

    def process_candle(self, coin: str, candles: list[Candle]) -> list[Signal]
    def get_pending_signals(self, time_window_seconds: int) -> list[Signal]
    def get_consensus_direction(self, coin: str) -> str | None  # "LONG" | "SHORT" | None
```

**Key Characteristics:**
- **Stateful**: Tracks cooldowns, last signals, history for divergence
- **Deterministic**: Same candles produce same signals (no AI randomness)
- **Configurable**: Thresholds, periods, cooldowns via config dataclasses

---

### 3.3 Data Manager (WebSocket Manager)

**Responsibility:** Maintain robust WebSocket connection to exchange for real-time market data.

**Location:** `bot/hyperliquid/websocket_manager.py`

| Capability | Details |
|------------|---------|
| WebSocket connection | Persistent connection to Hyperliquid with auto-reconnect |
| Reconnection | Exponential backoff (1s → 30s max), up to 50 attempts |
| Heartbeat monitoring | Ping/pong every 20s, stale connection detection |
| Multi-subscription | Prices, trades, orderbook subscriptions |
| State tracking | DISCONNECTED, CONNECTING, CONNECTED, RECONNECTING, FATAL_ERROR |

**Interfaces:**
- Input: WebSocket messages from Hyperliquid
- Output: Parsed market data to dashboard via async callbacks

**Key Features:**
```python
# bot/hyperliquid/websocket_manager.py
class WebSocketManager:
    def __init__(
        self,
        config: WebSocketConfig,
        on_message: Callable[[dict], Awaitable[None]],
        on_connect: Callable[[], Awaitable[None]],
        on_disconnect: Callable[[str], Awaitable[None]],  # CRITICAL for safety
    ):
        ...

    async def start(self) -> None
    async def stop(self) -> None
    def add_subscription(self, subscription: dict) -> None
    def get_status_string(self) -> str
```

**Safety Features:**
- `on_disconnect` callback fires immediately on connection loss
- Allows trading system to exit positions before reconnection
- Detailed logging for debugging connection issues

### 3.4 Signal Brain (Layer 3 - AI)

**Responsibility:** Evaluate signals from Layer 2 and decide whether to execute trades using AI judgment.

**Location:** `bot/ai/signal_brain.py`

| Capability | Details |
|------------|---------|
| Signal evaluation | Receives signals from detectors, decides action |
| Strategy-based decisions | Trading style defined by strategy (scalper, conservative, trend follower, etc.) |
| Dynamic risk management | Adjusts position size, stops based on signal strength + volatility |
| Local AI inference | Uses Ollama for decision-making |

**Interfaces:**
- **Input**: List of `Signal` objects + current positions + market context
- **Output**: `TradePlan` with action, stop-loss, take-profit, position size

**Key Classes:**
```python
# bot/ai/signal_brain.py
class SignalBrain:
    def __init__(self, strategy: Strategy, ollama_client: OllamaClient): ...

    async def evaluate_signals(
        self,
        signals: list[Signal],
        current_positions: dict[str, Position],
        market_context: MarketContext,
    ) -> TradePlan | None

# bot/ai/models.py
@dataclass
class TradePlan:
    coin: str
    action: Literal["ENTER_LONG", "ENTER_SHORT", "EXIT", "WAIT"]
    confidence: int  # 1-10
    stop_loss: float | None
    take_profit: float | None
    size_pct: float  # Position size as % of balance
    reason: str
```

**Trading Strategies:**
```python
# bot/strategies/base.py
@dataclass
class Strategy:
    name: str
    strategy_type: StrategyType
    prompt: str                  # The AI's trading mindset/style
    risk: RiskConfig             # Risk management parameters
    min_signal_strength: float   # Filter weak signals
    min_confidence: int          # AI confidence threshold
    prefer_consensus: bool       # Require multiple signals to agree
```

| Strategy | Style | Min Strength | Consensus Required |
|----------|-------|--------------|-------------------|
| `momentum_scalper` | Aggressive | 0.7 | No |
| `trend_follower` | Patient | 0.5 | Yes |
| `mean_reversion` | Contrarian | 0.6 | No |
| `conservative` | Cautious | 0.25 | Yes |

**AI Backend:**
| Backend | Use Case | Cost | Latency |
|---------|----------|------|---------|
| Ollama (local) | Default, privacy-focused | Free | ~1-3s (depends on hardware) |
| Claude API | Optional, higher quality | $$ | ~1-2s |

---

### 3.5 Legacy: Market Analyzer

**Note:** The `MarketAnalyzer` (`bot/ai/analyzer.py`) is the older approach that analyzes raw market data directly. The new 3-layer architecture uses `SignalBrain` instead, which receives pre-processed signals rather than raw data.

### 3.6 Order Manager

**Responsibility:** Execute trades, manage positions, track orders.

| Capability | Details |
|------------|---------|
| Order types | Market, Limit, Stop-Market |
| Position tracking | Current positions, average entry, P&L |
| Order lifecycle | Create, monitor, cancel, fill detection |
| Maker preference | Use limit orders for fee rebates |

**Interfaces:**
- Input: TradingDecision from AI Analyzer
- Output: Order requests to Hyperliquid REST API

### 3.7 Risk Manager

**Responsibility:** Enforce risk limits, prevent catastrophic losses.

| Rule | Default | Configurable |
|------|---------|--------------|
| Max position size | 0.1 BTC | Yes |
| Risk per trade | 1% of account | Yes |
| Max daily loss | $100 | Yes |
| Max open positions | 2 | Yes |
| Min confidence threshold | 70% | Yes |

**Kill Switches:**
- Daily loss limit hit → Stop all trading
- Drawdown threshold → Reduce position sizes
- API errors → Pause and alert

### 3.8 Paper Trading Simulator

**Responsibility:** Simulate order execution locally for strategy testing without real funds.

**Location:** `bot/simulation/paper_trader.py`

| Capability | Details |
|------------|---------|
| Position tracking | Simulated long/short positions with entry prices |
| P&L calculation | Real-time unrealized P&L based on live market prices |
| Balance management | Configurable starting balance, track equity curve |
| Trade history | Log all simulated trades (in-memory + JSON persistence) |
| Fee simulation | Apply Hyperliquid maker/taker fees (-0.02% / +0.025%) |
| Reset functionality | Clear all positions and reset to starting balance |
| State persistence | Load/save state via `SessionStateManager` |

**Interfaces:**
- Input: Trade commands (coin, size, price), live prices from WebSocket
- Output: `OrderResult` with success status, position updates, trade records

**Key Features:**
```python
# bot/simulation/paper_trader.py
class PaperTrader:
    def __init__(self, starting_balance: float = 10000, fees: FeeStructure = HYPERLIQUID_FEES):
        self.starting_balance = starting_balance
        self.balance = starting_balance
        self.positions: dict[str, Position] = {}
        self.trade_history: list[Trade] = []

    def open_long(self, coin: str, size: float, price: float, is_maker: bool = False) -> OrderResult
    def open_short(self, coin: str, size: float, price: float, is_maker: bool = False) -> OrderResult
    def close_position(self, coin: str, price: float, is_maker: bool = False) -> OrderResult
    def get_equity(self, current_prices: dict[str, float]) -> float
    def get_state(self, current_prices: dict | None = None) -> SimulatorState
    def reset(self) -> None
    def load_state(self, balance: float, positions: dict, total_fees_paid: float) -> None
```

**Advantages over Testnet:**
- No faucet or mainnet deposit requirements
- Unlimited resets with any starting balance
- Faster iteration (no network latency for orders)
- Test edge cases (what if I had $500? $50,000?)
- Session persistence - resume trading after restarts

### 3.9 State Store (Session State Manager)

**Responsibility:** Persist trading session state to disk for resumption after restarts.

**Location:** `bot/simulation/state_manager.py`

| Data | Storage | Retention |
|------|---------|-----------|
| Session state | JSON (`data/sessions/<name>/state.json`) | Permanent |
| Open positions | JSON (in session state) | Session |
| Trade feedback | JSON (`data/feedback/trades.json`) | Permanent |
| Configuration | Python dataclass (`bot/core/config.py`) | Code |

**Session Structure:**
```
data/sessions/
├── default/
│   ├── state.json      # Balance, positions, stats
│   └── reports/        # Tuning reports for this session
├── aggressive/
│   ├── state.json
│   └── reports/
└── ...
```

**Key Features:**
```python
# bot/simulation/state_manager.py
class SessionStateManager:
    def __init__(self, data_dir: str = "data", session_name: str = "default"):
        ...

    def save(self, trader: PaperTrader, ...) -> None
    def load(self) -> SessionState | None
    def has_saved_state(self) -> bool
    def list_sessions(self) -> list[str]
    def get_reports_dir(self) -> Path
```

### 3.10 UI Dashboard

**Responsibility:** Provide a terminal-based UI for monitoring and controlling the trading bot.

**Location:** `bot/ui/dashboard.py`

**Framework:** Textual (Python TUI framework)

| Panel | Purpose |
|-------|---------|
| Markets Panel | Live prices with momentum indicators |
| Charts Panel | Candlestick chart visualization |
| AI Panel | AI reasoning and analysis results |
| History Panel | Trade history with P&L |
| Status Bar | Connection status, session info, balance |

**Keybindings:**
| Key | Action |
|-----|--------|
| `q` | Quit |
| `r` | Reset session |
| `p` | Pause/resume trading |
| `Ctrl+R` | Restart with fresh code |
| `s` | Cycle AI strategy |
| `t` | Generate tuning report |

### 3.11 Tuning System

**Responsibility:** Collect trade feedback and analyze performance for parameter optimization.

**Location:** `bot/tuning/`

| Module | Purpose |
|--------|---------|
| `collector.py` | Collect trade outcomes and market conditions |
| `analyzer.py` | Calculate win rates, average P&L, drawdown |
| `exporter.py` | Generate tuning reports |

**Key Features:**
- Track per-trade feedback (entry conditions, exit reason, P&L)
- Analyze parameter effectiveness
- Export reports for manual review

---

### 3.12 Backtest Engine

**Responsibility:** Orchestrate backtesting using historical data through the 3-layer architecture.

**Location:** `bot/backtest/engine.py`

| Component | File | Purpose |
|-----------|------|---------|
| Engine | `engine.py` | Orchestrates the full backtest flow |
| Position Manager | `position_manager.py` | Manages positions with trailing stops |
| Models | `models.py` | `BacktestConfig`, `BacktestResult`, `EquityPoint` |
| Breakout Analyzer | `breakout_analyzer.py` | Post-backtest analysis of breakout patterns |

**Backtest Flow:**
```
Historical CSV → Candle Aggregator → Indicators → Signal Detectors
                                                        ↓
                    Position Manager ← Signal Brain (optional AI)
                          ↓
                   BacktestResult (equity curve, metrics)
```

**Key Features:**
```python
# bot/backtest/engine.py
class BacktestEngine:
    def __init__(self, config: BacktestConfig, ollama_client: OllamaClient | None): ...

    async def run(self) -> BacktestResult
    def run_signals_only(self) -> BacktestResult  # No AI, faster iteration

# bot/backtest/models.py
@dataclass
class BacktestConfig:
    data_file: str
    initial_balance: float = 10000.0
    use_ai: bool = True
    detectors: list[str] = ["momentum", "rsi"]  # Which signal detectors to use
    position_size_pct: float = 0.1
```

**Two Modes:**
| Mode | Method | Speed | Use Case |
|------|--------|-------|----------|
| Signals Only | `run_signals_only()` | Fast | Strategy iteration, no AI costs |
| Full AI | `run()` | Slower | Final validation with AI decisions |

---

## 4. External Integrations

### 4.1 Hyperliquid Exchange

**Why Hyperliquid:**
- Maker fee rebate (-0.002%) - critical for scalping
- No KYC required
- Decentralized - no geo-restrictions
- Good API quality
- **Public market data** - no auth needed for prices/candles

**Endpoints Used:**

| Type | Endpoint | Purpose | Auth Required |
|------|----------|---------|---------------|
| WebSocket | `wss://api.hyperliquid.xyz/ws` | Real-time market data | ❌ No |
| REST | `https://api.hyperliquid.xyz/info` | Market info, candles, orderbook | ❌ No |
| REST | `https://api.hyperliquid.xyz/exchange` | Order placement | ✅ Yes |
| REST | `https://api.hyperliquid.xyz/info` | Account info (balances, positions) | ✅ Yes |

**Authentication:** ETH wallet private key (signing transactions) - only required for trading operations

**Testnet Endpoints:**

| Type | Endpoint | Purpose |
|------|----------|---------|
| WebSocket | `wss://api.hyperliquid-testnet.xyz/ws` | Testnet market data |
| REST | `https://api.hyperliquid-testnet.xyz/info` | Testnet info |
| REST | `https://api.hyperliquid-testnet.xyz/exchange` | Testnet orders |

### 4.2 AI Backend (Ollama - Primary)

**Why Ollama:**
- **Local inference** - No API costs, no rate limits
- **Privacy** - Trading data stays on your machine
- **Offline capable** - Works without internet (after model download)
- **Customizable** - Use any compatible model

**Endpoints:**
| Endpoint | Purpose |
|----------|---------|
| `POST http://localhost:11434/api/generate` | Generate analysis |
| `GET http://localhost:11434/api/tags` | List available models |

**Authentication:** None required (local server)

**Setup:**
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model (e.g., llama3.2, mistral)
ollama pull llama3.2
```

### 4.3 Anthropic Claude API (Optional)

**Endpoints:**
| Endpoint | Purpose |
|----------|---------|
| `POST /v1/messages` | Send analysis requests |

**Authentication:** API key in header (`ANTHROPIC_API_KEY`)

**Rate Limits:**
- Tier 1: 60 requests/minute
- Consider batching if hitting limits

**Note:** Claude integration is optional. The bot defaults to Ollama for local inference.

---

## 5. Configuration

### 5.1 Environment Variables (.env)

```bash
# Optional - only needed if using Claude instead of Ollama
ANTHROPIC_API_KEY=sk-ant-...

# Required for testnet/live trading only (not needed for simulation mode)
HYPERLIQUID_PRIVATE_KEY=0x...

# Optional
LOG_LEVEL=INFO
```

### 5.2 Trading Configuration

All trading parameters are centralized in a single dataclass:

```python
# bot/core/config.py
@dataclass
class TradingConfig:
    """Configuration for trading behavior and thresholds."""

    # Opportunity Detection (TUNABLE)
    track_threshold_pct: float = 0.02    # Min momentum to track opportunity
    trade_threshold_pct: float = 0.04    # Min momentum to execute trade
    momentum_timeframe_seconds: int = 5  # Lookback for momentum calc

    # Position Management (TUNABLE)
    take_profit_pct: float = 0.10        # Exit at +10%
    stop_loss_pct: float = -0.05         # Exit at -5%
    position_size_pct: float = 0.10      # 10% of balance per trade
    cooldown_seconds: float = 30.0       # Wait between trades on same coin
    max_concurrent_positions: int = 2    # Max open positions

    # Analysis
    market_analysis_interval_seconds: int = 10
    price_history_maxlen: int = 500

    # Display
    max_trades_history: int = 100
    orderbook_depth: int = 8
    max_trades_displayed: int = 15
```

### 5.3 Fee Configuration

```python
# bot/simulation/models.py
HYPERLIQUID_FEES = FeeStructure(
    maker_fee=-0.0002,   # -0.02% rebate
    taker_fee=0.00025,   # +0.025% fee
)
```

### 5.4 WebSocket Configuration

```python
# bot/hyperliquid/websocket_manager.py
@dataclass
class WebSocketConfig:
    url: str = "wss://api.hyperliquid.xyz/ws"
    max_reconnect_attempts: int = 50
    initial_reconnect_delay: float = 1.0
    max_reconnect_delay: float = 30.0
    ping_interval: float = 20.0
    message_timeout: float = 60.0
```

---

## 6. Directory Structure

```
trading-bot/
├── .env                      # API keys (git-ignored)
├── .gitignore
├── requirements.txt          # Python dependencies
├── dev.sh                    # Development mode launcher (hot reload)
├── start.sh                  # Production launcher
├── stop.sh                   # Stop running bot
│
├── bot/                      # Main Python package
│   ├── __init__.py
│   │
│   ├── ai/                   # AI integration (Layer 3)
│   │   ├── __init__.py
│   │   ├── signal_brain.py   # SignalBrain - AI decision maker
│   │   ├── analyzer.py       # MarketAnalyzer - legacy AI interface
│   │   ├── ollama_client.py  # Local Ollama API client
│   │   ├── prompts.py        # Prompt templates (incl. AI_TRADING_PROMPT)
│   │   ├── models.py         # TradePlan, MarketContext, AnalysisResult
│   │   └── scalper_interpreter.py  # Scalper-specific interpretation
│   │
│   ├── strategies/           # Trading strategies
│   │   ├── __init__.py       # Registry: get_strategy(), list_strategies()
│   │   ├── base.py           # Strategy, RiskConfig, StrategyType classes
│   │   ├── momentum_scalper.py  # Momentum scalper strategy + prompt
│   │   ├── trend_follower.py # Trend follower strategy + prompt
│   │   ├── mean_reversion.py # Mean reversion strategy + prompt
│   │   ├── conservative.py   # Conservative strategy + prompt
│   │   └── README.md         # How to add custom strategies
│   │
│   ├── indicators/           # Technical indicators (Layer 1)
│   │   ├── __init__.py
│   │   ├── rsi.py            # RSI calculation
│   │   ├── macd.py           # MACD calculation
│   │   ├── atr.py            # ATR calculation
│   │   └── moving_averages.py  # SMA, EMA calculations
│   │
│   ├── signals/              # Signal detectors (Layer 2) (NEW)
│   │   ├── __init__.py
│   │   ├── base.py           # Signal dataclass, SignalDetector protocol
│   │   ├── aggregator.py     # SignalAggregator - combines detectors
│   │   ├── validator.py      # SignalValidator - filters bad signals
│   │   └── detectors/        # Individual detector implementations
│   │       ├── __init__.py
│   │       ├── rsi.py        # RSISignalDetector
│   │       ├── momentum.py   # MomentumSignalDetector
│   │       └── macd.py       # MACDSignalDetector
│   │
│   ├── backtest/             # Backtesting system (NEW)
│   │   ├── __init__.py
│   │   ├── engine.py         # BacktestEngine - orchestrates backtest
│   │   ├── models.py         # BacktestConfig, BacktestResult
│   │   ├── position_manager.py  # Position management with trailing stops
│   │   └── breakout_analyzer.py  # Post-backtest breakout analysis
│   │
│   ├── core/                 # Core business logic
│   │   ├── __init__.py
│   │   ├── config.py         # TradingConfig dataclass
│   │   ├── candle_aggregator.py  # Candle data structure
│   │   ├── models.py         # OpportunityCondition, PendingOpportunity
│   │   └── analysis/         # Market analysis modules
│   │       ├── __init__.py
│   │       ├── market.py     # MarketAnalyzer (conditions)
│   │       ├── momentum.py   # Momentum calculations
│   │       └── opportunities.py  # OpportunityAnalyzer
│   │
│   ├── historical/           # Historical data management (NEW)
│   │   ├── __init__.py
│   │   ├── fetcher.py        # Download historical data
│   │   ├── cli.py            # CLI for fetching data
│   │   └── models.py         # Historical data models
│   │
│   ├── hyperliquid/          # Exchange integration
│   │   ├── __init__.py
│   │   ├── client.py         # Authenticated client
│   │   ├── public_data.py    # Public market data (no auth)
│   │   ├── stream.py         # Data streaming utilities
│   │   ├── websocket_manager.py  # Robust WS with reconnection
│   │   ├── watch_prices.py   # Price monitoring
│   │   ├── test_connection.py
│   │   └── examples/         # Usage examples
│   │       ├── __init__.py
│   │       ├── market_data.py
│   │       └── place_order.py
│   │
│   ├── simulation/           # Paper trading system
│   │   ├── __init__.py
│   │   ├── paper_trader.py   # PaperTrader - simulated execution
│   │   ├── models.py         # Position, Trade, Side, FeeStructure
│   │   ├── state_manager.py  # Session persistence
│   │   ├── opportunity_seeker.py  # Opportunity detection
│   │   └── run_simulator.py  # Standalone simulator runner
│   │
│   ├── tuning/               # Feedback & optimization
│   │   ├── __init__.py
│   │   ├── collector.py      # FeedbackCollector
│   │   ├── analyzer.py       # PerformanceAnalyzer
│   │   └── exporter.py       # TuningReportExporter
│   │
│   └── ui/                   # Terminal UI (Textual)
│       ├── __init__.py
│       ├── dashboard.py      # Main TradingDashboard app
│       ├── cli.py            # CLI argument parsing
│       ├── components/       # UI panel components
│       │   ├── __init__.py
│       │   ├── ai_panel.py       # AI reasoning display
│       │   ├── charts_panel.py   # Candlestick charts
│       │   ├── history_panel.py  # Trade history
│       │   ├── markets_panel.py  # Prices and market data
│       │   └── status_bar.py     # Connection status, balance
│       └── styles/
│           └── theme.css     # Retro dark theme
│
├── data/                     # Persistent data
│   ├── sessions/             # Named trading sessions
│   │   └── default/
│   │       ├── state.json    # Session state
│   │       └── reports/      # Tuning reports
│   └── feedback/
│       └── trades.json       # Trade feedback log
│
├── docs/                     # Documentation
│   ├── PRDs/
│   │   ├── README.md
│   │   ├── system_architecture.md
│   │   └── local_ai_integration.md
│   ├── setup-guide.md
│   └── strategies/
│       ├── README.md
│       └── momentum-scalping-v1.md
│
├── Old/                      # Archived/legacy files
│   ├── indicators/           # Pine Script indicators
│   ├── strategies/           # Pine Script strategies
│   └── projects/             # Old project files
│
└── trading_bot.log           # Application log file
```

---

## 7. AI Analysis Triggers

### 7.1 Trigger Options

| Trigger | Description | When to Use |
|---------|-------------|-------------|
| **Candle Close** | Every 1m candle close | Standard operation |
| **Price Threshold** | >0.1% move from last analysis | Catch fast moves |
| **Volume Spike** | 2x average volume | News/events |
| **Manual** | User-initiated | Testing, overrides |

### 7.2 Default Trigger: Candle Close

Every time a 1-minute candle closes:
1. Package last 50 candles
2. Send to AI (Ollama) for analysis
3. Execute decision if confidence > threshold

### 7.3 Future Triggers (Roadmap)

- Order book imbalance detection
- Liquidation cascade detection
- Funding rate anomalies
- Cross-exchange arbitrage signals

---

## 8. Security Considerations

### 8.1 API Key Protection

- Store in `.env` file (git-ignored)
- Never log API keys
- Never commit `.env` to version control

### 8.2 Private Key Security

- Hyperliquid requires ETH wallet private key
- Consider using a dedicated trading wallet
- Keep minimal funds in hot wallet

### 8.3 Rate Limiting

- Implement exponential backoff on API errors
- Queue requests to avoid hitting limits
- Log rate limit responses for debugging

---

## 9. Monitoring & Logging

### 9.1 Log Levels

| Level | Use Case |
|-------|----------|
| DEBUG | Detailed data for troubleshooting |
| INFO | Trade executions, analysis results |
| WARNING | Risk limits approached, API issues |
| ERROR | Failed orders, connection drops |
| CRITICAL | Kill switch triggered, account issues |

### 9.2 Metrics to Track

- Win rate
- Average P&L per trade
- Max drawdown
- API latency
- AI response time
- Fill rate (orders filled / orders placed)

---

## 10. Development Phases

### Phase 1: Foundation ✅ Complete
- [x] Project structure setup
- [x] Configuration management (`bot/core/config.py`)
- [x] Hyperliquid public API wrapper (`bot/hyperliquid/public_data.py`)
- [x] Robust WebSocket connection (`bot/hyperliquid/websocket_manager.py`)
  - Auto-reconnection with exponential backoff
  - Heartbeat monitoring
  - Connection state tracking

### Phase 2: AI Integration ✅ Complete
- [x] Local AI integration via Ollama (`bot/ai/ollama_client.py`)
- [x] Prompt engineering (`bot/ai/prompts.py`)
- [x] Response parsing (`bot/ai/models.py`)
- [x] Decision data models (`AnalysisResult`, `Sentiment`, `Signal`)
- [x] MarketAnalyzer with async analysis (`bot/ai/analyzer.py`)

### Phase 3: 3-Layer Architecture ✅ Complete
- [x] **Layer 1: Indicators** (`bot/indicators/`)
  - RSI, MACD, ATR, Moving Averages
  - Pure mathematical functions
- [x] **Layer 2: Signal Detectors** (`bot/signals/`)
  - RSI, Momentum, MACD detectors
  - SignalAggregator for combining signals
  - SignalValidator for filtering
- [x] **Layer 3: Signal Brain** (`bot/ai/signal_brain.py`)
  - AI-powered decision making
  - Trading strategies (momentum_scalper, trend_follower, mean_reversion, conservative)
  - Dynamic risk management

### Phase 4: Backtesting System ✅ Complete
- [x] Backtest Engine (`bot/backtest/engine.py`)
- [x] Historical data fetcher (`bot/historical/`)
- [x] Position Manager with trailing stops
- [x] Signals-only mode (fast iteration without AI)
- [x] Full AI mode for validation
- [x] Equity curve tracking
- [x] Breakout analysis

### Phase 5: Paper Trading Simulation ✅ Complete
- [x] Paper Trading Simulator implementation (`PaperTrader` class)
- [x] Local position tracking and P&L calculation
- [x] Simulated order fills with fee calculation (Hyperliquid fees)
- [x] Trade history logging (JSON files)
- [x] Reset/restart functionality
- [x] Session persistence (`SessionStateManager`)
- [x] Performance metrics via tuning system

### Phase 6: Testnet Validation
- [ ] Hyperliquid testnet API integration
- [ ] Real order placement on testnet
- [ ] Order lifecycle testing (create, fill, cancel)
- [ ] API rate limit handling
- [ ] Error recovery testing

### Phase 7: Live Trading 🔄 Partial
- [ ] Small position testing
- [x] Monitoring dashboard (`bot/ui/dashboard.py` - Textual TUI)
- [ ] Alerting system
- [ ] Gradual position scaling

---

## 11. Future Considerations

### 11.1 Implemented ✅
- Terminal dashboard for monitoring (Textual TUI)
- Multiple symbol support (BTC, ETH, SOL, etc.)
- Session persistence and resume
- Performance tuning system
- 3-layer architecture (Indicators → Signals → AI Brain)
- Backtesting framework with historical data
- Trading strategies for different risk profiles

### 11.2 Potential Enhancements
- Web dashboard for remote monitoring
- Telegram/Discord alerts
- Multi-exchange support (Bybit, OKX)
- Strategy hot-swapping
- Additional signal detectors (volume profile, order flow)

### 11.3 Scalability
- Current design: Multiple symbols, single strategy
- Future: Strategy switching, A/B testing strategies

---

## Appendix A: API Reference Links

- **Hyperliquid Docs:** https://hyperliquid.gitbook.io/hyperliquid-docs/
- **Anthropic Docs:** https://docs.anthropic.com/
- **Hyperliquid Python SDK:** https://github.com/hyperliquid-dex/hyperliquid-python-sdk

---

## Appendix B: Cost Estimation

### Monthly Costs (Active Scalper)

| Item | Estimated Cost |
|------|----------------|
| AI Analysis (Ollama local) | $0 (runs on your hardware) |
| AI Analysis (Claude API, optional) | $30-50 if used |
| Hyperliquid fees | Rebates! (-$20 to +$50) |
| Server (local machine) | $0 |
| Electricity (GPU inference) | ~$5-10 |
| **Total (Ollama)** | **$0-10/month** |
| **Total (Claude)** | **$30-80/month** |

---

*Document maintained by: Trading Bot Development Team*
*Last synced with codebase: January 25, 2026*
