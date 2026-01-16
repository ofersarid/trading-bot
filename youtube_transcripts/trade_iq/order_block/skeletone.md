# Order Block Strategy (Improved)

> Source: Trade IQ / HyperTrade - "Market Structure Break and Order Block" strategy

## Overview

Enter trades when price retraces to order block zones, with trend confirmation via market structure (higher highs/lows for longs, lower lows/highs for shorts). The improved version adds trend validation to filter out counter-trend entries.

## Key Concepts

| Term | Definition |
|------|------------|
| **Order Block** | Zone marked by the indicator representing potential support/resistance. Bullish OB = green box, Bearish OB = red box |
| **Market Structure Break (MSB)** | When price breaks the most recent swing high (bullish) or swing low (bearish) |
| **Zigzag** | Indicator component that identifies swing highs and swing lows |
| **Higher High / Higher Low (HH/HL)** | Uptrend confirmation - each swing point is higher than the previous |
| **Lower Low / Lower High (LL/LH)** | Downtrend confirmation - each swing point is lower than the previous |

## Indicator Required

**Name:** "Market Structure Break and Order Block" by m-ray KB  
**Platform:** TradingView  
**Components used:** Order blocks (zones), Zigzag (swing points), MSB labels

---

## Entry Rules
x
### Long Entry

- [ ] Price action enters (crosses and closes into) the **bullish order block** (green zone)
- [ ] Price action crosses and **closes above** the bullish order block
- [ ] **Before the breakout**, price must have formed at least **2 higher highs AND 2 higher lows** (confirms uptrend)

### Short Entry

- [ ] Price action enters (crosses and closes into) the **bearish order block** (red zone)
- [ ] Price action crosses and **closes below** the bearish order block
- [ ] **Before the breakout**, price must have formed at least **2 lower lows AND 2 lower highs** (confirms downtrend)

---

## Exit Rules

### Take Profit
- **Target:** 1.5× the risk (1:1.5 risk-reward ratio)

### Stop Loss
- **Long:** Place slightly below the most recent swing low
- **Short:** Place slightly above the most recent swing high

---

## Filters / Invalidation Rules

1. **Long invalidation:** If price breaks below the most recent higher low during the pullback → setup is invalid, do not enter
2. **Short invalidation:** If price breaks above the most recent lower high before the sell signal → do not enter (bearish trend not strong enough)
3. **Room check:** Ensure enough space for take profit to be hit before price reaches the opposing order block

---

## Timeframe

- **Tested on:** 15-minute
- **Asset tested:** ETH/USDT
- **Works on:** [UNCLEAR] - video only tested 15m, likely works on other timeframes

---

## Visual Reference

**Long setup looks like:**
1. Zigzag showing 2+ higher highs and 2+ higher lows (uptrend structure)
2. Price pulls back into green (bullish) order block zone
3. Candle closes inside the zone
4. Next candle(s) close above the zone → ENTRY
5. Stop loss below recent swing low, TP at 1.5× risk distance

**Short setup looks like:**
1. Zigzag showing 2+ lower lows and 2+ lower highs (downtrend structure)
2. Price rallies into red (bearish) order block zone
3. Candle closes inside the zone
4. Next candle(s) close below the zone → ENTRY
5. Stop loss above recent swing high, TP at 1.5× risk distance

---

## Backtest Results (from video)

| Version | Win Rate | Profit Factor | Max Consecutive Wins | Max Consecutive Losses |
|---------|----------|---------------|----------------------|------------------------|
| Basic (no trend filter) | 54% | 1.76 | 6 | 4 |
| **Improved (with trend filter)** | **76%** | **4.75** | **16** | **2** |

---

## Notes

- The basic version (without trend confirmation) had poor results because it took counter-trend trades
- Author emphasizes: "When the trend direction has been confirmed, it's easier to win because market participants are more likely to continue pushing price in the prevailing direction"
- The 2 HH + 2 HL rule (or 2 LL + 2 LH for shorts) is the key improvement that dramatically increased win rate
- Video used 2% risk per trade with 1.5× reward target
- Max drawdown on basic version was 13.32%
- [UNCLEAR] Exact definition of "slightly below/above" for stop loss placement
