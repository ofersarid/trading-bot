# System Architecture - Crypto AI Trading Bot

> **Version:** 1.2  
> **Last Updated:** January 16, 2026  
> **Status:** Draft

---

## 1. Overview

### 1.1 Purpose
A locally-run AI-powered trading bot that connects to Hyperliquid exchange for crypto futures scalping, using Claude as the analysis engine.

### 1.2 Key Design Principles
- **Local-first**: Runs entirely on user's machine (no cloud dependency except APIs)
- **Event-driven**: Reacts to market data streams in real-time
- **AI-augmented**: Claude analyzes market data and generates trading decisions
- **Risk-managed**: Hard limits prevent catastrophic losses

### 1.3 Target User
- Scalp trader on 1-minute timeframe
- Small account (fee-sensitive)
- Based in Israel
- Using Cursor IDE for development

---

## 2. System Architecture

### 2.1 High-Level Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LOCAL MACHINE (Cursor IDE)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        TRADING BOT (Python)                          │   │
│  │                                                                       │   │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐           │   │
│  │  │   Data       │    │   Strategy   │    │   Execution  │           │   │
│  │  │   Manager    │───►│   Engine     │───►│   Router     │           │   │
│  │  │              │    │              │    │              │           │   │
│  │  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘           │   │
│  │         │                   │                   │                    │   │
│  │         │ Market Data       │ Analysis          │ Trade Decisions    │   │
│  │         │ Buffer            │ Request           │                    │   │
│  │         ▼                   ▼                   ▼                    │   │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐           │   │
│  │  │   State      │    │     AI       │    │   Risk       │           │   │
│  │  │   Store      │    │   Analyzer   │    │   Manager    │           │   │
│  │  │  (SQLite)    │    │   (Claude)   │    │              │           │   │
│  │  └──────────────┘    └──────────────┘    └──────┬───────┘           │   │
│  │                                                  │                    │   │
│  │                              ┌───────────────────┼───────────────┐    │   │
│  │                              │                   │               │    │   │
│  │                              ▼                   ▼               ▼    │   │
│  │                       ┌────────────┐    ┌─────────────┐  ┌─────────┐ │   │
│  │                       │   Paper    │    │   Order     │  │  Order  │ │   │
│  │                       │   Trading  │    │   Manager   │  │ Manager │ │   │
│  │                       │ Simulator  │    │  (Testnet)  │  │ (Live)  │ │   │
│  │                       └────────────┘    └──────┬──────┘  └────┬────┘ │   │
│  │                              │                 │              │      │   │
│  └──────────────────────────────┼─────────────────┼──────────────┼──────┘   │
│                                 │                 │              │          │
│         │                       │ Local           │ HTTPS        │ HTTPS    │
│         │ WebSocket             │ Only            │              │          │
│         ▼                       ▼                 ▼              ▼          │
└─────────┼───────────────────────────────────────────────────────────────────┘
          │                                         │              │
          │ (Public - No Auth)                      │              │
┌─────────▼─────────┐   ┌────────────────┐   ┌─────▼──────────────▼─────┐
│   HYPERLIQUID     │   │   ANTHROPIC    │   │      HYPERLIQUID         │
│   WebSocket API   │   │   Claude API   │   │       REST API           │
│  (Market Data)    │   │  (Analysis)    │   │  (Testnet / Mainnet)     │
└───────────────────┘   └────────────────┘   └──────────────────────────┘
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

### 2.3 Data Flow

```
1. MARKET DATA STREAM (Public - No Auth Required)
   Hyperliquid ──WebSocket──► Data Manager ──► Buffer (last N candles)
                                    │
                                    ▼
                              Trigger Check
                              (candle close / price move / volume spike)
                                    │
                                    ▼
2. AI ANALYSIS TRIGGER
   Buffer ──► Format Prompt ──► Claude API ──► Parse Response
                                                    │
                                                    ▼
                                              Decision:
                                              • LONG / SHORT / HOLD
                                              • Entry price
                                              • Stop loss
                                              • Take profit
                                              • Confidence score
                                                    │
                                                    ▼
3. ORDER EXECUTION (Mode-Dependent)
   Decision ──► Risk Check ──► Execution Router
                    │                 │
                    ▼                 ├──► [Simulation] Paper Trading Simulator
              Position sizing         │         └──► Local position tracking
              Loss limit check        │              P&L calculation
                                      │              Trade history (SQLite)
                                      │
                                      ├──► [Testnet] Order Manager ──► Hyperliquid Testnet API
                                      │
                                      └──► [Live] Order Manager ──► Hyperliquid Mainnet API
```

