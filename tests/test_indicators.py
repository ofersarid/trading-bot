#!/usr/bin/env python3
"""
Unit tests for the indicators module.

Run with:
    python -m pytest tests/test_indicators.py -v

Or standalone:
    python tests/test_indicators.py
"""

import sys
from pathlib import Path

# Add project root to path for standalone execution
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.indicators import atr, ema, ema_series, macd, rsi, sma
from bot.indicators.atr import ATRCandle, true_range
from bot.indicators.macd import MACDResult


class TestSMA:
    """Tests for Simple Moving Average."""

    def test_sma_basic(self):
        """Test basic SMA calculation."""
        prices = [10.0, 11.0, 12.0, 13.0, 14.0]
        result = sma(prices, period=3)
        # Last 3 prices: 12, 13, 14 -> avg = 13
        assert result == 13.0

    def test_sma_full_period(self):
        """Test SMA with period equal to data length."""
        prices = [10.0, 20.0, 30.0]
        result = sma(prices, period=3)
        assert result == 20.0

    def test_sma_insufficient_data(self):
        """Test SMA returns None with insufficient data."""
        prices = [10.0, 11.0]
        result = sma(prices, period=3)
        assert result is None

    def test_sma_empty_list(self):
        """Test SMA with empty list."""
        assert sma([], period=3) is None

    def test_sma_invalid_period(self):
        """Test SMA with invalid period."""
        prices = [10.0, 11.0, 12.0]
        assert sma(prices, period=0) is None
        assert sma(prices, period=-1) is None


class TestEMA:
    """Tests for Exponential Moving Average."""

    def test_ema_basic(self):
        """Test basic EMA calculation."""
        prices = [10.0, 11.0, 12.0, 13.0, 14.0]
        result = ema(prices, period=3)
        assert result is not None
        # EMA should be close to but not exactly the SMA
        assert 12.5 < result < 14.0

    def test_ema_series_length(self):
        """Test EMA series returns correct length."""
        prices = [10.0, 11.0, 12.0, 13.0, 14.0]
        result = ema_series(prices, period=3)
        # len(prices) - period + 1 = 5 - 3 + 1 = 3
        assert len(result) == 3

    def test_ema_first_value_is_sma(self):
        """Test that first EMA value equals SMA."""
        prices = [10.0, 11.0, 12.0, 13.0, 14.0]
        series = ema_series(prices, period=3)
        # First value should be SMA of first 3 prices = (10+11+12)/3 = 11
        assert series[0] == 11.0

    def test_ema_insufficient_data(self):
        """Test EMA returns None with insufficient data."""
        prices = [10.0, 11.0]
        assert ema(prices, period=3) is None


class TestRSI:
    """Tests for Relative Strength Index."""

    def test_rsi_uptrend(self):
        """Test RSI in a strong uptrend."""
        # All gains, no losses
        prices = [
            100.0,
            101.0,
            102.0,
            103.0,
            104.0,
            105.0,
            106.0,
            107.0,
            108.0,
            109.0,
            110.0,
            111.0,
            112.0,
            113.0,
            114.0,
            115.0,
        ]
        result = rsi(prices, period=14)
        assert result is not None
        assert result == 100.0  # All gains = RSI 100

    def test_rsi_downtrend(self):
        """Test RSI in a strong downtrend."""
        # All losses, no gains
        prices = [
            115.0,
            114.0,
            113.0,
            112.0,
            111.0,
            110.0,
            109.0,
            108.0,
            107.0,
            106.0,
            105.0,
            104.0,
            103.0,
            102.0,
            101.0,
            100.0,
        ]
        result = rsi(prices, period=14)
        assert result is not None
        assert result == 0.0  # All losses = RSI 0

    def test_rsi_neutral(self):
        """Test RSI with equal gains and losses."""
        # Alternating +1 and -1 gives RSI around 50
        prices = [
            100.0,
            101.0,
            100.0,
            101.0,
            100.0,
            101.0,
            100.0,
            101.0,
            100.0,
            101.0,
            100.0,
            101.0,
            100.0,
            101.0,
            100.0,
        ]
        result = rsi(prices, period=14)
        assert result is not None
        assert 45.0 < result < 55.0  # Should be close to 50

    def test_rsi_insufficient_data(self):
        """Test RSI returns None with insufficient data."""
        prices = [100.0, 101.0, 102.0]
        assert rsi(prices, period=14) is None


