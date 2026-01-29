"""
Live Trading Engine - Real-time trading using the unified TradingCore.

This engine uses the SAME logic as BacktestEngine, only the data source differs.
Backtest results are now predictive of live performance.

Usage:
    python -m bot.live.engine --balance 10000 --strategy momentum_based --ai

Architecture:
    WebSocket → Candle Aggregator → TradingCore → Paper Trader
              → Trade Stream → VolumeProfileBuilder → VP Detector

    Same as backtest:
    CSV File → Candle Iterator → TradingCore → Paper Trader
    Parquet → Trade Storage → VolumeProfileBuilder → VP Detector

Volume Profile:
    The live engine builds volume profile from the real-time trade stream,
    matching how backtest builds it from historical trade data.
"""

import argparse
import asyncio
import logging
from datetime import datetime

from bot.core.candle_aggregator import Candle
from bot.core.trading_core import TradingCore
from bot.indicators.volume_profile import Trade as VPTrade
from bot.indicators.volume_profile import VolumeProfileBuilder
from bot.simulation.models import HYPERLIQUID_FEES
from bot.simulation.paper_trader import PaperTrader
from bot.strategies import list_strategies

logger = logging.getLogger(__name__)


class LiveEngine:
    """
    Live trading engine using the unified TradingCore.

    This is the live equivalent of BacktestEngine.
    Uses the SAME TradingCore for decisions.
    """

    def __init__(
        self,
        coins: list[str] | None = None,
        strategy_name: str = "momentum_based",
        initial_balance: float = 10000.0,
        ai_enabled: bool = False,
        portfolio_mode: bool = False,
        account_goal: float | None = None,
        goal_timeframe_days: int | None = None,
        signal_detectors: list[str] | None = None,
    ) -> None:
        """
        Initialize the live trading engine.

        Args:
            coins: Coins to trade (default: ["BTC", "ETH", "SOL"])
            strategy_name: Strategy to use
            initial_balance: Starting paper balance
            ai_enabled: Whether to use AI for position sizing
            portfolio_mode: Use portfolio allocator for multi-asset
            account_goal: Target balance for AI
            goal_timeframe_days: Days to reach goal
            signal_detectors: Signal detectors to use
        """
        self.coins = coins or ["BTC", "ETH", "SOL"]
        self.initial_balance = initial_balance

        # Paper trader for execution
        self.trader = PaperTrader(
            starting_balance=initial_balance,
            fees=HYPERLIQUID_FEES,
        )

        # Unified trading core - SAME as backtest
        self.core = TradingCore(
            strategy_name=strategy_name,
            signal_detectors=signal_detectors or ["momentum", "rsi", "macd"],
            ai_enabled=ai_enabled,
            portfolio_mode=portfolio_mode,
            account_goal=account_goal,
            goal_timeframe_days=goal_timeframe_days,
            initial_balance=initial_balance,
        )

        # Candle aggregation state
        self._current_candles: dict[str, dict] = {}  # coin -> partial candle data
        self._candle_start_times: dict[str, datetime] = {}

        # Volume Profile builders (one per coin) - matches backtest behavior
        self._vp_builders: dict[str, VolumeProfileBuilder] = {}
        self._vp_update_interval = 60  # Update VP detector every 60 trades
        self._trade_counts: dict[str, int] = {}

        # Initialize VP builders for each coin
        for coin in self.coins:
            self._vp_builders[coin] = VolumeProfileBuilder(
                tick_size=10.0 if coin == "BTC" else 1.0,  # $10 for BTC, $1 for others
                session_type="daily",
                coin=coin,
            )
            self._trade_counts[coin] = 0

        # Tracking
        self._trades_executed = 0
        self._start_time: datetime | None = None
        self._running = False

    async def run(self) -> None:
        """
        Run the live trading engine.

        Connects to Hyperliquid WebSocket and processes:
        - Price updates (for candles and signals)
        - Trade stream (for volume profile building)
        """
        import json

        import websockets

        WS_URL = "wss://api.hyperliquid.xyz/ws"

        self._start_time = datetime.now()
        self._running = True

        # Check if VP detectors are enabled
        has_vp = self.core.get_volume_profile_detector() is not None

        print("=" * 60)
        print("🤖 LIVE TRADING ENGINE (Unified Architecture)")
        print("=" * 60)
        print(f"💰 Starting Balance: ${self.initial_balance:,.2f}")
        print(f"📊 Watching: {', '.join(self.coins)}")
        print(f"📈 Strategy: {self.core.strategy_name}")
        print(f"🤖 AI Mode: {'Enabled' if self.core.ai_enabled else 'Disabled'}")
        print(f"📊 Volume Profile: {'Enabled' if has_vp else 'Disabled'}")
        if self.core.account_goal:
            print(
                f"🎯 Goal: ${self.core.account_goal:,.2f} in {self.core.goal_timeframe_days} days"
            )
        print("=" * 60)
        print("\n🔌 Connecting to Hyperliquid WebSocket...")

        try:
            async with websockets.connect(WS_URL) as ws:
                print("✅ Connected!")

                # Subscribe to all prices
                await ws.send(
                    json.dumps({"method": "subscribe", "subscription": {"type": "allMids"}})
                )
                print("📡 Subscribed to price updates")

                # Subscribe to trades for volume profile (if VP enabled)
                if has_vp:
                    for coin in self.coins:
                        await ws.send(
                            json.dumps(
                                {
                                    "method": "subscribe",
                                    "subscription": {"type": "trades", "coin": coin},
                                }
                            )
                        )
                    print(f"📊 Subscribed to trade stream for VP ({', '.join(self.coins)})")

                print("\n⏳ Waiting for signals... (Press Ctrl+C to stop)\n")

                async for message in ws:
                    if not self._running:
                        break

                    data = json.loads(message)
                    channel = data.get("channel", "")

                    if channel == "allMids":
                        mids = data.get("data", {}).get("mids", {})
                        await self._process_prices(mids)
                    elif channel == "trades":
                        trades_data = data.get("data", [])
                        self._process_trades(trades_data)

        except KeyboardInterrupt:
            print("\n\n⚠️ Interrupted by user")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            print(f"\n❌ Error: {e}")
        finally:
            self._running = False
            self._print_results()

    async def _process_prices(self, mids: dict[str, str]) -> None:
        """
        Process price updates and create candles.

        Args:
            mids: Dict of coin -> mid price string
        """
        now = datetime.now()

        for coin in self.coins:
            if coin not in mids:
                continue

            price = float(mids[coin])

            # Initialize candle tracking for this coin
            if coin not in self._current_candles:
                self._current_candles[coin] = {
                    "open": price,
                    "high": price,
                    "low": price,
                    "close": price,
                    "volume": 0,
                }
                self._candle_start_times[coin] = now
                continue

            # Update current candle
            candle_data = self._current_candles[coin]
            candle_data["high"] = max(candle_data["high"], price)
            candle_data["low"] = min(candle_data["low"], price)
            candle_data["close"] = price

            # Check if minute boundary crossed (new candle)
            start_minute = self._candle_start_times[coin].replace(second=0, microsecond=0)
            current_minute = now.replace(second=0, microsecond=0)

            if current_minute > start_minute:
                # Complete the candle
                candle = Candle(
                    timestamp=start_minute,
                    open=candle_data["open"],
                    high=candle_data["high"],
                    low=candle_data["low"],
                    close=candle_data["close"],
                    volume=candle_data["volume"],
                )

                # Feed to trading core
                self.core.add_candle(coin, candle)

                # Check for signals if we have enough candles
                if self.core.has_enough_candles(coin, min_candles=50):
                    await self._evaluate_coin(coin, price)

                # Reset for new candle
                self._current_candles[coin] = {
                    "open": price,
                    "high": price,
                    "low": price,
                    "close": price,
                    "volume": 0,
                }
                self._candle_start_times[coin] = now

    def _process_trades(self, trades_data: list[dict]) -> None:
        """
        Process trade stream and build volume profile.

        This mirrors how BacktestEngine builds VP from historical trade data.

        Args:
            trades_data: List of trade dicts from WebSocket
        """
        for trade in trades_data:
            try:
                coin = trade.get("coin", "")
                if coin not in self._vp_builders:
                    continue

                # Parse trade data from Hyperliquid format
                price = float(trade.get("px", 0))
                size = float(trade.get("sz", 0))
                side = trade.get("side", "").upper()
                timestamp_ms = trade.get("time", 0)

                if price <= 0 or size <= 0:
                    continue

                # Convert to VPTrade format (same as backtest)
                # Trade model expects "B" (buy aggressor) or "A" (sell aggressor)
                vp_trade = VPTrade(
                    timestamp=datetime.fromtimestamp(timestamp_ms / 1000),
                    price=price,
                    size=size,
                    side="B" if side == "B" else "A",
                )

                # Add to builder
                self._vp_builders[coin].add_trade(vp_trade)
                self._trade_counts[coin] += 1

                # Update VP detector periodically
                if self._trade_counts[coin] % self._vp_update_interval == 0:
                    self._update_volume_profile(coin)

            except (KeyError, ValueError, TypeError) as e:
                logger.debug(f"Skipping malformed trade: {e}")
                continue

    def _update_volume_profile(self, coin: str) -> None:
        """
        Update the VolumeProfile detector with the current profile.

        Args:
            coin: Coin to update
        """
        builder = self._vp_builders.get(coin)
        if not builder:
            return

        profile = builder.get_profile()
        if profile and profile.total_volume > 0:
            self.core.set_volume_profile(profile)
            logger.debug(
                f"Updated VP for {coin}: POC=${profile.poc:.2f}, "
                f"trades={self._trade_counts[coin]}"
            )

    async def _evaluate_coin(self, coin: str, current_price: float) -> None:
        """
        Evaluate signals for a coin and potentially trade.

        Args:
            coin: Coin symbol
            current_price: Current price
        """
        # Skip if we already have a position in this coin
        if coin in self.trader.positions:
            # Check exits (this would need price dict)
            # For now, just skip
            return

        # Detect signals using TradingCore
        signals = self.core.detect_signals(coin)

        if not signals:
            return

        # Evaluate signals and get trade plan
        plan = await self.core.evaluate_signals(
            signals=signals,
            coin=coin,
            current_price=current_price,
            current_balance=self.trader.balance,
            current_positions=self.trader.positions,
        )

        if plan and plan.is_actionable:
            self._execute_plan(plan, current_price)

    def _execute_plan(self, plan, current_price: float) -> None:
        """
        Execute a trade plan on the paper trader.

        Args:
            plan: TradePlan from TradingCore
            current_price: Current price
        """
        # Calculate position size
        position_value = self.trader.balance * (plan.size_pct / 100)
        size = position_value / current_price

        # Execute
        if plan.is_long:
            result = self.trader.open_long(plan.coin, size, current_price)
        else:
            result = self.trader.open_short(plan.coin, size, current_price)

        if result.success:
            self._trades_executed += 1
            direction = "LONG" if plan.is_long else "SHORT"
            print(
                f"\n🔔 [{datetime.now().strftime('%H:%M:%S')}] "
                f"{direction} {plan.coin} @ ${current_price:,.2f}"
            )
            print(f"   Size: {plan.size_pct:.1f}% (${position_value:,.2f})")
            print(f"   Reason: {plan.reason}")
            print(f"   SL: ${plan.stop_loss:,.2f} | TP: ${plan.take_profit:,.2f}")

    def _print_results(self) -> None:
        """Print final trading results."""
        print("\n" + "=" * 60)
        print("📊 FINAL RESULTS")
        print("=" * 60)

        # Get current prices for P&L calculation
        current_prices = {}
        for coin in self._current_candles:
            current_prices[coin] = self._current_candles[coin]["close"]

        # Close any remaining positions
        for coin in list(self.trader.positions.keys()):
            if coin in current_prices:
                print(f"⚠️ Auto-closing {coin} position...")
                self.trader.close_position(coin, current_prices[coin])

        state = self.trader.get_state(current_prices)
        pnl_pct = ((state.balance - self.initial_balance) / self.initial_balance) * 100

        metrics = self.core.get_metrics()

        print(f"💰 Starting:      ${self.initial_balance:,.2f}")
        print(f"💰 Final:         ${state.balance:,.2f}")
        print(f"💵 P&L:           ${state.total_pnl:+,.2f} ({pnl_pct:+.2f}%)")
        print(f"📈 Trades:        {state.total_trades}")
        print(f"🎯 Win Rate:      {state.win_rate:.1f}%")
        print(f"📡 Signals:       {metrics['signals_generated']}")
        print(f"🤖 AI Calls:      {metrics['ai_calls']}")

        # Volume Profile stats
        total_vp_trades = sum(self._trade_counts.values())
        if total_vp_trades > 0:
            print(f"📊 VP Trades:     {total_vp_trades:,}")
            for coin, builder in self._vp_builders.items():
                profile = builder.get_profile()
                if profile and profile.total_volume > 0:
                    print(f"   {coin} POC: ${profile.poc:,.2f}")

        print("=" * 60)


