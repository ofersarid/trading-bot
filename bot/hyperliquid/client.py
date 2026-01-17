"""
Hyperliquid Client Wrapper

A simplified interface for interacting with Hyperliquid's testnet/mainnet API.
Handles authentication, order management, and market data retrieval.

NOTE: This client requires authentication (private key).
For public data (prices, candles), use public_data.py instead.
"""

import os
from dataclasses import dataclass
from typing import Literal

import eth_account
from dotenv import load_dotenv
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants


@dataclass
class OrderResult:
    """Structured result from order operations."""

    success: bool
    order_id: str | None = None
    filled_size: float | None = None
    avg_price: float | None = None
    error: str | None = None
    raw_response: dict | None = None


class HyperliquidClient:
    """
    Wrapper around Hyperliquid SDK for paper trading.

    Usage:
        client = HyperliquidClient.from_env()
        client.market_buy("ETH", 0.1)
    """

    def __init__(
        self,
        private_key: str,
        env: Literal["testnet", "mainnet"] = "testnet",
    ):
        self.env = env
        self._wallet = eth_account.Account.from_key(private_key)
        self._api_url = (
            constants.TESTNET_API_URL if env == "testnet" else constants.MAINNET_API_URL
        )

        self._info = Info(self._api_url, skip_ws=True)
        self._exchange = Exchange(self._wallet, self._api_url)

    @classmethod
    def from_env(cls, env_path: str | None = None) -> "HyperliquidClient":
        """
        Create client from environment variables.

        Looks for:
        - HYPERLIQUID_PRIVATE_KEY (required)
        - HYPERLIQUID_ENV (optional, defaults to 'testnet')
        """
        if env_path:
            load_dotenv(env_path)
        else:
            load_dotenv()

        private_key = os.getenv("HYPERLIQUID_PRIVATE_KEY")
        if not private_key:
            raise ValueError(
                "HYPERLIQUID_PRIVATE_KEY not found in environment. "
                "Set it in .env or export it."
            )

        env = os.getenv("HYPERLIQUID_ENV", "testnet")
        if env not in ("testnet", "mainnet"):
            raise ValueError(f"HYPERLIQUID_ENV must be 'testnet' or 'mainnet', got: {env}")

        return cls(private_key=private_key, env=env)

    @property
    def address(self) -> str:
        """The wallet address associated with this client."""
        return self._wallet.address

    def get_user_state(self) -> dict:
        """
        Get current account state including balances and positions.

        Returns dict with:
        - marginSummary: account equity, margin info
        - crossMarginSummary: cross margin details
        - assetPositions: list of open positions
        """
        return self._info.user_state(self.address)

    def get_balance(self) -> float:
        """Get available USDC balance."""
        state = self.get_user_state()
        return float(state.get("marginSummary", {}).get("accountValue", 0))

    def get_positions(self) -> list[dict]:
        """Get all open positions."""
        state = self.get_user_state()
        return state.get("assetPositions", [])

    def get_markets(self) -> list[dict]:
        """Get all available trading pairs with their metadata."""
        meta = self._info.meta()
        return meta.get("universe", [])

    def get_price(self, coin: str) -> float | None:
        """Get current mid price for a coin."""
        all_mids = self._info.all_mids()
        return float(all_mids.get(coin)) if coin in all_mids else None

    def market_buy(
        self,
        coin: str,
        size: float,
        slippage: float = 0.01,
    ) -> OrderResult:
        """
        Execute a market buy order.

        Args:
            coin: Trading pair symbol (e.g., "ETH", "BTC")
            size: Order size in base currency
            slippage: Max slippage tolerance (default 1%)

        Returns:
            OrderResult with fill details or error
        """
        return self._market_order(coin, is_buy=True, size=size, slippage=slippage)

    def market_sell(
        self,
        coin: str,
        size: float,
        slippage: float = 0.01,
    ) -> OrderResult:
        """
        Execute a market sell order.

        Args:
            coin: Trading pair symbol (e.g., "ETH", "BTC")
            size: Order size in base currency
            slippage: Max slippage tolerance (default 1%)

        Returns:
            OrderResult with fill details or error
        """
        return self._market_order(coin, is_buy=False, size=size, slippage=slippage)

    def _market_order(
        self,
        coin: str,
        is_buy: bool,
        size: float,
        slippage: float,
    ) -> OrderResult:
        """Internal market order execution."""
        try:
            result = self._exchange.market_open(
                coin=coin,
                is_buy=is_buy,
                sz=size,
                px=None,
                slippage=slippage,
            )

            if result.get("status") != "ok":
                return OrderResult(
                    success=False,
                    error=str(result),
                    raw_response=result,
                )

            statuses = result.get("response", {}).get("data", {}).get("statuses", [])
            for status in statuses:
                if "filled" in status:
                    filled = status["filled"]
                    return OrderResult(
                        success=True,
                        order_id=str(filled.get("oid")),
                        filled_size=float(filled.get("totalSz", 0)),
                        avg_price=float(filled.get("avgPx", 0)),
                        raw_response=result,
                    )

            return OrderResult(
                success=False,
                error="Order not filled",
                raw_response=result,
            )

        except Exception as e:
            return OrderResult(success=False, error=str(e))

    def limit_order(
        self,
        coin: str,
        is_buy: bool,
        size: float,
        price: float,
        time_in_force: Literal["Gtc", "Ioc", "Alo"] = "Gtc",
        reduce_only: bool = False,
    ) -> OrderResult:
        """
        Place a limit order.

        Args:
            coin: Trading pair symbol
            is_buy: True for buy, False for sell
            size: Order size
            price: Limit price
            time_in_force: Gtc (Good-til-canceled), Ioc (Immediate-or-cancel), Alo (Add-liquidity-only)
            reduce_only: If True, only reduces existing position

        Returns:
            OrderResult with order ID or error
        """
        try:
            result = self._exchange.order(
                coin=coin,
                is_buy=is_buy,
                sz=size,
                limit_px=price,
                order_type={"limit": {"tif": time_in_force}},
                reduce_only=reduce_only,
            )

            if result.get("status") != "ok":
                return OrderResult(
                    success=False,
                    error=str(result),
                    raw_response=result,
                )

            statuses = result.get("response", {}).get("data", {}).get("statuses", [])
            for status in statuses:
                if "resting" in status:
                    return OrderResult(
                        success=True,
                        order_id=str(status["resting"]["oid"]),
                        raw_response=result,
                    )
                if "filled" in status:
                    filled = status["filled"]
                    return OrderResult(
                        success=True,
                        order_id=str(filled.get("oid")),
                        filled_size=float(filled.get("totalSz", 0)),
                        avg_price=float(filled.get("avgPx", 0)),
                        raw_response=result,
                    )

            return OrderResult(
                success=False,
                error="Unknown order status",
                raw_response=result,
            )

        except Exception as e:
            return OrderResult(success=False, error=str(e))

    def cancel_order(self, coin: str, order_id: int) -> bool:
        """
        Cancel an open order.

        Args:
            coin: Trading pair symbol
            order_id: The order ID to cancel

        Returns:
            True if cancelled successfully
        """
        try:
            result = self._exchange.cancel(coin, order_id)
            return result.get("status") == "ok"
        except Exception:
            return False

    def close_position(self, coin: str) -> OrderResult:
        """
        Close entire position for a coin with a market order.

        Args:
            coin: Trading pair symbol

        Returns:
            OrderResult with close details
        """
        try:
            result = self._exchange.market_close(coin)

            if result.get("status") != "ok":
                return OrderResult(
                    success=False,
                    error=str(result),
                    raw_response=result,
                )

            return OrderResult(success=True, raw_response=result)

        except Exception as e:
            return OrderResult(success=False, error=str(e))

    def get_open_orders(self) -> list[dict]:
        """Get all open orders for this account."""
        return self._info.open_orders(self.address)
