# Momentum Calculation: Scalper's Decision

> **Decision Date:** January 20, 2026
> **Status:** Approved
> **Rationale:** Scalping strategy expert review
> **Related:** [Momentum Calculation Methods](../../strategies/momentum-calculation-methods.md)

---

## Selected Approach: Hybrid Velocity + Acceleration with Smoothed Base

After reviewing all options, the selected approach is a **hybrid method** combining:
1. Smoothed ROC for the base velocity calculation (noise reduction)
2. Acceleration as a trade quality filter (predictive power)

---

## Why This Combination

The core insight: **noise isn't the main enemy - entering fading moves is.**

Same momentum reading can represent two completely different situations:

| Scenario | Velocity | Acceleration | Trade Quality |
|----------|----------|--------------|---------------|
| Building move | +0.05% | +0.02% | High - move has legs |
| Fading move | +0.05% | -0.03% | Low - about to reverse |

Pure smoothing reduces noise but doesn't distinguish between these cases.
Acceleration provides the predictive signal we need.

---

## Why Not Pure Options

| Option | Rejection Reason |
|--------|------------------|
| Smoothed ROC alone | Solves noise but still enters dying moves |
| EMA-Based | Trend signal, not momentum signal; slow to stabilize |
| Multi-Timeframe | Too slow for sub-minute scalping; enter late |
| Raw Velocity + Accel | Acceleration amplifies noise without smoothed base |

---

## Implementation Details

### Trade Entry Logic

```python
def should_trade(smoothed_velocity, acceleration, threshold):
    """
    Only trade moves that are both strong AND building.

    Args:
        smoothed_velocity: Current momentum % (smoothed)
        acceleration: Rate of change of velocity
        threshold: Minimum momentum to consider

    Returns:
        True if trade criteria met
    """
    return abs(smoothed_velocity) >= threshold and acceleration >= 0
```

### Display Strategy

Keep UI simple - show one number (smoothed velocity), use acceleration internally:

| What User Sees | What System Uses |
|----------------|------------------|
| Momentum: +0.05% | velocity=+0.05%, accel=+0.02% → TRADE |
| Momentum: +0.05% | velocity=+0.05%, accel=-0.03% → SKIP |

Users don't need to understand acceleration. They just see fewer bad trades.

---

## Expected Benefits

| Metric | Expected Impact |
|--------|-----------------|
| Signal stability | Improved (smoothed base) |
| False signals | Reduced (acceleration filter) |
| Late entries | Same (no additional lag) |
| Win rate | Improved (filtering fading moves) |

---

## Parameters

| Parameter | Default | Range | Notes |
|-----------|---------|-------|-------|
| Velocity window | 5 seconds | 3-10s | Smoothing window for velocity |
| Acceleration window | 5 seconds | 3-10s | Period for measuring velocity change |
| Acceleration threshold | 0 | -0.01 to +0.01 | Minimum acceleration to allow trade |

---

## Implementation Phases

### Phase 1: Smoothed Velocity
1. Update `calculate_momentum()` to return smoothed velocity
2. Verify stability improvement
3. No behavior change yet (just better numbers)

### Phase 2: Add Acceleration Filter
1. Add `calculate_acceleration()` function
2. Modify trade entry logic to require acceleration ≥ 0
3. Log filtered trades for analysis

### Phase 3: Tune & Validate
1. Paper trade with new logic
2. Compare win rate vs. previous approach
3. Tune acceleration threshold if needed

---

*Decision by Scalper - see [full analysis](../../strategies/momentum-calculation-methods.md) for all options considered.*