class TestMACD:
    """Tests for MACD indicator."""

    def test_macd_basic(self):
        """Test basic MACD calculation."""
        # Generate enough prices for MACD (need slow + signal periods)
        prices = [100.0 + i for i in range(50)]
        result = macd(prices, fast=12, slow=26, signal=9)

        assert result is not None
        assert isinstance(result, MACDResult)
        assert hasattr(result, "macd_line")
        assert hasattr(result, "signal_line")
        assert hasattr(result, "histogram")

    def test_macd_uptrend_properties(self):
        """Test MACD properties in uptrend."""
        prices = [100.0 + i for i in range(50)]
        result = macd(prices)
        assert result is not None
        # MACD line should exist and histogram should be calculated
        assert isinstance(result.macd_line, float)
        assert isinstance(result.histogram, float)
        # In steady uptrend, fast EMA > slow EMA so MACD line should be positive
        assert result.macd_line > 0

    def test_macd_insufficient_data(self):
        """Test MACD returns None with insufficient data."""
        prices = [100.0 + i for i in range(20)]
        result = macd(prices, fast=12, slow=26, signal=9)
        assert result is None

    def test_macd_invalid_periods(self):
        """Test MACD with invalid period configuration."""
        prices = [100.0 + i for i in range(50)]
        # Fast period must be less than slow
        result = macd(prices, fast=26, slow=12, signal=9)
        assert result is None


class TestATR:
    """Tests for Average True Range."""

    def test_true_range_basic(self):
        """Test basic true range calculation."""
        candle = ATRCandle(high=105.0, low=95.0, close=100.0)
        tr = true_range(candle)
        assert tr == 10.0  # high - low

    def test_true_range_with_gap_up(self):
        """Test true range with gap up from previous close."""
        candle = ATRCandle(high=115.0, low=110.0, close=112.0)
        tr = true_range(candle, previous_close=100.0)
        # Gap: 110 to 100, so |high - prev_close| = 15
        assert tr == 15.0

    def test_true_range_with_gap_down(self):
        """Test true range with gap down from previous close."""
        candle = ATRCandle(high=95.0, low=90.0, close=92.0)
        tr = true_range(candle, previous_close=100.0)
        # Gap: 90 to 100, so |low - prev_close| = 10
        assert tr == 10.0

    def test_atr_basic(self):
        """Test basic ATR calculation."""
        candles = [
            ATRCandle(high=105.0, low=95.0, close=100.0),
            ATRCandle(high=106.0, low=96.0, close=101.0),
            ATRCandle(high=107.0, low=97.0, close=102.0),
            ATRCandle(high=108.0, low=98.0, close=103.0),
            ATRCandle(high=109.0, low=99.0, close=104.0),
            ATRCandle(high=110.0, low=100.0, close=105.0),
            ATRCandle(high=111.0, low=101.0, close=106.0),
            ATRCandle(high=112.0, low=102.0, close=107.0),
            ATRCandle(high=113.0, low=103.0, close=108.0),
            ATRCandle(high=114.0, low=104.0, close=109.0),
            ATRCandle(high=115.0, low=105.0, close=110.0),
            ATRCandle(high=116.0, low=106.0, close=111.0),
            ATRCandle(high=117.0, low=107.0, close=112.0),
            ATRCandle(high=118.0, low=108.0, close=113.0),
            ATRCandle(high=119.0, low=109.0, close=114.0),
            ATRCandle(high=120.0, low=110.0, close=115.0),
        ]
        result = atr(candles, period=14)
        assert result is not None
        # All candles have $10 range, so ATR should be close to 10
        assert 9.5 < result < 10.5

    def test_atr_insufficient_data(self):
        """Test ATR returns None with insufficient data."""
        candles = [ATRCandle(high=105.0, low=95.0, close=100.0) for _ in range(10)]
        assert atr(candles, period=14) is None


def run_tests():
    """Run all tests."""
    import traceback

    test_classes = [TestSMA, TestEMA, TestRSI, TestMACD, TestATR]
    passed = 0
    failed = 0

    for test_class in test_classes:
        print(f"\n{'='*60}")
        print(f"Running {test_class.__name__}")
        print("=" * 60)

        instance = test_class()
        for method_name in dir(instance):
            if method_name.startswith("test_"):
                try:
                    getattr(instance, method_name)()
                    print(f"  ✓ {method_name}")
                    passed += 1
                except AssertionError as e:
                    print(f"  ✗ {method_name}: {e}")
                    failed += 1
                except Exception as e:
                    print(f"  ✗ {method_name}: {e}")
                    traceback.print_exc()
                    failed += 1

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
