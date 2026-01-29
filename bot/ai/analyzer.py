"""
Market analyzer using local AI for trading signals.

DEPRECATED: This module uses different logic than the backtest system.
For consistent backtest-to-live results, use bot.core.TradingCore instead.

The MarketAnalyzer class uses prompts.py which has different AI prompts
than SignalBrain. This means backtest results won't match live performance.

Use bot.live.LiveEngine for live trading - it uses the same TradingCore
as BacktestEngine.
"""

import logging
from dataclasses import dataclass

from bot.ai.models import AIMetrics, AnalysisResult, Sentiment
from bot.ai.ollama_client import OllamaClient
from bot.ai.prompts import (
    format_ai_trading_prompt,
    format_entry_analysis,
    format_exit_analysis,
    format_market_analysis,
    format_quick_sentiment,
)
from bot.strategies import TradingStrategy


@dataclass
class AIDecision:
    """A complete trading decision from the AI."""

    action: str  # NONE, LONG, SHORT, EXIT_<COIN>
    coin: str  # BTC, ETH, SOL, or N/A
    size_pct: float  # Position size as % of balance
    confidence: int  # 1-10
    reason: str
    response_time_ms: float

    @property
    def is_entry(self) -> bool:
        return self.action in ("LONG", "SHORT")

    @property
    def is_exit(self) -> bool:
        return self.action.startswith("EXIT_")

    @property
    def exit_coin(self) -> str | None:
        if self.is_exit:
            return self.action.replace("EXIT_", "")
        return None

    @property
    def is_none(self) -> bool:
        return self.action == "NONE"


logger = logging.getLogger(__name__)


