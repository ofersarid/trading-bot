#!/usr/bin/env python3
"""
Paper Trading Simulator Runner

Connects everything together:
1. WebSocket stream for live prices
2. Opportunity Seeker for detecting trades
3. Paper Trader for simulating execution

Run with:
    python bot/simulation/run_simulator.py --balance 10000

Press Ctrl+C to stop and see final results.
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import websockets

from bot.simulation.models import HYPERLIQUID_FEES, Side
from bot.simulation.paper_trader import PaperTrader
from bot.simulation.opportunity_seeker import OpportunitySeeker, Opportunity, Signal


# Hyperliquid WebSocket
WS_URL = "wss://api.hyperliquid.xyz/ws"


class TradingSimulator:
    """
    Main simulator that connects WebSocket → Strategy → Paper Trader.
    """
    
    def __init__(
        self,
        starting_balance: float = 10000,
        coins: list[str] = None,
        position_size_pct: float = 0.1,  # Use 10% of balance per trade
        verbose: bool = True,
    ):
        self.coins = coins or ["BTC", "ETH", "SOL"]
        self.position_size_pct = position_size_pct
        self.verbose = verbose
        
        # Initialize paper trader
        self.trader = PaperTrader(
            starting_balance=starting_balance,
            fees=HYPERLIQUID_FEES,
            on_trade=self._on_trade_complete,
        )
        
        # Initialize opportunity seeker
        self.seeker = OpportunitySeeker(
            coins=self.coins,
            momentum_threshold_pct=0.3,   # 0.3% move = signal
            lookback_seconds=60,           # Measure over 60 seconds
            take_profit_pct=0.5,          # Take profit at 0.5%
            stop_loss_pct=0.3,            # Stop loss at 0.3%
            cooldown_seconds=30,          # 30s between signals
            on_opportunity=self._on_opportunity,
        )
        
        # Stats
        self.signals_received = 0
        self.start_time = None
    
    def _on_opportunity(self, opp: Opportunity):
        """Handle detected opportunity."""
        self.signals_received += 1
        
        if self.verbose:
            timestamp = opp.timestamp.strftime("%H:%M:%S")
            emoji = "🟢" if opp.signal == Signal.LONG else "🔴" if opp.signal == Signal.SHORT else "⚪"
            print(f"\n{emoji} [{timestamp}] SIGNAL: {opp.signal.value.upper()} {opp.coin}")
            print(f"   Price: ${opp.price:,.2f}")
            print(f"   Reason: {opp.reason}")
            print(f"   Strength: {opp.strength:.0%}")
        
        # Execute the signal
        self._execute_signal(opp)
    
    def _execute_signal(self, opp: Opportunity):
        """Execute a trading signal on the paper trader."""
        price = opp.price
        coin = opp.coin
        
        if opp.signal == Signal.CLOSE:
            # Close existing position
            result = self.trader.close_position(coin, price)
            if self.verbose:
                print(f"   → {result.message}")
            # Clear seeker's position tracking
            self.seeker.clear_position(coin)
            
        elif opp.signal in (Signal.LONG, Signal.SHORT):
            # Calculate position size
            balance = self.trader.balance
            position_value = balance * self.position_size_pct
            size = position_value / price
            
            # Open position
            if opp.signal == Signal.LONG:
                result = self.trader.open_long(coin, size, price)
            else:
                result = self.trader.open_short(coin, size, price)
            
            if self.verbose:
                print(f"   → {result.message}")
            
            # If failed, clear seeker's position tracking
            if not result.success:
                self.seeker.clear_position(coin)
    
    def _on_trade_complete(self, trade):
        """Called when a trade is closed."""
        if self.verbose:
            emoji = "✅" if trade.pnl > 0 else "❌"
            print(f"\n{emoji} TRADE CLOSED: {trade.coin}")
            print(f"   P&L: ${trade.pnl:+,.2f} ({trade.pnl_percent:+.2f}%)")
            print(f"   Duration: {trade.duration_seconds:.0f}s")
    
    async def run(self):
        """Main run loop - connects to WebSocket and processes prices."""
        self.start_time = datetime.now()
        
        print("=" * 60)
        print("🤖 PAPER TRADING SIMULATOR")
        print("=" * 60)
        print(f"💰 Starting Balance: ${self.trader.starting_balance:,.2f}")
        print(f"📊 Watching: {', '.join(self.coins)}")
        print(f"📈 Position Size: {self.position_size_pct*100:.0f}% of balance")
        print("=" * 60)
        print("\n🔌 Connecting to Hyperliquid WebSocket...")
        
        try:
            async with websockets.connect(WS_URL) as ws:
                print("✅ Connected!")
                
                # Subscribe to all prices
                await ws.send(json.dumps({
                    "method": "subscribe",
                    "subscription": {"type": "allMids"}
                }))
                print("📡 Subscribed to price updates")
                print("\n⏳ Waiting for opportunities... (Press Ctrl+C to stop)\n")
                
                # Process messages
                async for message in ws:
                    data = json.loads(message)
                    
                    if data.get("channel") == "allMids":
                        mids = data.get("data", {}).get("mids", {})
                        
                        # Update seeker with new prices
                        for coin in self.coins:
                            if coin in mids:
                                price = float(mids[coin])
                                self.seeker.update_price(coin, price)
                        
        except KeyboardInterrupt:
            pass
        
        # Print final results
        self._print_final_results()
    
    def _print_final_results(self):
        """Print final simulation results."""
        current_prices = self.seeker.get_current_prices()
        
        # Close any remaining positions at current price
        for coin in list(self.trader.positions.keys()):
            if coin in current_prices:
                print(f"\n⚠️ Auto-closing open position in {coin}...")
                self.trader.close_position(coin, current_prices[coin])
        
        duration = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        
        print("\n" + "=" * 60)
        print("📊 FINAL RESULTS")
        print("=" * 60)
        
        state = self.trader.get_state(current_prices)
        
        pnl_pct = ((state.balance - self.trader.starting_balance) / self.trader.starting_balance) * 100
        
        print(f"⏱️  Duration:        {duration/60:.1f} minutes")
        print(f"📡 Signals:         {self.signals_received}")
        print(f"📈 Trades:          {state.total_trades}")
        print(f"🎯 Win Rate:        {state.win_rate:.1f}%")
        print()
        print(f"💰 Starting:        ${self.trader.starting_balance:,.2f}")
        print(f"💰 Final Balance:   ${state.balance:,.2f}")
        print(f"💵 Total P&L:       ${state.total_pnl:+,.2f} ({pnl_pct:+.2f}%)")
        print(f"💸 Fees Paid:       ${state.total_fees:,.2f}")
        print("=" * 60)
        
        # Trade history
        if self.trader.trade_history:
            print("\n📜 TRADE HISTORY:")
            print("-" * 60)
            for i, trade in enumerate(self.trader.trade_history, 1):
                side = "LONG" if trade.side == Side.LONG else "SHORT"
                emoji = "✅" if trade.pnl > 0 else "❌"
                print(f"{i}. {emoji} {side} {trade.coin}: ${trade.pnl:+,.2f} ({trade.pnl_percent:+.2f}%)")
        
        print()


def main():
    parser = argparse.ArgumentParser(description="Paper Trading Simulator")
    parser.add_argument(
        "--balance", "-b",
        type=float,
        default=10000,
        help="Starting balance in USD (default: 10000)"
    )
    parser.add_argument(
        "--coins", "-c",
        nargs="+",
        default=["BTC", "ETH", "SOL"],
        help="Coins to watch (default: BTC ETH SOL)"
    )
    parser.add_argument(
        "--size", "-s",
        type=float,
        default=0.1,
        help="Position size as fraction of balance (default: 0.1 = 10%%)"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress trade-by-trade output"
    )
    
    args = parser.parse_args()
    
    simulator = TradingSimulator(
        starting_balance=args.balance,
        coins=[c.upper() for c in args.coins],
        position_size_pct=args.size,
        verbose=not args.quiet,
    )
    
    asyncio.run(simulator.run())


if __name__ == "__main__":
    main()
