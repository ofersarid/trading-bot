# Momentum Scalping Strategy v1

> **Status:** Active
> **Version:** 1.0
> **Last Updated:** January 18, 2026
> **Timeframe:** Sub-minute (scalping)
> **Assets:** BTC, ETH perpetual futures on Hyperliquid

---

## Overview

A momentum-based scalping strategy that detects short-term price movements and trades in the direction of momentum. Designed for high-frequency, small-profit trades with tight risk management.

### Core Premise

When price moves significantly in a short time window, it often continues briefly in that direction due to:
- Order flow momentum (large orders triggering stops/liquidations)
- Algorithmic trading following the move
- Retail FOMO entering the market

The strategy aims to capture the continuation of these moves before mean reversion occurs.

---

## Entry Logic

### Signal Generation

The strategy monitors price momentum over a configurable time window (default: 5 seconds).

```
momentum = (current_price - price_N_seconds_ago) / price_N_seconds_ago * 100
```

### Two-Tier Threshold System

| Threshold | Default | Purpose |
|-----------|---------|---------|
| **Track Threshold** | 0.02% | Begin monitoring when momentum exceeds this |
| **Trade Threshold** | 0.04% | Execute trade when momentum exceeds this |

This two-tier approach:
1. Reduces noise by filtering minor fluctuations
2. Allows the system to "warm up" before committing capital
3. Provides visual feedback as opportunities develop

### Direction Determination

| Momentum | Direction | Action |
|----------|-----------|--------|
| Positive (price rising) | LONG | Buy to profit from continued rise |
| Negative (price falling) | SHORT | Sell to profit from continued fall |

### Entry Conditions (ALL must be true)

1. **Momentum threshold met:** `|momentum| >= trade_threshold`
2. **No existing position:** Not already holding this coin
3. **Cooldown passed:** At least 30 seconds since last trade
4. **Sufficient margin:** Balance can support the position size

### Position Sizing

- **Default:** 10% of available balance per trade
- **Maximum positions:** 1 per coin (no pyramiding)
- **Leverage:** Uses exchange default (up to 10x available)

---

## Exit Logic

### Automatic Exits

Positions are closed automatically based on unrealized P&L percentage:

| Exit Type | Threshold | Behavior |
|-----------|-----------|----------|
| **Take Profit** | +10% | Close entire position when profit target reached |
| **Stop Loss** | -5% | Close entire position to limit losses |

### Risk/Reward Ratio

- **Risk:** 5% of position value
- **Reward:** 10% of position value
- **R:R Ratio:** 1:2

This means:
- Need >33% win rate to be profitable (before fees)
- With Hyperliquid maker rebates, threshold is lower

### Emergency Exits

Positions are force-closed when:
- WebSocket connection drops (market data unavailable)
- Application shutdown initiated
- Daily loss limit reached (future feature)

---

## Configuration Parameters

All parameters are defined in `bot/core/config.py`:

```python
@dataclass
class TradingConfig:
    # Entry thresholds (TUNABLE)
    track_threshold_pct: float = 0.02    # Start tracking at 0.02%
    trade_threshold_pct: float = 0.04    # Execute at 0.04%
    momentum_timeframe_seconds: int = 5  # Lookback for momentum

    # Exit thresholds (TUNABLE)
    take_profit_pct: float = 0.10        # Take profit at +10%
    stop_loss_pct: float = -0.05         # Stop loss at -5%

    # Position management (TUNABLE)
    position_size_pct: float = 0.10      # 10% of balance per trade
    cooldown_seconds: float = 30.0       # Wait between trades
    max_concurrent_positions: int = 2    # Max open positions
```

### All Tunable Parameters

| Category | Parameter | Range | Default | Effect |
|----------|-----------|-------|---------|--------|
| **Entry** | track_threshold_pct | 0.01% - 0.10% | 0.02% | Lower = more signals, more noise |
| **Entry** | trade_threshold_pct | 0.02% - 0.20% | 0.04% | Lower = more trades, lower quality |
| **Entry** | momentum_timeframe_seconds | 1-30s | 5s | Lower = more responsive, more noise |
| **Exit** | take_profit_pct | 1% - 20% | 10% | Higher = larger wins, fewer exits |
| **Exit** | stop_loss_pct | -2% to -10% | -5% | Tighter = smaller losses, more stops |
| **Position** | position_size_pct | 5% - 25% | 10% | Higher = more risk, more reward |
| **Position** | cooldown_seconds | 10-120s | 30s | Lower = more trades, potential overtrading |
| **Position** | max_concurrent_positions | 1-5 | 2 | Higher = more diversification |

### Runtime Adjustable Parameters

These can be changed during operation via keyboard shortcuts:

| Parameter | Keys | Range | Default |
|-----------|------|-------|---------|
| Track Threshold | `[` / `]` | 0.01% - (trade-0.01)% | 0.02% |
| Trade Threshold | `-` / `=` | (track+0.01)% - 2.00% | 0.04% |
| Momentum Timeframe | `,` / `.` | 1s, 2s, 3s, 5s, 10s, 15s, 30s | 5s |

---

## Momentum Timeframe

The lookback period for momentum calculation affects sensitivity:

| Timeframe | Behavior | Best For |
|-----------|----------|----------|
| 1-3s | Very sensitive, many false signals | Extremely volatile markets |
| 5s | Balanced sensitivity (default) | Normal market conditions |
| 10-15s | Fewer signals, higher quality | Calmer markets |
| 30s | Conservative, misses fast moves | Low volatility periods |

---

## Momentum Display Labels

The prices panel displays momentum with labels **derived from the trading thresholds**, creating a unified view:

