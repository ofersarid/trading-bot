"""
Scalper Interpreter Service.

Interprets market data through the Scalper strategy, returning
AI-derived momentum, pressure, and prediction values.

Key principles:
- "Tape is truth, book is noise"
- "One whale trade > 50 retail trades"
- "Never chase extended moves"
"""

import logging
from dataclasses import dataclass
from datetime import datetime

from bot.ai.ollama_client import OllamaClient
from bot.core.data_buffer import ScalperDataWindow
from bot.simulation.paper_trader import Position

logger = logging.getLogger(__name__)


# =============================================================================
# Scalper Prompt Templates
# =============================================================================

SCALPER_PROMPT = """You are a professional crypto scalper trading 1-minute charts.

## WHO YOU ARE

You're a human trader, not an algorithm. You watch charts, read the tape, and make
decisions every 10-30 seconds. You hold positions for 30 seconds to a few minutes.
You trade BTC, ETH, and SOL perpetual futures on Hyperliquid.

## YOUR MENTAL MODEL

### How You Read Momentum
You look at the last minute of price action:
- Is price pushing steadily in one direction, or chopping?
- Did the move just start (fresh) or has it been running (extended)?
- Are buyers/sellers following through, or is it losing steam?

Score momentum 0-100:
- 0-30: Choppy, no clear direction, stay out
- 31-50: Something forming, watch closely
- 51-70: Clear move with follow-through, look for entry
- 71-100: Strong one-sided action, be careful not to chase

### How You Read Pressure
TAPE IS TRUTH, BOOK IS NOISE.

You care about:
- WHO is hitting orders - buyers or sellers? And how big are they?
- Volume matters more than count - one whale trade > 50 small trades
- Is the aggression increasing or fading?

Score pressure 0-100 (50 = neutral):
- 0-30: Sellers dominating the tape
- 31-49: Slight selling bias
- 50: Balanced, no edge
- 51-70: Buyers stepping up
- 71-100: Aggressive buying, possible squeeze

### How You Read Freshness
- FRESH: Move just started in the last 10-15 seconds, early entry opportunity
- DEVELOPING: Move building for 15-30 seconds, still good entry
- EXTENDED: Move running for 30-60 seconds, risky to chase
- EXHAUSTED: Move been going 60+ seconds or >0.5%, expect pullback

## YOUR RULES (NEVER BREAK THESE)
1. Never chase extended moves - wait for pullback or fresh setup
2. Tape beats book - executed trades are real, orders can be pulled
3. Take the small win - 0.05-0.15% is fine, don't get greedy
4. Cut losers FAST - if momentum turns against you, EXIT immediately
5. When in doubt, stay out - there's always another setup"""


SCALPER_ANALYSIS_TEMPLATE = """
{scalper_prompt}

=== WHAT YOU SEE ON YOUR SCREEN ===

COIN: {coin}

PRICE ACTION (last 60 seconds):
  1 minute ago: ${price_1min_ago}
  Now: ${current_price}
  Change: {price_change_1min}

  Movement: {price_description}

TAPE (last {num_trades} trades, ~{tape_timespan}):
  Buys: {buy_count} trades, {buy_volume:.4f} total size
  Sells: {sell_count} trades, {sell_volume:.4f} total size

  Notable: {tape_notable}

ORDERBOOK:
  Bid side: {bid_depth:.4f} size across top 5 levels
  Ask side: {ask_depth:.4f} size across top 5 levels
  Imbalance: {book_imbalance}

{position_context}

=== YOUR READ ===

Look at this like you're sitting at your trading desk. What do you see?

Respond in this EXACT format:
MOMENTUM: [0-100]
PRESSURE: [0-100]
PREDICTION: [0-100]
FRESHNESS: [FRESH/DEVELOPING/EXTENDED/EXHAUSTED]
ACTION: [NONE/LONG/SHORT/EXIT]
CONFIDENCE: [1-10]
REASON: [What you see on the tape, one sentence]

Guidelines:
- MOMENTUM: Is this move strong and building, or weak and fading?
- PRESSURE: Who's winning - buyers or sellers? (50 = even)
- PREDICTION: Will this continue or reverse? (>50 = continue)
- ACTION: NONE if no clear setup, LONG/SHORT if setup is there, EXIT if you're in and should get out"""


