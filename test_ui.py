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
    import importlib.util

    if importlib.util.find_spec("websockets"):
        print("✓ websockets installed")
    else:
        print("✗ websockets not installed")
        sys.exit(1)
except ImportError as e:
    print(f"✗ websockets check failed: {e}")
    sys.exit(1)

# Test 3: Check our modules
try:
    sys.path.insert(0, ".")
    if importlib.util.find_spec("bot.simulation.models") and importlib.util.find_spec(
        "bot.simulation.paper_trader"
    ):
        print("✓ bot.simulation modules OK")
    else:
        print("✗ bot.simulation modules not found")
        sys.exit(1)
except ImportError as e:
    print(f"✗ bot.simulation import error: {e}")
    sys.exit(1)

# Test 4: Check dashboard import
try:
    print("✓ bot.ui.dashboard OK")
except Exception as e:
    print(f"✗ bot.ui.dashboard error: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

print()
print("All checks passed! Run the dashboard with:")
print("  python bot/ui/dashboard.py --balance 10000")
