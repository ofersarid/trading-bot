"""
Combined signal row component.

Displays weighted signal combination and scrollable log history for a market.
"""

from collections import deque
from datetime import datetime

from textual.app import ComposeResult
from textual.containers import Container, ScrollableContainer, Vertical
from textual.widgets import Static


class CombinedSignalRow(Container):
    """Row showing combined weighted signal + scrollable log."""

    def __init__(self, coin: str, **kwargs) -> None:
        """
        Initialize the combined signal row.

        Args:
            coin: Coin symbol (BTC, ETH, SOL)
        """
        super().__init__(**kwargs)
        self.coin = coin
        self.signal_log: deque[tuple[str, str]] = deque(maxlen=50)

    def compose(self) -> ComposeResult:
        base_id = f"{self.coin.lower()}"

        with Vertical(classes="combined-section"):
            yield Static("WAIT 0.00", id=f"{base_id}-combined-signal", classes="combined-signal")
            yield Static("--", id=f"{base_id}-contributions", classes="contributions")

        with ScrollableContainer(id=f"{base_id}-signal-log", classes="signal-log"):
            yield Static("", id=f"{base_id}-log-content", classes="log-content")

    def update_signal(
        self,
        direction: str,
        score: float,
        threshold: float,
        contributions: dict[str, float],
    ) -> None:
        """
        Update the combined signal display.

        Args:
            direction: Signal direction (LONG, SHORT, WAIT)
            score: Combined weighted score
            threshold: Strategy threshold for actionable signals
            contributions: Dict of indicator -> contribution (e.g., {"MOM": 0.85, "VP": 0.35})
        """
        base_id = f"{self.coin.lower()}"

        # Format signal with checkmark if above threshold
        is_actionable = score >= threshold and direction != "WAIT"
        checkmark = " ✓" if is_actionable else ""
        signal_text = f"{direction} {score:.2f}{checkmark}"

        try:
            signal_widget = self.query_one(f"#{base_id}-combined-signal", Static)
            signal_widget.update(signal_text)

            # Format contributions
            contrib_parts = [f"{k}: {v:.2f}" for k, v in contributions.items() if v > 0]
            contrib_text = "  ".join(contrib_parts) if contrib_parts else "--"
            contrib_widget = self.query_one(f"#{base_id}-contributions", Static)
            contrib_widget.update(contrib_text)
        except Exception:
            pass

        # Add to log with timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.add_log_entry(timestamp, signal_text)

    def add_log_entry(self, timestamp: str, message: str) -> None:
        """
        Add entry to scrollable log.

        Args:
            timestamp: Time string (HH:MM:SS)
            message: Log message
        """
        self.signal_log.appendleft((timestamp, message))
        self._refresh_log()

    def _refresh_log(self) -> None:
        """Update log display with all entries."""
        base_id = f"{self.coin.lower()}"
        try:
            content = self.query_one(f"#{base_id}-log-content", Static)
            lines = [f"[{ts}] {msg}" for ts, msg in self.signal_log]
            content.update("\n".join(lines))
        except Exception:
            pass
