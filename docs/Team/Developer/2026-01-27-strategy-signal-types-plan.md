# Implementation Plan: Strategy-Specific Signal Types

**Spec Source:** CTO Discussion (Jan 27, 2026)
**Created:** 2026-01-27
**Developer:** Sam Rivera

---

## Overview

Each trading strategy should explicitly define which signal types it considers relevant. This prevents AI confusion from seeing irrelevant signals and makes strategy design more intentional.

**Example:** A momentum_scalper should focus on MOMENTUM and VOLUME_PROFILE signals, while a mean_reversion strategy should focus on RSI signals.

---

## Prerequisites

- [ ] Understand current SignalType enum values: `MOMENTUM`, `RSI`, `MACD`, `VOLUME_PROFILE`
- [ ] Review each strategy's trading philosophy to map appropriate signals

---

## Implementation Phases

### Phase 1: Core Infrastructure

**Goal:** Add `signal_types` field to Strategy dataclass

**Tasks:**

- [ ] **Task 1.1**: Import SignalType in base.py
  - File: `bot/strategies/base.py`
  - Change: Add `from bot.signals.base import SignalType` import

- [ ] **Task 1.2**: Add signal_types field to Strategy dataclass
  - File: `bot/strategies/base.py`
  - Change: Add field with default that includes all types (backwards compatible)
  ```python
  signal_types: list[SignalType] = field(
      default_factory=lambda: list(SignalType)
  )
  ```

**Verification:**
- [ ] Existing strategies still work (default includes all signals)
- [ ] No import errors

---

### Phase 2: Update SignalBrain Filtering

**Goal:** Filter signals by type based on strategy configuration

**Tasks:**

- [ ] **Task 2.1**: Update _filter_signals() method
  - File: `bot/ai/signal_brain.py`
  - Change: Add signal type check in the filter loop
  ```python
  # In _filter_signals():
  if signal.signal_type not in self.strategy.signal_types:
      continue
  ```

- [ ] **Task 2.2**: Add debug logging for filtered signals
  - File: `bot/ai/signal_brain.py`
  - Change: Log when signals are filtered out by type (at DEBUG level)

**Verification:**
- [ ] Run backtest with default strategy - should see all signals
- [ ] Confirm filtering logs appear at DEBUG level

---

### Phase 3: Update Strategy Definitions

**Goal:** Configure each strategy with appropriate signal types

**Tasks:**

- [ ] **Task 3.1**: Update momentum_scalper
  - File: `bot/strategies/momentum_scalper.py`
  - Signal Types: `[MOMENTUM, VOLUME_PROFILE]`
  - Rationale: Focus on momentum moves, VP for support/resistance levels
  - Prompt Addition: "You focus on MOMENTUM and VOLUME_PROFILE signals. RSI and MACD signals are not relevant to quick scalping."

- [ ] **Task 3.2**: Update trend_follower
  - File: `bot/strategies/trend_follower.py`
  - Signal Types: `[MOMENTUM, MACD]`
  - Rationale: MACD for trend confirmation, momentum for direction
  - Prompt Addition: "You focus on MOMENTUM and MACD signals for trend confirmation."

- [ ] **Task 3.3**: Update mean_reversion
  - File: `bot/strategies/mean_reversion.py`
  - Signal Types: `[RSI, VOLUME_PROFILE]`
  - Rationale: RSI for overbought/oversold, VP for mean levels
  - Prompt Addition: "You focus on RSI signals for overbought/oversold conditions and VOLUME_PROFILE for identifying mean price levels."

- [ ] **Task 3.4**: Update conservative
  - File: `bot/strategies/conservative.py`
  - Signal Types: `[MOMENTUM, RSI, MACD]` (all except VP)
  - Rationale: Conservative uses all standard signals for consensus
  - Prompt Addition: "You require confluence from MOMENTUM, RSI, and MACD signals before acting."

**Verification:**
- [ ] Each strategy imports SignalType
- [ ] Each strategy has explicit signal_types list
- [ ] Each strategy prompt mentions which signals it uses

---

### Phase 4: Update __init__.py Exports

**Goal:** Export SignalType for strategy customization

**Tasks:**

- [ ] **Task 4.1**: Export SignalType from strategies module
  - File: `bot/strategies/__init__.py`
  - Change: Add SignalType to imports and __all__
  ```python
  from bot.signals.base import SignalType
  # ...
  __all__ = [
      # ...
      "SignalType",
  ]
  ```

**Verification:**
- [ ] Can do `from bot.strategies import SignalType`
- [ ] Custom strategies can define signal_types

---

### Phase 5: (Optional) Backtest Engine Optimization

**Goal:** Only instantiate detectors needed by the strategy

**Tasks:**

- [ ] **Task 5.1**: Use strategy signal_types to filter detectors
  - File: `bot/backtest/engine.py`
  - Change: In `_init_detectors()`, check if detector's signal type is in strategy's list
  - Note: This is optional - performance optimization only

**Verification:**
- [ ] Backtest with momentum_scalper only runs momentum + VP detectors
- [ ] No change in results (just faster execution)

---

## Files Changed Summary

| File | Action | Phase |
|------|--------|-------|
| `bot/strategies/base.py` | UPDATE | 1 |
| `bot/ai/signal_brain.py` | UPDATE | 2 |
| `bot/strategies/momentum_scalper.py` | UPDATE | 3 |
| `bot/strategies/trend_follower.py` | UPDATE | 3 |
| `bot/strategies/mean_reversion.py` | UPDATE | 3 |
| `bot/strategies/conservative.py` | UPDATE | 3 |
| `bot/strategies/__init__.py` | UPDATE | 4 |
| `bot/backtest/engine.py` | UPDATE | 5 (optional) |

---

## Signal Type Mapping Reference

| Strategy | Signal Types | Rationale |
|----------|--------------|-----------|
| **momentum_scalper** | MOMENTUM, VOLUME_PROFILE | Quick momentum + VP support/resistance |
| **trend_follower** | MOMENTUM, MACD | Trend direction + MACD confirmation |
| **mean_reversion** | RSI, VOLUME_PROFILE | Overbought/oversold + mean price levels |
| **conservative** | MOMENTUM, RSI, MACD | All standard signals for consensus |

---

## Testing Strategy

- [ ] Unit test: `Strategy` accepts `signal_types` field
- [ ] Unit test: `SignalBrain._filter_signals()` filters by type
- [ ] Integration test: Run backtest with each strategy, verify only relevant signals are processed
- [ ] Manual: Check AI prompts include signal focus language

---

## Rollback Plan

If issues arise:
1. Revert `signal_types` field to default that includes all types
2. Remove type check from `_filter_signals()` (one line change)
3. Keep prompt updates (they're additive and helpful regardless)

---

## Open Questions

- [ ] Should PREV_DAY_VP get its own SignalType or stay under VOLUME_PROFILE?
  - Current: Uses VOLUME_PROFILE (both are VP-based concepts)
  - Recommendation: Keep as VOLUME_PROFILE for now, separate later if needed

- [ ] Should strategies be able to opt-out of VP even if trade data is provided?
  - Current: VP runs if trade data exists
  - Recommendation: Defer - current approach is fine

---

## Notes for Implementation

1. **Backwards Compatibility**: Default `signal_types` includes all types, so existing code works
2. **Import Cycle**: Import SignalType from `bot.signals.base`, not `bot.signals` to avoid cycles
3. **Prompt Language**: Use exact signal type names in prompts for clarity to the AI
