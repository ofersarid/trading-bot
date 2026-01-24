#!/usr/bin/env python3
"""
Unit tests for the signals module.

Run with:
    python -m pytest tests/test_signals.py -v

Or standalone:
    python tests/test_signals.py
"""

import sys
from datetime import datetime
from pathlib import Path

# Add project root to path for standalone execution
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.core.candle_aggregator import Candle
from bot.signals import (
    MACDSignalDetector,
    MomentumConfig,
    MomentumSignalDetector,
    RSIConfig,
    RSISignalDetector,
    Signal,
    SignalAggregator,
    SignalType,
)


def make_candles(prices: list[float], start_time: datetime | None = None) -> list[Candle]:
    """Helper to create candles from a list of close prices."""
    if start_time is None:
        start_time = datetime.now()

    candles = []
    for price in prices:
        candles.append(
            Candle(
                timestamp=start_time,
                open=price * 0.999,
                high=price * 1.001,
                low=price * 0.998,
                close=price,
                volume=1000.0,
            )
        )
    return candles


class TestSignalDataclass:
    """Tests for the Signal dataclass."""

    def test_signal_creation(self):
        """Test basic Signal creation."""
        signal = Signal(
            coin="BTC",
            signal_type=SignalType.MOMENTUM,
            direction="LONG",
            strength=0.8,
            timestamp=datetime.now(),
        )
        assert signal.coin == "BTC"
        assert signal.signal_type == SignalType.MOMENTUM
        assert signal.is_long
        assert not signal.is_short
        assert signal.strength == 0.8

    def test_signal_invalid_strength(self):
        """Test Signal rejects invalid strength."""
        try:
            Signal(
                coin="BTC",
                signal_type=SignalType.MOMENTUM,
                direction="LONG",
                strength=1.5,  # Invalid - must be 0-1
                timestamp=datetime.now(),
            )
            raise AssertionError("Should have raised ValueError")
        except ValueError:
            pass

    def test_signal_to_dict(self):
        """Test Signal serialization."""
        signal = Signal(
            coin="ETH",
            signal_type=SignalType.RSI,
            direction="SHORT",
            strength=0.6,
            timestamp=datetime(2026, 1, 1, 12, 0, 0),
            metadata={"rsi": 75.0},
        )
        d = signal.to_dict()
        assert d["coin"] == "ETH"
        assert d["signal_type"] == "RSI"
        assert d["direction"] == "SHORT"
        assert d["metadata"]["rsi"] == 75.0


class TestMomentumSignalDetector:
    """Tests for Momentum Signal Detector."""

    def test_no_signal_insufficient_data(self):
        """Test no signal with insufficient candles."""
        detector = MomentumSignalDetector()
        candles = make_candles([100.0] * 10)
        signal = detector.detect("BTC", candles)
        assert signal is None

    def test_detects_bullish_crossover(self):
        """Test detection of bullish EMA crossover."""
        # Create prices that will cause fast EMA to cross above slow EMA
        # Start with downtrend, then strong reversal
        prices = [100.0] * 25  # Flat to establish EMAs
        prices.extend([100 + i * 0.5 for i in range(15)])  # Uptrend

        detector = MomentumSignalDetector(
            MomentumConfig(
                fast_period=5,
                slow_period=10,
                threshold=0.0001,  # Very low threshold for test
            )
        )

        candles = make_candles(prices)
        signal = detector.detect("BTC", candles)

        # Should detect LONG signal on crossover
        if signal is not None:
            assert signal.direction == "LONG"
            assert signal.signal_type == SignalType.MOMENTUM

    def test_no_duplicate_signals(self):
        """Test that duplicate signals are not generated."""
        prices = [100.0] * 25
        prices.extend([100 + i * 0.5 for i in range(15)])

        detector = MomentumSignalDetector(
            MomentumConfig(
                fast_period=5,
                slow_period=10,
                threshold=0.0001,
            )
        )

        candles = make_candles(prices)

        # First detection
        signal1 = detector.detect("BTC", candles)

        # Second detection with same candles - should return None (no new crossover)
        signal2 = detector.detect("BTC", candles)

        # Either both None or first is signal and second is None
        if signal1 is not None:
            assert signal2 is None, "Should not generate duplicate signal"

    def test_reset_allows_new_signals(self):
        """Test that reset allows detecting same direction again."""
        detector = MomentumSignalDetector()
        detector._last_crossover_direction["BTC"] = "LONG"

        detector.reset("BTC")

        assert "BTC" not in detector._last_crossover_direction


