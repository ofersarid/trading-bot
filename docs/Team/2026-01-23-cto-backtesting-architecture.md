# Discussion Summary: Backtesting Architecture Design

**Date:** 2026-01-23
**Persona:** Alex Chen (CTO)
**Type:** Architecture Consultation

---

## Topics Discussed

1. Backtesting requirements for running historical data faster than real-time
2. AI response time concerns and optimization strategies
3. OHLCV candle data configuration (already supported)
4. Volume data per candle (already supported)
5. Proposed indicators module for pure math calculations
6. Refined 3-layer architecture: Indicators → Signals → AI Brain

---

## Key Recommendations

### High Priority
- [ ] Create `bot/indicators/` module with pure math functions (SMA, EMA, RSI, MACD, ATR)
- [ ] Create `bot/signals/` module with pattern detectors that use indicators
- [ ] Refactor AI role from "validator" to "decision maker" that weighs multiple signals across instruments

### Medium Priority
- [ ] Create `bot/ai/personas/` with different trading styles (Scalper, Conservative, etc.)
- [ ] Build `bot/backtest/engine.py` that orchestrates the 3-layer architecture
- [ ] Add signal aggregator to batch signals by time window before AI evaluation

### Nice to Have
- [ ] AI response caching for similar market conditions
- [ ] Use smaller model (phi3:mini) for faster backtesting
- [ ] Multi-instrument backtesting with merged candle streams

---

## Technical Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| 3-layer architecture (Indicators → Signals → AI) | Clear separation of concerns; each layer has single responsibility | Enables independent testing, composability, and A/B testing of strategies |
| AI as "brain" not "validator" | AI should make judgment calls, not rubber-stamp rule-based decisions | Better use of AI capabilities; more sophisticated position management |
| Indicators are stateless pure functions | Predictable, testable, fast execution | Sub-millisecond indicator calculation |
| Signals are deterministic pattern detectors | Reproducible backtests; AI only called when signals exist | Reduces AI calls from 240 to ~20 for 4-hour backtest |
| Persona-driven AI decisions | Different trading styles can be A/B tested with same signal input | Strategy optimization without code changes |

---

## Code Changes Suggested

| File/Component | Change | Priority |
|----------------|--------|----------|
| `bot/indicators/` (new) | Create module with SMA, EMA, RSI, MACD, ATR functions | P0 |
| `bot/signals/` (new) | Create SignalDetector and SignalStrategy classes | P0 |
| `bot/ai/personas/` (new) | Create TradingPersona dataclass and persona definitions | P1 |
| `bot/backtest/engine.py` (new) | Create BacktestEngine with multi-instrument support | P1 |
| `bot/simulation/opportunity_seeker.py` | Refactor to use new Signals architecture or deprecate | P2 |

---

## Architecture Overview

```
Indicators (Tools) - Pure math, stateless
    ├── SMA, EMA
    ├── RSI
    ├── MACD
    └── ATR

Signals (Pattern Detectors) - Stateful, deterministic
    ├── Detects patterns using indicators
    ├── One detector per coin
    └── Outputs Signal objects with metadata

AI Brain (Decision Maker) - Judgment, persona-driven
    ├── Receives signals from all coins
    ├── Weighs probability based on persona
    └── Outputs TradePlan (entry, size, SL, TP, trailing)
```

---

## Estimated Backtest Performance

| Configuration | Time for 4-hour (240 candles) |
|---------------|-------------------------------|
| Rule-based only (Indicators + Signals) | <1 second |
| AI on signals (~20 signals) | ~40-60 seconds |
| AI every candle | ~8 minutes |

---

## Open Questions

- [ ] What signal strategies to implement first? (Momentum, RSI oversold/overbought, MACD crossover?)
- [ ] Should trailing stops be managed by AI or by a separate position manager?
- [ ] How to handle conflicting signals (e.g., BTC long signal + ETH short signal simultaneously)?

---

## Next Steps

1. Implement `bot/indicators/` module with core indicators
2. Implement `bot/signals/` module with 2-3 signal strategies
3. Create scalper persona in `bot/ai/personas/scalper.py`
4. Build backtest engine that ties everything together
5. Run comparative backtest: rule-based vs AI-enhanced

---

## References

- `docs/PRDs/system_architecture.md` - Current system design
- `docs/PRDs/local_ai_integration.md` - AI integration specs
- `bot/simulation/run_simulator.py` - Existing historical replay (rule-based only)
- `bot/historical/` - Historical data fetcher and models
- `bot/ai/personas/scalper.py` - Existing scalper persona (needs refactor)
