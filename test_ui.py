#!/usr/bin/env python3
"""Quick test to check if UI dependencies work."""

import sys

# Test 1: Check textual import
try:
    import textual
    print(f"✓ textual installed: {textual.__version__}")
except ImportError as e:
    print(f"✗ textual not installed: {e}")
    print("  Run: pip install textual")
    sys.exit(1)

# Test 2: Check websockets
try:
    import websockets
    print(f"✓ websockets installed")
except ImportError as e:
    print(f"✗ websockets not installed: {e}")
    sys.exit(1)

# Test 3: Check our modules
try:
    sys.path.insert(0, ".")
    from bot.simulation.paper_trader import PaperTrader
    from bot.simulation.models import HYPERLIQUID_FEES
    print(f"✓ bot.simulation modules OK")
except ImportError as e:
    print(f"✗ bot.simulation import error: {e}")
    sys.exit(1)

# Test 4: Check dashboard import
try:
    from bot.ui.dashboard import TradingDashboard
    print(f"✓ bot.ui.dashboard OK")
except Exception as e:
    print(f"✗ bot.ui.dashboard error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("All checks passed! Run the dashboard with:")
print("  python bot/ui/dashboard.py --balance 10000")
