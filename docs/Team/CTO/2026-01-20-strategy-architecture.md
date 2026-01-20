# Strategy Architecture for Multi-Strategy Support

**Date:** 2026-01-20
**Type:** Architecture Review
**Status:** Recommendation (Future Work)

## Context

Question raised: How should `strategies.py` be structured to support multiple trading strategies? Currently focusing on momentum scalper, but planning to add more strategies.

## Current Architecture

**Prompt-only strategies:**
```python
STRATEGY_PROMPTS = {
    TradingStrategy.MOMENTUM_SCALPER: "You are an aggressive momentum scalper...",
    TradingStrategy.TREND_FOLLOWER: "You are a patient trend follower...",
}
```

### Problems with Current Approach

| Aspect | Current | Issue |
|--------|---------|-------|
| Data requirements | Same for all | Scalper needs acceleration; trend follower needs HTF |
| Risk parameters | Global (TradingConfig) | Different strategies need different risk profiles |
| Timeframes | Single global setting | Scalper: 5s, Trend follower: 60s |
| Prompt | Strategy-specific | ✅ This works |

## Recommended Architecture

### Strategy as Configuration Object

```python
@dataclass(frozen=True)
class StrategyConfig:
    """Complete strategy definition - prompt + parameters."""

    name: str
    strategy_type: TradingStrategyType

    # AI Behavior
    prompt: str

    # Data Requirements
    momentum_timeframe_seconds: int = 5
    include_acceleration: bool = False
    include_htf_trend: bool = False

    # Risk Parameters
    position_size_pct: float = 0.10
    take_profit_pct: float = 0.10
    stop_loss_pct: float = 0.05
    max_positions: int = 2

    # Trading Behavior
    min_confidence: int = 6
    cooldown_seconds: float = 30.0


STRATEGIES: dict[TradingStrategyType, StrategyConfig] = {
    TradingStrategyType.MOMENTUM_SCALPER: StrategyConfig(
        name="Momentum Scalper",
        strategy_type=TradingStrategyType.MOMENTUM_SCALPER,
        prompt="...",
        momentum_timeframe_seconds=5,
        include_acceleration=True,
        position_size_pct=0.08,
        take_profit_pct=0.08,
        stop_loss_pct=0.04,
    ),
    TradingStrategyType.TREND_FOLLOWER: StrategyConfig(
        name="Trend Follower",
        strategy_type=TradingStrategyType.TREND_FOLLOWER,
        prompt="...",
        momentum_timeframe_seconds=60,
        include_htf_trend=True,
        position_size_pct=0.15,
        take_profit_pct=0.20,
        stop_loss_pct=0.08,
    ),
}
```

### Example Strategy Configurations

| Strategy | Timeframe | Acceleration | Position Size | TP/SL | Cooldown |
|----------|-----------|--------------|---------------|-------|----------|
| Momentum Scalper | 5s | Yes | 8% | 8%/4% | 15s |
| Trend Follower | 60s | No (uses HTF) | 15% | 20%/8% | 120s |
| Mean Reversion | 30s | No | 5% | 10%/3% | 60s |
| Conservative | 60s | No | 5% | 15%/5% | 180s |

## Migration Path

### Phase 1: Current (Momentum Scalper Focus)
- Keep current prompt-only architecture
- Add acceleration as parameter to `format_ai_trading_prompt()`
- Focus on making one strategy work well

### Phase 2: After Momentum Scalper Works
- Create `StrategyConfig` dataclass
- Migrate `STRATEGY_PROMPTS` to `STRATEGIES` registry
- Update dashboard to use `strategy.position_size_pct`, etc.
- Update prompt formatting to include strategy-specific data

### Phase 3: Advanced Features (Future)
- Strategy hot-swapping without restart
- A/B testing between strategies
- User-defined strategies via YAML/JSON
- Strategy performance comparison reports

## Action Items

- [ ] **NOW**: Add acceleration to `format_ai_trading_prompt()` as parameter
- [ ] **NOW**: Keep strategy prompt as single source of strategy behavior
- [ ] **LATER**: Refactor to `StrategyConfig` when adding second strategy
- [ ] **LATER**: Move risk parameters from `TradingConfig` to `StrategyConfig`

## Key Principle

**Don't refactor prematurely.** The prompt-only approach works for a single strategy. Refactor to `StrategyConfig` only when you have two working strategies that need different configurations.

## References

- `bot/ai/strategies.py` - Current strategy definitions
- `bot/core/config.py` - TradingConfig (currently global)
- `docs/PRDs/system_architecture.md` - Section 11.3 mentions strategy switching
