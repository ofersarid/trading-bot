"""
Public Market Data from Hyperliquid.

This module fetches live prices, candles, and market info WITHOUT authentication.
Perfect for paper trading simulation - no API keys needed!

For React developers:
- Python 'def' = JavaScript 'function'
- Python 'class' = JavaScript 'class' (very similar!)
- Python uses indentation instead of { } for blocks
- 'self' in Python = 'this' in JavaScript
"""

import requests

# Hyperliquid's public API endpoint (no auth required)
API_URL = "https://api.hyperliquid.xyz/info"


def get_all_prices() -> dict[str, float]:
    """
    Get current prices for ALL trading pairs.

    Returns:
        Dictionary like {"BTC": 97500.0, "ETH": 3200.0, ...}

    Example:
        prices = get_all_prices()
        print(prices["BTC"])  # 97500.0
    """
    response = requests.post(API_URL, json={"type": "allMids"})
    response.raise_for_status()  # Raises error if request failed
    return {coin: float(price) for coin, price in response.json().items()}


def get_price(coin: str) -> float | None:
    """
    Get current price for a single coin.

    Args:
        coin: Symbol like "BTC", "ETH", "SOL"

    Returns:
        Current price, or None if coin not found

    Example:
        btc_price = get_price("BTC")
        print(f"Bitcoin: ${btc_price:,.2f}")
    """
    prices = get_all_prices()
    return prices.get(coin)


def get_markets() -> list[dict]:
    """
    Get info about all available trading pairs.

    Returns:
        List of market info (name, max leverage, etc.)
    """
    response = requests.post(API_URL, json={"type": "meta"})
    response.raise_for_status()
    result: list[dict] = response.json().get("universe", [])
    return result


def get_candles(coin: str, interval: str = "1m", limit: int = 100) -> list[dict]:
    """
    Get historical price candles (OHLCV data).

    Args:
        coin: Symbol like "BTC", "ETH"
        interval: Candle size - "1m", "5m", "15m", "1h", "4h", "1d"
        limit: Number of candles to fetch (max ~5000)

    Returns:
        List of candles, each with: open, high, low, close, volume, timestamp

    Example:
        candles = get_candles("BTC", "1m", 50)
        latest = candles[-1]
        print(f"BTC Close: ${latest['close']}")
    """
    # Hyperliquid uses millisecond timestamps
    import time

    end_time = int(time.time() * 1000)

    # Calculate start time based on interval
    interval_ms = {
        "1m": 60 * 1000,
        "5m": 5 * 60 * 1000,
        "15m": 15 * 60 * 1000,
        "1h": 60 * 60 * 1000,
        "4h": 4 * 60 * 60 * 1000,
        "1d": 24 * 60 * 60 * 1000,
    }

    ms_per_candle = interval_ms.get(interval, 60 * 1000)
    start_time = end_time - (limit * ms_per_candle)

    response = requests.post(
        API_URL,
        json={
            "type": "candleSnapshot",
            "req": {
                "coin": coin,
                "interval": interval,
                "startTime": start_time,
                "endTime": end_time,
            },
        },
    )
    response.raise_for_status()

    raw_candles = response.json()

    # Convert to friendlier format
    candles = []
    for c in raw_candles:
        candles.append(
            {
                "timestamp": c["t"],
                "open": float(c["o"]),
                "high": float(c["h"]),
                "low": float(c["l"]),
                "close": float(c["c"]),
                "volume": float(c["v"]),
            }
        )

    return candles


def get_orderbook(coin: str) -> dict:
    """
    Get current order book (bids and asks).

    Args:
        coin: Symbol like "BTC", "ETH"

    Returns:
        Dict with 'bids' and 'asks' lists
    """
    response = requests.post(
        API_URL,
        json={"type": "l2Book", "coin": coin},
    )
    response.raise_for_status()

    data = response.json()

    # Parse into friendlier format
    return {
        "bids": [
            {"price": float(level["px"]), "size": float(level["sz"])}
            for level in data.get("levels", [[]])[0]
        ],
        "asks": [
            {"price": float(level["px"]), "size": float(level["sz"])}
            for level in data.get("levels", [[], []])[1]
        ],
    }


# ============================================================
# Quick test - run this file directly to see it working!
# ============================================================
if __name__ == "__main__":
    print("=" * 50)
    print("🔌 Testing Hyperliquid Public API (No Auth Needed!)")
    print("=" * 50)
    print()

    # Test 1: Get all prices
    print("📊 Fetching live prices...")
    prices = get_all_prices()
    print(f"   Found {len(prices)} trading pairs")
    print()

    # Test 2: Show top coins
    top_coins = ["BTC", "ETH", "SOL", "DOGE"]
    print("💰 Current Prices:")
    print("-" * 30)
    for coin in top_coins:
        price = prices.get(coin)
        if price:
            print(f"   {coin:6} ${price:>12,.2f}")
    print()

    # Test 3: Get recent candles
    print("🕯️  Last 5 BTC 1-minute candles:")
    print("-" * 50)
    candles = get_candles("BTC", "1m", 5)
    for candle in candles:
        print(f"   Close: ${candle['close']:,.2f}  |  Volume: {candle['volume']:,.4f}")
    print()

    print("✅ All tests passed! Market data is working.")