---

## 3. Component Specifications

### 3.1 Data Manager

**Responsibility:** Connect to exchange WebSocket, buffer market data, trigger analysis.

| Capability | Details |
|------------|---------|
| WebSocket connection | Persistent connection to Hyperliquid |
| Data buffering | Rolling window of last 100 candles per symbol |
| Multi-symbol support | BTC, ETH, and configurable list |
| Trigger mechanisms | Candle close, price threshold, volume spike |

**Interfaces:**
- Input: WebSocket messages from Hyperliquid
- Output: Market data packages to Strategy Engine

### 3.2 AI Analyzer

**Responsibility:** Send market data to Claude, receive and parse trading decisions.

| Capability | Details |
|------------|---------|
| Model selection | Configurable (Opus for complex, Sonnet for speed) |
| Prompt engineering | Structured prompts for consistent output |
| Response parsing | JSON extraction with fallback handling |
| Rate limiting | Respect API limits, queue requests if needed |

**Interfaces:**
- Input: Market data package (candles, orderbook, etc.)
- Output: TradingDecision object

**Model Options:**
| Model | Use Case | Cost | Latency |
|-------|----------|------|---------|
| claude-sonnet-4-20250514 | Default, fast analysis | Lower | ~1-2s |
| claude-opus-4-20250514 | Complex patterns, high-stakes | Higher | ~3-5s |

### 3.3 Order Manager

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

### 3.4 Risk Manager

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

### 3.5 Paper Trading Simulator

**Responsibility:** Simulate order execution locally for strategy testing without real funds.

| Capability | Details |
|------------|---------|
| Position tracking | Simulated long/short positions with entry prices |
| P&L calculation | Real-time unrealized P&L based on live market prices |
| Balance management | Configurable starting balance, track equity curve |
| Trade history | Log all simulated trades to SQLite |
| Slippage simulation | Optional: simulate realistic fill prices |
| Fee simulation | Apply maker/taker fees to simulate real costs |
| Reset functionality | Clear all positions and reset to starting balance |

**Interfaces:**
- Input: TradingDecision from AI Analyzer, live prices from Data Manager
- Output: Simulated fill confirmations, position updates, P&L reports

**Key Features:**
```python
class PaperTradingSimulator:
    def __init__(self, starting_balance: float = 10000):
        self.starting_balance = starting_balance
        self.balance = starting_balance
        self.positions = {}
        self.trade_history = []
    
    def execute_order(self, decision: TradingDecision, current_price: float) -> SimulatedFill
    def get_positions(self) -> dict
    def get_equity(self, current_prices: dict) -> float
    def get_pnl(self) -> float
    def reset(self) -> None
    def export_history(self) -> list[Trade]
```

**Advantages over Testnet:**
- No faucet or mainnet deposit requirements
- Unlimited resets with any starting balance
- Faster iteration (no network latency for orders)
- Test edge cases (what if I had $500? $50,000?)

### 3.6 State Store

**Responsibility:** Persist trade history, positions, and performance metrics.

| Data | Storage | Retention |
|------|---------|-----------|
| Trade history | SQLite | Permanent |
| Current positions | Memory + SQLite | Session |
| Performance metrics | SQLite | Permanent |
| Configuration | .env + config files | Permanent |

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

### 4.2 Anthropic Claude API

**Endpoints:**
| Endpoint | Purpose |
|----------|---------|
| `POST /v1/messages` | Send analysis requests |

**Authentication:** API key in header

**Rate Limits:** 
- Tier 1: 60 requests/minute
- Consider batching if hitting limits

---

## 5. Configuration

### 5.1 Environment Variables (.env)

```bash
# Required for AI analysis
ANTHROPIC_API_KEY=sk-ant-...

# Required for testnet/live trading only (not needed for simulation mode)
HYPERLIQUID_PRIVATE_KEY=0x...

# Optional
AI_MODEL=claude-sonnet-4-20250514
LOG_LEVEL=INFO
TRADING_MODE=simulation  # simulation | testnet | live
```

### 5.2 Simulation Configuration

```python
# config/simulation.py
STARTING_BALANCE = 10000      # USD - can be any amount
MAKER_FEE = -0.0002           # Hyperliquid maker rebate
TAKER_FEE = 0.00025           # Hyperliquid taker fee
SIMULATE_SLIPPAGE = True      # Add realistic slippage
SLIPPAGE_BPS = 1              # Basis points of slippage
```

