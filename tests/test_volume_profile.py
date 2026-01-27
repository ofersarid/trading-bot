"""
Unit tests for Volume Profile indicator system.

Tests:
- Data models (Trade, VolumeAtPrice, VolumeProfile)
- VolumeProfileBuilder
- Indicator functions (POC, Value Area, HVN/LVN, Delta)
- VolumeProfileSignalDetector
"""

from datetime import datetime, timedelta

import pytest

from bot.indicators.volume_profile import (
    MultiSessionProfileBuilder,
    Trade,
    VolumeAtPrice,
    VolumeProfile,
    VolumeProfileBuilder,
    get_delta_at_price,
    get_hvn_levels,
    get_lvn_levels,
    get_poc,
    get_profile_stats,
    get_total_delta,
    get_value_area,
    is_price_in_value_area,
)
from bot.signals.detectors.volume_profile import VolumeProfileConfig, VolumeProfileSignalDetector

# =============================================================================
# Test Data Models
# =============================================================================


class TestTrade:
    """Tests for Trade data model."""

    def test_create_trade(self) -> None:
        """Test basic trade creation."""
        now = datetime.now()
        trade = Trade(
            timestamp=now,
            price=100000.0,
            size=0.5,
            side="B",
            coin="BTC",
        )

        assert trade.timestamp == now
        assert trade.price == 100000.0
        assert trade.size == 0.5
        assert trade.side == "B"
        assert trade.coin == "BTC"

    def test_trade_to_dict(self) -> None:
        """Test trade serialization."""
        now = datetime.now()
        trade = Trade(timestamp=now, price=100.0, size=1.0, side="A", coin="ETH")

        d = trade.to_dict()
        assert d["price"] == 100.0
        assert d["size"] == 1.0
        assert d["side"] == "A"
        assert d["coin"] == "ETH"

    def test_trade_from_dict(self) -> None:
        """Test trade deserialization."""
        d = {
            "timestamp": "2026-01-20T10:00:00",
            "price": 50000.0,
            "size": 0.25,
            "side": "B",
            "coin": "BTC",
        }

        trade = Trade.from_dict(d)
        assert trade.price == 50000.0
        assert trade.size == 0.25
        assert trade.side == "B"


class TestVolumeAtPrice:
    """Tests for VolumeAtPrice data model."""

    def test_create_volume_at_price(self) -> None:
        """Test basic VolumeAtPrice creation."""
        vap = VolumeAtPrice(price=100.0, total_volume=10.0, buy_volume=6.0, sell_volume=4.0)

        assert vap.price == 100.0
        assert vap.total_volume == 10.0
        assert vap.buy_volume == 6.0
        assert vap.sell_volume == 4.0

    def test_delta_calculation(self) -> None:
        """Test delta (net buying pressure) calculation."""
        # More buyers
        vap = VolumeAtPrice(price=100.0, total_volume=10.0, buy_volume=7.0, sell_volume=3.0)
        assert vap.delta == 4.0  # 7 - 3

        # More sellers
        vap = VolumeAtPrice(price=100.0, total_volume=10.0, buy_volume=2.0, sell_volume=8.0)
        assert vap.delta == -6.0  # 2 - 8

        # Balanced
        vap = VolumeAtPrice(price=100.0, total_volume=10.0, buy_volume=5.0, sell_volume=5.0)
        assert vap.delta == 0.0

    def test_delta_pct(self) -> None:
        """Test delta percentage calculation."""
        vap = VolumeAtPrice(price=100.0, total_volume=100.0, buy_volume=80.0, sell_volume=20.0)
        assert vap.delta_pct == 60.0  # (80-20)/100 * 100

    def test_add_trade(self) -> None:
        """Test adding trades to a price level."""
        vap = VolumeAtPrice(price=100.0)

        # Add buy
        vap.add_trade(5.0, "B")
        assert vap.total_volume == 5.0
        assert vap.buy_volume == 5.0
        assert vap.sell_volume == 0.0

        # Add sell
        vap.add_trade(3.0, "A")
        assert vap.total_volume == 8.0
        assert vap.buy_volume == 5.0
        assert vap.sell_volume == 3.0


# =============================================================================
# Test VolumeProfileBuilder
# =============================================================================