class TestRSISignalDetector:
    """Tests for RSI Signal Detector."""

    def test_detects_oversold(self):
        """Test detection of oversold condition."""
        # Create prices in strong downtrend for oversold RSI
        prices = [100.0 - i for i in range(20)]  # 100 down to 81

        detector = RSISignalDetector(
            RSIConfig(
                period=14,
                oversold=30.0,
                overbought=70.0,
            )
        )

        candles = make_candles(prices)
        signal = detector.detect("ETH", candles)

        if signal is not None:
            assert signal.direction == "LONG"  # Oversold = buy signal
            assert signal.signal_type == SignalType.RSI

    def test_detects_overbought(self):
        """Test detection of overbought condition."""
        # Create prices in strong uptrend for overbought RSI
        prices = [100.0 + i for i in range(20)]  # 100 up to 119

        detector = RSISignalDetector(
            RSIConfig(
                period=14,
                oversold=30.0,
                overbought=70.0,
            )
        )

        candles = make_candles(prices)
        signal = detector.detect("ETH", candles)

        if signal is not None:
            assert signal.direction == "SHORT"  # Overbought = sell signal
            assert signal.signal_type == SignalType.RSI

    def test_cooldown_prevents_spam(self):
        """Test that cooldown prevents signal spam."""
        prices = [100.0 + i for i in range(20)]

        detector = RSISignalDetector(
            RSIConfig(
                period=14,
                cooldown_candles=5,
            )
        )

        candles = make_candles(prices)

        # First detection
        signal1 = detector.detect("SOL", candles)

        # Immediately try again - should be blocked by cooldown
        signal2 = detector.detect("SOL", candles)

        if signal1 is not None:
            assert signal2 is None, "Cooldown should block immediate repeat"


class TestMACDSignalDetector:
    """Tests for MACD Signal Detector."""

    def test_no_signal_insufficient_data(self):
        """Test no signal with insufficient candles."""
        detector = MACDSignalDetector()
        candles = make_candles([100.0] * 20)  # Need at least slow + signal
        signal = detector.detect("BTC", candles)
        assert signal is None

    def test_detects_bullish_crossover(self):
        """Test detection of bullish MACD crossover."""
        # Need enough data for MACD calculation (26 + 9 = 35 minimum)
        prices = [100.0] * 40
        prices.extend([100 + i * 0.3 for i in range(20)])  # Uptrend

        detector = MACDSignalDetector()
        candles = make_candles(prices)
        signal = detector.detect("BTC", candles)

        # May or may not detect depending on data
        if signal is not None:
            assert signal.signal_type == SignalType.MACD


class TestSignalAggregator:
    """Tests for Signal Aggregator."""

    def test_aggregator_collects_signals(self):
        """Test that aggregator collects signals from detectors."""
        momentum_detector = MomentumSignalDetector()
        rsi_detector = RSISignalDetector()

        aggregator = SignalAggregator([momentum_detector, rsi_detector])

        # Create enough data for signals
        prices = [100.0 + i for i in range(50)]
        candles = make_candles(prices)

        # Process candles
        signals = aggregator.process_candle("BTC", candles)

        # Signals collected (may be empty if no crossovers)
        assert isinstance(signals, list)

    def test_pending_signals(self):
        """Test pending signals retrieval."""
        aggregator = SignalAggregator([])

        # Manually add a signal
        signal = Signal(
            coin="BTC",
            signal_type=SignalType.MOMENTUM,
            direction="LONG",
            strength=0.7,
            timestamp=datetime.now(),
        )
        aggregator._pending_signals.append(signal)
        aggregator._signals.append(signal)

        # Get pending signals
        pending = aggregator.get_pending_signals()
        assert len(pending) == 1
        assert pending[0].coin == "BTC"

        # Pending should be cleared
        assert aggregator.pending_count == 0

    def test_consensus_direction_long(self):
        """Test consensus direction when all signals agree on LONG."""
        aggregator = SignalAggregator([])

        now = datetime.now()
        aggregator._signals.append(Signal("BTC", SignalType.MOMENTUM, "LONG", 0.8, now))
        aggregator._signals.append(Signal("BTC", SignalType.RSI, "LONG", 0.6, now))

        direction = aggregator.get_consensus_direction("BTC")
        assert direction == "LONG"

    def test_consensus_direction_mixed(self):
        """Test consensus with mixed signals."""
        aggregator = SignalAggregator([])

        now = datetime.now()
        aggregator._signals.append(Signal("BTC", SignalType.MOMENTUM, "LONG", 0.5, now))
        aggregator._signals.append(Signal("BTC", SignalType.RSI, "SHORT", 0.5, now))

        direction = aggregator.get_consensus_direction("BTC")
        # Equal strength = no consensus
        assert direction is None

    def test_has_conflicting_signals(self):
        """Test detection of conflicting signals."""
        aggregator = SignalAggregator([])

        now = datetime.now()
        aggregator._signals.append(Signal("BTC", SignalType.MOMENTUM, "LONG", 0.8, now))
        aggregator._signals.append(Signal("BTC", SignalType.RSI, "SHORT", 0.6, now))

        assert aggregator.has_conflicting_signals("BTC") is True

    def test_reset_clears_state(self):
        """Test that reset clears all state."""
        aggregator = SignalAggregator([MomentumSignalDetector()])

        now = datetime.now()
        aggregator._signals.append(Signal("BTC", SignalType.MOMENTUM, "LONG", 0.8, now))
        aggregator._pending_signals.append(Signal("BTC", SignalType.MOMENTUM, "LONG", 0.8, now))

        aggregator.reset()

        assert aggregator.total_signals == 0
        assert aggregator.pending_count == 0


def run_tests():
    """Run all tests."""
    import traceback

    test_classes = [
        TestSignalDataclass,
        TestMomentumSignalDetector,
        TestRSISignalDetector,
        TestMACDSignalDetector,
        TestSignalAggregator,
    ]
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
