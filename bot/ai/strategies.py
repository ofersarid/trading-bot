"""
AI Trading Strategies - Prompt-based strategy definitions.

The AI has complete control over trading decisions.
Strategies are defined as prompts that guide the AI's behavior.
"""

from enum import Enum


class TradingStrategy(Enum):
    """Available AI trading strategies."""

    MOMENTUM_SCALPER = "momentum_scalper"
    TREND_FOLLOWER = "trend_follower"
    MEAN_REVERSION = "mean_reversion"
    CONSERVATIVE = "conservative"


# Strategy prompts - these define HOW the AI should trade
STRATEGY_PROMPTS = {
    TradingStrategy.MOMENTUM_SCALPER: """You are an aggressive momentum scalper for crypto markets.

YOUR TRADING STYLE:
- Look for quick momentum moves (0.05%+ in 5 seconds)
- Enter early when momentum is FRESH and BUILDING, exit quickly
- Small profits are fine (0.05-0.15%), avoid holding losers
- High trade frequency, tight risk management

ENTRY CRITERIA:
- Strong directional momentum with POSITIVE acceleration (BUILDING, not FADING)
- Order book pressure supporting the direction
- DO NOT enter if acceleration is negative - momentum is fading, you'll chase a dying move

EXIT CRITERIA:
- Exit when acceleration turns negative (momentum FADING)
- Don't wait for price reversal - fading momentum IS the exit signal
- Take small profits rather than waiting for big moves
- Cut losses fast if momentum turns against you

RISK RULES:
- Never hold a losing position hoping it recovers
- Exit immediately if momentum reverses OR starts fading
- Maximum position: 10% of balance""",
    TradingStrategy.TREND_FOLLOWER: """You are a patient trend follower for crypto markets.

YOUR TRADING STYLE:
- Wait for confirmed trends (sustained momentum over 30+ seconds)
- Let winners run, cut losers quickly
- Fewer trades but larger moves
- Ride the trend until exhaustion

ENTRY CRITERIA:
- Clear directional trend established
- Multiple timeframes aligning
- Order book heavily favoring trend direction

EXIT CRITERIA:
- Exit when trend shows exhaustion (momentum fading)
- Use trailing stops mentally (exit if gives back 30% of gains)
- Don't exit just because of small pullbacks

RISK RULES:
- Wait for high-confidence setups only
- Accept missing some moves for better entries
- Maximum position: 15% of balance""",
    TradingStrategy.MEAN_REVERSION: """You are a mean reversion trader for crypto markets.

YOUR TRADING STYLE:
- Look for overextended moves that will snap back
- Fade extreme momentum (go opposite direction)
- Quick exits when price reverts to mean

ENTRY CRITERIA:
- Momentum is EXTENDED or EXHAUSTED
- Price moved too far too fast
- Order book showing reversal pressure building

EXIT CRITERIA:
- Exit when price returns toward starting point
- Take profits quickly on reversals
- Cut if trend continues against you

RISK RULES:
- Only fade CLEARLY overextended moves
- Small position sizes (fading is risky)
- Maximum position: 8% of balance""",
    TradingStrategy.CONSERVATIVE: """You are a conservative, risk-averse crypto trader.

YOUR TRADING STYLE:
- Only trade high-probability setups
- Require multiple confirming signals
- Preserve capital above all else
- Miss opportunities rather than take bad trades

ENTRY CRITERIA:
- Very strong momentum (top 10% of moves)
- Order book heavily skewed (65%+ in direction)
- Market pressure strongly supporting direction
- Multiple coins showing same direction

EXIT CRITERIA:
- Exit at first sign of weakness
- Take profits early and often
- Never let a winner turn into a loser

RISK RULES:
- Confidence must be 8+ to enter
- Skip anything uncertain
- Maximum position: 5% of balance""",
}


AI_TRADING_PROMPT = """You are an AI trading agent with COMPLETE CONTROL over trading decisions.

{strategy_prompt}

=== CURRENT MARKET STATE ===
PRICES:
{prices}

MOMENTUM ({momentum_timeframe}s):
{momentum}

MOMENTUM INTERPRETATION:
- Velocity: How fast price is moving (% change from average over window)
- Acceleration: Is momentum BUILDING (positive) or FADING (negative)?
- BUILDING momentum suggests move will continue - good for entries
- FADING momentum suggests move is exhausting - avoid chasing, consider exits

ORDER BOOK PRESSURE:
{orderbook}

MARKET PRESSURE: {pressure_score}/100 ({pressure_label})

RECENT TRADES FLOW:
{recent_trades}

=== YOUR CURRENT POSITIONS ===
{positions}

=== ACCOUNT STATUS ===
Balance: ${balance:,.2f}
Equity: ${equity:,.2f}
Open Positions: {num_positions}

=== YOUR DECISION ===
Analyze the market and decide your action.

Respond in this EXACT format (no extra text):
ACTION: [NONE/LONG/SHORT/EXIT_<COIN>]
COIN: [BTC/ETH/SOL or N/A]
SIZE_PCT: [5-20 or N/A]
CONFIDENCE: [1-10]
REASON: [One sentence explaining your decision]

ACTION meanings:
- NONE: No action, wait for better setup
- LONG: Open a long position on COIN
- SHORT: Open a short position on COIN
- EXIT_BTC: Close your BTC position (use EXIT_<COIN> format)

Only output ONE action per response."""