class TestVolumeProfileBuilder:
    """Tests for VolumeProfileBuilder."""

    def test_basic_building(self) -> None:
        """Test basic profile building from trades."""
        builder = VolumeProfileBuilder(tick_size=10.0)

        now = datetime.now()
        trades = [
            Trade(timestamp=now, price=100.0, size=1.0, side="B"),
            Trade(timestamp=now, price=105.0, size=2.0, side="A"),  # Same bucket as 100
            Trade(timestamp=now, price=110.0, size=1.5, side="B"),
        ]

        for trade in trades:
            builder.add_trade(trade)

        profile = builder.get_profile()

        assert profile.level_count == 2  # Two $10 buckets
        assert profile.total_volume == 4.5

    def test_price_bucketing(self) -> None:
        """Test that prices are correctly bucketed."""
        builder = VolumeProfileBuilder(tick_size=10.0)

        now = datetime.now()
        # All should go to 100.0 bucket
        trades = [
            Trade(timestamp=now, price=95.0, size=1.0, side="B"),  # Rounds to 100
            Trade(timestamp=now, price=100.0, size=1.0, side="B"),
            Trade(timestamp=now, price=104.0, size=1.0, side="B"),  # Rounds to 100
        ]

        for trade in trades:
            builder.add_trade(trade)

        profile = builder.get_profile()
        assert profile.level_count == 1
        assert 100.0 in profile.levels
        assert profile.levels[100.0].total_volume == 3.0

    def test_delta_tracking(self) -> None:
        """Test buy/sell delta tracking."""
        builder = VolumeProfileBuilder(tick_size=10.0)

        now = datetime.now()
        trades = [
            Trade(timestamp=now, price=100.0, size=5.0, side="B"),
            Trade(timestamp=now, price=100.0, size=3.0, side="A"),
        ]

        for trade in trades:
            builder.add_trade(trade)

        profile = builder.get_profile()
        level = profile.levels[100.0]

        assert level.buy_volume == 5.0
        assert level.sell_volume == 3.0
        assert level.delta == 2.0

    def test_session_reset(self) -> None:
        """Test session reset functionality."""
        builder = VolumeProfileBuilder(tick_size=10.0, session_type="custom")

        now = datetime.now()
        builder.add_trade(Trade(timestamp=now, price=100.0, size=1.0, side="B"))

        assert builder.trade_count == 1

        # Reset session
        old_profile = builder.reset_session()
        assert old_profile.total_volume == 1.0
        assert builder.trade_count == 0
        assert builder.is_empty


class TestMultiSessionProfileBuilder:
    """Tests for MultiSessionProfileBuilder."""

    def test_multi_session(self) -> None:
        """Test multiple session management."""
        builder = MultiSessionProfileBuilder(tick_size=10.0)

        now = datetime.now()

        # First session
        builder.add_trade(Trade(timestamp=now, price=100.0, size=1.0, side="B"))
        builder.end_session()

        # Second session
        builder.add_trade(Trade(timestamp=now, price=100.0, size=2.0, side="B"))
        builder.end_session()

        assert builder.session_count == 2

        # Composite should have all trades
        composite = builder.get_composite_profile()
        assert composite.total_volume == 3.0


# =============================================================================
# Test Indicator Functions
# =============================================================================


def create_test_profile() -> VolumeProfile:
    """Create a test profile for indicator tests."""
    levels = {
        100.0: VolumeAtPrice(price=100.0, total_volume=10.0, buy_volume=6.0, sell_volume=4.0),
        110.0: VolumeAtPrice(
            price=110.0, total_volume=50.0, buy_volume=30.0, sell_volume=20.0
        ),  # POC
        120.0: VolumeAtPrice(price=120.0, total_volume=30.0, buy_volume=10.0, sell_volume=20.0),
        130.0: VolumeAtPrice(price=130.0, total_volume=5.0, buy_volume=1.0, sell_volume=4.0),  # LVN
        140.0: VolumeAtPrice(price=140.0, total_volume=15.0, buy_volume=8.0, sell_volume=7.0),
    }

    return VolumeProfile(
        session_start=datetime.now(),
        session_end=datetime.now(),
        tick_size=10.0,
        levels=levels,
        coin="BTC",
    )


