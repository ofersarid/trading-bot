#!/usr/bin/env python3
"""
Real-time WebSocket streaming from Hyperliquid.

This connects to Hyperliquid's WebSocket API and receives 
price updates the INSTANT they happen - no polling!

For React developers:
- This is like a WebSocket connection in JS
- We subscribe to "channels" and receive events
- Uses async/await (similar to JS Promises)
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import websockets

# Hyperliquid WebSocket endpoint (public - no auth needed!)
WS_URL = "wss://api.hyperliquid.xyz/ws"


async def stream_prices(coins: list[str], on_price_update=None):
    """
    Stream live prices via WebSocket.
    
    Args:
        coins: List of coins to watch (e.g., ["BTC", "ETH"])
        on_price_update: Optional callback function(coin, price, timestamp)
    
    This runs forever until interrupted (Ctrl+C).
    """
    print(f"🔌 Connecting to Hyperliquid WebSocket...")
    
    async with websockets.connect(WS_URL) as ws:
        print(f"✅ Connected!")
        print()
        
        # Subscribe to allMids (all prices) channel
        subscribe_msg = {
            "method": "subscribe",
            "subscription": {"type": "allMids"}
        }
        await ws.send(json.dumps(subscribe_msg))
        print(f"📡 Subscribed to price updates")
        print(f"👀 Watching: {', '.join(coins)}")
        print("=" * 60)
        print()
        
        # Track previous prices for change calculation
        prev_prices = {}
        
        # Listen for messages
        async for message in ws:
            data = json.loads(message)
            
            # Handle price updates
            if data.get("channel") == "allMids":
                mids = data.get("data", {}).get("mids", {})
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                
                # Print updates for watched coins
                for coin in coins:
                    if coin in mids:
                        price = float(mids[coin])
                        prev = prev_prices.get(coin)
                        
                        # Calculate change
                        if prev is not None:
                            change = price - prev
                            if change != 0:  # Only show if changed
                                arrow = "▲" if change > 0 else "▼"
                                color_sign = "+" if change > 0 else ""
                                print(f"⚡ {timestamp}  {coin:6} ${price:>12,.2f}  {arrow} {color_sign}{change:.2f}")
                                
                                # Call callback if provided
                                if on_price_update:
                                    on_price_update(coin, price, timestamp)
                        else:
                            # First update - just show price
                            print(f"⚡ {timestamp}  {coin:6} ${price:>12,.2f}  (connected)")
                        
                        prev_prices[coin] = price


async def stream_trades(coin: str):
    """
    Stream live trades for a specific coin.
    
    Shows every trade as it happens!
    """
    print(f"🔌 Connecting to Hyperliquid WebSocket...")
    
    async with websockets.connect(WS_URL) as ws:
        print(f"✅ Connected!")
        
        # Subscribe to trades for this coin
        subscribe_msg = {
            "method": "subscribe",
            "subscription": {"type": "trades", "coin": coin}
        }
        await ws.send(json.dumps(subscribe_msg))
        print(f"📡 Subscribed to {coin} trades")
        print("=" * 60)
        print()
        
        async for message in ws:
            data = json.loads(message)
            
            if data.get("channel") == "trades":
                trades = data.get("data", [])
                for trade in trades:
                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    price = float(trade.get("px", 0))
                    size = float(trade.get("sz", 0))
                    side = trade.get("side", "?")
                    
                    # B = Buy (someone bought), A = Sell (someone sold)
                    side_emoji = "🟢" if side == "B" else "🔴"
                    side_text = "BUY " if side == "B" else "SELL"
                    
                    print(f"{side_emoji} {timestamp}  {side_text} {size:>10.4f} {coin} @ ${price:,.2f}")


async def stream_orderbook(coin: str):
    """
    Stream live order book updates.
    
    Shows bids and asks updating in real-time!
    """
    print(f"🔌 Connecting to Hyperliquid WebSocket...")
    
    async with websockets.connect(WS_URL) as ws:
        print(f"✅ Connected!")
        
        # Subscribe to L2 order book
        subscribe_msg = {
            "method": "subscribe", 
            "subscription": {"type": "l2Book", "coin": coin}
        }
        await ws.send(json.dumps(subscribe_msg))
        print(f"📡 Subscribed to {coin} order book")
        print("=" * 60)
        print()
        
        async for message in ws:
            data = json.loads(message)
            
            if data.get("channel") == "l2Book":
                book = data.get("data", {})
                levels = book.get("levels", [[], []])
                
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                
                # Get top 5 bids and asks
                bids = levels[0][:5] if len(levels) > 0 else []
                asks = levels[1][:5] if len(levels) > 1 else []
                
                # Clear screen and print order book
                print(f"\033[H\033[J", end="")  # Clear screen
                print(f"📊 {coin} Order Book - {timestamp}")
                print("=" * 50)
                print(f"{'ASKS (Sells)':^50}")
                print("-" * 50)
                
                # Print asks (reversed so lowest ask is at bottom)
                for ask in reversed(asks):
                    price = float(ask.get("px", 0))
                    size = float(ask.get("sz", 0))
                    print(f"  🔴 ${price:>12,.2f}  |  {size:>12.4f}")
                
                print("-" * 50)
                print(f"{'--- SPREAD ---':^50}")
                print("-" * 50)
                
                # Print bids
                for bid in bids:
                    price = float(bid.get("px", 0))
                    size = float(bid.get("sz", 0))
                    print(f"  🟢 ${price:>12,.2f}  |  {size:>12.4f}")
                
                print("-" * 50)
                print(f"{'BIDS (Buys)':^50}")


# ============================================================
# Run from command line
# ============================================================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Stream live data from Hyperliquid")
    parser.add_argument("mode", choices=["prices", "trades", "orderbook"], 
                        help="What to stream")
    parser.add_argument("coins", nargs="*", default=["BTC", "ETH"],
                        help="Coins to watch (default: BTC ETH)")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🚀 HYPERLIQUID LIVE STREAM (WebSocket)")
    print("   Press Ctrl+C to stop")
    print("=" * 60)
    print()
    
    try:
        if args.mode == "prices":
            asyncio.run(stream_prices([c.upper() for c in args.coins]))
        elif args.mode == "trades":
            coin = args.coins[0].upper() if args.coins else "BTC"
            asyncio.run(stream_trades(coin))
        elif args.mode == "orderbook":
            coin = args.coins[0].upper() if args.coins else "BTC"
            asyncio.run(stream_orderbook(coin))
    except KeyboardInterrupt:
        print("\n\n👋 Stream stopped.")
