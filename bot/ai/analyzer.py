"""Market analyzer using local AI for trading signals."""

import logging
from typing import Optional

from bot.ai.ollama_client import OllamaClient
from bot.ai.models import AnalysisResult, AIMetrics, Sentiment, Signal
from bot.ai.prompts import format_market_analysis, format_quick_sentiment

logger = logging.getLogger(__name__)


class MarketAnalyzer:
    """AI-powered market analyzer for trading signals."""

    def __init__(
        self,
        client: Optional[OllamaClient] = None,
        enabled: bool = True,
    ):
        self.client = client or OllamaClient()
        self.enabled = enabled
        self._last_analysis: Optional[AnalysisResult] = None

    async def is_available(self) -> bool:
        """Check if AI analysis is available."""
        if not self.enabled:
            return False
        return await self.client.is_available()

    async def analyze_market(
        self,
        coin: str,
        prices: dict[str, dict],
        momentum: dict[str, float],
        orderbook: dict[str, dict],
        recent_trades: list[dict],
    ) -> AnalysisResult:
        """
        Perform full market analysis for a specific coin.

        Args:
            coin: The coin to analyze (e.g., "BTC")
            prices: Dict of coin -> {price, change_1m}
            momentum: Dict of coin -> momentum percentage
            orderbook: Dict of coin -> {bid_ratio}
            recent_trades: List of recent trade dicts with 'side' key

        Returns:
            AnalysisResult with sentiment, confidence, signal, and reason
        """
        if not self.enabled:
            return AnalysisResult.error_result(coin, "AI analysis disabled")

        try:
            prompt = format_market_analysis(prices, momentum, orderbook, recent_trades)
            response_text, tokens, response_time_ms = await self.client.analyze(prompt)

            result = AnalysisResult.from_text(response_text, coin, response_time_ms)
            self._last_analysis = result

            logger.info(
                f"AI Analysis: {coin} - {result.sentiment.value} "
                f"(confidence: {result.confidence}/10, signal: {result.signal.value})"
            )

            return result

        except Exception as e:
            logger.error(f"Market analysis failed: {e}")
            return AnalysisResult.error_result(coin, str(e))

    async def quick_sentiment(
        self,
        prices: dict[str, dict],
        bid_ratio: float,
        buys: int,
        sells: int,
    ) -> Sentiment:
        """
        Get quick sentiment check (faster, less detailed).

        Returns:
            Sentiment enum (BULLISH, BEARISH, or NEUTRAL)
        """
        if not self.enabled:
            return Sentiment.NEUTRAL

        try:
            prompt = format_quick_sentiment(prices, bid_ratio, buys, sells)
            response_text, _, _ = await self.client.analyze(
                prompt,
                temperature=0.1,
                max_tokens=10,
            )

            # Parse single-word response
            word = response_text.strip().upper()
            if "BULLISH" in word:
                return Sentiment.BULLISH
            elif "BEARISH" in word:
                return Sentiment.BEARISH
            else:
                return Sentiment.NEUTRAL

        except Exception as e:
            logger.error(f"Quick sentiment failed: {e}")
            return Sentiment.NEUTRAL

    async def should_enter(
        self,
        coin: str,
        direction: str,
        price: float,
        momentum: float,
        bid_ratio: float,
    ) -> tuple[bool, int, str]:
        """
        Evaluate if we should enter a trade.

        Returns:
            Tuple of (should_enter, confidence, reason)
        """
        if not self.enabled:
            return True, 5, "AI disabled - using rule-based only"

        # Use full analysis for entry decisions
        result = await self.analyze_market(
            coin=coin,
            prices={coin: {"price": price, "change_1m": momentum}},
            momentum={coin: momentum},
            orderbook={coin: {"bid_ratio": bid_ratio}},
            recent_trades=[],
        )

        # Entry logic based on AI signal
        if direction == "LONG":
            should_enter = result.signal == Signal.LONG and result.confidence >= 6
        else:
            should_enter = result.signal == Signal.SHORT and result.confidence >= 6

        return should_enter, result.confidence, result.reason

    def get_last_analysis(self) -> Optional[AnalysisResult]:
        """Get the most recent analysis result."""
        return self._last_analysis

    def get_metrics(self) -> AIMetrics:
        """Get AI usage metrics."""
        return self.client.get_metrics()

    async def close(self) -> None:
        """Clean up resources."""
        await self.client.close()
