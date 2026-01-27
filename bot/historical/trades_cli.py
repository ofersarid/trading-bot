"""
Trades CLI - Fetch and process historical trade data.

Downloads trade fills from Hyperliquid S3, parses them, and stores
in Parquet format for efficient Volume Profile analysis.

Usage:
    python -m bot.historical.trades_cli fetch --start 20-01-2026 --end 21-01-2026 --coin BTC
    python -m bot.historical.trades_cli info data/historical/trades/BTC_trades_20260120.parquet
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path


def parse_date(date_str: str) -> datetime:
    """
    Parse date string in various formats.

    Supported formats:
    - dd-mm-yyyy
    - yyyy-mm-dd
    - yyyymmdd
    """
    formats = [
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%Y%m%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    raise ValueError(f"Invalid date format: {date_str}. Use dd-mm-yyyy, yyyy-mm-dd, or yyyymmdd")


def cmd_fetch(args: argparse.Namespace) -> int:
    """Fetch trade data from Hyperliquid S3."""
    from bot.historical.fill_parser import HyperliquidFillParser
    from bot.historical.s3_fetcher import HyperliquidS3Fetcher
    from bot.historical.trade_storage import TradeStorage, generate_trade_filename

    start_date = parse_date(args.start)
    end_date = parse_date(args.end) if args.end else start_date
    coin = args.coin.upper()

    output_dir = Path(args.output)
    raw_dir = output_dir / "raw"

    print("=" * 60)
    print("Hyperliquid Trade Data Fetcher")
    print("=" * 60)
    print(f"  Coin: {coin}")
    print(f"  Date range: {start_date.date()} to {end_date.date()}")
    print(f"  Output directory: {output_dir}")
    print()

    # Step 1: Download from S3
    fetcher = HyperliquidS3Fetcher(verbose=True)

    print("Step 1: Downloading from S3...")
    print(f"  Estimated cost: {fetcher.estimate_transfer_cost((end_date - start_date).days + 1)}")
    print()

    if not args.skip_download:
        try:
            downloaded = fetcher.fetch_range(start_date, end_date, raw_dir)
            print(f"  Downloaded {len(downloaded)} days")
        except RuntimeError as e:
            print(f"  Error: {e}")
            if not args.use_existing:
                return 1
            print("  Using existing data...")
    else:
        print("  Skipping download (--skip-download)")

    # Step 2: Decompress LZ4 files
    print()
    print("Step 2: Decompressing files...")

    if raw_dir.exists():
        decompressed = fetcher.decompress_files(raw_dir)
        print(f"  Decompressed {len(decompressed)} files")

    # Step 3: Parse fills
    print()
    print("Step 3: Parsing trade fills...")

    parser = HyperliquidFillParser(verbose=True)
    trades = []

    for date_dir in sorted(raw_dir.iterdir()):
        if date_dir.is_dir():
            print(f"  Parsing {date_dir.name}...")
            for trade in parser.parse_directory(date_dir, coin=coin):
                trades.append(trade)

    print(f"  Found {len(trades)} trades for {coin}")

    if parser.parse_errors > 0:
        print(f"  Warning: {parser.parse_errors} parse errors encountered")

    if not trades:
        print("  No trades found. Check the date range and coin symbol.")
        return 1

    # Step 4: Save to Parquet
    print()
    print("Step 4: Saving to Parquet...")

    storage = TradeStorage(verbose=True)
    filename = generate_trade_filename(coin, start_date, end_date)
    output_path = output_dir / filename

    storage.save_trades(trades, output_path)

    # Print summary
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    info = storage.get_file_info(output_path)
    print(f"  Output file: {info['path']}")
    print(f"  File size: {info['size_mb']:.2f} MB")
    print(f"  Trade count: {info.get('num_rows', len(trades))}")

    if trades:
        print(f"  Time range: {trades[0].timestamp} to {trades[-1].timestamp}")
        print(
            f"  Price range: ${min(t.price for t in trades):,.2f} - ${max(t.price for t in trades):,.2f}"
        )

    return 0


def cmd_info(args: argparse.Namespace) -> int:
    """Show information about a trade data file."""
    from bot.historical.trade_storage import TradeStorage

    filepath = Path(args.file)
    storage = TradeStorage()

    try:
        info = storage.get_file_info(filepath)
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
        return 1

    print("Trade Data File Info")
    print("=" * 40)
    print(f"  Path: {info['path']}")
    print(f"  Format: {info['format']}")
    print(f"  Size: {info['size_mb']:.2f} MB")

    if "num_rows" in info:
        print(f"  Rows: {info['num_rows']:,}")
        print(f"  Compression: {info['compression']}")

    # Show sample data
    if args.sample:
        print()
        print("Sample trades:")
        print("-" * 40)

        for count, trade in enumerate(storage.load_trades(filepath), start=1):
            print(
                f"  {trade.timestamp} | {trade.coin} | ${trade.price:,.2f} | {trade.size:.4f} | {trade.side}"
            )
            if count >= args.sample:
                break

    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """List available dates in S3."""
    from bot.historical.s3_fetcher import HyperliquidS3Fetcher

    fetcher = HyperliquidS3Fetcher(verbose=True)

    print("Available dates in Hyperliquid S3:")
    print("-" * 40)

    try:
        dates = fetcher.list_available_dates(limit=args.limit)
        for date in dates:
            print(f"  {date}")
        print()
        print(f"Total: {len(dates)} dates available")
    except RuntimeError as e:
        print(f"Error: {e}")
        return 1

    return 0


def main() -> int:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Fetch and process historical trade data from Hyperliquid",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Fetch command
    fetch_parser = subparsers.add_parser("fetch", help="Fetch trade data from S3")
    fetch_parser.add_argument(
        "--start",
        "-s",
        required=True,
        help="Start date (dd-mm-yyyy, yyyy-mm-dd, or yyyymmdd)",
    )
    fetch_parser.add_argument(
        "--end",
        "-e",
        help="End date (optional, defaults to start date)",
    )
    fetch_parser.add_argument(
        "--coin",
        "-c",
        default="BTC",
        help="Coin symbol (default: BTC)",
    )
    fetch_parser.add_argument(
        "--output",
        "-o",
        default="data/historical/trades",
        help="Output directory (default: data/historical/trades)",
    )
    fetch_parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip S3 download, use existing raw data",
    )
    fetch_parser.add_argument(
        "--use-existing",
        action="store_true",
        help="Continue with existing data if download fails",
    )
    fetch_parser.set_defaults(func=cmd_fetch)

    # Info command
    info_parser = subparsers.add_parser("info", help="Show trade data file info")
    info_parser.add_argument("file", help="Path to trade data file")
    info_parser.add_argument(
        "--sample",
        "-n",
        type=int,
        default=0,
        help="Show N sample trades",
    )
    info_parser.set_defaults(func=cmd_info)

    # List command
    list_parser = subparsers.add_parser("list", help="List available dates in S3")
    list_parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=30,
        help="Maximum dates to list (default: 30)",
    )
    list_parser.set_defaults(func=cmd_list)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    result: int = args.func(args)
    return result


if __name__ == "__main__":
    sys.exit(main())
