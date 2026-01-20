# Momentum Calculation Methods

> **Status:** Decision Made - Ready for Implementation
> **Created:** January 20, 2026
> **Decision Date:** January 20, 2026
> **Related:** [Momentum Scalping v1](./momentum-scalping-v1.md)
> **Implementation:** `bot/core/analysis/momentum.py`

---

## Overview

This document explores alternative methods for calculating price momentum in the trading bot. The goal is to find a calculation that:

1. **Reduces noise** - Filters out random tick-to-tick fluctuations
2. **Captures meaningful moves** - Identifies tradeable momentum
3. **Responds quickly** - Doesn't lag too far behind price action
4. **Is interpretable** - The number shown to the user makes intuitive sense

---

## Current Method: Single-Point Rate of Change (ROC)

### Implementation

```python
def calculate_momentum(current_price, price_history, lookback_seconds):
    # Find the first price that's >= lookback_seconds old
    for point in price_history:
        age = (now - point["time"]).total_seconds()
        if age >= lookback_seconds:
            lookback_price = point["price"]
            break

    return (current_price - lookback_price) / lookback_price * 100
```

### Parameters

| Parameter | Current Value |
|-----------|---------------|
| Lookback | 5 seconds |

### Formula

```
momentum % = ((current_price - price_N_seconds_ago) / price_N_seconds_ago) × 100
```

### Pros

- Simple to understand and implement
- Fast to calculate (O(n) worst case, usually O(1))
- Directly interpretable: "price changed X% in last 5 seconds"

### Cons

| Issue | Impact | Severity |
|-------|--------|----------|
| **Single point comparison** | One noisy tick skews the result | High |
| **No smoothing** | Jumpy values, hard to read trends | High |
| **Binary reference** | Misses acceleration/deceleration | Medium |
| **Very short window** | 5s captures noise, not signal | Medium |

### Example of Noise Problem

```
Time    Price       Momentum (5s lookback)
0s      $100.00     —
5s      $100.05     +0.05%
6s      $100.03     +0.03% (price dipped, momentum dropped)
7s      $100.08     +0.03% (comparing to noisy $100.05)
8s      $100.10     +0.05% (comparing to noisy $100.05)
```

The single-point reference at 5s ago creates instability.

---

## Option 1: Smoothed ROC (Average-Based)

### Concept

Instead of comparing current price to a single historical point, compare to the **average price** over the lookback window.

### Formula

```
avg_price = mean(all prices in last N seconds)
momentum % = ((current_price - avg_price) / avg_price) × 100
```

### Implementation Sketch

```python
def calculate_momentum_smoothed(current_price, price_history, lookback_seconds):
    now = datetime.now()
    prices_in_window = []

    for point in price_history:
        age = (now - point["time"]).total_seconds()
        if age <= lookback_seconds:
            prices_in_window.append(point["price"])
        else:
            break  # History is chronological, can stop early

    if not prices_in_window:
        return None

    avg_price = sum(prices_in_window) / len(prices_in_window)
    return (current_price - avg_price) / avg_price * 100
```

### Pros

- **Much less noisy** - Single outlier tick doesn't dominate
- **Simple change** - Minimal code modification
- **Still interpretable** - "Price is X% above/below recent average"

### Cons

- **Slightly lagging** - Average includes older prices
- **Center-weighted** - Treats all prices in window equally

### Tuning Parameters

| Parameter | Range | Notes |
|-----------|-------|-------|
| Window size | 3-30 seconds | Larger = smoother but more lag |

---

## Option 2: EMA-Based Momentum

### Concept

Use an Exponential Moving Average (EMA) as the reference point. EMA gives more weight to recent prices, making it more responsive than a simple average.

### Formula

```
EMA_today = (Price_today × k) + (EMA_yesterday × (1 - k))
where k = 2 / (N + 1)

momentum % = ((current_price - EMA) / EMA) × 100
```

### Implementation Sketch

```python
def calculate_ema(prices, span):
    """Calculate EMA with given span (number of periods)."""
    k = 2 / (span + 1)
    ema = prices[0]
    for price in prices[1:]:
        ema = (price * k) + (ema * (1 - k))
    return ema

def calculate_momentum_ema(current_price, price_history, span=10):
    prices = [p["price"] for p in reversed(price_history)]
    if len(prices) < span:
        return None

    ema = calculate_ema(prices, span)
    return (current_price - ema) / ema * 100
```

### Pros

- **Industry standard** - Traders understand EMA
- **Responsive yet smooth** - Recent prices weighted more
- **Well-studied** - Known behavior and tuning guidelines

### Cons

- **Span tuning required** - Need to find right balance
- **Less intuitive** - "X% from EMA" less clear than "X% change"

### Tuning Parameters

| Parameter | Range | Notes |
|-----------|-------|-------|
| Span | 5-20 periods | Lower = more responsive, higher = smoother |

### EMA Span Guidelines

| Span | Character | Use Case |
|------|-----------|----------|
| 5 | Very responsive | Scalping, high volatility |
| 10 | Balanced | Default recommendation |
| 20 | Smooth | Trend following, calmer markets |

---

## Option 3: Multi-Timeframe Composite

### Concept

Calculate momentum over multiple timeframes and combine them into a weighted score. This captures both immediate moves and underlying trend.

### Formula

```
short_mom  = ROC(5 seconds)   × weight_short
medium_mom = ROC(30 seconds)  × weight_medium
long_mom   = ROC(60 seconds)  × weight_long

composite = short_mom + medium_mom + long_mom
```

### Implementation Sketch

