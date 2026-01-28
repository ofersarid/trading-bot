#!/usr/bin/env python3
"""
Run a backtest with the 3-layer architecture.

Usage:
    python run_backtest.py                           # Signals-only mode (fast)
    python run_backtest.py --ai                      # With AI decisions (slower)
    python run_backtest.py --strategy momentum_scalper  # Use specific strategy
    python run_backtest.py --data path/to/ohlcv.csv  # Custom OHLCV data file
    python run_backtest.py --vp                      # Auto-detect trade data for Volume Profile
    python run_backtest.py --trade-data path/to/trades.parquet  # Explicit trade data
"""

import argparse
import asyncio
import sys
from pathlib import Path

from bot.backtest import BacktestConfig, BacktestEngine
from bot.strategies import list_strategies


def find_latest_data_file() -> str | None:
    """Find the most recent historical OHLCV data file from scenario folders."""
    data_dir = Path("data/historical")
    if not data_dir.exists():
        return None

    # Search in scenario folders (any subfolder containing CSV files)
    csv_files = list(data_dir.glob("*/*.csv"))
    if not csv_files:
        return None

    # Sort by modification time, newest first
    csv_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return str(csv_files[0])


def find_matching_trade_data(ohlcv_path: str) -> tuple[str | None, str | None]:
    """
    Find trade data in the same scenario folder as the OHLCV file.

    Returns:
        Tuple of (current_day_trade_data, prev_day_trade_data)
    """
    ohlcv_file = Path(ohlcv_path)
    scenario_dir = ohlcv_file.parent

    # Find parquet files in the same folder
    parquet_files = list(scenario_dir.glob("*.parquet"))
    if not parquet_files:
        return None, None

    # Separate current day and previous day files
    current_day = None
    prev_day = None

    for f in parquet_files:
        if f.name.startswith("prev_day_"):
            prev_day = str(f)
        else:
            current_day = str(f)

    # If no explicit prev_day file, try to use most recent as current
    if current_day is None and parquet_files:
        non_prev = [f for f in parquet_files if not f.name.startswith("prev_day_")]
        if non_prev:
            non_prev.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            current_day = str(non_prev[0])

    return current_day, prev_day


async def main():
    parser = argparse.ArgumentParser(description="Run backtest with 3-layer architecture")
    parser.add_argument(
        "--data",
        "-d",
        help="Path to CSV data file (default: latest in data/historical/)",
    )
    parser.add_argument(
        "--ai",
        action="store_true",
        help="Enable AI decisions (requires Ollama running)",
    )
    parser.add_argument(
        "--strategy",
        "-p",
        default="momentum_scalper",
        choices=[name for name, _ in list_strategies()],
        help="Trading strategy to use (default: momentum_scalper)",
    )
    parser.add_argument(
        "--balance",
        "-b",
        type=float,
        default=10000.0,
        help="Starting balance (default: 10000)",
    )
    parser.add_argument(
        "--signals",
        "-s",
        nargs="+",
        default=["momentum", "rsi", "macd"],
        help="Signal detectors to use (default: momentum rsi macd)",
    )
    parser.add_argument(
        "--trade-data",
        "-t",
        help="Path to trade data (Parquet) for Volume Profile analysis",
    )
    parser.add_argument(
        "--prev-day-data",
        "-pd",
        help="Path to previous day's trade data for VP context levels",
    )
    parser.add_argument(
        "--vp",
        action="store_true",
        help="Auto-detect matching trade data for Volume Profile",
    )

    args = parser.parse_args()

    # Find data file
    data_file = args.data or find_latest_data_file()
    if not data_file:
        print("❌ No data file found. Please specify with --data or add CSV to data/historical/")
        sys.exit(1)

    if not Path(data_file).exists():
        print(f"❌ Data file not found: {data_file}")
        sys.exit(1)

    # Find trade data for Volume Profile
    trade_data = args.trade_data
    prev_day_data = args.prev_day_data

    if not trade_data and args.vp:
        trade_data, auto_prev_day = find_matching_trade_data(data_file)
        if trade_data:
            print(f"✅ Found matching trade data: {trade_data}")
        else:
            print("⚠️  No matching trade data found for Volume Profile")

        # Auto-detect prev day data if not explicitly provided
        if not prev_day_data and auto_prev_day:
            prev_day_data = auto_prev_day
            print(f"✅ Found previous day VP data: {prev_day_data}")

    print(f"\n{'='*60}")
    print("🚀 BACKTEST CONFIGURATION")
    print("=" * 60)
    print(f"  Data:      {data_file}")
    if trade_data:
        print(f"  Trades:    {trade_data}")
    if prev_day_data:
        print(f"  Prev Day:  {prev_day_data}")
    print(f"  Strategy:  {args.strategy}")
    print(f"  Balance:   ${args.balance:,.2f}")
    print(f"  Signals:   {', '.join(args.signals)}")
    if trade_data:
        print("  Vol Prof:  Enabled")
    if prev_day_data:
        print("  Prev VP:   Enabled (POC/VAH/VAL levels)")
    print(f"  AI Mode:   {'Enabled' if args.ai else 'Disabled (signals-only)'}")
    print("=" * 60)

    if args.ai:
        print("\n⚠️  AI mode enabled - make sure Ollama is running!")
        print("   Start with: ollama serve")
        print("   Model needed: mistral (or change in config)")

    # Create config
    config = BacktestConfig(
        data_source=data_file,
        coins=[],  # Will be derived from data
        initial_balance=args.balance,
        strategy_name=args.strategy,
        signal_detectors=args.signals,
        ai_enabled=args.ai,
        trade_data_source=trade_data,
        prev_day_trade_data=prev_day_data,
        vp_enabled=bool(trade_data),
    )

    # Run backtest
    print("\n⏳ Running backtest...")
    engine = BacktestEngine(config)
    result = await engine.run()

    # Print results
    result.print_summary()

    # Show recent trades
    if result.trades:
        print("\n📜 RECENT TRADES (last 5)")
        print("-" * 60)
        for trade in result.trades[-5:]:
            direction = "LONG" if trade.side.value == "long" else "SHORT"
            pnl_emoji = "✅" if trade.pnl > 0 else "❌"
            print(
                f"  {pnl_emoji} {trade.coin} {direction}: "
                f"${trade.entry_price:,.2f} → ${trade.exit_price:,.2f} "
                f"| P&L: ${trade.pnl:+,.2f} ({trade.pnl_percent:+.2f}%)"
            )


if __name__ == "__main__":
    asyncio.run(main())
