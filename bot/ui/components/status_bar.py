"""
Status bar component.

Displays connection status, balance, equity, P&L, and threshold settings.
"""

from datetime import datetime

from textual.containers import Horizontal
from textual.widgets import Static
from textual.app import ComposeResult


# Theme colors (Rich markup)
COLOR_UP = "#44ffaa"
COLOR_DOWN = "#ff7777"


class StatusBar(Horizontal):
    """Status bar showing connection info, balance, and thresholds."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._start_time = datetime.now()
    
    def compose(self) -> ComposeResult:
        yield Static("", id="status-bar", classes="status-bar-left")
        yield Static("", id="threshold-bar", classes="status-bar-right")
    
    def update_status(
        self,
        ws_connected: bool,
        last_message_age: float | None,
        reconnect_count: int,
        balance: float,
        equity: float,
        starting_balance: float,
        trade_count: int,
    ) -> None:
        """
        Update the left status section.
        
        Args:
            ws_connected: WebSocket connection status
            last_message_age: Seconds since last WebSocket message
            reconnect_count: Number of reconnection attempts
            balance: Current cash balance
            equity: Total equity including positions
            starting_balance: Initial balance for P&L calculation
            trade_count: Number of completed trades
        """
        # Calculate P&L
        pnl = equity - starting_balance
        pnl_pct = (pnl / starting_balance) * 100 if starting_balance else 0
        pnl_color = COLOR_UP if pnl >= 0 else COLOR_DOWN
        
        # Calculate uptime
        uptime = datetime.now() - self._start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        # Connection status
        if ws_connected:
            ws_status = f"[{COLOR_UP}]🟢[/{COLOR_UP}]"
            if last_message_age is not None and last_message_age < 5:
                msg_rate = "[dim]live[/dim]"
            elif last_message_age is not None:
                msg_rate = f"[yellow]{last_message_age:.0f}s ago[/yellow]"
            else:
                msg_rate = "[dim]waiting[/dim]"
        else:
            ws_status = f"[{COLOR_DOWN}]🔴[/{COLOR_DOWN}]"
            msg_rate = f"[{COLOR_DOWN}]disconnected[/{COLOR_DOWN}]"
            if reconnect_count > 0:
                msg_rate += f" (r:{reconnect_count})"
        
        status_content = (
            f"{ws_status} {msg_rate}  │  "
            f"⏱️ {uptime_str}  │  "
            f"💰${balance:,.2f}  │  "
            f"📈${equity:,.2f}  │  "
            f"[{pnl_color}]P&L: ${pnl:+,.2f} ({pnl_pct:+.2f}%)[/{pnl_color}]  │  "
            f"📊{trade_count} trades"
        )
        
        try:
            status = self.query_one("#status-bar", Static)
            status.update(status_content)
        except Exception:
            pass
    
    def update_thresholds(
        self,
        track_threshold: float,
        trade_threshold: float,
        momentum_timeframe: int,
        momentum_timeframes: list[int],
    ) -> None:
        """
        Update the right threshold section.
        
        Args:
            track_threshold: Current tracking threshold percentage
            trade_threshold: Current trading threshold percentage
            momentum_timeframe: Current momentum lookback in seconds
            momentum_timeframes: List of available timeframe options
        """
        # Visual bar for track threshold (0-0.5%)
        track_pct = min(1.0, track_threshold / 0.5)
        track_filled = int(track_pct * 15)
        track_bar = "[yellow]" + "█" * track_filled + "░" * (15 - track_filled) + "[/yellow]"
        
        # Visual bar for trade threshold (0-1.0%)
        trade_pct = min(1.0, trade_threshold / 1.0)
        trade_filled = int(trade_pct * 15)
        trade_bar = f"[{COLOR_UP}]" + "█" * trade_filled + "░" * (15 - trade_filled) + f"[/{COLOR_UP}]"
        
        # Visual bar for momentum timeframe
        if momentum_timeframe in momentum_timeframes:
            mom_idx = momentum_timeframes.index(momentum_timeframe)
            mom_pct = mom_idx / max(1, len(momentum_timeframes) - 1)
        else:
            mom_pct = 0
        mom_filled = int(mom_pct * 15)
        mom_bar = "[cyan]" + "█" * mom_filled + "░" * (15 - mom_filled) + "[/cyan]"
        
        threshold_content = (
            f"Track: {track_bar} {track_threshold:.2f}%  │  "
            f"Trade: {trade_bar} {trade_threshold:.2f}%  │  "
            f"Mom: {mom_bar} {momentum_timeframe}s"
        )
        
        try:
            bar = self.query_one("#threshold-bar", Static)
            bar.update(threshold_content)
        except Exception:
            pass
