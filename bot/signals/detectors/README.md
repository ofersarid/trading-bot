# Detectors

Individual signal detector implementations.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Package exports |
| `macd.py` | MACDSignalDetector - MACD crossover signals |
| `momentum.py` | MomentumSignalDetector - EMA-based momentum |
| `prev_day_vp.py` | PrevDayVPSignalDetector - previous day VP level reactions |
| `rsi.py` | RSISignalDetector - RSI overbought/oversold |
| `volume_profile.py` | VolumeProfileSignalDetector - intraday VP signals |

## Signal Output

Each detector outputs signals with:
- `direction`: LONG or SHORT
- `strength`: 0.0 to 1.0 confidence score
- `signal_type`: Enum identifying the detector