class MarketAnalyzer:
    """AI-powered market analyzer for trading signals."""

    def __init__(
        self,
        client: OllamaClient | None = None,
        enabled: bool = True,
    ):
        self.client = client or OllamaClient()
        self.enabled = enabled
        self._last_analysis: AnalysisResult | None = None

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
        pressure_score: int = 50,
        pressure_label: str = "Neutral",
        momentum_timeframe: int = 60,
    ) -> AnalysisResult:
        """
        Perform full market analysis for a specific coin.

        Args:
            coin: The coin to analyze (e.g., "BTC")
            prices: Dict of coin -> {price, change_1m}
            momentum: Dict of coin -> momentum percentage
            orderbook: Dict of coin -> {bid_ratio}
            recent_trades: List of recent trade dicts with 'side' key
            pressure_score: Market pressure score 0-100
            pressure_label: Human-readable pressure label
            momentum_timeframe: Timeframe for momentum calculation in seconds

        Returns:
            AnalysisResult with sentiment, confidence, signal, and reason
        """
        if not self.enabled:
            return AnalysisResult.error_result(coin, "AI analysis disabled")

        try:
            prompt = format_market_analysis(
                prices,
                momentum,
                orderbook,
                recent_trades,
                pressure_score=pressure_score,
                pressure_label=pressure_label,
                momentum_timeframe=momentum_timeframe,
            )
            response_text, tokens, response_time_ms = await self.client.analyze(prompt)

            result = AnalysisResult.from_text(response_text, coin, response_time_ms)

            # Populate momentum data from input if AI didn't parse it correctly
            if not result.momentum_by_coin and momentum:
                result.momentum_by_coin = momentum

            self._last_analysis = result

            logger.info(
                f"AI Analysis: {coin} - {result.sentiment.value} "
                f"(confidence: {result.confidence}/10, signal: {result.signal.value}, "
                f"pressure: {result.pressure_score}, freshness: {result.freshness.value})"
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
        momentum_timeframe: int,
        bid_ratio: float,
        pressure_score: int,
        pressure_label: str,
        freshness: str,
        take_profit_pct: float,
        stop_loss_pct: float,
    ) -> tuple[bool, int, str, str]:
        """
        Evaluate if we should enter a trade.

        Returns:
            Tuple of (should_enter, confidence, reason, size)
        """
        if not self.enabled:
            return True, 5, "AI disabled - using rule-based only", "MEDIUM"

        try:
            prompt = format_entry_analysis(
                coin=coin,
                direction=direction,
                price=price,
                momentum=momentum,
                momentum_timeframe=momentum_timeframe,
                bid_ratio=bid_ratio,
                pressure_score=pressure_score,
                pressure_label=pressure_label,
                freshness=freshness,
                take_profit_pct=take_profit_pct,
                stop_loss_pct=stop_loss_pct,
            )

            response_text, tokens, response_time_ms = await self.client.analyze(
                prompt,
                temperature=0.2,
                max_tokens=100,
            )

            # Parse response
            lines = response_text.strip().split("\n")
            data = {}
            for line in lines:
                if ":" in line:
                    key, value = line.split(":", 1)
                    data[key.strip().upper()] = value.strip()

            decision = data.get("DECISION", "SKIP").upper()
            should_enter = "ENTER" in decision

            try:
                confidence = int(data.get("CONFIDENCE", "5"))
                confidence = max(1, min(10, confidence))
            except ValueError:
                confidence = 5

            size = data.get("SIZE", "MEDIUM").upper()
            if size not in ["SMALL", "MEDIUM", "LARGE"]:
                size = "MEDIUM"

            reason = data.get("REASON", "No reason provided")

            logger.info(
                f"AI Entry Decision: {coin} {direction} - {decision} "
                f"(confidence: {confidence}/10, size: {size}) - {reason}"
            )

            return should_enter, confidence, reason, size

        except Exception as e:
            logger.error(f"Entry analysis failed: {e}")
            return False, 0, f"Error: {e}", "MEDIUM"

    async def should_exit(
        self,
        coin: str,
        direction: str,
        entry_price: float,
        current_price: float,
        pnl_percent: float,
        hold_time: int,
        momentum: float,
        momentum_timeframe: int,
        pressure_score: int,
        pressure_label: str,
        take_profit_pct: float,
        stop_loss_pct: float,
    ) -> tuple[bool, int, str]:
        """
        Evaluate if we should exit a position.

        Returns:
            Tuple of (should_exit, confidence, reason)
        """
        if not self.enabled:
            return False, 5, "AI disabled - using rule-based only"

        try:
            prompt = format_exit_analysis(
                coin=coin,
                direction=direction,
                entry_price=entry_price,
                current_price=current_price,
                pnl_percent=pnl_percent,
                hold_time=hold_time,
                momentum=momentum,
                momentum_timeframe=momentum_timeframe,
                pressure_score=pressure_score,
                pressure_label=pressure_label,
                take_profit_pct=take_profit_pct,
                stop_loss_pct=stop_loss_pct,
            )

            response_text, tokens, response_time_ms = await self.client.analyze(
                prompt,
                temperature=0.2,
                max_tokens=80,
            )

            # Parse response
            lines = response_text.strip().split("\n")
            data = {}
            for line in lines:
                if ":" in line:
                    key, value = line.split(":", 1)
                    data[key.strip().upper()] = value.strip()

            action = data.get("ACTION", "HOLD").upper()
            should_exit = "EXIT" in action

            try:
                confidence = int(data.get("CONFIDENCE", "5"))
                confidence = max(1, min(10, confidence))
            except ValueError:
                confidence = 5

            reason = data.get("REASON", "No reason provided")

            logger.info(
                f"AI Exit Decision: {coin} {direction} - {action} "
                f"(confidence: {confidence}/10) - {reason}"
            )

            return should_exit, confidence, reason

        except Exception as e:
            logger.error(f"Exit analysis failed: {e}")
            return False, 0, f"Error: {e}"

    async def make_decision(
        self,
        strategy: TradingStrategy,
        prices: dict[str, float],
        momentum: dict[str, float],
        acceleration: dict[str, float],
        orderbook: dict[str, dict],
        pressure_score: int,
        pressure_label: str,
        recent_trades: list[dict],
        positions: dict,
        balance: float,
        equity: float,
        momentum_timeframe: int,
    ) -> AIDecision:
        """
        Make a complete trading decision - AI has full control.

        Returns:
            AIDecision with action (NONE/LONG/SHORT/EXIT_<COIN>), coin, size, confidence, reason
        """
        if not self.enabled:
            return AIDecision(
                action="NONE",
                coin="N/A",
                size_pct=0,
                confidence=0,
                reason="AI disabled",
                response_time_ms=0,
            )

        try:
            prompt = format_ai_trading_prompt(
                strategy=strategy,
                prices=prices,
                momentum=momentum,
                acceleration=acceleration,
                orderbook=orderbook,
                pressure_score=pressure_score,
                pressure_label=pressure_label,
                recent_trades=recent_trades,
                positions=positions,
                balance=balance,
                equity=equity,
                momentum_timeframe=momentum_timeframe,
            )

            response_text, tokens, response_time_ms = await self.client.analyze(
                prompt,
                temperature=0.3,
                max_tokens=150,
            )

            # Parse response
            lines = response_text.strip().split("\n")
            data = {}
            for line in lines:
                if ":" in line:
                    key, value = line.split(":", 1)
                    data[key.strip().upper()] = value.strip()

            action = data.get("ACTION", "NONE").upper()
            coin = data.get("COIN", "N/A").upper()

            # Parse size
            try:
                size_str = data.get("SIZE_PCT", "10").replace("%", "")
                size_pct = float(size_str) / 100  # Convert to decimal
                size_pct = max(0.05, min(0.20, size_pct))  # Clamp 5-20%
            except ValueError:
                size_pct = 0.10

            # Parse confidence
            try:
                confidence = int(data.get("CONFIDENCE", "5"))
                confidence = max(1, min(10, confidence))
            except ValueError:
                confidence = 5

            reason = data.get("REASON", "No reason provided")

            decision = AIDecision(
                action=action,
                coin=coin if coin != "N/A" else "",
                size_pct=size_pct,
                confidence=confidence,
                reason=reason,
                response_time_ms=response_time_ms,
            )

            logger.info(
                f"AI Decision: {action} {coin} (size: {size_pct * 100:.0f}%, "
                f"confidence: {confidence}/10) - {reason}"
            )

            return decision

        except Exception as e:
            logger.error(f"AI decision failed: {e}")
            return AIDecision(
                action="NONE",
                coin="N/A",
                size_pct=0,
                confidence=0,
                reason=f"Error: {e}",
                response_time_ms=0,
            )

    def get_last_analysis(self) -> AnalysisResult | None:
        """Get the most recent analysis result."""
        return self._last_analysis

    def get_metrics(self) -> AIMetrics:
        """Get AI usage metrics."""
        return self.client.get_metrics()

    async def close(self) -> None:
        """Clean up resources."""
        await self.client.close()
