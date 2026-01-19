"""Prompt templates for trading analysis."""

MARKET_ANALYSIS_PROMPT = """You are a crypto trading analyst. Analyze this market data and provide a structured assessment.

CURRENT PRICES:
{prices}

MOMENTUM ({momentum_timeframe}s):
{momentum}

ORDER BOOK IMBALANCE:
{orderbook}

RECENT TRADES:
{recent_trades}

MARKET PRESSURE: {pressure_score}/100 ({pressure_label})

Respond in this EXACT format (no extra text, no markdown):
SENTIMENT: [BULLISH/BEARISH/NEUTRAL]
CONFIDENCE: [1-10]
SIGNAL: [LONG/SHORT/WAIT]
MOMENTUM: {momentum_format}
PRESSURE: [0-100] ([Strong Selling/Moderate Selling/Neutral/Moderate Buying/Strong Buying])
FRESHNESS: [FRESH/DEVELOPING/EXTENDED/EXHAUSTED]
REASON: [One sentence explaining your signal, mentioning key factors]

FRESHNESS Guidelines:
- FRESH: Move just started (<0.2% in direction), high potential
- DEVELOPING: Building momentum (0.2-0.4%), good entry
- EXTENDED: Move has run (0.4-0.6%), consider waiting for pullback
- EXHAUSTED: Likely reversal zone (>0.6%), avoid chasing"""


QUICK_SENTIMENT_PROMPT = """Market data:
{prices}
Order book: {bid_ratio}% bids. Recent: {buys} buys, {sells} sells.
One word only: BULLISH, BEARISH, or NEUTRAL?"""


ENTRY_ANALYSIS_PROMPT = """You are a crypto trading analyst. Evaluate this trade opportunity.

OPPORTUNITY: {direction} {coin} at ${price:,.2f}
CURRENT MOMENTUM: {momentum:+.3f}% ({momentum_timeframe}s)
ORDER BOOK: {bid_ratio:.0f}% bids / {ask_ratio:.0f}% asks
MARKET PRESSURE: {pressure_score}/100 ({pressure_label})
FRESHNESS: {freshness}

CONTEXT:
- Take profit target: {take_profit_pct}%
- Stop loss: {stop_loss_pct}%
- Risk/reward must be favorable

Respond in this EXACT format (no extra text):
DECISION: [ENTER/SKIP]
CONFIDENCE: [1-10]
SIZE: [SMALL/MEDIUM/LARGE]
REASON: [One sentence explaining your decision]

Guidelines:
- ENTER only if momentum aligns with direction and freshness is FRESH/DEVELOPING
- SKIP if EXTENDED/EXHAUSTED (chasing) or momentum conflicts with direction
- High confidence (7+) needed for LARGE size"""


EXIT_ANALYSIS_PROMPT = """You are a crypto trading analyst. Should we exit this position?

POSITION: {direction} {coin}
ENTRY PRICE: ${entry_price:,.2f}
CURRENT PRICE: ${current_price:,.2f}
UNREALIZED P&L: {pnl_percent:+.2f}%
HOLD TIME: {hold_time}s
CURRENT MOMENTUM: {momentum:+.3f}% ({momentum_timeframe}s)
MARKET PRESSURE: {pressure_score}/100 ({pressure_label})

TARGETS:
- Take profit: {take_profit_pct}%
- Stop loss: {stop_loss_pct}%

Respond in this EXACT format (no extra text):
ACTION: [HOLD/EXIT]
CONFIDENCE: [1-10]
REASON: [One sentence explaining your decision]

Guidelines:
- EXIT if momentum reversed against position direction
- EXIT if approaching stop loss with weak momentum
- HOLD if momentum still supports position direction
- HOLD if approaching take profit with strong momentum (let it run)"""


def format_market_analysis(
    prices: dict[str, dict],
    momentum: dict[str, float],
    orderbook: dict[str, dict],
    recent_trades: list[dict],
    pressure_score: int = 50,
    pressure_label: str = "Neutral",
    momentum_timeframe: int = 60,
) -> str:
    """Format market data into the analysis prompt."""
    # Format prices
    price_lines = []
    for coin, data in prices.items():
        price = data.get("price", 0)
        change = data.get("change_1m", 0)
        price_lines.append(f"  {coin}: ${price:,.2f} ({change:+.2f}% 1min)")
    prices_str = "\n".join(price_lines) if price_lines else "  No data"

    # Format momentum
    momentum_lines = []
    momentum_parts = []
    for coin, mom in momentum.items():
        momentum_lines.append(f"  {coin}: {mom:+.3f}%")
        momentum_parts.append(f"{coin} {mom:+.2f}%")
    momentum_str = "\n".join(momentum_lines) if momentum_lines else "  No data"

    # Format for AI response template
    momentum_format = " | ".join(momentum_parts) if momentum_parts else "N/A"

    # Format orderbook
    orderbook_lines = []
    for coin, book in orderbook.items():
        bid_ratio = book.get("bid_ratio", 50)
        orderbook_lines.append(f"  {coin}: {bid_ratio:.0f}% bids / {100 - bid_ratio:.0f}% asks")
    orderbook_str = "\n".join(orderbook_lines) if orderbook_lines else "  No data"

    # Format recent trades
    if recent_trades:
        buys = sum(1 for t in recent_trades if t.get("side") == "buy")
        sells = len(recent_trades) - buys
        trades_str = f"  {buys} buys, {sells} sells in last minute"
    else:
        trades_str = "  No recent trades"

    return MARKET_ANALYSIS_PROMPT.format(
        prices=prices_str,
        momentum=momentum_str,
        momentum_timeframe=momentum_timeframe,
        orderbook=orderbook_str,
        recent_trades=trades_str,
        pressure_score=pressure_score,
        pressure_label=pressure_label,
        momentum_format=momentum_format,
    )


def format_quick_sentiment(
    prices: dict[str, dict],
    bid_ratio: float,
    buys: int,
    sells: int,
) -> str:
    """Format data for quick sentiment check."""
    price_parts = []
    for coin, data in prices.items():
        price = data.get("price", 0)
        change = data.get("change_1m", 0)
        price_parts.append(f"{coin}: ${price:,.0f} ({change:+.1f}% 1min)")
    prices_str = ", ".join(price_parts)

    return QUICK_SENTIMENT_PROMPT.format(
        prices=prices_str,
        bid_ratio=f"{bid_ratio:.0f}",
        buys=buys,
        sells=sells,
    )


def format_entry_analysis(
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
) -> str:
    """Format data for entry analysis prompt."""
    return ENTRY_ANALYSIS_PROMPT.format(
        direction=direction,
        coin=coin,
        price=price,
        momentum=momentum,
        momentum_timeframe=momentum_timeframe,
        bid_ratio=bid_ratio,
        ask_ratio=100 - bid_ratio,
        pressure_score=pressure_score,
        pressure_label=pressure_label,
        freshness=freshness,
        take_profit_pct=take_profit_pct,
        stop_loss_pct=stop_loss_pct,
    )


def format_exit_analysis(
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
) -> str:
    """Format data for exit analysis prompt."""
    return EXIT_ANALYSIS_PROMPT.format(
        direction=direction,
        coin=coin,
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