# =============================================================================
# Prompt Formatting Helpers
# =============================================================================


def _format_price_description(prices: list[dict]) -> str:
    """Describe price action like a human trader would."""
    if not prices or len(prices) < 2:
        return "Not enough data yet"

    start = prices[-1]["price"]  # Oldest
    mid = prices[len(prices) // 2]["price"]
    end = prices[0]["price"]  # Current (newest)

    if start <= 0:
        return "Waiting for price data"

    first_half_move = (mid - start) / start * 100
    second_half_move = (end - mid) / mid * 100 if mid > 0 else 0
    total_move = (end - start) / start * 100

    if abs(total_move) < 0.02:
        return "Chopping sideways, no clear direction"

    if first_half_move > 0 and second_half_move > first_half_move * 0.5:
        return "Moving up and ACCELERATING"

    if first_half_move > 0.02 and second_half_move < first_half_move * 0.3:
        return "Was moving up, now SLOWING DOWN"

    if first_half_move < 0 and second_half_move < first_half_move * 0.5:
        return "Moving down and ACCELERATING"

    if first_half_move < -0.02 and second_half_move > first_half_move * 0.3:
        return "Was moving down, now SLOWING DOWN"

    if second_half_move > 0.05:
        return "Sharp move UP in last 30 seconds"
    if second_half_move < -0.05:
        return "Sharp move DOWN in last 30 seconds"

    if total_move > 0:
        return "Grinding slowly higher"
    return "Grinding slowly lower"


def _format_tape_notable(trades: list[dict], avg_size: float) -> str:
    """Highlight notable tape activity."""
    if not trades:
        return "No recent trades"

    if avg_size <= 0:
        return "Normal flow"

    large_trades = [t for t in trades if t.get("size", 0) > avg_size * 2]

    if not large_trades:
        return "Normal flow, no standout trades"

    recent_large = large_trades[:5]
    buy_large = sum(1 for t in recent_large if t.get("side") == "buy")
    sell_large = len(recent_large) - buy_large
    total_large = len(large_trades)

    if buy_large > sell_large + 1:
        return f"{total_large} large trades, mostly BUYS - someone accumulating"
    if sell_large > buy_large + 1:
        return f"{total_large} large trades, mostly SELLS - someone distributing"
    return f"{total_large} large trades, mixed sides - big players active both ways"


def _format_book_imbalance(bid_depth: float, ask_depth: float) -> str:
    """Describe orderbook imbalance."""
    total = bid_depth + ask_depth
    if total <= 0:
        return "No orderbook data"

    bid_pct = bid_depth / total * 100

    if bid_pct > 65:
        return f"{bid_pct:.0f}% bids - HEAVY on bid side"
    if bid_pct > 55:
        return f"{bid_pct:.0f}% bids - Slightly bid-heavy"
    if bid_pct < 35:
        return f"{bid_pct:.0f}% bids - HEAVY on ask side"
    if bid_pct < 45:
        return f"{bid_pct:.0f}% bids - Slightly ask-heavy"
    return f"{bid_pct:.0f}% bids - Balanced"


def _format_position_context(position: Position | None, current_price: float) -> str:
    """Format position context for the prompt."""
    if position is None:
        return "=== YOUR POSITION ===\nNo open position."

    direction = "LONG" if position.side.value == "long" else "SHORT"
    entry = position.entry_price
    pnl_pct = position.unrealized_pnl_percent(current_price)

    hold_seconds = (datetime.now() - position.entry_time).total_seconds()
    hold_str = f"{hold_seconds:.0f}s" if hold_seconds < 60 else f"{hold_seconds / 60:.1f}m"

    pnl_direction = "profit" if pnl_pct >= 0 else "loss"

    return f"""=== YOUR POSITION ===
Direction: {direction}
Entry: ${entry:,.2f}
Current: ${current_price:,.2f}
P&L: {pnl_pct:+.2f}% ({pnl_direction})
Hold time: {hold_str}

You are IN a position - focus on whether to HOLD or EXIT."""


def format_scalper_prompt(
    data_window: ScalperDataWindow,
    position: Position | None = None,
) -> str:
    """
    Format the complete scalper analysis prompt with market data.

    Args:
        data_window: ScalperDataWindow with buffered market data
        position: Current position or None

    Returns:
        Complete formatted prompt for AI interpretation
    """
    summary = data_window.get_summary()

    current_price = summary.get("current_price")
    price_1min_ago = summary.get("price_1min_ago")
    price_change = summary.get("price_change_1min")

    current_price_str = f"{current_price:,.2f}" if current_price else "N/A"
    price_1min_str = f"{price_1min_ago:,.2f}" if price_1min_ago else "N/A"
    price_change_str = f"{price_change:+.2f}%" if price_change is not None else "N/A"

    price_list = list(data_window.price_history)
    price_description = _format_price_description(price_list)

    trades_list = list(data_window.recent_trades)
    avg_size = summary.get("avg_trade_size", 0)
    tape_notable = _format_tape_notable(trades_list, avg_size)

    book_imbalance = _format_book_imbalance(
        summary.get("bid_depth", 0),
        summary.get("ask_depth", 0),
    )

    position_context = _format_position_context(position, current_price if current_price else 0)

    return SCALPER_ANALYSIS_TEMPLATE.format(
        scalper_prompt=SCALPER_PROMPT,
        coin=data_window.coin,
        current_price=current_price_str,
        price_1min_ago=price_1min_str,
        price_change_1min=price_change_str,
        price_description=price_description,
        num_trades=summary.get("num_trades", 0),
        tape_timespan=data_window.get_tape_timespan(),
        buy_count=summary.get("buy_count", 0),
        buy_volume=summary.get("buy_volume", 0),
        sell_count=summary.get("sell_count", 0),
        sell_volume=summary.get("sell_volume", 0),
        tape_notable=tape_notable,
        bid_depth=summary.get("bid_depth", 0),
        ask_depth=summary.get("ask_depth", 0),
        book_imbalance=book_imbalance,
        position_context=position_context,
    )


# =============================================================================
# Scalper Interpretation Models
# =============================================================================


@dataclass
class ScalperInterpretation:
    """
    AI Scalper's interpretation of market data.

    All numeric values are AI-interpreted, not calculated.
    """

    coin: str

    # Core metrics (AI-derived, 0-100 scale)
    momentum: int  # 0-100: strength and quality of the move
    pressure: int  # 0-100: buying vs selling pressure (50 = neutral)
    prediction: int  # 0-100: continuation probability

    # Trading guidance
    freshness: str  # FRESH/DEVELOPING/EXTENDED/EXHAUSTED
    action: str  # NONE/LONG/SHORT/EXIT
    confidence: int  # 1-10
    reason: str  # Scalper's tape read

    # Metadata
    response_time_ms: float
    timestamp: datetime

    @property
    def is_bullish(self) -> bool:
        """Whether the interpretation suggests bullish conditions."""
        return self.pressure > 55 and self.momentum > 50

    @property
    def is_bearish(self) -> bool:
        """Whether the interpretation suggests bearish conditions."""
        return self.pressure < 45 and self.momentum > 50

    @property
    def is_actionable(self) -> bool:
        """Whether the AI suggests taking action."""
        return self.action in ("LONG", "SHORT", "EXIT")

    @property
    def age_seconds(self) -> float:
        """Seconds since this interpretation was created."""
        return (datetime.now() - self.timestamp).total_seconds()

    @property
    def is_stale(self) -> bool:
        """Whether this interpretation is considered stale (>20s old)."""
        return self.age_seconds > 20.0

    @classmethod
    def empty(cls, coin: str) -> "ScalperInterpretation":
        """Create an empty/default interpretation."""
        return cls(
            coin=coin,
            momentum=50,
            pressure=50,
            prediction=50,
            freshness="DEVELOPING",
            action="NONE",
            confidence=0,
            reason="No interpretation yet",
            response_time_ms=0,
            timestamp=datetime.now(),
        )

    @classmethod
    def error(cls, coin: str, error_msg: str) -> "ScalperInterpretation":
        """Create an error interpretation."""
        return cls(
            coin=coin,
            momentum=50,
            pressure=50,
            prediction=50,
            freshness="DEVELOPING",
            action="NONE",
            confidence=0,
            reason=f"Error: {error_msg}",
            response_time_ms=0,
            timestamp=datetime.now(),
        )


def _parse_int(value: str, min_val: int, max_val: int, default: int) -> int:
    """Parse an integer from string, clamping to range."""
    try:
        # Handle values like "72/100" or "72"
        if "/" in value:
            value = value.split("/")[0]
        num = int(value.strip())
        return max(min_val, min(max_val, num))
    except (ValueError, AttributeError):
        return default


def parse_scalper_response(
    response: str,
    coin: str,
    response_time_ms: float,
) -> ScalperInterpretation:
    """
    Parse the AI's structured response into a ScalperInterpretation.

    Args:
        response: Raw response text from AI
        coin: Coin symbol
        response_time_ms: Response time in milliseconds

    Returns:
        Parsed ScalperInterpretation
    """
    lines = response.strip().split("\n")
    data: dict[str, str] = {}

    for line in lines:
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip().upper()] = value.strip()

    # Parse values with defaults
    momentum = _parse_int(data.get("MOMENTUM", "50"), 0, 100, 50)
    pressure = _parse_int(data.get("PRESSURE", "50"), 0, 100, 50)
    prediction = _parse_int(data.get("PREDICTION", "50"), 0, 100, 50)
    confidence = _parse_int(data.get("CONFIDENCE", "5"), 1, 10, 5)

    # Parse freshness
    freshness = data.get("FRESHNESS", "DEVELOPING").upper()
    if freshness not in ("FRESH", "DEVELOPING", "EXTENDED", "EXHAUSTED"):
        freshness = "DEVELOPING"

    # Parse action
    action = data.get("ACTION", "NONE").upper()
    if action not in ("NONE", "LONG", "SHORT", "EXIT"):
        action = "NONE"

    # Parse reason
    reason = data.get("REASON", "No reason provided")

    return ScalperInterpretation(
        coin=coin,
        momentum=momentum,
        pressure=pressure,
        prediction=prediction,
        freshness=freshness,
        action=action,
        confidence=confidence,
        reason=reason,
        response_time_ms=response_time_ms,
        timestamp=datetime.now(),
    )


