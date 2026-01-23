"""
Bybit Historical Data Fetcher.

Downloads historical kline (candlestick) data from Bybit's public API.
"""

import csv
import time
from datetime import datetime
from pathlib import Path

import httpx

from bot.historical.models import HistoricalCandle

# Bybit API endpoint
BYBIT_API_URL = "https://api.bybit.com/v5/market/kline"

# Maximum candles per request (Bybit limit)
MAX_LIMIT = 1000

# Interval to milliseconds mapping
INTERVAL_MS = {
    "1": 60_000,
    "3": 3 * 60_000,
    "5": 5 * 60_000,
    "15": 15 * 60_000,
    "30": 30 * 60_000,
    "60": 60 * 60_000,
    "120": 2 * 60 * 60_000,
    "240": 4 * 60 * 60_000,
    "360": 6 * 60 * 60_000,
    "720": 12 * 60 * 60_000,
    "D": 24 * 60 * 60_000,
    "W": 7 * 24 * 60 * 60_000,
}


class BybitHistoricalFetcher:
    """
    Fetches historical kline data from Bybit.

    Usage:
        fetcher = BybitHistoricalFetcher()
        candles = fetcher.fetch(
            symbol="BTCUSDT",
            start=datetime(2026, 1, 12, 10, 15),
            end=datetime(2026, 1, 12, 11, 15),
            interval="1",
        )
        fetcher.save_csv(candles, "data/historical/btc_data.csv")
    """

    def __init__(self, category: str = "linear"):
        """
        Initialize the fetcher.

        Args:
            category: Market category - "linear" (USDT perps), "spot", or "inverse"
        """
        self.category = category
        self.client = httpx.Client(timeout=30.0)

    def fetch(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        interval: str = "1",
        verbose: bool = True,
    ) -> list[HistoricalCandle]:
        """
        Fetch historical kline data.

        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            start: Start datetime
            end: End datetime
            interval: Candle interval ("1", "5", "15", "60", etc.)
            verbose: Print progress

        Returns:
            List of HistoricalCandle objects, sorted by timestamp ascending
        """
        start_ms = int(start.timestamp() * 1000)
        end_ms = int(end.timestamp() * 1000)
        interval_ms = INTERVAL_MS.get(interval, 60_000)

        # Calculate expected candles
        expected = (end_ms - start_ms) // interval_ms
        if verbose:
            print(f"📡 Requesting klines... (~{expected} candles expected)")

        all_candles: list[HistoricalCandle] = []
        current_end = end_ms
        request_count = 0

        while current_end > start_ms:
            params: dict[str, str | int] = {
                "category": self.category,
                "symbol": symbol,
                "interval": interval,
                "end": current_end,
                "limit": MAX_LIMIT,
            }

            response = self.client.get(BYBIT_API_URL, params=params)
            data = response.json()

            if data.get("retCode") != 0:
                raise RuntimeError(f"Bybit API error: {data.get('retMsg', 'Unknown error')}")

            candles_data = data.get("result", {}).get("list", [])
            if not candles_data:
                break

            # Convert to HistoricalCandle objects
            for candle_data in candles_data:
                candle = HistoricalCandle.from_bybit_response(candle_data)
                # Only include candles within our range
                candle_ms = int(candle.timestamp.timestamp() * 1000)
                if start_ms <= candle_ms < end_ms:
                    all_candles.append(candle)

            # Get oldest candle timestamp for next iteration
            oldest_ms = int(candles_data[-1][0])
            if oldest_ms >= current_end:
                # No progress, avoid infinite loop
                break
            current_end = oldest_ms

            request_count += 1
            if verbose and request_count % 5 == 0:
                print(f"   ... fetched {len(all_candles)} candles so far")

            # Rate limiting - be nice to the API
            time.sleep(0.1)

        # Sort by timestamp ascending (Bybit returns descending)
        all_candles.sort(key=lambda c: c.timestamp)

        if verbose:
            print(f"✅ Received {len(all_candles)} candles")

        return all_candles

    def save_csv(
        self,
        candles: list[HistoricalCandle],
        filepath: str | Path,
        verbose: bool = True,
    ) -> Path:
        """
        Save candles to CSV file.

        Args:
            candles: List of candles to save
            filepath: Output file path
            verbose: Print progress

        Returns:
            Path to saved file
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with filepath.open("w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["timestamp", "open", "high", "low", "close", "volume", "turnover"],
            )
            writer.writeheader()
            for candle in candles:
                writer.writerow(candle.to_dict())

        if verbose:
            size_kb = filepath.stat().st_size / 1024
            print(f"💾 Saved to: {filepath}")
            print(f"   File size: {size_kb:.1f} KB")

        return filepath

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def generate_filename(
    symbol: str,
    interval: str,
    start: datetime,
    end: datetime,
) -> str:
    """Generate a descriptive filename for the data."""
    start_str = start.strftime("%Y%m%d_%H%M")
    end_str = end.strftime("%Y%m%d_%H%M")
    return f"{symbol}_{interval}m_{start_str}_to_{end_str}.csv"