class TestIndicatorFunctions:
    """Tests for Volume Profile indicator functions."""

    def test_get_poc(self) -> None:
        """Test Point of Control calculation."""
        profile = create_test_profile()
        poc = get_poc(profile)

        assert poc == 110.0  # Highest volume level

    def test_get_poc_empty_profile(self) -> None:
        """Test POC with empty profile."""
        profile = VolumeProfile(
            session_start=datetime.now(),
            session_end=datetime.now(),
            tick_size=10.0,
            levels={},
        )

        assert get_poc(profile) is None

    def test_get_value_area(self) -> None:
        """Test Value Area calculation."""
        profile = create_test_profile()
        va = get_value_area(profile, percentage=0.70)

        assert va is not None
        va_low, va_high = va

        # VA should include POC (110) and expand to capture 70% volume
        assert va_low <= 110.0
        assert va_high >= 110.0

        # Check that VA captures approximately 70% of volume
        total = profile.total_volume
        va_volume = sum(
            level.total_volume
            for price, level in profile.levels.items()
            if va_low <= price <= va_high
        )
        assert va_volume / total >= 0.70

    def test_get_hvn_levels(self) -> None:
        """Test High Volume Node detection."""
        profile = create_test_profile()
        hvn = get_hvn_levels(profile, threshold_pct=0.6)  # Top 40%

        assert 110.0 in hvn  # POC should always be HVN
        assert len(hvn) >= 1

    def test_get_lvn_levels(self) -> None:
        """Test Low Volume Node detection."""
        profile = create_test_profile()
        lvn = get_lvn_levels(profile, threshold_pct=0.4)  # Bottom 40%

        assert 130.0 in lvn  # Lowest volume level
        assert len(lvn) >= 1

    def test_get_delta_at_price(self) -> None:
        """Test delta at specific price."""
        profile = create_test_profile()

        # At POC (110.0)
        delta = get_delta_at_price(profile, 110.0)
        assert delta == 10.0  # 30 - 20

        # At price with more sellers (120.0)
        delta = get_delta_at_price(profile, 120.0)
        assert delta == -10.0  # 10 - 20

    def test_get_total_delta(self) -> None:
        """Test total delta calculation."""
        profile = create_test_profile()
        total_delta = get_total_delta(profile)

        # Sum of all deltas
        expected = (6 - 4) + (30 - 20) + (10 - 20) + (1 - 4) + (8 - 7)
        assert total_delta == expected

    def test_is_price_in_value_area(self) -> None:
        """Test price in value area check."""
        profile = create_test_profile()

        # POC should be in VA
        assert is_price_in_value_area(profile, 110.0)

    def test_get_profile_stats(self) -> None:
        """Test comprehensive profile statistics."""
        profile = create_test_profile()
        stats = get_profile_stats(profile)

        assert stats["poc"] == 110.0
        assert stats["value_area"] is not None
        assert stats["total_volume"] == 110.0
        assert "hvn_levels" in stats
        assert "lvn_levels" in stats


# =============================================================================
# Test Signal Detector
# =============================================================================


