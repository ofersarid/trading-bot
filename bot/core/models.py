"""
Core data models for the trading bot.

Contains dataclasses for:
- Opportunity tracking and validation
- Market conditions
- Trade signals
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class OpportunityCondition:
    """A single condition that must be met for opportunity validation.
    
    Attributes:
        name: Short identifier for the condition (e.g., "Momentum", "Balance")
        description: Human-readable description of what must be true
        met: Whether this condition is currently satisfied
        value: Current value/status to display (e.g., "+0.35%", "✓")
    """
    name: str
    description: str
    met: bool = False
    value: str = ""


@dataclass
class PendingOpportunity:
    """An opportunity being validated before execution.
    
    Tracks a potential trade as conditions are progressively validated.
    When all conditions are met, the opportunity becomes valid for execution.
    
    Attributes:
        coin: Trading pair symbol (e.g., "BTC", "ETH")
        direction: Trade direction - "LONG" or "SHORT"
        conditions: List of conditions to validate
        start_time: When this opportunity was first detected
        current_price: Latest price for this coin
    """
    coin: str
    direction: str  # "LONG" or "SHORT"
    conditions: list[OpportunityCondition] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    current_price: float = 0.0

    @property
    def conditions_met(self) -> int:
        """Number of conditions currently satisfied."""
        return sum(1 for c in self.conditions if c.met)

    @property
    def total_conditions(self) -> int:
        """Total number of conditions to validate."""
        return len(self.conditions)

    @property
    def progress_bar(self) -> str:
        """Visual progress bar showing validation status."""
        filled = self.conditions_met
        total = self.total_conditions
        bar = "█" * filled + "░" * (total - filled)
        return f"[{bar}]"

    @property
    def is_valid(self) -> bool:
        """True when all conditions are met and trade can execute."""
        return all(c.met for c in self.conditions)
