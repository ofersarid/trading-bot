# Data

Data storage for historical data, trading sessions, and feedback.

## Folders

| Folder | Purpose |
|--------|---------|
| `historical/` | Historical candle data (CSV) and trade data (Parquet) |
| `sessions/` | Saved trading session states for resumption |
| `feedback/` | Trade feedback data for analysis |

## Session Persistence

Sessions are saved to `sessions/<name>/state.json` and include:
- Balance and starting balance
- Open positions
- Total fees paid
- Trade count and win count

Resume a session with:
```bash
./dev.sh <session_name> --resume
```