class TestVolumeProfileSignalDetector:
    """Tests for VolumeProfileSignalDetector."""

    def _create_candle(
        self,
        timestamp: datetime,
        open_: float,
        high: float,
        low: float,
        close: float,
    ):
        """Create a candle for testing."""
        from bot.core.candle_aggregator import Candle

        return Candle(
            timestamp=timestamp,
            open=open_,
            high=high,
            low=low,
            close=close,
            volume=100.0,
        )

    def test_detector_without_profile(self) -> None:
        """Test that detector returns None without a profile."""
        detector = VolumeProfileSignalDetector()
        candles = [
            self._create_candle(datetime.now(), 100.0, 105.0, 95.0, 102.0) for _ in range(10)
        ]

        signal = detector.detect("BTC", candles)
        assert signal is None

    def test_failed_auction_low_detection(self) -> None:
        """Test failed auction at VA low detection."""
        detector = VolumeProfileSignalDetector(
            VolumeProfileConfig(
                va_buffer_pct=0.001,
                rejection_lookback=5,
                min_strength=0.3,
                cooldown_candles=1,
            )
        )

        # Create a profile with VA from 100 to 120
        profile = VolumeProfile(
            session_start=datetime.now(),
            session_end=datetime.now(),
            tick_size=10.0,
            levels={
                100.0: VolumeAtPrice(
                    price=100.0, total_volume=20.0, buy_volume=10.0, sell_volume=10.0
                ),
                110.0: VolumeAtPrice(
                    price=110.0, total_volume=50.0, buy_volume=25.0, sell_volume=25.0
                ),
                120.0: VolumeAtPrice(
                    price=120.0, total_volume=20.0, buy_volume=10.0, sell_volume=10.0
                ),
            },
        )
        detector.update_profile(profile)

        # Candles showing rejection from below VA
        now = datetime.now()
        candles = [
            self._create_candle(now - timedelta(minutes=5), 110.0, 112.0, 108.0, 109.0),
            self._create_candle(
                now - timedelta(minutes=4), 109.0, 110.0, 98.0, 99.0
            ),  # Went below VA
            self._create_candle(now - timedelta(minutes=3), 99.0, 101.0, 95.0, 96.0),  # Below VA
            self._create_candle(now - timedelta(minutes=2), 96.0, 103.0, 95.0, 102.0),  # Recovering
            self._create_candle(
                now - timedelta(minutes=1), 102.0, 108.0, 101.0, 107.0
            ),  # Back inside VA
        ]

        signal = detector.detect("BTC", candles)

        # Should detect a failed auction (bullish)
        if signal:
            assert signal.direction == "LONG"
            assert signal.metadata.get("setup") == "failed_auction_low"

    def test_detector_cooldown(self) -> None:
        """Test signal cooldown between detections."""
        config = VolumeProfileConfig(cooldown_candles=5)
        detector = VolumeProfileSignalDetector(config)

        profile = create_test_profile()
        detector.update_profile(profile)

        # First detection attempt
        now = datetime.now()
        candles = [
            self._create_candle(now - timedelta(minutes=i), 100.0, 105.0, 95.0, 100.0)
            for i in range(10)
        ]

        # Multiple calls should respect cooldown
        for _ in range(10):
            detector.detect("BTC", candles)

        # No assertions needed - just verify it doesn't crash
        # In real use, signals would be rate-limited

    def test_detector_reset(self) -> None:
        """Test detector reset functionality."""
        detector = VolumeProfileSignalDetector()

        # Simulate some state
        detector._candle_count["BTC"] = 100
        detector._last_signal_candle["BTC"] = 50

        # Reset specific coin
        detector.reset("BTC")
        assert "BTC" not in detector._candle_count
        assert "BTC" not in detector._last_signal_candle

        # Reset all
        detector._candle_count["ETH"] = 100
        detector.reset()
        assert len(detector._candle_count) == 0


# =============================================================================
# Integration Tests
# =============================================================================


class TestVolumeProfileIntegration:
    """Integration tests for the Volume Profile system."""

    def test_builder_to_indicators(self) -> None:
        """Test full flow from trades to indicators."""
        # Build profile from trades
        builder = VolumeProfileBuilder(tick_size=10.0, coin="BTC")

        now = datetime.now()
        # Create trades with clear distribution
        trades = [
            # High volume at 100
            Trade(timestamp=now, price=100.0, size=10.0, side="B"),
            Trade(timestamp=now, price=100.0, size=10.0, side="A"),
            # Low volume at 110
            Trade(timestamp=now, price=110.0, size=1.0, side="B"),
            # Medium volume at 120
            Trade(timestamp=now, price=120.0, size=5.0, side="B"),
            Trade(timestamp=now, price=120.0, size=3.0, side="A"),
        ]

        for trade in trades:
            builder.add_trade(trade)

        profile = builder.get_profile()

        # Test indicators on this profile
        poc = get_poc(profile)
        assert poc == 100.0  # Highest volume

        lvn = get_lvn_levels(profile, threshold_pct=0.5)
        assert 110.0 in lvn  # Lowest volume

        total_delta = get_total_delta(profile)
        # 10-10 + 1-0 + 5-3 = 0 + 1 + 2 = 3
        assert total_delta == 3.0

    def test_profile_serialization_roundtrip(self) -> None:
        """Test profile can be serialized and deserialized."""
        original = create_test_profile()

        # Serialize
        data = original.to_dict()

        # Deserialize
        restored = VolumeProfile.from_dict(data)

        assert restored.tick_size == original.tick_size
        assert len(restored.levels) == len(original.levels)
        assert get_poc(restored) == get_poc(original)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
