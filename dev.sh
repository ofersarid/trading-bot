#!/bin/bash
# Development mode with full hot reload
# - CSS changes: instant (via TEXTUAL_DEV=1)
# - Python changes: auto-restart (via watchfiles)
#
# Usage:
#   ./dev.sh <session_name> [balance]
#
# Examples:
#   ./dev.sh my_strategy           # Load/create session with $10000
#   ./dev.sh aggressive 5000       # Load/create session with $5000
#   ./dev.sh --list                # List all sessions

cd "$(dirname "$0")"
source venv/bin/activate

# Handle --list flag
if [ "$1" = "--list" ] || [ "$1" = "-l" ]; then
    python bot/ui/dashboard.py --list-sessions
    exit 0
fi

# Session name is required
SESSION_NAME="$1"
BALANCE="${2:-10000}"

if [ -z "$SESSION_NAME" ]; then
    echo ""
    echo "Usage: ./dev.sh <session_name> [balance]"
    echo ""
    echo "Examples:"
    echo "  ./dev.sh my_strategy           # Load/create 'my_strategy' with \$10000"
    echo "  ./dev.sh aggressive 5000       # Load/create 'aggressive' with \$5000"
    echo "  ./dev.sh --list                # List all sessions"
    echo ""
    
    # Show available sessions if any
    python bot/ui/dashboard.py --list-sessions 2>/dev/null
    exit 1
fi

# Install watchfiles if not present
pip show watchfiles > /dev/null 2>&1 || pip install watchfiles

# Check if session exists (for display purposes)
SESSION_DIR="data/sessions/$SESSION_NAME"
if [ -d "$SESSION_DIR" ] && [ -f "$SESSION_DIR/state.json" ]; then
    echo "📂 Resuming session: $SESSION_NAME"
else
    echo "📂 Creating new session: $SESSION_NAME (balance: \$$BALANCE)"
fi

echo ""
echo "Starting development mode with hot reload..."
echo "  - CSS changes update instantly"
echo "  - Python changes trigger auto-restart"
echo "  - Press Ctrl+S to save session"
echo ""

# TEXTUAL_DEV=1 enables CSS hot reload
# Always use --resume so hot reload preserves session state
export TEXTUAL_DEV=1
watchfiles "python bot/ui/dashboard.py --session $SESSION_NAME --balance $BALANCE --resume" bot/
