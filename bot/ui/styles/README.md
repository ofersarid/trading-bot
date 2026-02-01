# Styles

CSS theme files for the Textual TUI dashboard.

## Files

| File | Purpose |
|------|---------|
| `theme.css` | Legacy dark theme (kept for reference) |
| `dashboard.tcss` | Dashboard v2 responsive layout |

## Dashboard v2 Layout

The `dashboard.tcss` file implements:
- 3 market columns (BTC | ETH | SOL) using `1fr` widths
- Indicator sub-columns within each market
- Scrollable signal logs
- Missing data warning state

## Hot Reload

CSS changes are hot-reloaded when running in dev mode:

```bash
TEXTUAL_DEV=1 python -m bot.ui.cli --live
```
