# Prompts Architecture Consolidation

**Date:** 2026-01-20
**Type:** Architecture Review
**Status:** Recommendation

## Context

Question raised: Should different strategies have different prompts? Review of `prompts.py` vs `strategies.py` architecture.

## Findings

### Current State - Two Prompt Systems

| File | Purpose | Strategy-Aware? |
|------|---------|-----------------|
| `strategies.py` | Main trading decisions via `AI_TRADING_PROMPT` | ✅ Yes - injects `{strategy_prompt}` |
| `prompts.py` | Entry/exit analysis via `ENTRY_ANALYSIS_PROMPT`, `EXIT_ANALYSIS_PROMPT` | ❌ No - completely generic |

### The Problem

In `analyzer.py`:
- `make_decision()` uses `format_ai_trading_prompt()` - **strategy-aware**
- `should_enter()` uses `format_entry_analysis()` - **NOT strategy-aware**
- `should_exit()` uses `format_exit_analysis()` - **NOT strategy-aware**

A momentum scalper and conservative trader would receive identical entry/exit prompts - this is architecturally incorrect.

### Root Cause

`prompts.py` is legacy from the hybrid rule-based + AI architecture:
- Rule-based system detected opportunities → AI confirmed entry
- Rule-based system signaled exits → AI confirmed exit

With AI-only trading, this flow is obsolete.

## Recommendation

### Deprecate `prompts.py`

The AI-only flow uses `make_decision()` exclusively:

```
Market Data → AI_TRADING_PROMPT (with strategy) → ACTION: LONG/SHORT/EXIT/NONE
```

No separate entry/exit confirmation needed.

### Clean Up `analyzer.py`

Remove unused methods:
- `should_enter()` - not used in AI-only path
- `should_exit()` - not used in AI-only path
- `analyze_market()` - replaced by `make_decision()`

### Keep for Future Use (Optional)

- `QUICK_SENTIMENT_PROMPT` - useful for fast market checks
- `format_quick_sentiment()` - lightweight sentiment polling

## Action Items

- [ ] Verify `should_enter()` and `should_exit()` are not called in AI-only mode
- [ ] Consider adding deprecation comments to `prompts.py`
- [ ] Future cleanup: Remove dead code from `analyzer.py`
- [ ] Future cleanup: Delete or minimize `prompts.py`

## Impact on Current Work

**No change needed to momentum upgrade plan.** The plan correctly targets `strategies.py` which is the active code path for AI-only trading.

## References

- `bot/ai/prompts.py` - Legacy prompts (to deprecate)
- `bot/ai/strategies.py` - Active strategy system
- `bot/ai/analyzer.py` - MarketAnalyzer with both old and new methods
