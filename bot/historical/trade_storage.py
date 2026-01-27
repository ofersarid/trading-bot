"""
Trade Data Storage.

Stores and loads trade data in efficient formats:
- Parquet: Primary format (~10x smaller than CSV, fast columnar reads)
- CSV: Fallback format for compatibility

Usage:
    storage = TradeStorage()

    # Save trades
    storage.save_trades(trades, Path("data/trades/BTC_20260120.parquet"))

    # Load trades
    for trade in storage.load_trades(Path("data/trades/BTC_20260120.parquet")):
        process(trade)
"""

import csv
import logging
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Literal, cast

from bot.indicators.volume_profile.models import Trade

logger = logging.getLogger(__name__)

# Check for pyarrow availability
try:
    import pyarrow as pa
    import pyarrow.parquet as pq

    PARQUET_AVAILABLE = True
except ImportError:
    pa = None
    pq = None
    PARQUET_AVAILABLE = False
    logger.warning(
        "pyarrow not installed. Parquet support disabled. Install with: pip install pyarrow"
    )


class TradeStorage:
    """
    Stores and loads trade data in Parquet or CSV format.

    Parquet is preferred for:
    - ~10x smaller file size
    - Fast columnar reads
    - Efficient filtering

    CSV is used as fallback if pyarrow is not installed.
    """

    def __init__(self, verbose: bool = False):
        """
        Initialize the storage.

        Args:
            verbose: Print progress information
        """
        self.verbose = verbose

    def _log(self, message: str) -> None:
        """Log message if verbose mode is enabled."""
        if self.verbose:
            print(message)
        logger.info(message)

    def save_trades(
        self,
        trades: list[Trade] | Iterator[Trade],
        filepath: Path,
        format: str = "auto",
    ) -> Path:
        """
        Save trades to file.

        Args:
            trades: List or iterator of Trade objects
            filepath: Output file path
            format: "parquet", "csv", or "auto" (based on extension)

        Returns:
            Path to saved file
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Determine format
        if format == "auto":
            if filepath.suffix == ".parquet":
                format = "parquet"
            elif filepath.suffix == ".csv":
                format = "csv"
            else:
                format = "parquet" if PARQUET_AVAILABLE else "csv"
                filepath = filepath.with_suffix(f".{format}")

        # Convert iterator to list if needed
        if not isinstance(trades, list):
            trades = list(trades)

        if format == "parquet":
            return self._save_parquet(trades, filepath)
        else:
            return self._save_csv(trades, filepath)

    def _save_parquet(self, trades: list[Trade], filepath: Path) -> Path:
        """Save trades to Parquet format."""
        if not PARQUET_AVAILABLE:
            raise RuntimeError("pyarrow not installed. Install with: pip install pyarrow")

        self._log(f"Saving {len(trades)} trades to Parquet: {filepath}")

        # Create arrays for each column
        timestamps = [t.timestamp for t in trades]
        prices = [t.price for t in trades]
        sizes = [t.size for t in trades]
        sides = [t.side for t in trades]
        coins = [t.coin for t in trades]

        # Create PyArrow table
        table = pa.table(
            {
                "timestamp": pa.array(timestamps, type=pa.timestamp("us")),
                "price": pa.array(prices, type=pa.float64()),
                "size": pa.array(sizes, type=pa.float64()),
                "side": pa.array(sides, type=pa.string()),
                "coin": pa.array(coins, type=pa.string()),
            }
        )

        # Write to Parquet
        pq.write_table(table, filepath, compression="snappy")

        size_kb = filepath.stat().st_size / 1024
        self._log(f"  Saved {len(trades)} trades ({size_kb:.1f} KB)")

        return filepath

    def _save_csv(self, trades: list[Trade], filepath: Path) -> Path:
        """Save trades to CSV format."""
        self._log(f"Saving {len(trades)} trades to CSV: {filepath}")

        with filepath.open("w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["timestamp", "price", "size", "side", "coin"],
            )
            writer.writeheader()

            for trade in trades:
                writer.writerow(trade.to_dict())

        size_kb = filepath.stat().st_size / 1024
        self._log(f"  Saved {len(trades)} trades ({size_kb:.1f} KB)")

        return filepath

    def load_trades(
        self,
        filepath: Path,
        coin: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> Iterator[Trade]:
        """
        Load trades from file.

        Args:
            filepath: Path to trades file
            coin: Optional coin filter
            start_time: Optional start time filter
            end_time: Optional end time filter

        Yields:
            Trade objects
        """
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        if filepath.suffix == ".parquet":
            yield from self._load_parquet(filepath, coin, start_time, end_time)
        else:
            yield from self._load_csv(filepath, coin, start_time, end_time)

    def _load_parquet(
        self,
        filepath: Path,
        coin: str | None,
        start_time: datetime | None,
        end_time: datetime | None,
    ) -> Iterator[Trade]:
        """Load trades from Parquet format."""
        if not PARQUET_AVAILABLE:
            raise RuntimeError("pyarrow not installed. Install with: pip install pyarrow")

        self._log(f"Loading trades from Parquet: {filepath}")

        # Build filters for efficient reading
        filters = []
        if coin:
            filters.append(("coin", "==", coin.upper()))

        # Read table with filters
        table = pq.read_table(
            filepath,
            filters=filters if filters else None,
        )

        # Convert to pandas for easy iteration
        df = table.to_pandas()

        count = 0
        for _, row in df.iterrows():
            timestamp = row["timestamp"].to_pydatetime()

            # Apply time filters
            if start_time and timestamp < start_time:
                continue
            if end_time and timestamp > end_time:
                continue

            yield Trade(
                timestamp=timestamp,
                price=float(row["price"]),
                size=float(row["size"]),
                side=row["side"],
                coin=row["coin"],
            )
            count += 1

        self._log(f"  Loaded {count} trades")

    def _load_csv(
        self,
        filepath: Path,
        coin: str | None,
        start_time: datetime | None,
        end_time: datetime | None,
    ) -> Iterator[Trade]:
        """Load trades from CSV format."""
        self._log(f"Loading trades from CSV: {filepath}")

        count = 0
        with filepath.open("r") as f:
            reader = csv.DictReader(f)

            for row in reader:
                # Parse timestamp
                timestamp = datetime.fromisoformat(row["timestamp"])

                # Apply filters
                if coin and row.get("coin", "").upper() != coin.upper():
                    continue
                if start_time and timestamp < start_time:
                    continue
                if end_time and timestamp > end_time:
                    continue

                yield Trade(
                    timestamp=timestamp,
                    price=float(row["price"]),
                    size=float(row["size"]),
                    side=cast(Literal["B", "A"], row["side"]),
                    coin=row.get("coin", ""),
                )
                count += 1

        self._log(f"  Loaded {count} trades")

    def get_file_info(self, filepath: Path) -> dict:
        """
        Get information about a trade data file.

        Args:
            filepath: Path to trades file

        Returns:
            Dictionary with file information
        """
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        info = {
            "path": str(filepath),
            "size_bytes": filepath.stat().st_size,
            "size_mb": filepath.stat().st_size / (1024 * 1024),
            "format": filepath.suffix.lstrip("."),
        }

        if filepath.suffix == ".parquet" and PARQUET_AVAILABLE:
            # Get Parquet metadata
            parquet_file = pq.ParquetFile(filepath)
            info["num_rows"] = parquet_file.metadata.num_rows
            info["num_columns"] = parquet_file.metadata.num_columns
            info["compression"] = parquet_file.metadata.row_group(0).column(0).compression

        return info


def generate_trade_filename(
    coin: str,
    start_date: datetime,
    end_date: datetime | None = None,
    extension: str = "parquet",
) -> str:
    """
    Generate a descriptive filename for trade data.

    Args:
        coin: Coin symbol
        start_date: Start date
        end_date: End date (optional, uses start_date if not provided)
        extension: File extension

    Returns:
        Filename string
    """
    start_str = start_date.strftime("%Y%m%d")

    if end_date and end_date.date() != start_date.date():
        end_str = end_date.strftime("%Y%m%d")
        return f"{coin}_trades_{start_str}_to_{end_str}.{extension}"
    else:
        return f"{coin}_trades_{start_str}.{extension}"
