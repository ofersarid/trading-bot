# Discussion Summary: Strategies Folder Architecture

**Date:** 2026-01-25
**Persona:** Alex Chen (CTO)
**Type:** Architecture Consultation

---

## Topics Discussed

1. Proposal to create a `bot/strategies/` folder mirroring the `indicators/` and `signals/` pattern
2. Current state of `bot/ai/strategies.py` (436 lines, doing too much)
3. Where strategy prompts should live (with strategy vs. separate in AI module)

---

## Key Recommendations

### High Priority
- [ ] Create `bot/strategies/` folder with one file per strategy
- [ ] Move `Strategy`, `RiskConfig`, `StrategyType` to `bot/strategies/base.py`
- [ ] Keep strategy prompts inside each strategy file (self-contained)

### Medium Priority
- [ ] Move `AI_TRADING_PROMPT` wrapper template to `bot/ai/prompts.py`
- [ ] Update `system_architecture.md` to reflect new structure

---

## Technical Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Create `bot/strategies/` folder | Consistency with indicators/signals pattern; scalability | New folder structure |
| Prompts live inside strategy files | The prompt IS the strategy - defines trading philosophy | Self-contained strategy definitions |
| `AI_TRADING_PROMPT` stays in `bot/ai/` | It's generic infrastructure for formatting market data | Clean separation of concerns |

---

## Implementation Guidance

*These are recommendations for implementation - the CTO does not implement, only advises.*

| Area/Component | What Needs to Be Done | Priority |
|----------------|----------------------|----------|
| `bot/strategies/` | Create folder with `__init__.py`, `base.py`, README.md | P0 |
| `bot/strategies/base.py` | Move `Strategy`, `RiskConfig`, `StrategyType` dataclasses | P0 |
| `bot/strategies/*.py` | Create `momentum_scalper.py`, `trend_follower.py`, `mean_reversion.py`, `conservative.py` | P0 |
| `bot/ai/prompts.py` | Move `AI_TRADING_PROMPT` and `format_ai_trading_prompt()` | P1 |
| `bot/ai/signal_brain.py` | Update imports to use `bot.strategies` | P1 |
| `bot/ai/scalper_interpreter.py` | Update imports | P1 |
| `bot/ai/strategies.py` | Delete after migration | P1 |
| `docs/PRDs/system_architecture.md` | Add strategies folder to directory structure, remove personas reference | P2 |

---

## Proposed Structure

```
bot/strategies/
├── __init__.py               # Registry, get_strategy(), list_strategies()
├── base.py                   # Strategy, RiskConfig, StrategyType
├── momentum_scalper.py       # Momentum scalper strategy + prompt
├── trend_follower.py         # Trend follower strategy + prompt
├── mean_reversion.py         # Mean reversion strategy + prompt
├── conservative.py           # Conservative strategy + prompt
└── README.md                 # How to add custom strategies
```

---

## Open Questions

- [ ] None - approach is clear

---

## Next Steps

1. Switch to regular agent session to implement the migration
2. Create the folder structure and split the files
3. Update all imports
4. Delete old `bot/ai/strategies.py`
5. Update architecture documentation

---

## References

- `bot/ai/strategies.py` - Current implementation (to be split)
- `bot/ai/signal_brain.py` - Consumer of strategies
- `docs/PRDs/system_architecture.md` - Architecture documentation to update
