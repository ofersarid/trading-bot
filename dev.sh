#!/bin/bash
# Development mode with full hot reload
# - CSS changes: instant (via TEXTUAL_DEV=1)
# - Python changes: auto-restart (via watchfiles)
#
# Usage:
#   ./dev.sh                       # Live mode with BTC, ETH, SOL
#   ./dev.sh BTC                   # Live mode, single coin (for multi-terminal setup)
#   ./dev.sh BTC ETH               # Live mode, specific coins
#   ./dev.sh --historical <folder> [--speed <seconds>]
#
# Examples:
#   ./dev.sh                                    # All 3 coins in one window
#   ./dev.sh BTC                                # BTC only (run in separate terminal)
#   ./dev.sh ETH                                # ETH only (run in separate terminal)
#   ./dev.sh SOL                                # SOL only (run in separate terminal)
#   ./dev.sh --historical data/historical/BTC_20260126
#   ./dev.sh --strategy rsi_based               # Use different strategy

cd "$(dirname "$0")"

# Use explicit path to venv python
PYTHON="./venv/bin/python"

# Verify venv exists
if [ ! -f "$PYTHON" ]; then
    echo "❌ Virtual environment not found at ./venv"
    echo "   Run: python3 -m venv venv && ./venv/bin/pip install -e ."
    exit 1
fi

# Handle --historical flag
if [ "$1" = "--historical" ] || [ "$1" = "-H" ]; then
    FOLDER="$2"
    SPEED="0.5"
    STRATEGY="momentum_based"

    # Parse remaining arguments
    shift 2
    while [[ $# -gt 0 ]]; do
        case $1 in
            --speed) SPEED="$2"; shift 2 ;;
            --strategy) STRATEGY="$2"; shift 2 ;;
            *) shift ;;
        esac
    done

    if [ -z "$FOLDER" ]; then
        echo ""
        echo "Usage: ./dev.sh --historical <folder> [--speed <seconds>] [--strategy <name>]"
        echo ""
        echo "Examples:"
        echo "  ./dev.sh --historical data/historical/BTC_20260126"
        echo "  ./dev.sh --historical data/historical/BTC_20260126 --speed 0.1"
        echo ""
        echo "Available data folders:"
        ls -d data/historical/*/ 2>/dev/null || echo "  No folders found in data/historical/"
        echo ""
        exit 1
    fi

    if [ ! -d "$FOLDER" ]; then
        echo "❌ Folder not found: $FOLDER"
        exit 1
    fi

    echo ""
    echo "📼 Starting historical replay mode..."
    echo "   Folder: $FOLDER"
    echo "   Speed: ${SPEED}s per candle"
    echo "   Strategy: $STRATEGY"
    echo ""

    # Run in historical mode (no hot reload needed for replay)
    export TEXTUAL_DEV=1
    $PYTHON -m bot.ui.dashboard --historical "$FOLDER" --speed "$SPEED" --strategy "$STRATEGY"
    exit 0
fi

# Default: Live mode with hot reload
STRATEGY="momentum_based"
COINS=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --strategy|-s) STRATEGY="$2"; shift 2 ;;
        [A-Z]*) COINS="$COINS $1"; shift ;;  # Capture coin names (uppercase)
        *) shift ;;
    esac
done

# Default to all coins if none specified
COINS="${COINS:-BTC ETH SOL}"
COINS=$(echo $COINS | xargs)  # Trim whitespace

# Install watchfiles if not present
$PYTHON -m pip show watchfiles > /dev/null 2>&1 || $PYTHON -m pip install watchfiles

echo ""
echo "🔴 Starting LIVE mode with hot reload..."
echo "   Coins: $COINS"
echo "   Strategy: $STRATEGY"
echo "   - CSS changes update instantly"
echo "   - Python changes trigger auto-restart"
echo ""

# TEXTUAL_DEV=1 enables CSS hot reload
export TEXTUAL_DEV=1
./venv/bin/watchfiles "$PYTHON -m bot.ui.dashboard --live --strategy $STRATEGY --coins $COINS" bot/