def get_strategy_prompt(strategy: TradingStrategy) -> str:
    """Get the full trading prompt for a strategy."""
    return STRATEGY_PROMPTS.get(strategy, STRATEGY_PROMPTS[TradingStrategy.MOMENTUM_SCALPER])


def format_ai_trading_prompt(
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
) -> str:
    """Format the complete AI trading prompt with current market state."""

    strategy_prompt = get_strategy_prompt(strategy)

    # Format prices
    price_lines = []
    for coin, price in prices.items():
        mom = momentum.get(coin, 0)
        mom_str = f"+{mom:.3f}%" if mom >= 0 else f"{mom:.3f}%"
        price_lines.append(f"  {coin}: ${price:,.2f} (momentum: {mom_str})")
    prices_str = "\n".join(price_lines) if price_lines else "  No data"

    # Format momentum WITH acceleration
    momentum_lines = []
    for coin, mom in momentum.items():
        accel = acceleration.get(coin, 0)
        direction = "UP" if mom > 0.05 else "DOWN" if mom < -0.05 else "FLAT"

        # Show if momentum is building or fading
        if accel > 0.01:
            trend = "BUILDING"
        elif accel < -0.01:
            trend = "FADING"
        else:
            trend = "STEADY"

        momentum_lines.append(f"  {coin}: {mom:+.3f}% {direction} | Accel: {accel:+.3f}% ({trend})")
    momentum_str = "\n".join(momentum_lines) if momentum_lines else "  No data"

    # Format orderbook
    orderbook_lines = []
    for coin, book in orderbook.items():
        bid_ratio = book.get("bid_ratio", 50)
        if bid_ratio > 60:
            pressure = "BUYERS dominating"
        elif bid_ratio < 40:
            pressure = "SELLERS dominating"
        else:
            pressure = "Balanced"
        orderbook_lines.append(f"  {coin}: {bid_ratio:.0f}% bids - {pressure}")
    orderbook_str = "\n".join(orderbook_lines) if orderbook_lines else "  No data"

    # Format recent trades
    if recent_trades:
        buys = sum(1 for t in recent_trades if t.get("side") == "buy")
        sells = len(recent_trades) - buys
        trades_str = f"  Last {len(recent_trades)} trades: {buys} buys, {sells} sells"
    else:
        trades_str = "  No recent trades"

    # Format positions
    if positions:
        pos_lines = []
        for coin, pos in positions.items():
            direction = "LONG" if pos.side.value == "long" else "SHORT"
            current_price = prices.get(coin, pos.entry_price)
            pnl_pct = pos.unrealized_pnl_percent(current_price)
            pnl_color = "profit" if pnl_pct >= 0 else "loss"
            pos_lines.append(
                f"  {direction} {coin}: entry ${pos.entry_price:,.2f}, "
                f"current ${current_price:,.2f}, P&L: {pnl_pct:+.2f}% ({pnl_color})"
            )
        positions_str = "\n".join(pos_lines)
    else:
        positions_str = "  No open positions"

    return AI_TRADING_PROMPT.format(
        strategy_prompt=strategy_prompt,
        prices=prices_str,
        momentum=momentum_str,
        momentum_timeframe=momentum_timeframe,
        orderbook=orderbook_str,
        pressure_score=pressure_score,
        pressure_label=pressure_label,
        recent_trades=trades_str,
        positions=positions_str,
        balance=balance,
        equity=equity,
        num_positions=len(positions),
    )


def list_strategies() -> list[tuple[str, str]]:
    """List available strategies with descriptions."""
    return [
        ("momentum_scalper", "Aggressive momentum scalping - quick entries/exits"),
        ("trend_follower", "Patient trend following - ride the wave"),
        ("mean_reversion", "Fade overextended moves - contrarian"),
        ("conservative", "High-confidence only - preserve capital"),
    ]
