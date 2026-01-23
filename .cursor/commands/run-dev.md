---
name: Run Trading Bot
description: Generate the command to launch the trading bot
tags: [trading, bot, dev, dashboard, simulation]
---

# Trading Bot Command Generator

Generate a `./dev.sh` command for copy-paste into any terminal.

## Flow

**Step 1:** Ask for mode

```
What mode?

1. Live Mode - Real-time market data
2. Historical Mode - Replay from CSV
```

**Step 2a (Live):** Ask for session and balance

- Session name (default: `default`)
- Starting balance (default: `10000`)

Then output:

```
./dev.sh <session> <balance>
```

**Step 2b (Historical):** List available CSV files and ask for selection

Run `ls data/historical/*.csv` to list files, then ask:
- Which CSV file
- Playback speed (default: `0.5`)

Then output:

```
./dev.sh --historical data/historical/<csv_file> --speed <speed>
```

## Output Format

Output the command in a code block so it's easy to copy:

```bash
./dev.sh --historical data/historical/BTCUSD_1m_20260120_2313_to_20260121_0923.csv --speed 0.5
```

## Quick Reference

| Mode | Command |
|------|---------|
| Live | `./dev.sh <session> [balance]` |
| Historical | `./dev.sh --historical <csv> [--speed <s>]` |
| List Sessions | `./dev.sh --list` |
