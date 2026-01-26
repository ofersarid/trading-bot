# Trading Info: How to Actually Use Volume Profiles

> Extracted from transcript on 2026-01-26

---

## Indicators

### Volume Profile

**What it measures:** Shows where most money in the market was traded - the distribution of trading activity (buyer matched with seller) at each price level within a session.

**How to use it:**
- Identify high volume nodes (HVN) - areas where lots of trading happened
- Identify low volume nodes (LVN) - valleys/gaps where less trading happened
- Use value area edges as support/resistance
- Track when volume distribution shifts to identify real trends

**Settings:**
- Can be set to daily, weekly, or any timeframe
- Split by RTH (Regular Trading Hours) vs ETH (Electronic Trading Hours)
- Cash session profiles often respond best for price action setups

**Key concept:** Volume drives price - consider it a leading indicator.

---

### Value Area (First Standard Deviation)

**What it measures:** The price range where ~70% (rounded from 68%) of volume was traded within a session.

**How to use it:**
- Anything inside = "normal" trading activity
- Anything outside = statistical anomaly likely to revert to mean
- Upper edge = premium prices (smart money sells)
- Lower edge = cheap prices (smart money buys)

**Settings:** Typically displayed as highlighted area within volume profile

---

### High Volume Nodes (HVN)

**What it measures:** Price levels with peaks in volume distribution - lots of trading activity from both buyers and sellers.

**How to use it:**
- Areas where price tends to spend time
- Strong support/resistance zones
- Common targets for take-profits
- Look for clusters, not single levels

---

### Low Volume Nodes (LVN)

**What it measures:** Price levels with valleys in volume distribution - directional "sprints" where one side dominated.

**How to use it:**
- Price moves quickly through these areas
- Less price action/retracement expected
- One side of market exerting harder pressure
- Indicates fast, directional moves

---

### Point of Control (POC)

**What it measures:** The single price level with the highest volume traded in a session.

**How to use it:**
- Use as reference, NOT as precise entry level
- Can be random - multiple levels often have similar volume
- Better to identify the HVN area rather than exact POC
- Conservative take-profit target

**Warning:** Don't treat as a singular tradeable level - look at distribution instead.

---

### VWAP (Volume Weighted Average Price)

**What it measures:** Average price of session weighted by volume.

**How to use it:**
- Developing VWAP shows real-time average
- One of the most common institutional references
- Used in best execution algorithms
- Mean reversion target

---

### Delta Profile

**What it measures:** Net buying pressure at each price level (total buying - total selling).

**Formula:** Delta = Total Buying Pressure - Total Selling Pressure

**How to use it:**
- See where aggressive buying/selling clusters
- Identify absorptions (big order blocking price movement)
- Confirm who controls the auction
- Green = net buying, Red = net selling
- Extend significant delta clusters as zones - these are "battle areas" where control shifts repeatedly

**Practical example from video:**
1. A big sell cluster appeared at the top of a candle
2. This blocked buyers trying to push higher (absorption)
3. Price returned to balance
4. Later, a clear buying cluster formed at a lower level
5. That's where buyers stepped in and pumped price up

**Key insight:** Shows the "battle" between buyers and sellers at each level. Unlike regular volume profile, delta reveals WHO is in control, not just how much was traded.

**Notable user:** Fabio Valentini (described as "one of the best scalpers out there") uses delta profile extensively to identify where sellers/buyers take control.

---

### Composite Volume Profile

**What it measures:** Overall volume distribution across entire chart timeframe (e.g., 90 days).

**How to use it:**
- Long-term bias determination
- Major support/resistance identification
- Context for daily session profiles

---

## Signals

### Entry Signals

| Signal | Condition | Notes |
|--------|-----------|-------|
| Failed Auction Fade | Price breaks outside value area then fails and re-enters | Buy bottoms, sell tops when breakout fails |
| Breakout Entry | Price spends significant time outside value area | Wait for volume to also shift, not just price |
| Opening Range Breakout | Break of opening range with volume confirmation | Stop-loss below opening range |
| Volume Shift Confirmation | Lower timeframe shows volume distribution shifting | Use candle-level profiles for timing |
| Engulfing with Delta | Engulfing pattern + clear delta shift to one side | Volume confirmation adds edge to price pattern |

