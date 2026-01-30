# Tests

Unit and integration tests for the trading bot.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Test package marker |
| `test_backtest.py` | Tests for backtesting engine |
| `test_indicators.py` | Tests for technical indicators (SMA, EMA, RSI, MACD, ATR) |
| `test_signals.py` | Tests for signal detection |
| `test_volume_profile.py` | Tests for Volume Profile calculations |

## Commands

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_indicators.py
python -m pytest tests/test_signals.py
python -m pytest tests/test_backtest.py

# Run with verbose output
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=bot

# Direct Python execution
python tests/test_indicators.py
python tests/test_signals.py
```

## Integration Tests

```bash
# Test UI layout (no data connection)
python test_ui.py

# Test AI connection and strategies
python test_ai.py -l              # List strategies and scenarios
python test_ai.py -s momentum     # Test momentum strategy
python test_ai.py --compare       # Compare all strategies
```
