#!/usr/bin/env python3
"""
Test script to verify Hyperliquid API connection.

Run this after setting up your .env file to confirm everything works.
"""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bot.hyperliquid.client import HyperliquidClient


def main():
    print("=" * 50)
    print("Hyperliquid Connection Test")
    print("=" * 50)

    # Load client from environment
    try:
        client = HyperliquidClient.from_env()
        print("✓ Client initialized successfully")
        print(f"  Environment: {client.env}")
        print(f"  Address: {client.address}")
    except ValueError as e:
        print(f"✗ Failed to initialize client: {e}")
        print("\nMake sure you have a .env file with HYPERLIQUID_PRIVATE_KEY set.")
        return 1

    print()

    # Test account state
    print("Fetching account state...")
    try:
        state = client.get_user_state()
        balance = client.get_balance()
        print("✓ Account state retrieved")
        print(f"  Account Value: ${balance:,.2f}")

        margin = state.get("marginSummary", {})
        print(f"  Total Margin Used: ${float(margin.get('totalMarginUsed', 0)):,.2f}")
        print(f"  Withdrawable: ${float(margin.get('withdrawable', 0)):,.2f}")
    except Exception as e:
        print(f"✗ Failed to get account state: {e}")
        return 1

    print()

    # Test positions
    print("Fetching positions...")
    try:
        positions = client.get_positions()
        if positions:
            print(f"✓ Found {len(positions)} position(s):")
            for pos in positions:
                position = pos.get("position", {})
                coin = position.get("coin", "?")
                size = float(position.get("szi", 0))
                entry = float(position.get("entryPx", 0))
                pnl = float(position.get("unrealizedPnl", 0))
                print(f"  {coin}: {size:+.4f} @ ${entry:,.2f} (PnL: ${pnl:+,.2f})")
        else:
            print("✓ No open positions")
    except Exception as e:
        print(f"✗ Failed to get positions: {e}")

    print()

    # Test market data
    print("Fetching available markets...")
    try:
        markets = client.get_markets()
        print(f"✓ Found {len(markets)} trading pairs")

        # Show a few examples
        print("  Sample markets:")
        for market in markets[:5]:
            name = market.get("name", "?")
            print(f"    - {name}")
        if len(markets) > 5:
            print(f"    ... and {len(markets) - 5} more")
    except Exception as e:
        print(f"✗ Failed to get markets: {e}")

    print()

    # Test price fetch
    print("Fetching current prices...")
    try:
        test_coins = ["BTC", "ETH", "SOL"]
        for coin in test_coins:
            price = client.get_price(coin)
            if price:
                print(f"  {coin}: ${price:,.2f}")
            else:
                print(f"  {coin}: Not available")
        print("✓ Price data retrieved")
    except Exception as e:
        print(f"✗ Failed to get prices: {e}")

    print()
    print("=" * 50)
    print("Connection test complete!")
    print("=" * 50)

    if balance == 0:
        print()
        print("⚠ Your balance is $0. To start paper trading:")
        print("  1. Go to https://app.hyperliquid-testnet.xyz/drip")
        print("  2. Claim testnet USDC from the faucet")
        print("  (Note: You need to have used mainnet first)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