| Label | Threshold | Meaning |
|-------|-----------|---------|
| **flat** | < track × 0.5 | Negligible movement |
| **weak** | < track threshold | Minor movement, not yet actionable |
| **tracking** | ≥ track threshold | System is monitoring this opportunity |
| **TRADE!** | ≥ trade threshold | Trade entry criteria met |

With default thresholds (track: 0.02%, trade: 0.04%):

| Label | Range |
|-------|-------|
| flat | < 0.01% |
| weak | 0.01% - 0.02% |
| tracking | 0.02% - 0.04% |
| TRADE! | ≥ 0.04% |

This ensures what you see in the prices panel directly corresponds to trading actions.

---

## Market Condition Awareness

The strategy classifies overall market conditions based on average momentum across all tracked coins:

| Condition | Avg Momentum | Trading Approach |
|-----------|--------------|------------------|
| Very Calm | < 0.05% | May need lower thresholds |
| Calm | 0.05% - 0.10% | Standard thresholds work |
| Active | 0.10% - 0.20% | Good trading conditions |
| Volatile | 0.20% - 0.50% | Consider higher thresholds |
| Extreme | > 0.50% | Reduce position size or pause |

---

## Fees & Costs

Using Hyperliquid fee structure:

| Order Type | Fee |
|------------|-----|
| Maker (limit orders) | -0.02% (rebate!) |
| Taker (market orders) | +0.025% |

**Current implementation uses taker orders** (market orders for speed).

### Break-even Analysis

With 0.025% taker fee on both entry and exit:
- Total fee cost: ~0.05% per round trip
- Minimum profitable move: >0.05%
- Trade threshold (0.04%) is below break-even

**Note:** The strategy relies on momentum continuation to overcome the fee gap. Take profit at +10% provides significant buffer.

---

## Known Limitations

### Current Implementation Gaps

1. **No AI integration** - Pure momentum, no pattern recognition
2. **No order book analysis** - L2 data displayed but not used
3. **No volume confirmation** - Trade volume not factored in
4. **No multi-timeframe analysis** - Single timeframe only
5. **No correlation filtering** - BTC/ETH may signal simultaneously
6. **Market orders only** - Missing maker rebate opportunity

### Risk Factors

1. **Whipsaw markets** - Rapid reversals trigger stop losses
2. **Low liquidity periods** - Slippage can exceed expectations
3. **News events** - Strategy doesn't account for fundamentals
4. **Exchange issues** - Single exchange dependency

---

## Performance Tracking

Metrics tracked by the paper trader:

| Metric | Description |
|--------|-------------|
| Win Rate | Percentage of profitable trades |
| Total P&L | Net profit/loss after fees |
| Total Fees | Cumulative fee impact |
| Equity Curve | Balance over time |
| Max Drawdown | Largest peak-to-trough decline |

---

## Feedback Loop & Parameter Tuning

The strategy includes a feedback loop system for automated parameter optimization.

### How It Works

1. **Data Collection**: Every trade is logged with:
   - Exact parameters used at entry
   - Market conditions (volatility, BTC/ETH correlation)
   - Entry momentum that triggered the trade
   - Outcome and duration

2. **Analysis**: The system analyzes performance across:
   - Different parameter combinations
   - Market conditions
   - Time of day patterns
   - Trade duration effectiveness

3. **Suggestions**: Automated suggestions for parameter adjustments based on:
   - Win rate vs threshold relationships
   - Stop loss hit frequency
   - Take profit achievement rates
   - Market condition performance

### Usage

```python
from bot.tuning import FeedbackCollector, PerformanceAnalyzer, TuningReportExporter

# Initialize
collector = FeedbackCollector()
analyzer = PerformanceAnalyzer(collector)
exporter = TuningReportExporter(collector, analyzer)

# After collecting trades, generate report
json_path, md_path = exporter.export_both()
print(f"Reports saved to: {json_path}, {md_path}")
```

### Report Contents

The tuning report includes:
- Overall performance metrics (win rate, profit factor, expectancy)
- Performance by market condition
- Parameter effectiveness analysis
- Temporal patterns (best hours, optimal trade duration)
- Actionable suggestions with confidence levels

### AI-Assisted Tuning

The markdown report is designed for AI analysis. Share the report with Claude to get:
- Parameter optimization recommendations
- Market condition-specific strategies
- Risk assessment
- Suggestions for new parameters to track

---

## Future Improvements

### Planned Enhancements

1. **AI Analysis Layer** - Use Claude to validate momentum signals
2. **Order Book Imbalance** - Confirm direction with bid/ask pressure
3. **Volume Confirmation** - Require above-average volume
4. **Limit Order Execution** - Capture maker rebates
5. **Dynamic Thresholds** - Adjust based on volatility
6. **Correlation Filter** - Avoid doubling exposure

### Potential Strategy Variants

- **Mean Reversion Mode** - Trade against extreme moves
- **Breakout Mode** - Trade confirmed support/resistance breaks
- **Trend Following Mode** - Use longer timeframes for direction

---

## Files & Code References

| Component | File |
|-----------|------|
| Configuration | `bot/core/config.py` |
| Momentum Calculation | `bot/core/analysis/momentum.py` |
| Opportunity Detection | `bot/core/analysis/opportunities.py` |
| Market Analysis | `bot/core/analysis/market.py` |
| Trade Execution | `bot/simulation/paper_trader.py` |
| Dashboard/UI | `bot/ui/dashboard.py` |
| **Tuning System** | |
| Feedback Collector | `bot/tuning/collector.py` |
| Performance Analyzer | `bot/tuning/analyzer.py` |
| Report Exporter | `bot/tuning/exporter.py` |

---

*Strategy document maintained as part of trading-bot development.*
