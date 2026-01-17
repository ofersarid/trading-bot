# CHoCH + FVG Strategy v1 - Overview

Based on Craig Percoco's "The Perfect Beginner DAY TRADING Strategy"

---

## The 3-Step Setup

1. **IDENTIFY TREND** → Look for 2+ Break of Structures (BOS) confirming direction
2. **SPOT REVERSAL** → CHoCH = price fails to make new extreme, breaks opposite way
3. **ENTER AT FVG** → Position at 50% of FVG (Consequential Encroachment level)

---

## How Change of Character (CHoCH) is Calculated

CHoCH detects trend reversals. It builds on three concepts:

### Step 1: Swing Point Detection

A **swing high** is a candle where the high is higher than X candles on both sides.  
A **swing low** is a candle where the low is lower than X candles on both sides.

```
Swing High: ta.pivothigh(high, swing_length, swing_length)
Swing Low:  ta.pivotlow(low, swing_length, swing_length)
```

Default `swing_length = 5` means we look 5 bars left AND 5 bars right.

### Step 2: Break of Structure (BOS)

BOS = price **closes** beyond the last swing point in the trend direction.

| BOS Type | Condition |
|----------|-----------|
| **Bullish BOS** | `close > last_swing_high` AND `close[1] <= last_swing_high` |
| **Bearish BOS** | `close < last_swing_low` AND `close[1] >= last_swing_low` |

Each BOS in the same direction increments `bos_count`.  
When direction changes, `bos_count` resets to 1.

### Step 3: CHoCH Detection

CHoCH = the **first BOS in the opposite direction** after an established trend.

| CHoCH Type | Condition |
|------------|-----------|
| **Bullish CHoCH** | Bullish BOS + previous bar was in downtrend (`trend_state[1] == -1`) |
| **Bearish CHoCH** | Bearish BOS + previous bar was in uptrend (`trend_state[1] == 1`) |

**Visual:**

```
DOWNTREND (2+ bearish BOS)
         ↓
    [Bullish BOS breaks above last swing high]
         ↓
    = BULLISH CHoCH (trend reversal signal)
```

---

## How Fair Value Gap (FVG) is Calculated

An FVG is simply a **gap** between 3 candles where price moved so fast that it left empty space.

### Think of it like this:

Imagine 3 people standing in a line. Normally they overlap a bit (shoulder to shoulder). But if the middle person jumps really far, there's now a gap between person 1 and person 3.

### Bullish FVG (Price shot UP)

```
                                        ┌───────┐
                                        │       │
                                        │   3   │
                        ┌───────┐       │       │
                        │       │       └───────┘ ← Candle 3's LOW
                        │   2   │
                        │   ▲   │  ░░░░░░░░░░░░░░░ THE GAP
┌───────┐               │   │   │
│       │               │   │   │  ░░░░░░░░░░░░░░░ (empty space)
│   1   │ ← Candle 1's  └───────┘
│       │    HIGH
└───────┘

TIME →   [oldest]                      [newest]
```

**In plain English:** Candle 2 shot up so fast that Candle 1's top doesn't touch Candle 3's bottom.

**The gap = the empty space between them**
- Top of gap = Candle 3's LOW
- Bottom of gap = Candle 1's HIGH
- Entry = middle of the gap (50%)

### Bearish FVG (Price crashed DOWN)

```
┌───────┐
│       │
│   1   │ ← Candle 1's
│       │    LOW
└───────┘               ┌───────┐
                        │   │   │  ░░░░░░░░░░░░░░░ THE GAP
                        │   ▼   │
                        │   2   │  ░░░░░░░░░░░░░░░ (empty space)
                        │       │       ┌───────┐ ← Candle 3's HIGH
                        └───────┘       │       │
                                        │   3   │
                                        │       │
                                        └───────┘

TIME →   [oldest]                      [newest]
```

**In plain English:** Candle 2 dropped so fast that Candle 1's bottom doesn't touch Candle 3's top.

**The gap = the empty space between them**
- Top of gap = Candle 1's low  
- Bottom of gap = Candle 3's high
- Entry = middle of the gap (50%)

### Why do we care?

Price tends to **come back** to fill these gaps before continuing. So:
- Bullish FVG → we wait for price to retrace DOWN into the gap, then BUY
- Bearish FVG → we wait for price to retrace UP into the gap, then SELL

