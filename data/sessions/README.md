# Sessions

Trading session state storage for resumable paper trading.

## Structure

Each session is stored in its own folder:

```
sessions/
├── default/
│   └── state.json
├── aggressive/
│   ├── state.json
│   ├── logs/
│   │   └── session_log_*.txt
│   └── reports/
│       └── tuning_report_*.json
└── historical_BTCUSD_*.../
    └── state.json
```

## Commands

```bash
# List all sessions
./dev.sh --list

# Create or resume a session
./dev.sh my_session
./dev.sh my_session --resume

# Historical sessions are auto-named from the CSV file
./dev.sh --historical data/historical/BTCUSD_1m_....csv
```
