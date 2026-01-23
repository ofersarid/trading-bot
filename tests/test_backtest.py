#!/usr/bin/env python3
"""
Integration tests for the backtest engine.

Run with:
    python -m pytest tests/test_backtest.py -v

Or standalone:
    python tests/test_backtest.py

Note: Requires httpx to be installed for full test coverage.
"""

import importlib.util
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path for standalone execution
sys.path.insert(0, str(Path(__file__).parent.parent))

# Check for httpx availability
HTTPX_AVAILABLE = importlib.util.find_spec("httpx") is not None

# Import modules that don't require httpx
# ruff: noqa: E402
from bot.simulation.models import Position, Side
from bot.simulation.paper_trader import PaperTrader


def import_from_file(filepath: str, module_name: str):
    """Import a module directly from a file path."""
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Import personas base directly (doesn't need httpx)
_personas_base = import_from_file(
    str(Path(__file__).parent.parent / "bot" / "ai" / "personas" / "base.py"), "personas_base"
)
RiskParams = _personas_base.RiskParams
TradingPersona = _personas_base.TradingPersona
get_persona = _personas_base.get_persona

# These imports require httpx indirectly
if HTTPX_AVAILABLE:
    from bot.ai.models import MarketContext, TradePlan
    from bot.backtest.models import BacktestConfig
    from bot.backtest.position_manager import ManagedPosition, PositionManager
else:
    # Create minimal stubs for testing without httpx
    MarketContext = None
    TradePlan = None
    BacktestConfig = None
    ManagedPosition = None
    PositionManager = None


class TestTradingPersona:
    """Tests for TradingPersona."""

    def test_persona_creation(self):
        """Test basic persona creation."""
        persona = TradingPersona(
            name="Test",
            style="balanced",
            description="Test persona",
            prompt_template="Test prompt",
        )
        assert persona.name == "Test"
        assert persona.style == "balanced"

    def test_persona_validation(self):
        """Test persona validates risk params."""
        try:
            TradingPersona(
                name="Invalid",
                style="aggressive",
                description="Invalid",
                prompt_template="Test",
                risk_params=RiskParams(max_position_pct=150),  # Invalid - > 100
            )
            raise AssertionError("Should have raised ValueError")
        except ValueError:
            pass

    def test_get_persona_scalper(self):
        """Test getting pre-defined scalper persona."""
        persona = get_persona("scalper")
        assert persona.name == "Scalper"
        assert persona.style == "aggressive"

    def test_get_persona_conservative(self):
        """Test getting pre-defined conservative persona."""
        persona = get_persona("conservative")
        assert persona.name == "Conservative"
        assert persona.style == "conservative"

    def test_get_persona_invalid(self):
        """Test getting invalid persona raises error."""
        try:
            get_persona("nonexistent")
            raise AssertionError("Should have raised ValueError")
        except ValueError:
            pass


class TestMarketContext:
    """Tests for MarketContext."""

    def test_from_atr_low_volatility(self):
        if not HTTPX_AVAILABLE:
            print("  (skipped - httpx not available)")
            return
        """Test market context with low volatility."""
        context = MarketContext.from_atr("BTC", 100000.0, 300.0)
        assert context.coin == "BTC"
        assert context.current_price == 100000.0
        assert context.atr == 300.0
        assert context.atr_percent == 0.3
        assert context.volatility_level == "low"

    def test_from_atr_high_volatility(self):
        """Test market context with high volatility."""
        if not HTTPX_AVAILABLE:
            print("  (skipped - httpx not available)")
            return
        context = MarketContext.from_atr("BTC", 100000.0, 2000.0)
        assert context.volatility_level == "high"


class TestTradePlan:
    """Tests for TradePlan."""

    def test_trade_plan_creation(self):
        """Test basic TradePlan creation."""
        if not HTTPX_AVAILABLE:
            print("  (skipped - httpx not available)")
            return
        plan = TradePlan(
            action="LONG",
            coin="BTC",
            size_pct=10.0,
            stop_loss=99000.0,
            take_profit=102000.0,
            trail_activation=101000.0,
            trail_distance_pct=0.5,
            confidence=7,
            reason="Strong momentum signal",
        )
        assert plan.is_actionable
        assert plan.is_long
        assert not plan.is_short

    def test_trade_plan_wait(self):
        """Test WAIT TradePlan."""
        if not HTTPX_AVAILABLE:
            print("  (skipped - httpx not available)")
            return
        plan = TradePlan.wait("ETH", "No signals")
        assert not plan.is_actionable
        assert plan.action == "WAIT"
        assert plan.coin == "ETH"

    def test_trade_plan_from_text(self):
        """Test parsing TradePlan from AI response."""
        if not HTTPX_AVAILABLE:
            print("  (skipped - httpx not available)")
            return
        text = """ACTION: LONG
SIZE: 10
STOP_LOSS: 99000
TAKE_PROFIT: 102000
TRAIL_ACTIVATION: 101000
TRAIL_DISTANCE: 0.5
CONFIDENCE: 7
REASON: Strong momentum with RSI confirmation"""

        plan = TradePlan.from_text(text, "BTC", ["MOMENTUM:LONG", "RSI:LONG"])
        assert plan.action == "LONG"
        assert plan.size_pct == 10.0
        assert plan.stop_loss == 99000.0
        assert plan.confidence == 7
        assert len(plan.signals_considered) == 2


class TestManagedPosition:
    """Tests for ManagedPosition."""

    def test_trailing_stop_activation_long(self):
        """Test trailing stop activation for long position."""
        if not HTTPX_AVAILABLE:
            print("  (skipped - httpx not available)")
            return
        position = Position(
            coin="BTC",
            side=Side.LONG,
            size=0.1,
            entry_price=100000.0,
            entry_time=datetime.now(),
        )
        managed = ManagedPosition(
            position=position,
            stop_loss=99000.0,
            take_profit=102000.0,
            trail_activation=101000.0,
            trail_distance_pct=0.5,
        )

        # Price below activation
        managed.update_price(100500.0)
        assert not managed.trailing_active

        # Price at activation
        managed.update_price(101000.0)
        assert managed.trailing_active
        assert managed.trailing_stop > 0

    def test_trailing_stop_moves_up_only(self):
        """Test trailing stop only moves up for long position."""
        if not HTTPX_AVAILABLE:
            print("  (skipped - httpx not available)")
            return
        position = Position(
            coin="BTC",
            side=Side.LONG,
            size=0.1,
            entry_price=100000.0,
            entry_time=datetime.now(),
        )
        managed = ManagedPosition(
            position=position,
            stop_loss=99000.0,
            take_profit=105000.0,
            trail_activation=101000.0,
            trail_distance_pct=0.5,
        )

        # Activate trailing and move stop up
        managed.update_price(102000.0)
        stop1 = managed.trailing_stop

        managed.update_price(103000.0)
        stop2 = managed.trailing_stop

        assert stop2 > stop1, "Trailing stop should move up"

        # Price drops - stop should NOT move down
        managed.update_price(102500.0)
        stop3 = managed.trailing_stop

        assert stop3 == stop2, "Trailing stop should not move down"

    def test_stop_loss_triggered(self):
        """Test stop loss exit detection."""
        if not HTTPX_AVAILABLE:
            print("  (skipped - httpx not available)")
            return
        position = Position(
            coin="BTC",
            side=Side.LONG,
            size=0.1,
            entry_price=100000.0,
            entry_time=datetime.now(),
        )
        managed = ManagedPosition(
            position=position,
            stop_loss=99000.0,
            take_profit=102000.0,
            trail_activation=101000.0,
            trail_distance_pct=0.5,
        )

        # Price above stop
        exit_reason = managed.check_exit(99500.0)
        assert exit_reason is None

        # Price at stop
        exit_reason = managed.check_exit(99000.0)
        assert exit_reason == "stop_loss"

    def test_take_profit_triggered(self):
        """Test take profit exit detection."""
        if not HTTPX_AVAILABLE:
            print("  (skipped - httpx not available)")
            return
        position = Position(
            coin="BTC",
            side=Side.LONG,
            size=0.1,
            entry_price=100000.0,
            entry_time=datetime.now(),
        )
        managed = ManagedPosition(
            position=position,
            stop_loss=99000.0,
            take_profit=102000.0,
            trail_activation=101000.0,
            trail_distance_pct=0.5,
        )

        exit_reason = managed.check_exit(102000.0)
        assert exit_reason == "take_profit"


class TestPositionManager:
    """Tests for PositionManager."""

    def test_open_position_from_plan(self):
        """Test opening position from TradePlan."""
        if not HTTPX_AVAILABLE:
            print("  (skipped - httpx not available)")
            return
        trader = PaperTrader(starting_balance=10000.0)
        manager = PositionManager(trader)

        plan = TradePlan(
            action="LONG",
            coin="BTC",
            size_pct=10.0,
            stop_loss=99000.0,
            take_profit=102000.0,
            trail_activation=101000.0,
            trail_distance_pct=0.5,
            confidence=7,
            reason="Test",
        )

        managed = manager.open_position(plan, 100000.0)

        assert managed is not None
        assert managed.coin == "BTC"
        assert manager.has_position("BTC")
        assert manager.position_count == 1

    def test_check_exits(self):
        """Test checking exits across all positions."""
        if not HTTPX_AVAILABLE:
            print("  (skipped - httpx not available)")
            return
        trader = PaperTrader(starting_balance=10000.0)
        manager = PositionManager(trader)

        # Open a position
        plan = TradePlan(
            action="LONG",
            coin="BTC",
            size_pct=10.0,
            stop_loss=99000.0,
            take_profit=102000.0,
            trail_activation=101000.0,
            trail_distance_pct=0.5,
            confidence=7,
            reason="Test",
        )
        manager.open_position(plan, 100000.0)

        # Price moves to take profit
        closed = manager.check_exits({"BTC": 102000.0})

        assert len(closed) == 1
        assert closed[0][0] == "BTC"
        assert closed[0][1] == "take_profit"
        assert not manager.has_position("BTC")

    def test_close_all_positions(self):
        """Test closing all positions."""
        if not HTTPX_AVAILABLE:
            print("  (skipped - httpx not available)")
            return
        trader = PaperTrader(starting_balance=10000.0)
        manager = PositionManager(trader)

        # Open multiple positions
        for coin in ["BTC", "ETH"]:
            plan = TradePlan(
                action="LONG",
                coin=coin,
                size_pct=5.0,
                stop_loss=99000.0,
                take_profit=102000.0,
                trail_activation=101000.0,
                trail_distance_pct=0.5,
                confidence=7,
                reason="Test",
            )
            manager.open_position(plan, 100000.0 if coin == "BTC" else 3000.0)

        assert manager.position_count == 2

        trades = manager.close_all({"BTC": 100500.0, "ETH": 3050.0})

        assert len(trades) == 2
        assert manager.position_count == 0


class TestBacktestConfig:
    """Tests for BacktestConfig."""

    def test_config_creation(self):
        """Test basic config creation."""
        if not HTTPX_AVAILABLE:
            print("  (skipped - httpx not available)")
            return
        config = BacktestConfig(
            data_source="data/historical/test.csv",
            coins=["BTC"],
            initial_balance=10000.0,
        )
        assert config.data_source == "data/historical/test.csv"
        assert config.initial_balance == 10000.0
        assert "momentum" in config.signal_detectors

    def test_config_validation(self):
        """Test config validates parameters."""
        if not HTTPX_AVAILABLE:
            print("  (skipped - httpx not available)")
            return
        try:
            BacktestConfig(
                data_source="test.csv",
                coins=[],
                initial_balance=-1000.0,  # Invalid
            )
            raise AssertionError("Should have raised ValueError")
        except ValueError:
            pass


def run_tests():
    """Run all tests."""
    import traceback

    test_classes = [
        TestTradingPersona,
        TestMarketContext,
        TestTradePlan,
        TestManagedPosition,
        TestPositionManager,
        TestBacktestConfig,
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
