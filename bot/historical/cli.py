#!/usr/bin/env python3
"""
CLI for fetching historical data from Bybit.

Usage:
    python -m bot.historical.cli --start 12-01-2026:10-15 --end 12-01-2026:11-15

Or via the shell script:
    ./get-data-set-from --start 12-01-2026:10-15 --end 12-01-2026:11-15

If no start/end provided, fetches the last hour of data.
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

from bot.historical.fetcher import BybitHistoricalFetcher, generate_filename


def parse_datetime(value: str) -> datetime:
    """
    Parse datetime from format: dd-mm-yyyy:hh-mm

    Examples:
        12-01-2026:10-15 -> 2026-01-12 10:15:00
        01-12-2025:09-30 -> 2025-12-01 09:30:00
    """
    try:
        return datetime.strptime(value, "%d-%m-%Y:%H-%M")
    except ValueError as e:
        raise argparse.ArgumentTypeError(
            f"Invalid datetime format: '{value}'. Expected: dd-mm-yyyy:hh-mm (e.g., 12-01-2026:10-15)"
        ) from e


def main():
    parser = argparse.ArgumentParser(
        description="Fetch historical kline data from Bybit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Fetch most recent 1 hour (default)
    %(prog)s

    # Fetch most recent 1 hour for ETH
    %(prog)s --symbol ETHUSDT

    # Fetch specific time range
    %(prog)s --start 12-01-2026:10-15 --end 12-01-2026:11-15

    # Fetch with specific symbol and interval
    %(prog)s --start 12-01-2026:10-00 --end 12-01-2026:12-00 --symbol ETHUSDT --interval 5

    # Fetch spot market data
    %(prog)s --start 12-01-2026:10-00 --end 12-01-2026:11-00 --category spot
        """,
    )

    parser.add_argument(
        "--start",
        "-s",
        type=parse_datetime,
        default=None,
        help="Start time in format dd-mm-yyyy:hh-mm (default: 1 hour ago)",
    )
    parser.add_argument(
        "--end",
        "-e",
        type=parse_datetime,
        default=None,
        help="End time in format dd-mm-yyyy:hh-mm (default: now)",
    )
    parser.add_argument(
        "--symbol",
        "-S",
        default="BTCUSDT",
        help="Trading pair symbol (default: BTCUSDT)",
    )
    parser.add_argument(
        "--interval",
        "-i",
        default="1",
        choices=["1", "3", "5", "15", "30", "60", "120", "240", "360", "720", "D", "W"],
        help="Candle interval in minutes (default: 1)",
    )
    parser.add_argument(
        "--category",
        "-c",
        default="linear",
        choices=["linear", "spot", "inverse"],
        help="Market category (default: linear = USDT perpetuals)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("data/historical"),
        help="Output directory (default: data/historical/)",
    )
    parser.add_argument(
        "--filename",
        "-f",
        help="Custom output filename (default: auto-generated)",
    )

    args = parser.parse_args()

    # Default time range: last 1 hour
    if args.end is None:
        args.end = datetime.now().replace(second=0, microsecond=0)
    if args.start is None:
        args.start = args.end - timedelta(hours=1)

    # Validate time range
    if args.end <= args.start:
        parser.error("End time must be after start time")

    # Print header
    print()
    print("=" * 60)
    print("🔄 Fetching historical data from Bybit")
    print("=" * 60)
    print(f"   Symbol:   {args.symbol}")
    print(f"   Category: {args.category}")
    print(f"   Interval: {args.interval}m")
    print(f"   Start:    {args.start.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"   End:      {args.end.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print()

    try:
        with BybitHistoricalFetcher(category=args.category) as fetcher:
            # Fetch data
            candles = fetcher.fetch(
                symbol=args.symbol,
                start=args.start,
                end=args.end,
                interval=args.interval,
            )

            if not candles:
                print("❌ No data received for the specified time range")
                sys.exit(1)

            # Generate filename
            if args.filename:
                filename = args.filename
            else:
                filename = generate_filename(args.symbol, args.interval, args.start, args.end)

            filepath = args.output / filename

            # Save to CSV
            print()
            fetcher.save_csv(candles, filepath)

            # Print summary
            print()
            print("=" * 60)
            print("📊 Summary")
            print("=" * 60)
            print(f"   Candles:     {len(candles)}")

            duration = args.end - args.start
            hours = duration.total_seconds() / 3600
            print(f"   Time span:   {hours:.1f}h")

            prices = [c.close for c in candles]
            print(f"   Price range: ${min(prices):,.2f} - ${max(prices):,.2f}")

            total_volume = sum(c.volume for c in candles)
            print(f"   Volume:      {total_volume:,.2f}")
            print()
            print("✅ Done!")
            print()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
