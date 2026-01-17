#!/usr/bin/env python3
"""
Example: Placing orders on Hyperliquid testnet.

Demonstrates market orders, limit orders, and order cancellation.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from bot.hyperliquid.client import HyperliquidClient


def example_market_order():
    """Place a small market buy order."""
    client = HyperliquidClient.from_env()

    print("Placing market buy order for 0.001 ETH...")
    result = client.market_buy("ETH", size=0.001, slippage=0.02)

    if result.success:
        print(f"✓ Order filled!")
        print(f"  Order ID: {result.order_id}")
        print(f"  Filled: {result.filled_size} ETH")
        print(f"  Avg Price: ${result.avg_price:,.2f}")
    else:
        print(f"✗ Order failed: {result.error}")


def example_limit_order():
    """Place a limit order below current price (won't fill immediately)."""
    client = HyperliquidClient.from_env()

    # Get current price and place order 5% below
    current_price = client.get_price("ETH")
    if not current_price:
        print("Could not get ETH price")
        return

    limit_price = current_price * 0.95
    print(f"Current ETH price: ${current_price:,.2f}")
    print(f"Placing limit buy at ${limit_price:,.2f} (5% below market)...")

    result = client.limit_order(
        coin="ETH",
        is_buy=True,
        size=0.001,
        price=limit_price,
        time_in_force="Gtc",
    )

    if result.success:
        print(f"✓ Limit order placed!")
        print(f"  Order ID: {result.order_id}")

        # Cancel it since this is just a demo
        print("Cancelling order (demo cleanup)...")
        cancelled = client.cancel_order("ETH", int(result.order_id))
        print(f"  Cancelled: {cancelled}")
    else:
        print(f"✗ Order failed: {result.error}")


def example_close_position():
    """Close any open ETH position."""
    client = HyperliquidClient.from_env()

    positions = client.get_positions()
    eth_position = next(
        (p for p in positions if p.get("position", {}).get("coin") == "ETH"),
        None,
    )

    if not eth_position:
        print("No ETH position to close")
        return

    size = float(eth_position["position"]["szi"])
    print(f"Closing ETH position: {size:+.4f}")

    result = client.close_position("ETH")
    if result.success:
        print("✓ Position closed!")
    else:
        print(f"✗ Failed to close: {result.error}")


if __name__ == "__main__":
    print("=" * 50)
    print("Order Examples")
    print("=" * 50)

    if len(sys.argv) > 1:
        example = sys.argv[1]
        if example == "market":
            example_market_order()
        elif example == "limit":
            example_limit_order()
        elif example == "close":
            example_close_position()
        else:
            print(f"Unknown example: {example}")
            print("Options: market, limit, close")
    else:
        print("Usage: python place_order.py [market|limit|close]")
        print()
        print("Examples:")
        print("  python place_order.py market  # Place market buy")
        print("  python place_order.py limit   # Place and cancel limit order")
        print("  python place_order.py close   # Close ETH position")