class ScalperInterpreter:
    """
    AI service that interprets market data through the Scalper strategy.

    Calls the local AI (Ollama) with formatted prompts and parses
    the structured response into ScalperInterpretation objects.
    """

    def __init__(self, client: OllamaClient | None = None):
        """
        Initialize the interpreter.

        Args:
            client: OllamaClient instance (creates default if None)
        """
        self.client = client or OllamaClient()
        self._interpretations: dict[str, ScalperInterpretation] = {}

    async def interpret(
        self,
        data_window: ScalperDataWindow,
        position: Position | None = None,
    ) -> ScalperInterpretation:
        """
        Get the Scalper's interpretation of current market state.

        Args:
            data_window: ScalperDataWindow with buffered market data
            position: Current position or None

        Returns:
            ScalperInterpretation with AI-derived metrics
        """
        coin = data_window.coin

        try:
            # Format the prompt
            prompt = format_scalper_prompt(data_window, position)

            # Call AI
            response_text, _tokens, response_time_ms = await self.client.analyze(
                prompt,
                temperature=0.3,
                max_tokens=200,
            )

            # Parse response
            interpretation = parse_scalper_response(
                response_text,
                coin,
                response_time_ms,
            )

            # Cache it
            self._interpretations[coin] = interpretation

            logger.info(
                f"Scalper interpretation for {coin}: "
                f"Mom={interpretation.momentum} Press={interpretation.pressure} "
                f"Pred={interpretation.prediction} [{interpretation.freshness}] "
                f"Action={interpretation.action} Conf={interpretation.confidence}/10 "
                f"({response_time_ms:.0f}ms)"
            )

            return interpretation

        except Exception as e:
            logger.error(f"Scalper interpretation failed for {coin}: {e}")
            return ScalperInterpretation.error(coin, str(e))

    def get_last_interpretation(self, coin: str) -> ScalperInterpretation | None:
        """
        Get the most recent interpretation for a coin.

        Args:
            coin: Coin symbol

        Returns:
            Last ScalperInterpretation or None
        """
        return self._interpretations.get(coin)

    def get_all_interpretations(self) -> dict[str, ScalperInterpretation]:
        """Get all cached interpretations."""
        return self._interpretations.copy()

    def clear_interpretations(self) -> None:
        """Clear all cached interpretations."""
        self._interpretations.clear()

    async def is_available(self) -> bool:
        """Check if the AI backend is available."""
        return await self.client.is_available()
