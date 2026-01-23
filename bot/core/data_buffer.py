"""
Data buffer for Scalper AI interpretation.

Buffers raw market data (prices, trades, orderbook) at human-scale intervals
for AI interpretation through the Scalper persona.
"""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ScalperDataWindow:
    """
    Raw data window for AI interpretation - human scalper scale.

    Holds the last 60 seconds of market data for a single coin,
    formatted for AI interpretation rather than algorithmic analysis.
    """

    coin: str

    # Price data (last 60 seconds at 1s granularity)
    price_history: deque[dict] = field(default_factory=lambda: deque(maxlen=60))

    # Trade tape (last 50 trades with full details)
    recent_trades: deque[dict] = field(default_factory=lambda: deque(maxlen=50))

    # Orderbook snapshots (last 3 snapshots at 5s intervals)
    orderbook_snapshots: deque[dict] = field(default_factory=lambda: deque(maxlen=3))

    # Last price update timestamp (for 1s throttling)
    _last_price_time: datetime | None = field(default=None, repr=False)

    # Last orderbook update timestamp (for 5s throttling)
    _last_orderbook_time: datetime | None = field(default=None, repr=False)

    def add_price(self, price: float, timestamp: datetime | None = None) -> None:
        """
        Add a price point to history (throttled to 1s intervals).

        Args:
            price: Current price of the asset
            timestamp: Optional timestamp (uses current time if None).
                       For historical replay, pass simulated time to
                       ensure proper throttling based on simulated intervals.
        """
        now = timestamp or datetime.now()

        # Throttle to 1 price per second based on provided time
        if self._last_price_time is not None:
            elapsed = (now - self._last_price_time).total_seconds()
            if elapsed < 1.0:
                return

        self.price_history.appendleft(
            {
                "price": price,
                "time": now,
            }
        )
        self._last_price_time = now

    def add_trade(self, trade: dict) -> None:
        """
        Add a trade to the tape.

        Args:
            trade: Trade dict with keys: side, size, price, time (optional)
        """
        trade_record = {
            "side": trade.get("side", "unknown"),
            "size": float(trade.get("sz", trade.get("size", 0))),
            "price": float(trade.get("px", trade.get("price", 0))),
            "time": trade.get("time", datetime.now()),
        }
        self.recent_trades.appendleft(trade_record)

    def add_orderbook(self, bids: list, asks: list) -> None:
        """
        Add an orderbook snapshot (throttled to 5s intervals).

        Args:
            bids: List of bid levels [{px, sz, n}, ...]
            asks: List of ask levels [{px, sz, n}, ...]
        """
        now = datetime.now()

        # Throttle to 1 snapshot per 5 seconds
        if self._last_orderbook_time is not None:
            elapsed = (now - self._last_orderbook_time).total_seconds()
            if elapsed < 5.0:
                return

        self.orderbook_snapshots.appendleft(
            {
                "bids": bids[:5],  # Top 5 levels
                "asks": asks[:5],
                "time": now,
            }
        )
        self._last_orderbook_time = now

    def get_summary(self) -> dict[str, Any]:
        """
        Get a summary of the data window for prompt formatting.

        Returns:
            Dict with price_1min_ago, price_change_1min, tape stats, etc.
        """
        summary: dict[str, Any] = {
            "coin": self.coin,
            "current_price": None,
            "price_1min_ago": None,
            "price_change_1min": None,
            "num_prices": len(self.price_history),
            "num_trades": len(self.recent_trades),
            "buy_count": 0,
            "sell_count": 0,
            "buy_volume": 0.0,
            "sell_volume": 0.0,
            "avg_trade_size": 0.0,
            "large_trades": [],
            "bid_depth": 0.0,
            "ask_depth": 0.0,
            "book_imbalance": "Balanced",
        }

        # Price summary
        if self.price_history:
            summary["current_price"] = self.price_history[0]["price"]

            # Find price from ~60s ago
            if len(self.price_history) > 1:
                oldest = self.price_history[-1]
                summary["price_1min_ago"] = oldest["price"]

                if oldest["price"] > 0:
                    change = (summary["current_price"] - oldest["price"]) / oldest["price"] * 100
                    summary["price_change_1min"] = change

        # Trade tape summary
        if self.recent_trades:
            sizes = []
            for trade in self.recent_trades:
                size = trade["size"]
                sizes.append(size)

                if trade["side"] == "buy":
                    summary["buy_count"] += 1
                    summary["buy_volume"] += size
                else:
                    summary["sell_count"] += 1
                    summary["sell_volume"] += size

            if sizes:
                summary["avg_trade_size"] = sum(sizes) / len(sizes)

                # Find large trades (>2x average)
                avg = summary["avg_trade_size"]
                if avg > 0:
                    summary["large_trades"] = [t for t in self.recent_trades if t["size"] > avg * 2]

        # Orderbook summary
        if self.orderbook_snapshots:
            latest = self.orderbook_snapshots[0]

            bid_depth = sum(float(b.get("sz", 0)) for b in latest.get("bids", []))
            ask_depth = sum(float(a.get("sz", 0)) for a in latest.get("asks", []))

            summary["bid_depth"] = bid_depth
            summary["ask_depth"] = ask_depth

            total = bid_depth + ask_depth
            if total > 0:
                bid_pct = bid_depth / total * 100
                if bid_pct > 60:
                    summary["book_imbalance"] = f"{bid_pct:.0f}% bids - BUYERS dominating"
                elif bid_pct < 40:
                    summary["book_imbalance"] = f"{bid_pct:.0f}% bids - SELLERS dominating"
                else:
                    summary["book_imbalance"] = f"{bid_pct:.0f}% bids - Balanced"

        return summary

    def get_tape_timespan(self) -> str:
        """Get human-readable timespan of the trade tape."""
        if len(self.recent_trades) < 2:
            return "N/A"

        newest = self.recent_trades[0]["time"]
        oldest = self.recent_trades[-1]["time"]

        if isinstance(newest, datetime) and isinstance(oldest, datetime):
            seconds = (newest - oldest).total_seconds()
            if seconds < 60:
                return f"{seconds:.0f}s"
            else:
                return f"{seconds/60:.1f}m"

        return "N/A"

    def clear(self) -> None:
        """Clear all buffered data."""
        self.price_history.clear()
        self.recent_trades.clear()
        self.orderbook_snapshots.clear()
        self._last_price_time = None
        self._last_orderbook_time = None


