"""
Hyperliquid exchange integration.

Public (no auth needed):
- get_all_prices(): Get live prices for all pairs
- get_price(coin): Get price for a single coin
- get_candles(coin, interval, limit): Get historical OHLCV data
- get_markets(): Get available trading pairs

Authenticated (requires API key):
- HyperliquidClient: Full trading client

WebSocket (robust connection management):
- WebSocketManager: Auto-reconnect, heartbeat, emergency callbacks
"""

from bot.hyperliquid.public_data import (
    get_all_prices,
    get_candles,
    get_markets,
    get_orderbook,
    get_price,
)
from bot.hyperliquid.websocket_manager import (
    WebSocketManager,
    WebSocketConfig,
    ConnectionState,
    ConnectionMetrics,
)

__all__ = [
    "get_all_prices",
    "get_price", 
    "get_candles",
    "get_markets",
    "get_orderbook",
    "WebSocketManager",
    "WebSocketConfig",
    "ConnectionState",
    "ConnectionMetrics",
]
