"""
Hyperliquid S3 Historical Data Fetcher.

Downloads historical trade fills from Hyperliquid's public S3 bucket.
Data is stored in LZ4-compressed format and organized by date.

Bucket: s3://hl-mainnet-node-data/node_fills_by_block/
Cost: ~$0.09/GB (requester pays for transfer)

Usage:
    fetcher = HyperliquidS3Fetcher()
    files = fetcher.fetch_range(
        start_date=datetime(2026, 1, 20),
        end_date=datetime(2026, 1, 21),
        output_dir=Path("data/historical/trades/raw"),
    )
"""

import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# Hyperliquid S3 bucket paths
S3_BUCKET = "hl-mainnet-node-data"
S3_FILLS_PATH = "node_fills_by_block"

# Older data formats (for historical reference)
S3_FILLS_OLD_PATH = "node_fills"  # May 25 - July 27, 2025
S3_TRADES_PATH = "node_trades"  # March 22 - May 25, 2025


class HyperliquidS3Fetcher:
    """
    Downloads historical trade fills from Hyperliquid S3.

    Uses AWS CLI for downloading (must be installed and configured).
    Data transfer costs are paid by the requester (~$0.09/GB).
    """

    def __init__(self, bucket: str = S3_BUCKET, verbose: bool = True):
        """
        Initialize the fetcher.

        Args:
            bucket: S3 bucket name
            verbose: Print progress information
        """
        self.bucket = bucket
        self.verbose = verbose

    def _check_aws_cli(self) -> bool:
        """Check if AWS CLI is available."""
        try:
            result = subprocess.run(
                ["aws", "--version"],
                capture_output=True,
                text=True,
                check=False,
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def _format_date_path(self, date: datetime) -> str:
        """Format date as S3 path component (YYYYMMDD)."""
        return date.strftime("%Y%m%d")

    def _log(self, message: str) -> None:
        """Log message if verbose mode is enabled."""
        if self.verbose:
            print(message)
        logger.info(message)

    def list_available_dates(self, limit: int = 30) -> list[str]:
        """
        List available dates in the S3 bucket.

        Args:
            limit: Maximum number of dates to return

        Returns:
            List of date strings (YYYYMMDD format)
        """
        if not self._check_aws_cli():
            raise RuntimeError("AWS CLI not found. Install with: brew install awscli")

        s3_path = f"s3://{self.bucket}/{S3_FILLS_PATH}/"

        result = subprocess.run(
            [
                "aws",
                "s3",
                "ls",
                s3_path,
                "--request-payer",
                "requester",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to list S3 bucket: {result.stderr}")

        # Parse output: "PRE 20260120/"
        dates = []
        for line in result.stdout.strip().split("\n"):
            if "PRE" in line:
                parts = line.split()
                if len(parts) >= 2:
                    date_str = parts[-1].rstrip("/")
                    dates.append(date_str)

        return dates[-limit:] if len(dates) > limit else dates

    def fetch_fills(
        self,
        date: datetime,
        output_dir: Path,
    ) -> Path:
        """
        Download fills for a specific date.

        Args:
            date: Date to fetch
            output_dir: Directory to save files

        Returns:
            Path to the downloaded directory
        """
        if not self._check_aws_cli():
            raise RuntimeError("AWS CLI not found. Install with: brew install awscli")

        date_str = self._format_date_path(date)
        s3_path = f"s3://{self.bucket}/{S3_FILLS_PATH}/{date_str}/"

        # Create output directory
        output_path = output_dir / date_str
        output_path.mkdir(parents=True, exist_ok=True)

        self._log(f"Downloading fills for {date_str}...")
        self._log(f"  Source: {s3_path}")
        self._log(f"  Destination: {output_path}")

        # Download using AWS CLI
        result = subprocess.run(
            [
                "aws",
                "s3",
                "cp",
                s3_path,
                str(output_path),
                "--recursive",
                "--request-payer",
                "requester",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to download from S3: {result.stderr}")

        # Count downloaded files
        files = list(output_path.glob("*.lz4")) + list(output_path.glob("*.json"))
        self._log(f"  Downloaded {len(files)} files")

        return output_path

    def fetch_range(
        self,
        start_date: datetime,
        end_date: datetime,
        output_dir: Path,
    ) -> list[Path]:
        """
        Download fills for a date range.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            output_dir: Directory to save files

        Returns:
            List of paths to downloaded directories
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        downloaded = []
        current_date = start_date

        while current_date <= end_date:
            try:
                path = self.fetch_fills(current_date, output_dir)
                downloaded.append(path)
            except RuntimeError as e:
                self._log(f"  Warning: Failed to fetch {current_date}: {e}")

            current_date += timedelta(days=1)

        self._log(f"Downloaded {len(downloaded)} days of data")
        return downloaded

    def decompress_files(self, directory: Path) -> list[Path]:
        """
        Decompress LZ4 files in a directory.

        Args:
            directory: Directory containing .lz4 files

        Returns:
            List of decompressed file paths
        """
        lz4_files = list(directory.glob("**/*.lz4"))

        if not lz4_files:
            self._log("No .lz4 files found to decompress")
            return []

        self._log(f"Decompressing {len(lz4_files)} files...")

        decompressed = []
        for lz4_file in lz4_files:
            output_file = lz4_file.with_suffix("")

            result = subprocess.run(
                ["lz4", "-d", "-f", str(lz4_file), str(output_file)],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                decompressed.append(output_file)
                # Remove compressed file after successful decompression
                lz4_file.unlink()
            else:
                self._log(f"  Warning: Failed to decompress {lz4_file}: {result.stderr}")

        self._log(f"Decompressed {len(decompressed)} files")
        return decompressed

    def estimate_transfer_cost(self, num_days: int) -> str:
        """
        Estimate data transfer cost for a given number of days.

        Args:
            num_days: Number of days of data

        Returns:
            Estimated cost string
        """
        # Rough estimate: ~50-200MB per day depending on volume
        avg_mb_per_day = 100
        total_gb = (num_days * avg_mb_per_day) / 1024
        cost = total_gb * 0.09  # $0.09/GB

        return f"~{total_gb:.1f} GB, estimated cost: ${cost:.2f}"