```python
def calculate_momentum_composite(current_price, price_history, weights=None):
    if weights is None:
        weights = {
            5: 0.2,   # Short-term: 20%
            30: 0.5,  # Medium-term: 50%
            60: 0.3,  # Long-term: 30%
        }

    composite = 0
    for timeframe, weight in weights.items():
        mom = calculate_single_roc(current_price, price_history, timeframe)
        if mom is not None:
            composite += mom * weight

    return composite
```

### Pros

- **Rich signal** - Captures multiple dimensions of momentum
- **Trend-aware** - Long timeframe provides context
- **Configurable** - Weights can be tuned per strategy

### Cons

- **More complex** - Harder to understand at a glance
- **Multiple parameters** - Three timeframes + three weights
- **Interpretation** - "Composite score" less intuitive than "% change"

### Tuning Parameters

| Parameter | Range | Notes |
|-----------|-------|-------|
| Short timeframe | 3-10s | Immediate reactivity |
| Medium timeframe | 15-60s | Core signal |
| Long timeframe | 60-300s | Trend context |
| Weight distribution | Various | Sum should = 1.0 |

### Recommended Weight Presets

| Preset | Short | Medium | Long | Use Case |
|--------|-------|--------|------|----------|
| **Scalping** | 0.4 | 0.4 | 0.2 | Quick entries, less trend |
| **Balanced** | 0.2 | 0.5 | 0.3 | Default |
| **Trend** | 0.1 | 0.3 | 0.6 | Ride larger moves |

---

## Option 4: Velocity + Acceleration

### Concept

Instead of just showing where price is relative to the past, show:
1. **Velocity** - How fast price is moving (current momentum)
2. **Acceleration** - Is momentum increasing or decreasing?

This is predictive: rising acceleration suggests momentum will continue.

### Formula

```
velocity = ROC(current, 5s ago)
previous_velocity = ROC(5s ago, 10s ago)
acceleration = velocity - previous_velocity
```

### Implementation Sketch

```python
def calculate_velocity_acceleration(current_price, price_history, timeframe=5):
    # Current velocity
    price_5s_ago = get_price_at(price_history, timeframe)
    price_10s_ago = get_price_at(price_history, timeframe * 2)

    if price_5s_ago is None or price_10s_ago is None:
        return None, None

    velocity = (current_price - price_5s_ago) / price_5s_ago * 100
    prev_velocity = (price_5s_ago - price_10s_ago) / price_10s_ago * 100
    acceleration = velocity - prev_velocity

    return velocity, acceleration
```

### Display Options

```
# Option A: Two separate values
Velocity: +0.05%  Accel: +0.02%

# Option B: Combined indicator
+0.05% ↑↑  (momentum rising)
+0.05% ↑↓  (momentum fading)
-0.03% ↓↓  (momentum falling, accelerating down)
```

### Pros

- **Predictive** - Acceleration indicates if move is strengthening/weakening
- **Earlier signals** - Detect momentum building before it peaks
- **Richer information** - Two dimensions vs one

### Cons

- **Two numbers** - More cognitive load for user
- **Display complexity** - Need to design clear visualization
- **More noise** - Acceleration is derivative, amplifies noise

### Tuning Parameters

| Parameter | Range | Notes |
|-----------|-------|-------|
| Velocity timeframe | 3-10s | Base momentum calculation |
| Smoothing | Optional | May need smoothing on acceleration |

---

## Comparison Matrix

| Method | Noise Reduction | Responsiveness | Interpretability | Complexity |
|--------|-----------------|----------------|------------------|------------|
| **Current (Single ROC)** | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ |
| **Smoothed ROC** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| **EMA-Based** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| **Multi-Timeframe** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| **Velocity + Accel** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |

### Initial Recommendation

**Start with Smoothed ROC** - It provides the best improvement with minimal complexity:

1. Significant noise reduction
2. Simple code change
3. Still interpretable to users
4. Can be enhanced later with EMA or multi-timeframe if needed

---

## Decision

> **Decision Date:** January 20, 2026
> **Status:** Approved
> **Full Details:** [Scalper's Momentum Decision](../Team/Scalper/momentum-decision.md)

**Selected:** Hybrid Velocity + Acceleration with Smoothed Base

The Scalper chose a hybrid approach combining smoothed ROC for noise reduction with acceleration as a trade quality filter. The key insight: entering fading moves is more costly than noise itself.

See the [full decision document](../Team/Scalper/momentum-decision.md) for:
- Detailed rationale and rejection reasons for other options
- Implementation code and trade entry logic
- Parameters and tuning guidelines
- Phased implementation plan

---

## Testing Approach

### Metrics to Compare

1. **Signal stability** - How often does momentum flip sign without price trend change?
2. **Lag measurement** - Time between price move start and momentum detection
3. **False signal rate** - Trades triggered that immediately reverse
4. **Win rate impact** - A/B test with paper trading

### Test Scenarios

| Scenario | Expected Behavior |
|----------|-------------------|
| Steady trend up | Consistent positive momentum |
| Steady trend down | Consistent negative momentum |
| Choppy/sideways | Near-zero, stable (not flipping) |
| Sharp spike then reversal | Quick detection, not fooled by single tick |
| Gradual acceleration | Increasing momentum values |

---

## References

- [Investopedia: Rate of Change (ROC)](https://www.investopedia.com/terms/r/rateofchange.asp)
- [Investopedia: Exponential Moving Average](https://www.investopedia.com/terms/e/ema.asp)
- [TradingView: Momentum Indicator](https://www.tradingview.com/support/solutions/43000502344-momentum/)

---

*Document maintained as part of trading-bot strategy research.*
