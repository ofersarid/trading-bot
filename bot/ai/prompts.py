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


ENTRY_ANALYSIS_PROMPT = """Evaluate this trade opportunity:

OPPORTUNITY: {direction} {coin} at ${price}
MOMENTUM: {momentum}% in 60s
ORDER BOOK: {bid_ratio}% bids
CURRENT P&L: ${pnl}

Respond in this exact format:
CONFIDENCE: [1-10]
POSITION_SIZE: [SMALL/MEDIUM/LARGE]
REASON: [One sentence]"""


EXIT_ANALYSIS_PROMPT = """Should we exit this position?

POSITION: {direction} {coin}
ENTRY PRICE: ${entry_price}
CURRENT PRICE: ${current_price}
P&L: {pnl_percent}%
HOLD TIME: {hold_time}s
MOMENTUM: {momentum}%

Respond in this exact format:
ACTION: [HOLD/EXIT]
CONFIDENCE: [1-10]
REASON: [One sentence]"""


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
        orderbook_lines.append(f"  {coin}: {bid_ratio:.0f}% bids / {100-bid_ratio:.0f}% asks")
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
