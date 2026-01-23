"""
Command-line interface for the Trading Dashboard.

Handles argument parsing, session management commands,
and launching the dashboard application.
"""

import argparse

from bot.simulation.state_manager import SessionStateManager


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(description="Paper Trading Dashboard")
    parser.add_argument(
        "--balance", "-b", type=float, default=10000, help="Starting balance (default: 10000)"
    )
    parser.add_argument(
        "--coins",
        "-c",
        nargs="+",
        default=["BTC", "ETH", "SOL"],
        help="Coins to watch (default: BTC ETH SOL)",
    )
    parser.add_argument(
        "--resume", "-r", action="store_true", help="Resume from saved session state"
    )
    parser.add_argument(
        "--fresh", "-f", action="store_true", help="Start fresh, ignoring any saved state"
    )
    parser.add_argument(
        "--session", "-s", type=str, default=None, help="Session name to use (required for trading)"
    )
    parser.add_argument(
        "--list-sessions", "-l", action="store_true", help="List all available sessions and exit"
    )
    parser.add_argument(
        "--delete-session", type=str, metavar="NAME", help="Delete a saved session and exit"
    )
    # Historical replay mode
    parser.add_argument(
        "--historical",
        "-H",
        type=str,
        metavar="CSV_FILE",
        help="Run in historical replay mode with specified CSV file",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=0.5,
        help="Playback speed in seconds between candles (default: 0.5)",
    )
    return parser


def handle_list_sessions() -> None:
    """Display all available sessions."""
    sessions = SessionStateManager.list_sessions()
    if not sessions:
        print("\n📂 No saved sessions found.")
        print("   Sessions are saved to data/sessions/")
        print()
    else:
        print(f"\n📂 Available Sessions ({len(sessions)}):")
        print("-" * 70)
        for s in sessions:
            pnl_symbol = "+" if s["pnl"] >= 0 else ""
            print(f"  📊 {s['name']}")
            print(
                f"     Balance: ${s['balance']:,.2f} | P&L: {pnl_symbol}${s['pnl']:.2f} ({s['pnl_pct']:+.1f}%)"
            )
            report_status = "✓" if s.get("has_report") else "-"
            print(
                f"     Trades: {s['total_trades']} | Win Rate: {s['win_rate']:.1f}% | Open: {s['open_positions']} | Report: {report_status}"
            )
            print(f"     Last updated: {s['last_update']}")
            print()
        print("   Use --session <name> --resume to load a session")
        print()


def handle_delete_session(session_name: str) -> None:
    """Delete a saved session."""
    if SessionStateManager.delete_session(session_name):
        print(f"✓ Deleted session '{session_name}'")
    else:
        print(f"✗ Session '{session_name}' not found")


def show_session_required_error() -> None:
    """Display error when session name is not provided."""
    print("\n❌ Session name required!")
    print("\nUsage:")
    print("  python bot/ui/dashboard.py --session <name> [--balance 10000] [--resume]")
    print("\nExamples:")
    print("  python bot/ui/dashboard.py --session my_strategy")
    print("  python bot/ui/dashboard.py --session aggressive --balance 5000")
    print("  python bot/ui/dashboard.py --session my_strategy --resume")
    print("\nOr use dev.sh:")
    print("  ./dev.sh my_strategy")
    print("  ./dev.sh aggressive 5000")
    print()

    sessions = SessionStateManager.list_sessions()
    if sessions:
        print(f"📂 Available Sessions ({len(sessions)}):")
        for s in sessions:
            print(f"  • {s['name']} - ${s['balance']:,.2f} ({s['total_trades']} trades)")
        print()


def handle_fresh_session(session_name: str) -> None:
    """Clear saved state for a fresh start."""
    state_manager = SessionStateManager(session_name=session_name)
    if state_manager.has_saved_state:
        state_manager.clear_state()
        print(f"Cleared session '{session_name}'. Starting fresh.")


def show_existing_session_info(session_name: str) -> None:
    """Display info about an existing session if not resuming."""
    state_manager = SessionStateManager(session_name=session_name)
    summary = state_manager.get_session_summary()
    if summary:
        print(f"\n📊 Found saved session '{session_name}':")
        print(
            f"   Balance: ${summary['balance']:,.2f} (started: ${summary['starting_balance']:,.2f})"
        )
        print(f"   P&L: ${summary['pnl']:+,.2f} ({summary['pnl_pct']:+.2f}%)")
        print(f"   Trades: {summary['total_trades']} ({summary['win_rate']:.1f}% win rate)")
        print(f"   Open positions: {summary['open_positions']}")
        print(f"\n   Use --resume --session {session_name} to continue")
        print(f"   Use --fresh --session {session_name} to reset this session")
        print("   Use --session <new_name> to create a new session")
        print()


def run_cli() -> None:
    """Parse arguments and run the appropriate command or launch the dashboard."""
    from pathlib import Path

    from bot.ui.dashboard import TradingDashboard

    parser = create_parser()
    args = parser.parse_args()

    # Handle --list-sessions
    if args.list_sessions:
        handle_list_sessions()
        return

    # Handle --delete-session
    if args.delete_session:
        handle_delete_session(args.delete_session)
        return

    # Historical mode doesn't require session name
    if args.historical:
        historical_path = Path(args.historical)
        if not historical_path.exists():
            print(f"\n❌ Historical data file not found: {args.historical}")
            return

        # Generate session name from filename if not provided
        session_name = args.session or f"historical_{historical_path.stem}"

        print("\n📼 Historical Replay Mode")
        print(f"   File: {historical_path.name}")
        print(f"   Session: {session_name}")
        print(f"   Speed: {args.speed}s per candle")
        print()

        app = TradingDashboard(
            starting_balance=args.balance,
            coins=[c.upper() for c in args.coins],
            resume=False,  # Don't resume in historical mode
            session_name=session_name,
            historical_file=str(historical_path),
            historical_speed=args.speed,
        )
        app.run()
        return

    # Session name is required for live trading
    if not args.session:
        show_session_required_error()
        return

    # Handle --fresh flag
    if args.fresh:
        handle_fresh_session(args.session)

    # Show saved state info if available and not resuming
    if not args.resume and not args.fresh:
        show_existing_session_info(args.session)

    # Launch the dashboard
    app = TradingDashboard(
        starting_balance=args.balance,
        coins=[c.upper() for c in args.coins],
        resume=args.resume,
        session_name=args.session,
    )
    app.run()