### When is an FVG "used up"?

When price closes completely through the gap (fills it), it turns gray and we ignore it.

---

## Position Sizing Strategy

### Formula

```
Position Value ($) = Current Equity × Grade Risk %
Position Qty (units) = Position Value / Entry Price
```

### Risk % Per Grade

| Grade | Quality Factors | Position % | Example ($100 equity) |
|-------|-----------------|------------|----------------------|
| A+    | 5/5             | 80%        | $80 position         |
| A     | 4/5             | 70%        | $70 position         |
| B     | 3/5             | 60%        | $60 position         |
| C     | 2/5             | 50%        | $50 position         |
| F     | 0-1/5           | 0%         | No trade             |

*All percentages are configurable in strategy settings*

---

## Minimum Criteria (Must ALL be true)

1. **Confirmed Trend** → 2+ BOS in the previous trend before CHoCH
2. **Valid CHoCH** → Price breaks in opposite direction
3. **Valid FVG** → Gap exists (high[2] < low for bullish, low[2] > high for bearish)
4. **FVG Not Filled Immediately** → Price hasn't closed inside the FVG yet

---

## Quality Factors (5 total)

These determine position size for setups that pass minimum criteria:

| Factor | What It Checks |
|--------|----------------|
| 1. Strong Displacement | FVG-creating candle is 1.5× average size |
| 2. Failed Extreme | Price failed to make new high/low before CHoCH |
| 3. Significant FVG | Gap is larger than average candle size |
| 4. Recent Structure | BOS occurred within last 10 bars |
| 5. FVG Untouched | Price hasn't even wicked into the FVG yet |

---

## Entry Logic

1. **Setup detected** → Check minimum criteria (2+ BOS, CHoCH, valid FVG)
2. **Minimum passed** → Calculate grade based on 5 quality factors
3. **Grade filter passed** → Calculate position size = equity × grade %
4. **Price retraces to 50% of FVG** → Enter with calculated qty
5. **Exit set** → Stop loss + Take profit (default 4× risk)

---

## Stop Loss & Take Profit

| Direction | Stop Loss | Take Profit |
|-----------|-----------|-------------|
| **Long**  | Below FVG bottom or swing low (whichever is lower) - 10% buffer | Entry + (Risk × R:R ratio) |
| **Short** | Above FVG top or swing high (whichever is higher) + 10% buffer | Entry - (Risk × R:R ratio) |

Default R:R = 1:4 (risk $1 to make $4)

---

## Trailing Stop Logic

After first BOS confirms direction in your favor:
- **Trailing stop activates** automatically
- Stop loss trails price by a configurable offset (default: 2R)
  - **For longs:** Stop trails below the high by 2× initial risk
  - **For shorts:** Stop trails above the low by 2× initial risk
- Stop only moves in favorable direction (never against you)
- Locks in profits while giving the trade room to run
- Take profit target remains unchanged

**Example (Long Trade):**
- Entry: 100, Stop: 98 → Initial risk = 2 points
- Trail offset: 2R = 4 points
- When price reaches 110, trailing stop = 110 - 4 = 106
- Guaranteed profit of 6 points (3R) even if price reverses

---

## Key Settings

| Setting | Default | Purpose |
|---------|---------|---------|
| Initial Capital | $100 | Starting account size |
| A+ Position % | 80% | Max position for best setups |
| C Position % | 50% | Min position for weakest valid setups |
| Minimum Grade | C | Skip setups below this grade |
| R:R Ratio | 4.0 | Target 4× risk for take profit |
| Use Trailing Stop | true | Enable trailing stop after first BOS |
| Trail Offset (R) | 2.0 | Trail by 2× initial risk distance |
| Swing Length | 5 | Bars to look left/right for swing detection |
| FVG Entry % | 50% | Enter at midpoint of FVG |

---

## Files

- `choch_fvg_strategy_v1.pine` - The TradingView strategy script
- `strategy_overview.md` - This file

---

## Related Indicators

For visual analysis, use these companion indicators:
- `indicators/fvg_indicator_v1.pine` - Fair Value Gap visualization
- `indicators/market_structure_v1.pine` - BOS/CHoCH detection
