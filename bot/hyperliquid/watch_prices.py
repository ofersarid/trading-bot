#!/usr/bin/env python3
"""
Watch live prices updating in real-time.

This polls the API every second to show price changes.
(Not a true WebSocket stream, but demonstrates the concept)

Press Ctrl+C to stop.
"""

import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bot.hyperliquid.public_data import get_all_prices


def watch_prices(coins: list[str] = None, interval: float = 1.0):
    """
    Watch prices update in real-time.
    
    Args:
        coins: List of coins to watch (default: BTC, ETH, SOL)
        interval: Seconds between updates (default: 1)
    """
    if coins is None:
        coins = ["BTC", "ETH", "SOL"]
    
    print("=" * 60)
    print("📈 LIVE PRICE WATCHER (Press Ctrl+C to stop)")
    print("=" * 60)
    print()
    
    # Store previous prices to show changes
    prev_prices = {}
    
    try:
        while True:
            prices = get_all_prices()
            now = datetime.now().strftime("%H:%M:%S")
            
            # Clear line and print header
            print(f"\r⏰ {now}", end="")
            print(" " * 40)  # Clear rest of line
            
            for coin in coins:
                price = prices.get(coin)
                if price is None:
                    continue
                
                # Calculate change from last update
                prev = prev_prices.get(coin)
                if prev is not None:
                    change = price - prev
                    pct = (change / prev) * 100
                    
                    # Color indicator (using text since terminal may not support colors)
                    if change > 0:
                        arrow = "▲"
                        sign = "+"
                    elif change < 0:
                        arrow = "▼"
                        sign = ""
                    else:
                        arrow = "─"
                        sign = ""
                    
                    print(f"   {coin:6} ${price:>12,.2f}  {arrow} {sign}{change:>8,.2f} ({sign}{pct:.3f}%)")
                else:
                    print(f"   {coin:6} ${price:>12,.2f}")
                
                prev_prices[coin] = price
            
            print()
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\n👋 Stopped watching prices.")


if __name__ == "__main__":
    # Allow passing coins as arguments
    if len(sys.argv) > 1:
        coins = [c.upper() for c in sys.argv[1:]]
    else:
        coins = ["BTC", "ETH", "SOL"]
    
    print(f"Watching: {', '.join(coins)}")
    print("(Run with different coins: python watch_prices.py BTC ETH DOGE)")
    print()
    
    watch_prices(coins, interval=1.0)
