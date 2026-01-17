#!/usr/bin/env python3
"""
Example: Fetching market data from Hyperliquid.

Demonstrates how to get prices, order books, and market metadata.
"""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from bot.hyperliquid.client import HyperliquidClient


def show_all_prices():
    """Display current prices for major coins."""
    client = HyperliquidClient.from_env()

    coins = ["BTC", "ETH", "SOL", "AVAX", "ARB", "OP", "DOGE", "LINK"]

    print("Current Prices")
    print("-" * 30)

    for coin in coins:
        price = client.get_price(coin)
        if price:
            print(f"{coin:6} ${price:>12,.2f}")
        else:
            print(f"{coin:6} {'N/A':>12}")


def show_markets():
    """List all available trading pairs."""
    client = HyperliquidClient.from_env()

    markets = client.get_markets()

    print(f"Available Markets ({len(markets)} total)")
    print("-" * 50)
    print(f"{'Name':<10} {'Max Leverage':>12} {'Tick Size':>12}")
    print("-" * 50)

    for market in sorted(markets, key=lambda m: m.get("name", "")):
        name = market.get("name", "?")
        max_leverage = market.get("maxLeverage", "?")
        # szDecimals indicates precision
        sz_decimals = market.get("szDecimals", "?")
        print(f"{name:<10} {max_leverage:>12}x {sz_decimals:>12} decimals")


def show_account_summary():
    """Display account summary with balance and positions."""
    client = HyperliquidClient.from_env()

    print(f"Account: {client.address}")
    print(f"Environment: {client.env}")
    print("-" * 50)

    balance = client.get_balance()
    print(f"Account Value: ${balance:,.2f}")

    positions = client.get_positions()
    if positions:
        print(f"\nOpen Positions ({len(positions)}):")
        print(f"{'Coin':<6} {'Size':>10} {'Entry':>12} {'PnL':>12}")
        print("-" * 42)

        for pos in positions:
            p = pos.get("position", {})
            coin = p.get("coin", "?")
            size = float(p.get("szi", 0))
            entry = float(p.get("entryPx", 0))
            pnl = float(p.get("unrealizedPnl", 0))
            print(f"{coin:<6} {size:>+10.4f} ${entry:>10,.2f} ${pnl:>+10.2f}")
    else:
        print("\nNo open positions")

    orders = client.get_open_orders()
    if orders:
        print(f"\nOpen Orders ({len(orders)}):")
        for order in orders:
            coin = order.get("coin", "?")
            side = "BUY" if order.get("side") == "B" else "SELL"
            size = order.get("sz", "?")
            price = order.get("limitPx", "?")
            print(f"  {coin} {side} {size} @ ${price}")
    else:
        print("\nNo open orders")


if __name__ == "__main__":
    print("=" * 50)
    print("Market Data Examples")
    print("=" * 50)

    if len(sys.argv) > 1:
        example = sys.argv[1]
        if example == "prices":
            show_all_prices()
        elif example == "markets":
            show_markets()
        elif example == "account":
            show_account_summary()
        else:
            print(f"Unknown example: {example}")
            print("Options: prices, markets, account")
    else:
        print("Usage: python market_data.py [prices|markets|account]")
        print()
        print("Running all examples...")
        print()

        show_all_prices()
        print()
        show_account_summary()
