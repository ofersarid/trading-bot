"""
AI reasoning panel component.

Displays AI/analysis reasoning log with auto-scroll.
"""

from collections import deque
from datetime import datetime
import logging

from textual.containers import Container, ScrollableContainer
from textual.widgets import Static
from textual.app import ComposeResult


logger = logging.getLogger("ai_panel")


class AIPanel(Container):
    """Panel displaying AI reasoning and analysis log."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.messages: deque = deque(maxlen=100)
        self._title_widget: Static | None = None
    
    def compose(self) -> ComposeResult:
        yield Static("🧠 AI REASONING", classes="panel-title", id="ai-title")
        with ScrollableContainer(id="ai-scroll", classes="panel-content"):
            yield Static("", id="ai-content")
    
    def log(self, message: str) -> None:
        """
        Log a message to the AI panel.
        
        Args:
            message: Message with optional Rich markup
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.messages.append(f"[dim]{timestamp}[/dim] {message}")
        
        try:
            content = self.query_one("#ai-content", Static)
            content.update("\n".join(self.messages))
            # Auto-scroll to bottom
            scroll = self.query_one("#ai-scroll", ScrollableContainer)
            scroll.scroll_end(animate=False)
        except Exception as e:
            logger.debug(f"AI panel not ready: {e}")
    
    def update_title(
        self,
        analysis_mode: str,
        ai_model: str,
        tokens_used: int = 0,
        ai_calls: int = 0,
        disconnects: int = 0,
        reconnects: int = 0,
    ) -> None:
        """
        Update the AI panel title with mode and stats.
        
        Args:
            analysis_mode: Current analysis mode ("RULE-BASED" or "AI (Claude)")
            ai_model: Name of the AI model in use
            tokens_used: Total tokens consumed
            ai_calls: Number of AI API calls made
            disconnects: Total WebSocket disconnects
            reconnects: Successful reconnection count
        """
        try:
            title = self.query_one("#ai-title", Static)
            
            # Connection stats
            conn_info = ""
            if disconnects > 0:
                conn_info = f" [dim]│[/dim] [yellow]Reconn: {reconnects}[/yellow] [dim]│[/dim] [red]Disc: {disconnects}[/red]"
            
            if analysis_mode == "RULE-BASED":
                title.update(
                    f"🧠 ANALYSIS [dim]│[/dim] [yellow]📐 {analysis_mode}[/yellow] [dim]│[/dim] "
                    f"Model: [cyan]{ai_model}[/cyan]{conn_info}"
                )
            else:
                title.update(
                    f"🧠 AI REASONING [dim]│[/dim] [#44ffaa]🤖 {analysis_mode}[/#44ffaa] [dim]│[/dim] "
                    f"Model: [cyan]{ai_model}[/cyan] [dim]│[/dim] "
                    f"Tokens: [magenta]{tokens_used:,}[/magenta] [dim]│[/dim] "
                    f"Calls: [blue]{ai_calls}[/blue]{conn_info}"
                )
        except Exception as e:
            logger.debug(f"AI title not ready: {e}")