### 5.3 Strategy Configuration

```python
# config/strategy.py
SYMBOLS = ["BTC", "ETH"]
TIMEFRAME = "1m"
CANDLES_FOR_ANALYSIS = 50
MIN_CONFIDENCE = 0.7
```

### 5.4 Risk Configuration

```python
# config/risk.py
MAX_POSITION_SIZE = 0.1      # BTC
RISK_PER_TRADE = 0.01        # 1% of account
MAX_DAILY_LOSS = 100         # USD
MAX_OPEN_POSITIONS = 2
```

---

## 6. Directory Structure

```
trading-bot/
├── .env                      # API keys (git-ignored)
├── .env.example              # Template
├── requirements.txt          # Python dependencies
├── README.md                 # Project overview
│
├── bot/                      # Main Python package
│   ├── __init__.py
│   │
│   ├── hyperliquid/          # Exchange integration
│   │   ├── __init__.py
│   │   ├── client.py         # Authenticated client
│   │   ├── public_data.py    # Public market data (no auth)
│   │   └── examples/         # Usage examples
│   │
│   ├── simulation/           # Paper trading (coming soon)
│   │   ├── __init__.py
│   │   ├── paper_trader.py
│   │   ├── fills.py
│   │   └── metrics.py
│   │
│   ├── ai/                   # Claude integration (coming soon)
│   │   ├── __init__.py
│   │   ├── analyzer.py
│   │   ├── prompts.py
│   │   └── parser.py
│   │
│   ├── trading/              # Order management (coming soon)
│   │   ├── __init__.py
│   │   ├── orders.py
│   │   ├── positions.py
│   │   └── risk.py
│   │
│   └── utils/
│       ├── __init__.py
│       └── logger.py
│
├── config/                   # Configuration files
│   ├── __init__.py
│   ├── settings.py
│   ├── strategy.py
│   └── risk.py
│
├── docs/                     # Documentation
│   └── PRDs/
│       ├── README.md
│       └── system_architecture.md
│
├── strategies/               # Pine Script strategies
│   └── ...
│
├── indicators/               # Pine Script indicators
│   └── ...
│
├── data/                     # SQLite database
│   └── trades.db
│
├── logs/                     # Log files
│   └── trading.log
│
└── tests/                    # Test suite
    ├── __init__.py
    └── ...
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
2. Send to Claude for analysis
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

### Phase 1: Foundation (Current)
- [x] Project structure setup
- [ ] Configuration management
- [x] Hyperliquid public API wrapper
- [ ] Basic WebSocket connection

### Phase 2: AI Integration
- [ ] Claude API integration
- [ ] Prompt engineering
- [ ] Response parsing
- [ ] Decision data models

### Phase 3: Trading Logic
- [ ] Order placement
- [ ] Position tracking
- [ ] Risk management
- [ ] Stop loss / take profit

### Phase 4: Paper Trading Simulation
- [ ] Paper Trading Simulator implementation
- [ ] Local position tracking and P&L calculation
- [ ] Simulated order fills with fee calculation
- [ ] Trade history logging to SQLite
- [ ] Reset/restart functionality
- [ ] Equity curve tracking
- [ ] Performance metrics (win rate, avg P&L, max drawdown)

### Phase 5: Testnet Validation
- [ ] Hyperliquid testnet API integration
- [ ] Real order placement on testnet
- [ ] Order lifecycle testing (create, fill, cancel)
- [ ] API rate limit handling
- [ ] Error recovery testing

### Phase 6: Live Trading
- [ ] Small position testing
- [ ] Monitoring dashboard
- [ ] Alerting system
- [ ] Gradual position scaling

---

## 11. Future Considerations

### 11.1 Potential Enhancements
- Web dashboard for monitoring
- Telegram/Discord alerts
- Multiple strategy support
- Backtesting framework
- Multi-exchange support (Bybit, OKX)

### 11.2 Scalability
- Current design: Single symbol, single strategy
- Future: Multiple symbols in parallel, strategy switching

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
| Claude API (Sonnet, ~1000 calls/day) | $30-50 |
| Hyperliquid fees | Rebates! (-$20 to +$50) |
| Server (local machine) | $0 |
| **Total** | **$30-80/month** |

---

*Document maintained by: Trading Bot Development Team*
