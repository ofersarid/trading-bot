"""
Scalper Persona for AI Trading.

Defines the Scalper's identity, mental model, and prompt templates
for interpreting market data through a human scalper's perspective.

Key principles from docs/Team/Scalper/:
- "Tape is truth, book is noise"
- "One whale trade > 50 retail trades"
- "Never chase extended moves"
- Hybrid velocity + acceleration for momentum quality
"""

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot.core.data_buffer import ScalperDataWindow
    from bot.simulation.paper_trader import Position


SCALPER_PERSONA_PROMPT = """You are a professional crypto scalper trading 1-minute charts.

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


SCALPER_ANALYSIS_PROMPT = """
{scalper_persona}

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


def format_price_description(prices: list[dict]) -> str:
    """
    Describe price action like a human trader would.

    Args:
        prices: List of price dicts with 'price' key, newest first

    Returns:
        Human-readable description of price movement
    """
    if not prices or len(prices) < 2:
        return "Not enough data yet"

    # Look at trajectory: start -> mid -> end
    start = prices[-1]["price"]  # Oldest
    mid = prices[len(prices) // 2]["price"]
    end = prices[0]["price"]  # Current (newest)

    if start <= 0:
        return "Waiting for price data"

    first_half_move = (mid - start) / start * 100
    second_half_move = (end - mid) / mid * 100 if mid > 0 else 0
    total_move = (end - start) / start * 100

    # Very small moves = chopping
    if abs(total_move) < 0.02:
        return "Chopping sideways, no clear direction"

    # Accelerating up
    if first_half_move > 0 and second_half_move > first_half_move * 0.5:
        return "Moving up and ACCELERATING"

    # Decelerating up (was moving up, slowing)
    if first_half_move > 0.02 and second_half_move < first_half_move * 0.3:
        return "Was moving up, now SLOWING DOWN"

    # Accelerating down
    if first_half_move < 0 and second_half_move < first_half_move * 0.5:
        return "Moving down and ACCELERATING"

    # Decelerating down
    if first_half_move < -0.02 and second_half_move > first_half_move * 0.3:
        return "Was moving down, now SLOWING DOWN"

    # Sharp recent move
    if second_half_move > 0.05:
        return "Sharp move UP in last 30 seconds"
    if second_half_move < -0.05:
        return "Sharp move DOWN in last 30 seconds"

    # Steady grind
    if total_move > 0:
        return "Grinding slowly higher"
    else:
        return "Grinding slowly lower"


def format_tape_notable(trades: list[dict], avg_size: float) -> str:
    """
    Highlight notable tape activity like a trader would describe it.

    Args:
        trades: List of trade dicts with 'side' and 'size' keys, newest first
        avg_size: Average trade size for comparison

    Returns:
        Human-readable description of notable tape activity
    """
    if not trades:
        return "No recent trades"

    if avg_size <= 0:
        return "Normal flow"

    # Find large trades (>2x average)
    large_trades = [t for t in trades if t.get("size", 0) > avg_size * 2]

    if not large_trades:
        return "Normal flow, no standout trades"

    # Analyze the large trades
    recent_large = large_trades[:5]  # Focus on most recent large trades
    buy_large = sum(1 for t in recent_large if t.get("side") == "buy")
    sell_large = len(recent_large) - buy_large

    total_large = len(large_trades)

    if buy_large > sell_large + 1:
        return f"{total_large} large trades, mostly BUYS - someone accumulating"
    elif sell_large > buy_large + 1:
        return f"{total_large} large trades, mostly SELLS - someone distributing"
    else:
        return f"{total_large} large trades, mixed sides - big players active both ways"


def format_book_imbalance(bid_depth: float, ask_depth: float) -> str:
    """
    Describe orderbook imbalance.

    Args:
        bid_depth: Total bid volume in top levels
        ask_depth: Total ask volume in top levels

    Returns:
        Human-readable description of book imbalance
    """
    total = bid_depth + ask_depth
    if total <= 0:
        return "No orderbook data"

    bid_pct = bid_depth / total * 100

    if bid_pct > 65:
        return f"{bid_pct:.0f}% bids - HEAVY on bid side"
    elif bid_pct > 55:
        return f"{bid_pct:.0f}% bids - Slightly bid-heavy"
    elif bid_pct < 35:
        return f"{bid_pct:.0f}% bids - HEAVY on ask side"
    elif bid_pct < 45:
        return f"{bid_pct:.0f}% bids - Slightly ask-heavy"
    else:
        return f"{bid_pct:.0f}% bids - Balanced"


def format_position_context(position: "Position | None", current_price: float) -> str:
    """
    Format position context for the prompt.

    Args:
        position: Current position or None
        current_price: Current market price

    Returns:
        Position context string for the prompt
    """
    if position is None:
        return "=== YOUR POSITION ===\nNo open position."

    direction = "LONG" if position.side.value == "long" else "SHORT"
    entry = position.entry_price
    pnl_pct = position.unrealized_pnl_percent(current_price)

    # Calculate hold time
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
    data_window: "ScalperDataWindow",
    position: "Position | None" = None,
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

    # Format price values
    current_price = summary.get("current_price")
    price_1min_ago = summary.get("price_1min_ago")
    price_change = summary.get("price_change_1min")

    current_price_str = f"{current_price:,.2f}" if current_price else "N/A"
    price_1min_str = f"{price_1min_ago:,.2f}" if price_1min_ago else "N/A"
    price_change_str = f"{price_change:+.2f}%" if price_change is not None else "N/A"

    # Get price description
    price_list = list(data_window.price_history)
    price_description = format_price_description(price_list)

    # Get tape description
    trades_list = list(data_window.recent_trades)
    avg_size = summary.get("avg_trade_size", 0)
    tape_notable = format_tape_notable(trades_list, avg_size)

    # Get book imbalance
    book_imbalance = format_book_imbalance(
        summary.get("bid_depth", 0),
        summary.get("ask_depth", 0),
    )

    # Position context
    position_context = format_position_context(position, current_price if current_price else 0)

    return SCALPER_ANALYSIS_PROMPT.format(
        scalper_persona=SCALPER_PERSONA_PROMPT,
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
