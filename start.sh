#!/bin/bash
# Start the Paper Trading Simulator

cd "$(dirname "$0")"
source venv/bin/activate
python bot/ui/dashboard.py --balance "${1:-10000}"
