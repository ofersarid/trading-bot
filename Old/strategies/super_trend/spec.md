# SuperTrend Trend-Following Strategy Specification

Based on: SuperTrend + Relative Volume (Kernel Optimized) | Flux Charts
Version: 0.1
Last Updated: January 13, 2026

---

## Overview

This is an always-in-market trend-following strategy that flips positions when the SuperTrend indicator changes direction. When a trend flip occurs, the strategy simultaneously exits the current position and enters the opposite position. You are always holding either a long or short position, never flat.

**Strategy Type:** Swing Trading / Day Trading
**Timeframe:** Works on multiple timeframes (15m to Daily recommended)
**Market:** Crypto / Forex / Stocks / Futures (leveraged products required for shorting)

---

## Indicator Foundation

This strategy is built on the following indicator:

**File:** `indicators.pine`
**Key Components:**
- SuperTrend with ATR-based dynamic support/resistance bands
- Trend direction state machine (tracks bullish/bearish state)
- Visual trend signals with arrows and colored bands

**Primary Signals:**
- 🟢 **Bullish Signal:** Price crosses above SuperTrend line (trend flip from bearish to bullish)
- 🔴 **Bearish Signal:** Price crosses below SuperTrend line (trend flip from bullish to bearish)

**Indicator Settings:**
- ATR Length: 10
- ATR Multiplier: 3

---

## Entry Rules

### Long Entry Conditions

