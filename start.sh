#!/bin/bash
# Start the Paper Trading Simulator

cd "$(dirname "$0")"
source venv/bin/activate

# Check for --dev flag (enables CSS hot reload)
if [[ "$1" == "--dev" ]]; then
    shift
    export TEXTUAL_DEV=1
fi

python bot/ui/dashboard.py --balance "${1:-10000}"
