"""
Command-line interface for the Trading Dashboard v2.

Supports:
- Live mode (WebSocket connection)
- Historical mode (CSV/Parquet replay)
- Server mode (background data server for multi-terminal)
- Client mode (single-coin terminal reading from data server)
- Interactive startup with prompts
"""

import argparse
from pathlib import Path
from typing import Literal

from bot.strategies import list_strategies


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="Trading Bot Dashboard v2 - Observation Mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Live mode with default strategy
  python -m bot.ui.cli --live

  # Historical mode with specific folder
  python -m bot.ui.cli --historical data/historical/BTC_20260126

  # Specify strategy and coins
  python -m bot.ui.cli --live --strategy rsi_based --coins BTC ETH

  # Multi-terminal mode:
  # 1. Start the data server (once, in background)
  python -m bot.ui.cli --server --strategy equal_weight

  # 2. Start individual market terminals (one per market)
  python -m bot.ui.cli --coin BTC
  python -m bot.ui.cli --coin ETH
  python -m bot.ui.cli --coin SOL

  # Interactive mode (will prompt for options)
  python -m bot.ui.cli
        """,
    )

    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--live",
        action="store_true",
        help="Live mode - connect to Hyperliquid WebSocket",
    )
    mode_group.add_argument(
        "--historical",
        type=str,
        metavar="FOLDER",
        help="Historical mode - replay from data folder",
    )
    mode_group.add_argument(
        "--server",
        action="store_true",
        help="Server mode - run background data server for multi-terminal",
    )
    mode_group.add_argument(
        "--coin",
        type=str,
        metavar="COIN",
        help="Client mode - single-coin terminal (reads from data server)",
    )

    # Strategy
    parser.add_argument(
        "--strategy",
        "-s",
        type=str,
        default="equal_weight",
        help="Strategy name (default: equal_weight)",
    )

    # Coins
    parser.add_argument(
        "--coins",
        "-c",
        nargs="+",
        default=["BTC", "ETH", "SOL"],
        help="Coins to monitor (default: BTC ETH SOL)",
    )

    # Replay speed
    parser.add_argument(
        "--speed",
        type=float,
        default=0.5,
        help="Replay speed in seconds between candles (default: 0.5)",
    )

    # List options
    parser.add_argument(
        "--list-strategies",
        action="store_true",
        help="List available strategies and exit",
    )
    parser.add_argument(
        "--list-historical",
        action="store_true",
        help="List available historical data folders and exit",
    )

    return parser


def list_historical_folders() -> list[Path]:
    """List available historical data folders."""
    historical_dir = Path("data/historical")
    if not historical_dir.exists():
        return []

    folders = []
    for item in historical_dir.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            # Check if it has any data files
            csv_files = list(item.glob("*.csv"))
            parquet_files = list(item.glob("*.parquet"))
            if csv_files or parquet_files:
                folders.append(item)

    return sorted(folders)


def show_strategies() -> None:
    """Display available strategies."""
    print("\n📊 Available Strategies:")
    print("-" * 50)
    for name, description in list_strategies():
        print(f"  {name}")
        print(f"    └─ {description}")
    print()


def show_historical_folders() -> None:
    """Display available historical data folders."""
    folders = list_historical_folders()
    if not folders:
        print("\n📂 No historical data found in data/historical/")
        print("   Run the data fetcher first to download historical data.")
        return

    print("\n📂 Available Historical Data:")
    print("-" * 50)
    for folder in folders:
        csv_count = len(list(folder.glob("*.csv")))
        parquet_count = len(list(folder.glob("*.parquet")))
        print(f"  {folder.name}")
        print(f"    └─ {csv_count} CSV, {parquet_count} Parquet files")
    print()


def interactive_mode_selection() -> Literal["live", "historical"]:
    """Prompt user to select mode."""
    print("\n🚀 Trading Bot Dashboard v2")
    print("-" * 40)
    print("Select mode:")
    print("  1. Live (WebSocket)")
    print("  2. Historical (Replay)")
    print()

    while True:
        choice = input("Enter choice [1/2]: ").strip()
        if choice == "1":
            return "live"
        elif choice == "2":
            return "historical"
        print("Invalid choice. Enter 1 or 2.")


def interactive_historical_selection() -> str | None:
    """Prompt user to select historical folder."""
    folders = list_historical_folders()
    if not folders:
        print("\n❌ No historical data found in data/historical/")
        return None

    print("\n📂 Select historical data folder:")
    for i, folder in enumerate(folders, 1):
        print(f"  {i}. {folder.name}")
    print()

    while True:
        choice = input(f"Enter choice [1-{len(folders)}]: ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(folders):
                return str(folders[idx])
        except ValueError:
            pass
        print(f"Invalid choice. Enter a number between 1 and {len(folders)}.")


def interactive_strategy_selection() -> str:
    """Prompt user to select strategy."""
    strategies = list_strategies()

    print("\n📊 Select strategy:")
    for i, (name, desc) in enumerate(strategies, 1):
        print(f"  {i}. {name} - {desc}")
    print()

    while True:
        choice = input(f"Enter choice [1-{len(strategies)}] (default: 1): ").strip()
        if not choice:
            return strategies[0][0]
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(strategies):
                return strategies[idx][0]
        except ValueError:
            pass
        print(f"Invalid choice. Enter a number between 1 and {len(strategies)}.")


def run_cli() -> None:
    """Parse arguments and run the dashboard or server."""
    import asyncio

    from bot.ui.dashboard import TradingDashboard

    parser = create_parser()
    args = parser.parse_args()

    # Handle list commands
    if args.list_strategies:
        show_strategies()
        return

    if args.list_historical:
        show_historical_folders()
        return

    # Handle server mode
    if args.server:
        from bot.server.data_server import run_server

        print("\n" + "=" * 50)
        print("Starting Data Server")
        print("=" * 50)
        print(f"  Strategy: {args.strategy}")
        print(f"  Coins: {', '.join(args.coins)}")
        print("  State files: data/live-state/")
        print("=" * 50)
        print("\nPress Ctrl+C to stop\n")

        asyncio.run(
            run_server(
                coins=[c.upper() for c in args.coins],
                strategy_name=args.strategy,
            )
        )
        return

    # Handle client mode (single-coin terminal)
    if args.coin:
        coin = args.coin.upper()
        print("\n" + "=" * 50)
        print(f"Starting {coin} Terminal (Client Mode)")
        print("=" * 50)
        print("  Reading from: data/live-state/")
        print("  Make sure the data server is running!")
        print("=" * 50)
        print()

        app = TradingDashboard(
            mode="client",
            strategy_name=args.strategy,
            coins=[coin],
        )
        app.run()
        return

    # Determine mode for standard dashboard
    mode: Literal["live", "historical"]
    historical_folder: str | None = None
    strategy_name: str = args.strategy

    if args.live:
        mode = "live"
    elif args.historical:
        mode = "historical"
        historical_folder = args.historical

        # Validate historical folder
        if not Path(args.historical).exists():
            print(f"\n❌ Historical data folder not found: {historical_folder}")
            show_historical_folders()
            return
    else:
        # Interactive mode
        mode = interactive_mode_selection()

        if mode == "historical":
            historical_folder = interactive_historical_selection()
            if not historical_folder:
                return

        strategy_name = interactive_strategy_selection()

    # Display startup info
    print("\n" + "=" * 50)
    print("Starting Trading Bot Dashboard v2")
    print("=" * 50)
    print(f"  Mode: {mode.upper()}")
    print(f"  Strategy: {strategy_name}")
    print(f"  Coins: {', '.join(args.coins)}")
    if mode == "historical":
        print(f"  Data: {historical_folder}")
        print(f"  Speed: {args.speed}s/candle")
    print("=" * 50)
    print()

    # Launch dashboard
    app = TradingDashboard(
        mode=mode,
        strategy_name=strategy_name,
        coins=[c.upper() for c in args.coins],
        historical_folder=historical_folder,
        replay_speed=args.speed,
    )
    app.run()


if __name__ == "__main__":
    run_cli()
