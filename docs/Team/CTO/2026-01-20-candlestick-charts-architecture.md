# Candlestick Charts Architecture

**Date:** 2026-01-20
**Type:** Architecture Decision
**Status:** Implemented

## Context

Request to add 1-minute candlestick charts under each trading coin in the dashboard. The implementation needed to be flexible to support any number of coins dynamically.

## Constraint

The current dashboard is built with **Textual** - a Python terminal UI (TUI) framework. This means:
- ❌ No HTML Canvas - That's a browser technology
- ❌ No TradingView/Highcharts - Web libraries won't work
- ❌ No pixel-perfect graphics - Terminal cells only

## Decision

Use **Plotext** for terminal-native candlestick visualization.

### Why Plotext

| Criteria | Assessment |
|----------|------------|
| Terminal-native | ✅ Designed for terminal output |
| Candlestick support | ✅ Built-in `plt.candlestick()` |
| Textual compatible | ✅ Output captured via `plt.build()` |
| Lightweight | ✅ ~200KB |
| Installation | ✅ `pip install plotext` |

### Alternatives Considered

1. **Custom Unicode rendering** - More work, less features
2. **Web dashboard hybrid** - Larger architectural change, better for later
3. **asciichartpy** - No candlestick support

## Implementation

### New Files

| File | Purpose |
|------|---------|
| `bot/core/candle_aggregator.py` | Aggregates price ticks into 1-minute OHLC candles |
| `bot/ui/components/charts_panel.py` | Candlestick chart widgets using plotext |

### Key Components

**CandleAggregator** - Converts streaming price data to candles:
```python
class CandleAggregator:
    def add_tick(self, price: float, volume: float = 0) -> Candle | None:
        # Returns completed candle when minute boundary crossed
```

**MultiCoinCandleManager** - Manages aggregators for all coins:
```python
class MultiCoinCandleManager:
    def __init__(self, coins: list[str], max_candles: int = 60)
    def add_tick(self, coin: str, price: float) -> Candle | None
    def get_candles(self, coin: str) -> list[Candle]
```

**ChartsPanel** - Dynamic chart container:
```python
class ChartsPanel(Container):
    def __init__(self, coins: list[str])  # Creates chart for each coin
    def update_chart(self, coin: str, candles: list[Candle])
```

### Dashboard Integration

- Charts refresh every 5 seconds
- Also update on candle completion
- Layout: Markets → Charts → History (vertical stack)

## Future Enhancement Path

If more sophisticated charts are needed later:

```
Textual TUI ──► FastAPI Server ──► React + TradingView Charts
 (trading)       (data relay)       (visualization)
```

This would allow full TradingView-style charting with zoom, pan, indicators, but requires maintaining two UIs.

## Action Items

- [x] Create candle aggregator (`bot/core/candle_aggregator.py`)
- [x] Create charts panel (`bot/ui/components/charts_panel.py`)
- [x] Add plotext to requirements.txt
- [x] Integrate into dashboard
- [ ] Optional: Add volume bars below candles
- [ ] Optional: Add moving average overlay

## References

- [Plotext Documentation](https://github.com/piccolomo/plotext)
- [Textual Framework](https://textual.textualize.io/)
- `docs/PRDs/system_architecture.md` - UI Dashboard section
