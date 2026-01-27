"""
Hyperliquid Fill Parser.

Parses trade fill data from Hyperliquid's node_fills format into Trade objects.

Hyperliquid has evolved through three fill data formats:
1. node_trades (March 22 - May 25, 2025): Basic trade data
2. node_fills (May 25 - July 27, 2025): Enhanced with PnL and fees
3. node_fills_by_block (July 27, 2025 - Current): Organized by block

This parser handles the current node_fills_by_block format.
"""

import json
import logging
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Literal

from bot.indicators.volume_profile.models import Trade

logger = logging.getLogger(__name__)


class HyperliquidFillParser:
    """
    Parses Hyperliquid node_fills format into Trade objects.

    The node_fills_by_block format contains fills organized by block,
    with each fill including: coin, px (price), sz (size), side, time, etc.
    """

    def __init__(self, verbose: bool = False):
        """
        Initialize the parser.

        Args:
            verbose: Print progress information
        """
        self.verbose = verbose
        self._parse_errors = 0

    def _log(self, message: str) -> None:
        """Log message if verbose mode is enabled."""
        if self.verbose:
            print(message)
        logger.debug(message)

    def parse_file(self, filepath: Path) -> Iterator[Trade]:
        """
        Parse a single fills file.

        Args:
            filepath: Path to the fills file (JSON or decompressed LZ4)

        Yields:
            Trade objects
        """
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        self._log(f"Parsing {filepath.name}...")

        try:
            with filepath.open("r") as f:
                content = f.read()

            # Try to parse as JSON
            # The file might contain one JSON object per line (NDJSON)
            # or a single JSON array
            if content.strip().startswith("["):
                # Single JSON array
                data = json.loads(content)
                yield from self._parse_fills_array(data)
            else:
                # NDJSON format (one object per line)
                for line in content.strip().split("\n"):
                    if line.strip():
                        try:
                            obj = json.loads(line)
                            yield from self._parse_fill_object(obj)
                        except json.JSONDecodeError as e:
                            self._parse_errors += 1
                            logger.warning(f"Failed to parse line: {e}")

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {filepath}: {e}") from e

    def _parse_fills_array(self, data: list) -> Iterator[Trade]:
        """Parse a JSON array of fills."""
        for item in data:
            yield from self._parse_fill_object(item)

    def _parse_fill_object(self, obj: dict) -> Iterator[Trade]:
        """
        Parse a single fill object or block of fills.

        The structure can vary:
        - Direct fill: {coin, px, sz, side, time, ...}
        - Block with fills: {fills: [...], ...}
        - Nested structure with multiple fills
        """
        # Check if this is a block containing fills
        if "fills" in obj:
            fills = obj["fills"]
            if isinstance(fills, list):
                for fill in fills:
                    trade = self._fill_to_trade(fill)
                    if trade:
                        yield trade
        elif "coin" in obj and "px" in obj:
            # Direct fill object
            trade = self._fill_to_trade(obj)
            if trade:
                yield trade
        else:
            # Try to find fills in nested structure
            for _, value in obj.items():
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict) and "px" in item:
                            trade = self._fill_to_trade(item)
                            if trade:
                                yield trade

    def _fill_to_trade(self, fill: dict) -> Trade | None:
        """
        Convert a fill dictionary to a Trade object.

        Expected fields:
        - coin: Asset symbol (e.g., "BTC", "ETH")
        - px: Price
        - sz: Size
        - side: "B" (buy) or "A" (sell)
        - time: Timestamp (milliseconds or ISO string)
        """
        try:
            # Parse timestamp
            time_value = fill.get("time", fill.get("timestamp", fill.get("t")))
            if time_value is None:
                # Use current time if no timestamp
                timestamp = datetime.now()
            elif isinstance(time_value, int):
                # Milliseconds timestamp
                timestamp = datetime.fromtimestamp(time_value / 1000)
            elif isinstance(time_value, float):
                timestamp = datetime.fromtimestamp(time_value)
            else:
                # ISO string
                timestamp = datetime.fromisoformat(str(time_value).replace("Z", "+00:00"))

            # Parse price
            price = float(fill.get("px", fill.get("price", 0)))

            # Parse size
            size = float(fill.get("sz", fill.get("size", fill.get("fillSz", 0))))

            # Parse side
            side_raw = fill.get("side", fill.get("dir", ""))
            side: Literal["B", "A"]
            if side_raw in ("B", "buy", "Buy", "BUY", "Long", "long"):
                side = "B"
            elif side_raw in ("A", "sell", "Sell", "SELL", "Short", "short"):
                side = "A"
            else:
                # Default to "B" if unknown
                side = "B"

            # Parse coin
            coin = str(fill.get("coin", fill.get("asset", fill.get("symbol", ""))))

            if price <= 0 or size <= 0:
                return None

            return Trade(
                timestamp=timestamp,
                price=price,
                size=size,
                side=side,
                coin=coin,
            )

        except (KeyError, ValueError, TypeError) as e:
            self._parse_errors += 1
            logger.warning(f"Failed to parse fill: {e}")
            return None

    def parse_directory(self, directory: Path, coin: str | None = None) -> Iterator[Trade]:
        """
        Parse all fill files in a directory.

        Args:
            directory: Directory containing fill files
            coin: Optional coin filter (e.g., "BTC")

        Yields:
            Trade objects, optionally filtered by coin
        """
        directory = Path(directory)

        if not directory.is_dir():
            raise NotADirectoryError(f"Not a directory: {directory}")

        # Find all JSON files
        files = list(directory.glob("**/*.json"))
        files.extend(directory.glob("**/*[!.lz4]"))  # Files without .lz4 extension

        # Filter out non-data files
        files = [f for f in files if f.is_file() and f.suffix != ".lz4"]

        self._log(f"Found {len(files)} files to parse")

        for filepath in sorted(files):
            try:
                for trade in self.parse_file(filepath):
                    if coin is None or trade.coin.upper() == coin.upper():
                        yield trade
            except Exception as e:
                logger.warning(f"Failed to parse {filepath}: {e}")

    def filter_by_coin(self, trades: Iterator[Trade], coin: str) -> Iterator[Trade]:
        """
        Filter trades for a specific coin.

        Args:
            trades: Iterator of Trade objects
            coin: Coin symbol to filter (e.g., "BTC")

        Yields:
            Trades matching the specified coin
        """
        coin_upper = coin.upper()
        for trade in trades:
            if trade.coin.upper() == coin_upper:
                yield trade

    def filter_by_time_range(
        self,
        trades: Iterator[Trade],
        start: datetime,
        end: datetime,
    ) -> Iterator[Trade]:
        """
        Filter trades by time range.

        Args:
            trades: Iterator of Trade objects
            start: Start time (inclusive)
            end: End time (inclusive)

        Yields:
            Trades within the specified time range
        """
        for trade in trades:
            if start <= trade.timestamp <= end:
                yield trade

    @property
    def parse_errors(self) -> int:
        """Number of parsing errors encountered."""
        return self._parse_errors

    def reset_errors(self) -> None:
        """Reset the error counter."""
        self._parse_errors = 0
