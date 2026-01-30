# Indicators

Technical indicators for signal generation and analysis.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Package exports |
| `atr.py` | Average True Range (ATR) calculation |
| `macd.py` | Moving Average Convergence Divergence |
| `moving_averages.py` | EMA, SMA, and other moving averages |
| `rsi.py` | Relative Strength Index |
| `volume_profile/` | Volume Profile indicator suite |

## Usage

```python
from bot.indicators import atr, rsi, macd

# Calculate ATR for stop-loss placement
atr_value = atr(candles, period=14)

# Calculate RSI for overbought/oversold detection
rsi_value = rsi(candles, period=14)

# Calculate MACD for trend confirmation
macd_line, signal_line, histogram = macd(candles)
```
