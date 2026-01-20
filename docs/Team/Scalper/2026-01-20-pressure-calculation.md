# Pressure Calculation for Scalping

**Date:** 2026-01-20
**Type:** Strategy Evaluation
**Status:** Recommendation

## Context

Question raised: How should market pressure be calculated? Should it be based on buy/sell volume?

Review of current implementation in `bot/core/models.py` - `MarketPressure` class.

## Analysis

### Current Implementation Problems

| Component | Current | Issue |
|-----------|---------|-------|
| Order Book (40%) | Volume-weighted | ✅ OK |
| Trade Flow (40%) | **Count-based** | ❌ Counts trades, ignores size |
| Momentum (20%) | Direction alignment | ⚠️ Irrelevant for scalping |

**Critical flaw:** Trade flow counts trades instead of weighting by volume.
- 50 small buys = "strong buying"
- 1 whale dump = barely registers
- Result: Misleading pressure readings

### Why Volume-Weighted Tape Reading Matters

For scalping, what matters is **aggressive volume** - who's hitting the tape:
- Executed trades = real money, can't be faked
- Order book = intentions, easily spoofed by market makers
- Trade count = misleading, doesn't reflect actual flow

### Recommended Pressure Formula

| Component | Weight | Measurement |
|-----------|--------|-------------|
| **Tape Pressure** | 50% | `buy_volume / total_volume` from executed trades |
| **Book Imbalance** | 30% | `bid_volume / total_volume` from top 5 levels |
| **Delta Trend** | 20% | Is buy volume accelerating or fading? |

## Key Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| Tape weight | 50% | Executed trades are truth |
| Book weight | 30% | Passive orders, can be spoofed |
| Delta weight | 20% | Momentum of the momentum |
| Trade window | Last 20 trades | Adjust based on volatility |

## Implementation

```python
def calculate_pressure(recent_trades: list, orderbook: dict) -> float:
    # 1. TAPE PRESSURE (50%) - Volume-weighted executed trades
    buy_vol = sum(float(t.get("sz", 0)) for t in recent_trades if t.get("side") == "buy")
    sell_vol = sum(float(t.get("sz", 0)) for t in recent_trades if t.get("side") == "sell")
    total_tape = buy_vol + sell_vol
    tape_score = (buy_vol / total_tape * 100) if total_tape > 0 else 50

    # 2. BOOK IMBALANCE (30%) - Passive orders
    bid_vol = sum(float(b.get("sz", 0)) for b in orderbook.get("bids", [])[:5])
    ask_vol = sum(float(a.get("sz", 0)) for a in orderbook.get("asks", [])[:5])
    total_book = bid_vol + ask_vol
    book_score = (bid_vol / total_book * 100) if total_book > 0 else 50

    # 3. DELTA TREND (20%) - Is buying accelerating or fading?
    mid = len(recent_trades) // 2
    early_buys = sum(float(t.get("sz", 0)) for t in recent_trades[mid:] if t.get("side") == "buy")
    recent_buys = sum(float(t.get("sz", 0)) for t in recent_trades[:mid] if t.get("side") == "buy")

    if early_buys > 0:
        delta_ratio = recent_buys / early_buys
        delta_score = min(100, max(0, delta_ratio * 50))
    else:
        delta_score = 50

    return tape_score * 0.50 + book_score * 0.30 + delta_score * 0.20
```

## Rules Summary

1. **Tape > Book**: Executed trades are real, order book can be spoofed
2. **Volume > Count**: One whale trade matters more than 50 retail trades
3. **Trend matters**: Accelerating pressure is stronger than static pressure

## Action Items

- [ ] Update `MarketPressure.calculate()` to use volume-weighted trade flow
- [ ] Remove or reduce momentum alignment component
- [ ] Add delta trend component (pressure acceleration)
- [ ] Update AI prompts to explain what pressure means

## References

- `bot/core/models.py` - MarketPressure class (lines 137-270)
- Tape reading is standard institutional trading practice
