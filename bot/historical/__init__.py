"""
Historical data module for backtesting and case studies.

Provides two types of historical data:
1. Candle data (OHLCV) from Bybit - for standard indicator backtesting
2. Trade data (tick-level) from Hyperliquid S3 - for Volume Profile analysis
"""

from bot.historical.fetcher import BybitHistoricalFetcher
from bot.historical.fill_parser import HyperliquidFillParser
from bot.historical.models import HistoricalCandle
from bot.historical.s3_fetcher import HyperliquidS3Fetcher
from bot.historical.trade_storage import TradeStorage

__all__ = [
    # Candle data (Bybit)
    "BybitHistoricalFetcher",
    "HistoricalCandle",
    # Trade data (Hyperliquid)
    "HyperliquidS3Fetcher",
    "HyperliquidFillParser",
    "TradeStorage",
]