### Exit Signals

| Signal | Condition | Notes |
|--------|-----------|-------|
| Other Side of Value Area | Price reaches opposite edge of distribution | Full range target |
| Point of Control | Price reaches POC/highest volume node | Conservative target |
| Mean Reversion Complete | Price returns to VWAP or value area center | For reversal trades |

### Warning Signs

- Price breaking highs/lows alone (can be random fake outs)
- Relying on exact POC level (can be arbitrary which level wins)
- Using tick-based volume profiles (proxy data, not real volume)
- Ignoring time spent at levels (volume needs time to accumulate)

### Signal Quality

**High Quality Signals (strong/reliable):**
- Volume distribution shifting (not just price breaking)
- Multiple candles/time spent outside value area before entry
- Delta confirmation showing clear control by one side
- Cash session (RTH) profiles over ETH
- Real exchange volume data (CME) over tick volume

**Low Quality Signals (weak/unreliable):**
- Price-only breakouts without volume shift
- Exact POC entries (too precise, can be random)
- Tick-based volume profiles (proxy approximation)
- Single level analysis vs. distribution analysis

---

## Trading Strategies

### Strategy 1: Mean Reversion / Failed Auction

**Setup:**
1. Identify previous session's value area (70% volume range)
2. Wait for price to break outside value area
3. Look for rejection/failure to continue outside
4. Confirm with delta/volume shift on lower timeframe

**Entry:** When price fails outside and re-enters value area

**Exit:**
- Conservative: Point of control / highest volume node
- Aggressive: Other side of value area

**Risk Management:** Stop-loss beyond the failed breakout extreme

**Win Rate:** High, with good risk-to-reward (1:3 mentioned)

---

### Strategy 2: Breakout / Trend Following

**Setup:**
1. Identify current value area distribution
2. Wait for price to break AND spend time outside
3. Confirm new volume distribution forming at higher/lower prices
4. Look for test of breakout area

**Entry:**
- Aggressive: Buy/sell at edge of old value area during breakout
- Conservative: Wait for test after breakout, enter with stop under HVN

**Exit:** Trail with new value areas forming in trend direction

**Risk Management:** Stop-loss under the main high volume node

**Key confirmation:** Money (volume) must shift, not just price highs/lows

---

### Strategy 3: Multi-Timeframe Volume Analysis

**Setup:**
1. Use composite profile (90+ days) for long-term bias
2. Use daily session profiles for intraday bias/levels
3. Use candle-level footprint for entry triggers

**Bias Determination:**
- Uptrend = volume distributions moving higher over time
- Downtrend = volume distributions moving lower over time

**Entry Trigger:**
- Volume shift visible in 5-minute candle footprints
- Delta showing clear control change
- Absorption patterns (big order blocking price)

**Risk Management:** Align entries with higher timeframe bias

---

### Strategy 4: Opening Range Breakout with Volume

**Setup:**
1. Mark opening range of cash session
2. Identify previous session's value area
3. Wait for break of opening range AND value area edge

**Entry:** Break of opening range with volume confirmation

**Exit:** Target new session high/low or measured move

**Risk Management:** Stop-loss below opening range low (for longs)

**Condition:** Works best when aligned with higher timeframe trend

---

## Key Takeaways

- **Volume drives price** - price action is lagging, volume is leading
- **Trade distributions, not single levels** - HVN areas matter more than exact POC
- **68-70% rule** - first standard deviation contains most normal activity
- **Anomalies revert** - prices outside value area tend to return to mean
- **Confirm breakouts with volume** - price-only breakouts can be fake outs
- **Use real data** - CME exchange data > tick volume approximations
- **Cash session matters most** - RTH profiles often more reliable than ETH
- **Delta adds edge** - knowing net pressure at each level provides confirmation
- **Multi-timeframe alignment** - composite for bias, daily for levels, candles for triggers
- **Time matters** - volume accumulates with time spent at price levels

---

## Tools Mentioned

- **TradingView** - Has session volume profile (paid feature), but uses tick volume
- **Deep Charts** - Desktop platform with real CME exchange data, delta profiles
- **Templates** - Andrea Cimi ES 5-minute template in Deep Charts
