"""
Data Server Package.

Background server for multi-terminal dashboard architecture.
Handles WebSocket connection and writes state files for UI terminals.
"""

from bot.server.data_server import DataServer

__all__ = ["DataServer"]
