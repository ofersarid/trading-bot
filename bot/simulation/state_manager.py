"""
Session State Manager

Persists trading session state (balance, positions, settings) to disk
so the bot can resume from where it left off after restarts.

Supports multiple named sessions stored in data/sessions/ folder.
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from bot.simulation.models import Position, Side


@dataclass
class SessionState:
    """
    Complete session state that gets persisted to disk.
    
    Stores everything needed to resume trading after a restart.
    """
    # Session identity
    session_name: str
    
    # Account state
    balance: float
    starting_balance: float
    total_fees_paid: float
    
    # Open positions (serialized)
    positions: dict[str, dict]  # coin -> position data
    
    # Trading statistics
    total_trades: int
    winning_trades: int
    
    # Report tracking - ISO timestamp of last report generation
    last_report_timestamp: str | None
    
    # Session metadata
    session_start: str  # ISO timestamp
    last_update: str    # ISO timestamp
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "SessionState":
        """Create from dictionary."""
        # Handle old format without session_name
        if "session_name" not in data:
            data["session_name"] = "default"
        return cls(**data)


class SessionStateManager:
    """
    Manages persistence of trading session state.
    
    Saves state to disk on every significant change, ensuring
    the bot can resume from the exact point it stopped.
    
    Each session has its own folder structure:
        data/sessions/<name>/
            state.json      - Session state
            reports/        - Tuning reports for this session
    """
    
    SESSIONS_DIR = "sessions"
    DEFAULT_SESSION = "default"
    STATE_FILENAME = "state.json"
    REPORTS_DIRNAME = "reports"
    
    def __init__(self, data_dir: str = "data", session_name: str | None = None):
        """
        Initialize the state manager.
        
        Args:
            data_dir: Base directory for data storage
            session_name: Name of the session to use (default: "default")
        """
        self.data_dir = Path(data_dir)
        self.sessions_dir = self.data_dir / self.SESSIONS_DIR
        
        self.session_name = session_name or self.DEFAULT_SESSION
        self.session_dir = self.sessions_dir / self.session_name
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        self.state_file = self.session_dir / self.STATE_FILENAME
        self.reports_dir = self.session_dir / self.REPORTS_DIRNAME
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        self._state: SessionState | None = None
        
        # Migrate old session formats if they exist
        self._migrate_old_sessions()
    
    def _migrate_old_sessions(self) -> None:
        """Migrate from old formats to new session folder structure."""
        # Migrate from data/session_state.json (oldest format)
        old_state_file = self.data_dir / "session_state.json"
        if old_state_file.exists() and self.session_name == self.DEFAULT_SESSION:
            if not self.state_file.exists():
                old_state_file.rename(self.state_file)
        
        # Migrate from data/sessions/<name>.json (previous format)
        old_flat_file = self.sessions_dir / f"{self.session_name}.json"
        if old_flat_file.exists() and old_flat_file.is_file():
            if not self.state_file.exists():
                old_flat_file.rename(self.state_file)
    
    @property
    def has_saved_state(self) -> bool:
        """Check if there's a saved session state for current session."""
        return self.state_file.exists()
    
    def get_reports_dir(self) -> Path:
        """Get the reports directory for this session."""
        return self.reports_dir
    
    @classmethod
    def list_sessions(cls, data_dir: str = "data") -> list[dict]:
        """
        List all available sessions with their summaries.
        
        Args:
            data_dir: Base directory for data storage
            
        Returns:
            List of session info dictionaries
        """
        sessions_dir = Path(data_dir) / cls.SESSIONS_DIR
        if not sessions_dir.exists():
            return []
        
        sessions = []
        # Look for session folders (directories containing state.json)
        for session_folder in sorted(sessions_dir.iterdir()):
            if not session_folder.is_dir():
                continue
            
            state_file = session_folder / cls.STATE_FILENAME
            if not state_file.exists():
                continue
            
            try:
                with open(state_file, "r") as f:
                    data = json.load(f)
                
                state = SessionState.from_dict(data)
                pnl = state.balance - state.starting_balance
                pnl_pct = (pnl / state.starting_balance) * 100 if state.starting_balance > 0 else 0
                win_rate = (state.winning_trades / state.total_trades * 100) if state.total_trades > 0 else 0
                
                # Check if report exists in the session folder
                reports_dir = session_folder / cls.REPORTS_DIRNAME
                has_report = (reports_dir / "report.json").exists() if reports_dir.exists() else False
                
                sessions.append({
                    "name": session_folder.name,
                    "balance": state.balance,
                    "starting_balance": state.starting_balance,
                    "pnl": pnl,
                    "pnl_pct": pnl_pct,
                    "total_trades": state.total_trades,
                    "win_rate": win_rate,
                    "open_positions": len(state.positions),
                    "last_update": state.last_update,
                    "session_start": state.session_start,
                    "has_report": has_report,
                })
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
        
        return sessions
    
    def switch_session(self, session_name: str) -> None:
        """
        Switch to a different session.
        
        Args:
            session_name: Name of the session to switch to
        """
        self.session_name = session_name
        self.session_dir = self.sessions_dir / session_name
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.session_dir / self.STATE_FILENAME
        self.reports_dir = self.session_dir / self.REPORTS_DIRNAME
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self._state = None
    
    def load_state(self) -> SessionState | None:
        """
        Load session state from disk.
        
        Returns:
            SessionState if found and valid, None otherwise
        """
        if not self.state_file.exists():
            return None
        
        try:
            with open(self.state_file, "r") as f:
                data = json.load(f)
            self._state = SessionState.from_dict(data)
            return self._state
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Warning: Could not load session state: {e}")
            return None
    
    def save_state(self, state: SessionState) -> None:
        """
        Save session state to disk.
        
        Args:
            state: The session state to save
        """
        state.last_update = datetime.now().isoformat()
        self._state = state
        
        with open(self.state_file, "w") as f:
            json.dump(state.to_dict(), f, indent=2)
    
    def create_initial_state(self, starting_balance: float) -> SessionState:
        """
        Create a new initial session state.
        
        Args:
            starting_balance: The starting balance for the session
            
        Returns:
            A new SessionState
        """
        now = datetime.now().isoformat()
        return SessionState(
            session_name=self.session_name,
            balance=starting_balance,
            starting_balance=starting_balance,
            total_fees_paid=0.0,
            positions={},
            total_trades=0,
            winning_trades=0,
            last_report_timestamp=None,
            session_start=now,
            last_update=now,
        )
    
    def update_from_trader(
        self,
        balance: float,
        starting_balance: float,
        total_fees_paid: float,
        positions: dict[str, Position],
        trade_count: int,
        winning_count: int,
    ) -> None:
        """
        Update state from PaperTrader data.
        
        Args:
            balance: Current balance
            starting_balance: Original starting balance
            total_fees_paid: Total fees paid
            positions: Dictionary of open positions
            trade_count: Total number of trades
            winning_count: Number of winning trades
        """
        if self._state is None:
            self._state = self.create_initial_state(starting_balance)
        
        # Serialize positions
        serialized_positions = {}
        for coin, pos in positions.items():
            serialized_positions[coin] = {
                "coin": pos.coin,
                "side": pos.side.value,
                "size": pos.size,
                "entry_price": pos.entry_price,
                "entry_time": pos.entry_time.isoformat(),
            }
        
        self._state.balance = balance
        self._state.starting_balance = starting_balance
        self._state.total_fees_paid = total_fees_paid
        self._state.positions = serialized_positions
        self._state.total_trades = trade_count
        self._state.winning_trades = winning_count
        
        self.save_state(self._state)
    
    def deserialize_positions(self, positions_data: dict[str, dict]) -> dict[str, Position]:
        """
        Deserialize positions from saved state.
        
        Args:
            positions_data: Serialized positions dictionary
            
        Returns:
            Dictionary of Position objects
        """
        positions = {}
        for coin, data in positions_data.items():
            positions[coin] = Position(
                coin=data["coin"],
                side=Side(data["side"]),
                size=data["size"],
                entry_price=data["entry_price"],
                entry_time=datetime.fromisoformat(data["entry_time"]),
            )
        return positions
    
    def mark_report_generated(self) -> None:
        """Mark that a report was just generated (for incremental reports)."""
        if self._state:
            self._state.last_report_timestamp = datetime.now().isoformat()
            self.save_state(self._state)
    
    def get_last_report_timestamp(self) -> datetime | None:
        """
        Get the timestamp of the last report generation.
        
        Returns:
            datetime if a report was generated, None if never
        """
        if self._state and self._state.last_report_timestamp:
            return datetime.fromisoformat(self._state.last_report_timestamp)
        return None
    
    def clear_state(self) -> None:
        """Remove saved state (for reset functionality)."""
        if self.state_file.exists():
            self.state_file.unlink()
        self._state = None
    
    def get_session_summary(self) -> dict[str, Any] | None:
        """
        Get a summary of the saved session for display.
        
        Returns:
            Summary dict or None if no saved state
        """
        state = self.load_state()
        if not state:
            return None
        
        pnl = state.balance - state.starting_balance
        pnl_pct = (pnl / state.starting_balance) * 100 if state.starting_balance > 0 else 0
        win_rate = (state.winning_trades / state.total_trades * 100) if state.total_trades > 0 else 0
        
        return {
            "name": self.session_name,
            "balance": state.balance,
            "starting_balance": state.starting_balance,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "total_trades": state.total_trades,
            "winning_trades": state.winning_trades,
            "win_rate": win_rate,
            "open_positions": len(state.positions),
            "session_start": state.session_start,
            "last_update": state.last_update,
            "last_report": state.last_report_timestamp,
        }
    
    @classmethod
    def delete_session(cls, session_name: str, data_dir: str = "data") -> bool:
        """
        Delete a saved session and all its data (state and reports).
        
        Args:
            session_name: Name of the session to delete
            data_dir: Base directory for data storage
            
        Returns:
            True if deleted, False if not found
        """
        import shutil
        session_dir = Path(data_dir) / cls.SESSIONS_DIR / session_name
        if session_dir.exists() and session_dir.is_dir():
            shutil.rmtree(session_dir)
            return True
        return False
