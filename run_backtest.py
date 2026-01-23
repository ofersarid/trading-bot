#!/usr/bin/env python3
"""
Run a backtest with the 3-layer architecture.

Usage:
    python run_backtest.py                           # Signals-only mode (fast)
    python run_backtest.py --ai                      # With AI decisions (slower)
    python run_backtest.py --persona scalper         # Use scalper persona
    python run_backtest.py --data path/to/data.csv   # Custom data file
"""

import argparse
import asyncio
import sys
from pathlib import Path

from bot.backtest import BacktestConfig, BacktestEngine


def find_latest_data_file() -> str | None:
    """Find the most recent historical data file."""
    data_dir = Path("data/historical")
    if not data_dir.exists():
        return None

    csv_files = list(data_dir.glob("*.csv"))
    if not csv_files:
        return None

    # Sort by modification time, newest first
    csv_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return str(csv_files[0])


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
        "--persona",
        "-p",
        default="balanced",
        choices=["scalper", "conservative", "balanced"],
        help="Trading persona to use (default: balanced)",
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

    args = parser.parse_args()

    # Find data file
    data_file = args.data or find_latest_data_file()
    if not data_file:
        print("❌ No data file found. Please specify with --data or add CSV to data/historical/")
        sys.exit(1)

    if not Path(data_file).exists():
        print(f"❌ Data file not found: {data_file}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print("🚀 BACKTEST CONFIGURATION")
    print("=" * 60)
    print(f"  Data:      {data_file}")
    print(f"  Persona:   {args.persona}")
    print(f"  Balance:   ${args.balance:,.2f}")
    print(f"  Signals:   {', '.join(args.signals)}")
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
        persona_name=args.persona,
        signal_detectors=args.signals,
        ai_enabled=args.ai,
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
