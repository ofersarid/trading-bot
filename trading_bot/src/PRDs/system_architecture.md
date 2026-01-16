# System Architecture - Crypto AI Trading Bot

> **Version:** 1.0  
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
│  │  │   Data       │    │   Strategy   │    │   Order      │           │   │
│  │  │   Manager    │───►│   Engine     │───►│   Manager    │           │   │
│  │  │              │    │              │    │              │           │   │
│  │  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘           │   │
│  │         │                   │                   │                    │   │
│  │         │ Market Data       │ Analysis          │ Orders             │   │
│  │         │ Buffer            │ Request           │                    │   │
│  │         ▼                   ▼                   ▼                    │   │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐           │   │
│  │  │   State      │    │     AI       │    │   Risk       │           │   │
│  │  │   Store      │    │   Analyzer   │    │   Manager    │           │   │
│  │  │  (SQLite)    │    │   (Claude)   │    │              │           │   │
│  │  └──────────────┘    └──────────────┘    └──────────────┘           │   │
│  │                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│         │                       │                       │                   │
│         │ WebSocket             │ HTTPS                 │ HTTPS             │
│         ▼                       ▼                       ▼                   │
└─────────┼───────────────────────┼───────────────────────┼───────────────────┘
          │                       │                       │
┌─────────▼─────────┐   ┌────────▼────────┐   ┌─────────▼─────────┐
│   HYPERLIQUID     │   │   ANTHROPIC      │   │   HYPERLIQUID     │
│   WebSocket API   │   │   Claude API     │   │   REST API        │
│  (Market Data)    │   │  (Analysis)      │   │  (Orders)         │
└───────────────────┘   └──────────────────┘   └───────────────────┘
```

### 2.2 Data Flow

```
1. MARKET DATA STREAM
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
3. ORDER EXECUTION
   Decision ──► Risk Check ──► Order Manager ──► Hyperliquid API
                    │                                   │
                    ▼                                   ▼
              Position sizing               Order confirmation
              Loss limit check              Position tracking
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

### 3.5 State Store

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

**Endpoints Used:**

| Type | Endpoint | Purpose |
|------|----------|---------|
| WebSocket | `wss://api.hyperliquid.xyz/ws` | Real-time market data |
| REST | `https://api.hyperliquid.xyz/exchange` | Order placement |
| REST | `https://api.hyperliquid.xyz/info` | Account info |

**Authentication:** ETH wallet private key (signing transactions)

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
# Required
ANTHROPIC_API_KEY=sk-ant-...
HYPERLIQUID_PRIVATE_KEY=0x...

# Optional
AI_MODEL=claude-sonnet-4-20250514
LOG_LEVEL=INFO
```

### 5.2 Strategy Configuration

```python
# config/strategy.py
SYMBOLS = ["BTC", "ETH"]
TIMEFRAME = "1m"
CANDLES_FOR_ANALYSIS = 50
MIN_CONFIDENCE = 0.7
```

### 5.3 Risk Configuration

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
trading_bot/
├── .env                      # API keys (git-ignored)
├── .env.example              # Template
├── requirements.txt          # Dependencies
├── README.md                 # Setup instructions
│
├── config/
│   ├── __init__.py
│   ├── settings.py           # Main settings loader
│   ├── strategy.py           # Strategy parameters
│   └── risk.py               # Risk management rules
│
├── src/
│   ├── __init__.py
│   ├── main.py               # Entry point
│   │
│   ├── PRDs/                 # Product Requirements Documents
│   │   ├── system_architecture.md    # This document
│   │   └── ...
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   ├── stream.py         # WebSocket connection
│   │   ├── buffer.py         # Data buffering logic
│   │   └── models.py         # Data classes
│   │
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── analyzer.py       # Claude integration
│   │   ├── prompts.py        # Prompt templates
│   │   └── parser.py         # Response parsing
│   │
│   ├── trading/
│   │   ├── __init__.py
│   │   ├── orders.py         # Order management
│   │   ├── positions.py      # Position tracking
│   │   └── risk.py           # Risk enforcement
│   │
│   ├── exchange/
│   │   ├── __init__.py
│   │   └── hyperliquid.py    # Exchange wrapper
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logger.py         # Logging setup
│       └── helpers.py        # Utility functions
│
├── data/
│   └── trades.db             # SQLite database
│
├── logs/
│   └── trading.log           # Log files
│
└── tests/
    ├── __init__.py
    ├── test_ai.py
    ├── test_orders.py
    └── test_risk.py
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
- [ ] Project structure setup
- [ ] Configuration management
- [ ] Hyperliquid API wrapper
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

### Phase 4: Testing & Paper Trading
- [ ] Unit tests
- [ ] Paper trading mode
- [ ] Performance logging
- [ ] Strategy refinement

### Phase 5: Live Trading
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