**Required Conditions:**
1. Price crosses above the SuperTrend line (`bullishBreak`)
2. Previous trend state was bearish (ensures it's a trend flip, not continuation)

**Entry Timing:**
- Enter immediately when price crosses above SuperTrend line

**Entry Type:** Market order (immediate execution on signal)

**Important:** If you are currently in a short position when `bullishBreak` occurs, you simultaneously:
1. Close the short position
2. Open a new long position
This is a **position flip**, not just an entry.

### Short Entry Conditions

**Required Conditions:**
1. Price crosses below the SuperTrend line (`bearishBreak`)
2. Previous trend state was bullish (ensures it's a trend flip, not continuation)

**Entry Timing:**
- Enter immediately when price crosses below SuperTrend line

**Entry Type:** Market order (immediate execution on signal)

**Important:** If you are currently in a long position when `bearishBreak` occurs, you simultaneously:
1. Close the long position
2. Open a new short position
This is a **position flip**, not just an entry.

---

## Exit Rules

### Stop Loss

**Long Positions:**
- **Placement:** At the SuperTrend line value (dynamic trailing stop)
- **Buffer:** Add 0.5% buffer below SuperTrend line to avoid premature stops from wicks
- **Calculation:** `stopLoss = Pine_Supertrend * 0.995`
- **Update:** Trail stop up as SuperTrend line moves higher each candle

**Short Positions:**
- **Placement:** At the SuperTrend line value (dynamic trailing stop)
- **Buffer:** Add 0.5% buffer above SuperTrend line to avoid premature stops from wicks
- **Calculation:** `stopLoss = Pine_Supertrend * 1.005`
- **Update:** Trail stop down as SuperTrend line moves lower each candle

### Position Exit & Flip

**Primary Exit Method:** Position Flip on Trend Reversal

This is an **always-in-market strategy**. You never close a position without immediately opening the opposite position.

**Long to Short Flip:**
- When `bearishBreak` occurs while holding long
- Close long position AND open short position simultaneously
- New short stop is set at SuperTrend line + buffer

**Short to Long Flip:**
- When `bullishBreak` occurs while holding short
- Close short position AND open long position simultaneously
- New long stop is set at SuperTrend line - buffer

**Stop Loss Hit:**
- If SuperTrend stop is hit before trend flip occurs
- Close position and wait for next trend flip signal
- Re-enter when next `bullishBreak` or `bearishBreak` occurs
- This is the ONLY time you'll be flat (temporarily until next signal)

**Note:** No take profit targets - ride the trend until it flips. The SuperTrend trailing stop protects profits.

### Trailing Stop

**Activation:** Immediately on entry
**Method:** SuperTrend line acts as dynamic trailing stop
**Update Frequency:** Every candle close
**Rule:** Stop only moves in favorable direction, never against position

---

## Position Sizing

**Method:** Percentage of Equity

- **Default Position Size:** 100% of available equity
- **Customizable:** User can adjust position size percentage in strategy inputs
- **Max Open Trades:** 1 (always-in-market on single instrument)

### Calculation

```
accountEquity = current account balance
positionSizePercent = input setting (default 100%)
positionValue = accountEquity × (positionSizePercent / 100)
positionSize = positionValue / entryPrice
```

**Example ($10,000 account, 100% position size):**
- Entry: $50,000 (BTC/USD)
- Position value: $10,000 (100% of equity)
- Position size: 0.2 BTC

**Example ($10,000 account, 50% position size):**
- Entry: $50,000 (BTC/USD)
- Position value: $5,000 (50% of equity)
- Position size: 0.1 BTC

---

## Trade Filters

### Volatility Filter

**Minimum ATR Filter:**
- **Purpose:** Avoids trading in extremely low volatility conditions
- **Setting:** Minimum ATR threshold (customizable input)
- **Default:** Current ATR should be at least 50% of 50-period ATR average
- **Formula:** `ta.atr(10) >= ta.ema(ta.atr(10), 50) * minATRMultiplier`
- **Input Parameter:** `minATRMultiplier` (default: 0.5, range: 0.0 to 1.0)
- **Set to 0.0 to disable this filter**

**How it works:**
- If current ATR is below the threshold, skip trend flip signals
- Only enter positions when volatility is sufficient
- Helps avoid whipsaws during tight consolidation periods

---

## Key Settings

Settings to use when implementing this strategy:

| Setting | Default | Purpose |
|---------|---------|---------|
| ATR Length | 10 | Lookback period for Average True Range calculation |
| ATR Multiplier | 3 | Multiplier for ATR to create SuperTrend bands |
| Stop Buffer % | 0.5% | Buffer added to SuperTrend line for stop loss placement |
| Position Size % | 100% | Percentage of equity to use per position (customizable) |
| Min ATR Multiplier | 0.5 | Minimum ATR threshold as fraction of 50-period average (0.0 to disable) |
| Show SuperTrend Line | true | Display the SuperTrend line on chart |
| Display Volume Gradient | true | Visual aid showing relative volume intensity |

**Note:** The original indicator has KDE (Kernel Density Estimation) volume analysis with a 70% threshold, but this is **disabled** for this strategy per user requirements. We're focusing purely on SuperTrend direction changes.

---

## Visual Setup Checklist

Before entering a trade, verify on the chart:

### Long Setup:
- [ ] SuperTrend line changes from red to green (or bearish to bullish color)
- [ ] Up arrow appears below the candle
- [ ] Price crosses above the SuperTrend line
- [ ] Previous trend state was bearish (confirms it's a flip, not continuation)
- [ ] Clear space above for price to move (no immediate resistance)

### Short Setup:
- [ ] SuperTrend line changes from green to red (or bullish to bearish color)
- [ ] Down arrow appears above the candle
- [ ] Price crosses below the SuperTrend line
- [ ] Previous trend state was bullish (confirms it's a flip, not continuation)
- [ ] Clear space below for price to move (no immediate support)

---

## Example Trade Scenarios

### Example Long Trade with Position Flip

**Setup:**
Currently holding short position from previous bearish trend. Price starts consolidating near SuperTrend support, then breaks above.

**Entry (Flip from Short to Long):**
- Price: $48,500 (BTC/USD)
- Signal: Bullish break (price crosses above SuperTrend)
- Action: Close short position + Open long position
- SuperTrend Line: $48,200
- Previous short entry: $50,000 (loss: $1,500 per unit, -3R)

**Position Details:**
- Stop Loss: $48,006 (SuperTrend × 0.995 = $48,200 × 0.995)
- Account: $10,000
- Position Size: 100% of equity
- Position: 0.206 BTC ($10,000 notional)

**Progression:**
- Bar 10: SuperTrend trails to $48,500 → stop moves to $48,257
- Bar 20: SuperTrend trails to $49,000 → stop moves to $48,755 (now profitable)
- Bar 35: SuperTrend trails to $50,200 → stop moves to $49,949 (locked in profit)
- Bar 48: Price crosses below SuperTrend → Bearish break signal → **FLIP TO SHORT**

**Exit & Flip:**
- Flip Price: $51,100
- Exit Signal: Bearish break (trend flip)
- Close long: +$2,600 per BTC × 0.206 = +$536 (+26% account growth)
- Open short: Entry $51,100, Stop $51,351 (SuperTrend × 1.005)
- New position: 0.201 BTC short ($10,266 notional, using new account balance)
- **Now holding short position, waiting for next trend flip**

**Outcome:** Excellent trend capture. Position flipped from long to short in one action, now riding the new bearish trend.

### Example Short Trade with Position Flip

**Setup:**
Currently holding long position from previous bullish trend. Price loses momentum and breaks below SuperTrend resistance.

**Entry (Flip from Long to Short):**
- Price: $49,800 (BTC/USD)
- Signal: Bearish break (price crosses below SuperTrend)
- Action: Close long position + Open short position
- SuperTrend Line: $50,100
- Previous long entry: $48,000 (profit: +$1,800 per unit, +3.6R)

**Position Details:**
- Stop Loss: $50,350 (SuperTrend × 1.005 = $50,100 × 1.005)
- Account: $10,000
- Position Size: 100% of equity
- Position: 0.201 BTC ($10,000 notional)

**Progression:**
- Bar 8: SuperTrend trails to $49,800 → stop moves to $50,049
- Bar 15: SuperTrend trails to $49,300 → stop moves to $49,546 (now profitable)
- Bar 25: SuperTrend trails to $48,500 → stop moves to $48,742
- Bar 32: Price crosses above SuperTrend → Bullish break signal → **FLIP TO LONG**

**Exit & Flip:**
- Flip Price: $48,200
- Exit Signal: Bullish break (trend flip)
- Close short: +$1,600 per BTC × 0.201 = +$322 (+16% account growth)
- Open long: Entry $48,200, Stop $47,959 (SuperTrend × 0.995)
- New position: 0.214 BTC long ($10,322 notional, using new account balance)
- **Now holding long position, waiting for next trend flip**

**Outcome:** Good short trade capture. Position flipped from short to long, now riding the new bullish trend.

---

## Common Mistakes to Avoid

1. **Ignoring the dynamic stop loss**
   - Why it's bad: SuperTrend trails quickly in trending markets; using fixed stops defeats the purpose
   - Solution: Update stop loss to SuperTrend line value every candle (with buffer)

3. **Going flat instead of flipping positions**
   - Why it's bad: This strategy is designed to be always-in-market; missing trends defeats the purpose
   - Solution: When bearish break occurs, close long AND open short simultaneously (not just close long)

4. **Trading against higher timeframe trend**
   - Why it's bad: Lower timeframe signals can whipsaw if higher timeframe trend is opposite
   - Solution: Check higher timeframe (4x current) for trend alignment before entry

5. **Not adjusting for low volatility**
   - Why it's bad: Low volatility periods generate more false signals and whipsaws
   - Solution: Use the Min ATR Multiplier filter to avoid trading in low volatility conditions

6. **Forgetting double commission on flips**
   - Why it's bad: Each position flip pays commission twice (exit + entry), eating into profits
   - Solution: Include realistic commission in backtests (0.1-0.2% for crypto) and factor into R calculations

---

## Optimization & Backtesting

**Recommended Test Period:** Minimum 12 months of data across different market conditions

**Key Metrics to Track:**
- Win rate (target: 40-50% for trend-following)
- Average R multiple (target: 2.5R+)
- Profit factor (target: 1.5+)
- Max drawdown (acceptable: 15-20%)
- Sharpe ratio (target: 1.0+)
- Average bars in trade (shows trend capture efficiency)

**Parameters to Optimize:**

| Parameter | Default | Test Range | Notes |
|-----------|---------|------------|-------|
| ATR Length | 10 | 5-20 | Lower = more sensitive, higher = smoother |
| ATR Multiplier | 3 | 2-5 | Lower = tighter stops, higher = fewer signals |
| Stop Buffer % | 0.5% | 0.2%-1.0% | Adjust based on asset volatility |
| Min ATR Multiplier | 0.5 | 0.0-1.0 | Higher = stricter filter, 0.0 = disabled |
| Position Size % | 100% | 25%-100% | Lower = more conservative, higher = aggressive |

**What NOT to optimize:**
- Don't curve-fit buffer percentages to exact decimal places
- Don't optimize entry timing beyond "close of signal candle"
- Don't add complex filters that weren't in original indicator
- Avoid optimizing separate parameters for different market conditions (overfitting)

**Market Condition Testing:**
Test strategy across:
- Trending bull markets (2020-2021 crypto)
- Trending bear markets (2022 crypto)
- Range-bound choppy markets (consolidation periods)
- High volatility (March 2020, FTX collapse)
- Low volatility (summer doldrums)

---

## Implementation Notes

### Converting to strategy.pine

When implementing this spec as a Pine Script strategy:

1. **Copy indicator calculations** from `indicators.pine` (SuperTrend calculation)
2. **Add strategy header** with initial capital, commission, slippage settings
3. **Implement entry conditions** using `strategy.entry()` on trend flips
4. **Implement exit logic** using `strategy.exit()` with dynamic stop at SuperTrend line
5. **Add position sizing logic** based on risk percentage
6. **Include visual markers** for entries/exits on chart
7. **Add alerts** for signal notifications
8. **Disable KDE activation threshold** (set `activationThresholdEnabled = false`)

### Code Structure

```pinescript
//@version=6
strategy("SuperTrend Always-In Strategy",
         overlay=true,
         initial_capital=10000,
         default_qty_type=strategy.percent_of_equity,
         commission_type=strategy.commission.percent,
         commission_value=0.1,
         close_entries_rule="ANY",
         max_bars_back=5000)

// 1. Import SuperTrend calculation
import TradingView/ta/9 as ta

// 2. Inputs
atrLength = input.int(10, "ATR Length", minval=1)
atrMultiplier = input.int(3, "ATR Multiplier", minval=1)
stopBuffer = input.float(0.5, "Stop Buffer %", minval=0.0, maxval=5.0)
positionSizePercent = input.float(100.0, "Position Size %", minval=1.0, maxval=100.0)
minATRMultiplier = input.float(0.5, "Min ATR Multiplier", minval=0.0, maxval=1.0,
                               tooltip="Minimum ATR as fraction of 50-period average. Set to 0.0 to disable filter.")

// 3. Calculate SuperTrend
[supertrend, direction] = ta.supertrend(atrMultiplier, atrLength)

// 4. Volatility filter
currentATR = ta.atr(atrLength)
avgATR = ta.ema(currentATR, 50)
minATRThreshold = avgATR * minATRMultiplier
atrFilterPass = minATRMultiplier == 0.0 or currentATR >= minATRThreshold

// 5. Detect trend flip signals
bullishBreak = ta.crossover(close, supertrend) and atrFilterPass
bearishBreak = ta.crossunder(close, supertrend) and atrFilterPass

// 6. Calculate stops
longStop = supertrend * (1 - stopBuffer/100)
shortStop = supertrend * (1 + stopBuffer/100)

// 7. Execute position flips with custom position sizing
if bullishBreak
    strategy.entry("Long", strategy.long, qty=positionSizePercent, comment="Flip to Long")

if bearishBreak
    strategy.entry("Short", strategy.short, qty=positionSizePercent, comment="Flip to Short")

// 8. Update trailing stops every bar
if strategy.position_size > 0  // In long position
    newStop = supertrend * (1 - stopBuffer/100)
    strategy.exit("Long Stop", "Long", stop=newStop)

if strategy.position_size < 0  // In short position
    newStop = supertrend * (1 + stopBuffer/100)
    strategy.exit("Short Stop", "Short", stop=newStop)

// 9. Visualizations
plot(supertrend, "SuperTrend", direction < 0 ? color.green : color.red, linewidth=2)

plotshape(bullishBreak, "Flip to Long", shape.triangleup,
          location.belowbar, color.green, size=size.normal)
plotshape(bearishBreak, "Flip to Short", shape.triangledown,
          location.abovebar, color.red, size=size.normal)

// Background color for current position
bgcolor(strategy.position_size > 0 ? color.new(color.green, 95) :
        strategy.position_size < 0 ? color.new(color.red, 95) : na)

// Plot ATR filter status (optional)
plot(atrFilterPass ? 1 : 0, "ATR Filter", display=display.none)
```

### Key Implementation Considerations

1. **Always-In-Market:** Use `strategy.entry()` which automatically closes opposite positions - no need for explicit `strategy.close()` calls
2. **Position Sizing:** Set `default_qty_type=strategy.percent_of_equity` in strategy declaration, then use `qty=X` parameter in `strategy.entry()` where X is the percentage (0-100)
3. **Stop Loss Updates:** Call `strategy.exit()` every bar to update trailing stop to current SuperTrend value
4. **Position Flipping:** `strategy.entry()` handles the flip - it closes the opposite position and opens new one atomically
5. **ATR Filter:** Apply volatility filter before allowing signals - prevents trading in low volatility conditions
6. **Commission:** Include realistic commission (0.1% for crypto, 0.05% for stocks) - you pay commission on BOTH the exit and entry when flipping
7. **Slippage:** Add slippage setting (5-10 ticks) for realistic backtest
8. **Pyramiding:** Set `pyramiding=1` (no adding to existing positions)
9. **Close Entries Rule:** Set `close_entries_rule="ANY"` to allow position flips
10. **Immediate Execution:** Signals trigger immediately on crossover/crossunder without waiting for candle close

---

## Performance Expectations

### Realistic Targets (Based on Always-In-Market SuperTrend Strategy)

**Important Note:** As an always-in-market strategy, you're constantly exposed to price movements. This means:
- Higher total number of trades (every trend flip)
- More commission/slippage costs (double on each flip)
- No cash drag (always compounding)
- Potential for large drawdowns in choppy markets
- Captures every trend (no missed opportunities)

**Strong Trending Markets (Bull or Bear):**
- Win Rate: 45-55%
- Average R: 3-5R per winning trade
- Profit Factor: 2.0-3.0
- Monthly Return: 8-20%
- Drawdown: 5-10% (trends don't reverse often)

**Ranging/Choppy Markets:**
- Win Rate: 25-35% (many false signals)
- Average R: 0.5-1R (stopped out quickly)
- Profit Factor: 0.6-1.0 (losing or breakeven)
- Monthly Return: -5% to 0%
- Drawdown: 15-25% (constant whipsaws)

**Mixed Conditions (Most Realistic):**
- Win Rate: 35-45%
- Average R: 2-3R
- Profit Factor: 1.3-1.6
- Annual Return: 20-40%
- Max Drawdown: 20-30%
- **Expectation:** Few large winners cover many small losses

### When Strategy Performs Best
- Clear trending markets (up or down)
- Medium to high volatility
- Strong momentum with follow-through
- Higher timeframes (4H, Daily better than 1m, 5m)

### When Strategy Struggles
- Tight ranging markets
- Choppy/whipsaw conditions
- Post-news volatility spikes
- Low volume consolidation periods

---

## Next Steps

1. ✅ **Review this specification** - Adjust any parameters to match your risk tolerance
2. 📝 **Implement in Pine Script** - Use the code structure above as starting point
3. 📊 **Backtest thoroughly** - Test on 12+ months across different market conditions
4. 📈 **Optimize parameters** - Find best ATR length/multiplier for your asset/timeframe
5. 📄 **Paper trade** - Run strategy on demo account for 1-2 months
6. 💰 **Start small** - Begin with 0.5% risk per trade, scale up after proving consistency
7. 🔄 **Monitor and adjust** - Track performance, adjust for changing market conditions

---

## Risk Warning

⚠️ **Important Disclaimer:**

This strategy is for educational purposes and is not financial advice. SuperTrend is a lagging indicator that performs well in trending markets but suffers in ranging conditions. Expect drawdown periods and consecutive losses.

- Never risk more than you can afford to lose
- Past performance does not guarantee future results
- Backtest results can differ significantly from live trading
- Always use proper position sizing and risk management
- Consider starting with paper trading before risking real capital

**Always-In-Market Risks:**
- You are ALWAYS exposed to market risk (long or short)
- No "sitting on the sidelines" during uncertain periods
- Choppy/ranging markets can cause rapid position flips and drawdowns
- Double commission paid on every flip (exit old + enter new)
- Consider using the KDE volume filter or other quality filters if whipsaws become excessive

**The user requirement to ignore volume percentile means this strategy has no filter for low-quality signals. In choppy markets, expect frequent position flips and higher commission costs.**
