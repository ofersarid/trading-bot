# Project: $100 → $1,000 Trading Challenge

## 🎯 Objective
Grow a $100 paper trading account to $1,000 using algorithmic trading strategies implemented in PineScript on TradingView.

**Target Return:** 900% (10x)  
**Timeframe:** 2 months  
**Primary Instrument:** Bitcoin Futures (BTC perpetuals)  
**Account Type:** Paper/Demo  

---

## ⚠️ Reality Check

A 10x return in 2 months requires ~35% weekly compounding gains. This is:
- Extremely aggressive for any trader
- Near-impossible without high leverage and significant risk
- A learning exercise, NOT a realistic expectation for real money

**Adjusted Mindset:** Focus on learning proper trading mechanics. If the paper account succeeds, the real victory is the knowledge gained—not the simulated profits.

---

## 📊 Parameters & Constraints

### Capital
- Starting balance: $100
- No additional deposits during the challenge
- Milestone checkpoints: $200 → $400 → $700 → $1,000

### Trading Environment
- **Platform:** TradingView (PineScript strategies)
- **Backtesting:** TradingView Strategy Tester
- **Paper Trading:** TradingView Paper Trading or exchange demo accounts
- **Timeframes to explore:** 5m, 15m, 1H, 4H

### Instruments to Consider
| Instrument | Pros | Cons |
|------------|------|------|
| BTC Futures | High volatility, 24/7 markets | Can be choppy, high leverage risk |
| ETH Futures | Similar to BTC, sometimes cleaner trends | Correlated with BTC |
| Micro Futures (ES, NQ) | Regulated, clear sessions | Requires different capital |
| Forex Majors | High liquidity, clear sessions | Lower volatility |

---

## 🛠️ Technical Approach

### Phase 1: Foundation (Week 1-2)
- [ ] Learn PineScript basics (variables, indicators, strategy functions)
- [ ] Understand TradingView backtester metrics (Sharpe, Max DD, Win Rate)
- [ ] Build first simple strategy (Moving Average Crossover)
- [ ] Learn to read backtest results critically (avoid overfitting)

### Phase 2: Strategy Development (Week 3-4)
- [ ] Study and implement common day trading patterns:
  - Trend following (EMA crosses, MACD)
  - Mean reversion (RSI oversold/overbought)
  - Breakout strategies (support/resistance)
  - Volume-based entries
- [ ] Add proper position sizing to strategies
- [ ] Implement stop-loss and take-profit logic

### Phase 3: Refinement (Week 5-6)
- [ ] Combine multiple signals (confluence)
- [ ] Add filters (trend filter, volatility filter, session filter)
- [ ] Optimize parameters WITHOUT overfitting
- [ ] Walk-forward testing on unseen data

### Phase 4: Live Paper Testing (Week 7-8)
- [ ] Deploy best strategy on paper account
- [ ] Track real-time performance vs backtest
- [ ] Document discrepancies (slippage, timing issues)
- [ ] Final assessment and learnings

---

## 📈 Risk Management Rules

### Position Sizing
```
Max risk per trade: 2-5% of account
Position size = (Account × Risk%) / (Entry - Stop Loss)
```

### With $100 Account Reality:
- 2% risk = $2 per trade (very small positions)
- Need 10-20x leverage to make meaningful trades
- **High leverage = high risk of liquidation**

### Hard Rules
1. Never risk more than 5% on a single trade
2. Maximum 3 concurrent positions
3. Daily loss limit: 10% of account (stop trading for the day)
4. Weekly loss limit: 20% of account (reassess strategy)

---

## 📚 Learning Resources to Explore

### YouTube Topics to Study
- [ ] Candlestick patterns (doji, engulfing, hammer)
- [ ] Support and resistance identification
- [ ] Trend structure (higher highs, lower lows)
- [ ] Volume analysis basics
- [ ] Risk/Reward ratios
- [ ] Trading psychology and discipline

### PineScript Learning
- [ ] TradingView PineScript documentation
- [ ] PineScript built-in functions reference
- [ ] Open-source strategies on TradingView (study, don't just copy)

---

## 📝 Strategy Log Template

For each strategy developed:

```markdown
### Strategy Name: [Name]
**Date Created:** YYYY-MM-DD
**Concept:** [What edge is this exploiting?]

**Entry Rules:**
1. 
2. 

**Exit Rules:**
1. 
2. 

**Backtest Results (BTC 15m, 6 months):**
- Net Profit: 
- Max Drawdown: 
- Win Rate: 
- Profit Factor: 
- Total Trades: 

**Notes:**

**Status:** [ ] Testing | [ ] Promising | [ ] Rejected | [ ] Active
```

---

## 🎓 Success Metrics

Beyond the $1,000 target, success is measured by:

1. **Knowledge Gained**
   - Can write PineScript strategies from scratch
   - Understands backtesting limitations
   - Grasps risk management fundamentals

2. **Process Quality**
   - Maintained trading journal
   - Documented all strategies
   - Identified what works and what doesn't

3. **Discipline**
   - Followed risk rules consistently
   - Didn't chase losses
   - Treated paper trading seriously

---

## 📅 Weekly Check-ins

| Week | Focus | Account Target | Actual | Notes |
|------|-------|----------------|--------|-------|
| 1 | PineScript basics | $100 | | |
| 2 | First strategy built | $100 | | |
| 3 | Strategy iteration | $150 | | |
| 4 | Multiple strategies | $200 | | |
| 5 | Optimization | $300 | | |
| 6 | Paper trading begins | $450 | | |
| 7 | Live paper testing | $650 | | |
| 8 | Final assessment | $1,000 | | |

---

## 🚀 Getting Started

**Immediate Next Steps:**
1. Set up TradingView account (free tier works for learning)
2. Open your first PineScript editor window
3. Create a "Hello World" indicator
4. Watch 2-3 beginner PineScript tutorials
5. Build your first Moving Average strategy

---

*Remember: The goal is learning. If you end up with deep knowledge of trading mechanics and PineScript, you've succeeded—regardless of the paper account balance.*
