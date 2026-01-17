#!/bin/bash
# Development mode with full hot reload
# - CSS changes: instant (via TEXTUAL_DEV=1)
# - Python changes: auto-restart (via watchfiles)

cd "$(dirname "$0")"
source venv/bin/activate

# Install watchfiles if not present
pip show watchfiles > /dev/null 2>&1 || pip install watchfiles

echo "Starting development mode with hot reload..."
echo "  - CSS changes update instantly"
echo "  - Python changes trigger auto-restart"
echo ""

# TEXTUAL_DEV=1 enables CSS hot reload
export TEXTUAL_DEV=1
watchfiles "python bot/ui/dashboard.py --balance ${1:-10000}" bot/
