#!/bin/bash
# Stop the Paper Trading Simulator

pkill -9 -f "dashboard.py" 2>/dev/null
echo "✓ Stopped"
reset