class CoinDataBufferManager:
    """
    Manages ScalperDataWindow instances for multiple coins.

    Provides a unified interface for updating market data across all tracked coins.
    """

    def __init__(self, coins: list[str]):
        """
        Initialize buffer manager for given coins.

        Args:
            coins: List of coin symbols to track (e.g., ["BTC", "ETH", "SOL"])
        """
        self.coins = coins
        self._windows: dict[str, ScalperDataWindow] = {
            coin: ScalperDataWindow(coin=coin) for coin in coins
        }

    def update_price(self, coin: str, price: float, timestamp: datetime | None = None) -> None:
        """
        Update price for a coin.

        Args:
            coin: Coin symbol
            price: Current price
            timestamp: Optional timestamp for historical replay
        """
        if coin in self._windows:
            self._windows[coin].add_price(price, timestamp)

    def update_trade(self, coin: str, trade: dict) -> None:
        """
        Add a trade for a coin.

        Args:
            coin: Coin symbol
            trade: Trade data dict
        """
        if coin in self._windows:
            self._windows[coin].add_trade(trade)

    def update_orderbook(self, coin: str, bids: list, asks: list) -> None:
        """
        Update orderbook for a coin.

        Args:
            coin: Coin symbol
            bids: List of bid levels
            asks: List of ask levels
        """
        if coin in self._windows:
            self._windows[coin].add_orderbook(bids, asks)

    def get_window(self, coin: str) -> ScalperDataWindow | None:
        """
        Get the data window for a coin.

        Args:
            coin: Coin symbol

        Returns:
            ScalperDataWindow or None if coin not tracked
        """
        return self._windows.get(coin)

    def get_all_windows(self) -> dict[str, ScalperDataWindow]:
        """Get all data windows."""
        return self._windows

    def clear_all(self) -> None:
        """Clear all buffered data for all coins."""
        for window in self._windows.values():
            window.clear()