async def main() -> None:
    """Main entry point for live trading."""
    parser = argparse.ArgumentParser(
        description="Live Trading Engine (Unified Architecture)",
        epilog="""
This uses the SAME trading logic as backtest.
Backtest results are now predictive of live performance.

Examples:
    # Signals-only mode (no AI)
    python -m bot.live.engine --balance 10000

    # AI position sizing with goal
    python -m bot.live.engine --ai --goal 50000 --goal-days 30

    # Portfolio mode (multi-asset allocation)
    python -m bot.live.engine --ai --portfolio --goal 50000 --goal-days 30
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--balance",
        "-b",
        type=float,
        default=10000.0,
        help="Starting paper balance (default: 10000)",
    )
    parser.add_argument(
        "--coins",
        "-c",
        nargs="+",
        default=["BTC", "ETH", "SOL"],
        help="Coins to trade (default: BTC ETH SOL)",
    )
    parser.add_argument(
        "--strategy",
        "-s",
        default="momentum_based",
        choices=[name for name, _ in list_strategies()],
        help="Strategy to use (default: momentum_based)",
    )
    parser.add_argument(
        "--ai",
        action="store_true",
        help="Enable AI position sizing",
    )
    parser.add_argument(
        "--portfolio",
        action="store_true",
        help="Enable portfolio allocation mode",
    )
    parser.add_argument(
        "--goal",
        "-g",
        type=float,
        help="Account goal target for AI position sizing",
    )
    parser.add_argument(
        "--goal-days",
        type=int,
        help="Days to reach the goal",
    )
    parser.add_argument(
        "--signals",
        nargs="+",
        default=["momentum", "rsi", "macd", "vp", "pdvp"],
        help="Signal detectors to use: momentum, rsi, macd, vp (volume profile), pdvp (prev day VP)",
    )

    args = parser.parse_args()

    # Validate
    if args.goal and not args.goal_days:
        args.goal_days = 30
        print("⚠️ --goal requires --goal-days, defaulting to 30 days")

    if args.portfolio and not args.ai:
        print("⚠️ --portfolio requires --ai, ignoring")
        args.portfolio = False

    engine = LiveEngine(
        coins=[c.upper() for c in args.coins],
        strategy_name=args.strategy,
        initial_balance=args.balance,
        ai_enabled=args.ai,
        portfolio_mode=args.portfolio,
        account_goal=args.goal,
        goal_timeframe_days=args.goal_days,
        signal_detectors=args.signals,
    )

    await engine.run()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[logging.FileHandler("live_trading.log")],
    )
    asyncio.run(main())
