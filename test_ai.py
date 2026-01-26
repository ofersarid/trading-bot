#!/usr/bin/env python3
"""
AI Strategy Tester - Interactive tool to experiment with AI trading analysis.

Run with:
    python test_ai.py                    # Interactive mode
    python test_ai.py --strategy momentum # Use specific strategy
    python test_ai.py --list             # List available strategies
    python test_ai.py --custom           # Enter custom market data

This script lets you:
1. See exactly what prompt is sent to the AI
2. Test different strategies with the same market data
3. Understand how the AI makes decisions
4. Experiment with custom market scenarios
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path before local imports
sys.path.insert(0, str(Path(__file__).parent))

import questionary
from questionary import Style

from bot.ai.ollama_client import OllamaClient
from bot.ai.prompts import get_strategy_prompt
from bot.core.models import MarketPressure
from bot.strategies import StrategyType, list_strategies

# Backwards compatibility alias
TradingStrategy = StrategyType

# Historical data folder path
HISTORICAL_DATA_DIR = Path(__file__).parent / "data" / "historical"

# Scenario definitions - folder name -> (description, sample market data for AI testing)
SCENARIOS = {
    "bullish_momentum": {
        "name": "🟢 Bullish Momentum",
        "description": "Strong upward movement with buyer dominance",
        "prices": {
            "BTC": {"price": 95000, "change_1m": 0.45},
            "ETH": {"price": 3300, "change_1m": 0.32},
        },
        "momentum": {"BTC": 0.45, "ETH": 0.32},
        "orderbook": {"BTC": {"bid_ratio": 68}},
        "recent_trades": [{"side": "buy"}] * 7 + [{"side": "sell"}] * 3,
    },
    "bearish_momentum": {
        "name": "🔴 Bearish Momentum",
        "description": "Strong downward movement with seller dominance",
        "prices": {
            "BTC": {"price": 93000, "change_1m": -0.52},
            "ETH": {"price": 3150, "change_1m": -0.41},
        },
        "momentum": {"BTC": -0.52, "ETH": -0.41},
        "orderbook": {"BTC": {"bid_ratio": 32}},
        "recent_trades": [{"side": "sell"}] * 8 + [{"side": "buy"}] * 2,
    },
    "choppy_neutral": {
        "name": "⚪ Choppy/Neutral",
        "description": "No clear direction, conflicting signals",
        "prices": {
            "BTC": {"price": 94500, "change_1m": 0.05},
            "ETH": {"price": 3250, "change_1m": -0.08},
        },
        "momentum": {"BTC": 0.05, "ETH": -0.08},
        "orderbook": {"BTC": {"bid_ratio": 52}},
        "recent_trades": [{"side": "buy"}] * 5 + [{"side": "sell"}] * 5,
    },
    "extreme_buying": {
        "name": "🟡 Extreme Buying",
        "description": "Overextended buying - potential reversal",
        "prices": {
            "BTC": {"price": 96500, "change_1m": 0.65},
            "ETH": {"price": 3400, "change_1m": 0.55},
        },
        "momentum": {"BTC": 0.65, "ETH": 0.55},
        "orderbook": {"BTC": {"bid_ratio": 78}},
        "recent_trades": [{"side": "buy"}] * 9 + [{"side": "sell"}] * 1,
    },
    "extreme_selling": {
        "name": "🟡 Extreme Selling",
        "description": "Panic selling - potential bounce",
        "prices": {
            "BTC": {"price": 91000, "change_1m": -0.75},
            "ETH": {"price": 3050, "change_1m": -0.68},
        },
        "momentum": {"BTC": -0.75, "ETH": -0.68},
        "orderbook": {"BTC": {"bid_ratio": 25}},
        "recent_trades": [{"side": "sell"}] * 9 + [{"side": "buy"}] * 1,
    },
    "uncategorized": {
        "name": "📁 Uncategorized",
        "description": "Unclassified historical data",
        "prices": {
            "BTC": {"price": 94000, "change_1m": 0.1},
            "ETH": {"price": 3200, "change_1m": 0.05},
        },
        "momentum": {"BTC": 0.1, "ETH": 0.05},
        "orderbook": {"BTC": {"bid_ratio": 50}},
        "recent_trades": [{"side": "buy"}] * 5 + [{"side": "sell"}] * 5,
    },
}

# Build strategy descriptions dict from list_strategies()
STRATEGY_DESCRIPTIONS = {StrategyType(name): desc for name, desc in list_strategies()}

# Custom style for questionary prompts
MENU_STYLE = Style(
    [
        ("qmark", "fg:cyan bold"),
        ("question", "fg:white bold"),
        ("answer", "fg:green bold"),
        ("pointer", "fg:cyan bold"),
        ("highlighted", "fg:cyan bold"),
        ("selected", "fg:green"),
    ]
)


def format_prompt_with_data(
    strategy_prompt: str,
    prices: dict,
    momentum: dict,
    orderbook: dict,
    recent_trades: list,
) -> str:
    """Format market data into a strategy prompt."""
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
    momentum_format = " | ".join(momentum_parts) if momentum_parts else "N/A"

    # Format orderbook - convert bid_ratio format to bids/asks lists for pressure calculation
    orderbook_lines = []
    orderbook_for_pressure = {}
    for coin, book in orderbook.items():
        bid_ratio = book.get("bid_ratio", 50)
        orderbook_lines.append(f"  {coin}: {bid_ratio:.0f}% bids / {100-bid_ratio:.0f}% asks")
        # Mock orderbook structure for pressure calculation
        orderbook_for_pressure[coin] = {
            "bids": [{"sz": bid_ratio}],  # Simplified: use ratio as volume proxy
            "asks": [{"sz": 100 - bid_ratio}],
        }
    orderbook_str = "\n".join(orderbook_lines) if orderbook_lines else "  No data"

    # Format recent trades
    if recent_trades:
        buys = sum(1 for t in recent_trades if t.get("side") == "buy")
        sells = len(recent_trades) - buys
        trades_str = f"  {buys} buys, {sells} sells in last minute"
    else:
        trades_str = "  No recent trades"

    # Calculate market pressure
    pressure = MarketPressure.calculate(
        orderbook=orderbook_for_pressure,
        recent_trades=recent_trades,
        momentum=momentum,
    )

    return strategy_prompt.format(
        prices=prices_str,
        momentum=momentum_str,
        orderbook=orderbook_str,
        recent_trades=trades_str,
        pressure_score=int(pressure.score),
        pressure_label=pressure.label,
        momentum_format=momentum_format,
    )


def print_header(text: str) -> None:
    """Print a styled header."""
    print()
    print("=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_section(title: str) -> None:
    """Print a section divider."""
    print()
    print(f"─── {title} ───")


async def check_ollama() -> OllamaClient | None:
    """Check if Ollama is running and return client."""
    client = OllamaClient(model="mistral")

    if await client.is_available():
        print("✓ Ollama server connected")
        print(f"  Model: {client.model}")
        return client
    else:
        print("❌ Ollama server not available!")
        print()
        print("To start Ollama:")
        print("  1. Open a new terminal")
        print("  2. Run: ollama serve")
        print("  3. Wait for 'Listening on...' message")
        print("  4. Run this script again")
        return None


async def run_analysis(
    client: OllamaClient,
    strategy: TradingStrategy,
    scenario: dict,
    show_prompt: bool = True,
) -> None:
    """Run AI analysis with a specific strategy and scenario."""
    strategy_prompt = get_strategy_prompt(strategy)
    prompt = format_prompt_with_data(
        strategy_prompt,
        scenario["prices"],
        scenario["momentum"],
        scenario["orderbook"],
        scenario["recent_trades"],
    )

    if show_prompt:
        print_section("PROMPT SENT TO AI")
        print(prompt)

    print_section("AI RESPONSE")
    print("Thinking...", end="", flush=True)

    response, tokens, time_ms = await client.analyze(prompt)
    print("\r", end="")  # Clear "Thinking..."

    # Parse and highlight the response
    for line in response.strip().split("\n"):
        if line.startswith("SENTIMENT:"):
            sentiment = line.split(":", 1)[1].strip()
            color = {"BULLISH": "\033[92m", "BEARISH": "\033[91m", "NEUTRAL": "\033[93m"}.get(
                sentiment, ""
            )
            print(f"SENTIMENT: {color}{sentiment}\033[0m")
        elif line.startswith("CONFIDENCE:"):
            conf = line.split(":", 1)[1].strip()
            print(f"CONFIDENCE: \033[96m{conf}\033[0m")
        elif line.startswith("SIGNAL:"):
            signal = line.split(":", 1)[1].strip()
            color = {"LONG": "\033[92m", "SHORT": "\033[91m", "WAIT": "\033[93m"}.get(signal, "")
            print(f"SIGNAL: {color}{signal}\033[0m")
        elif line.startswith("MOMENTUM:"):
            momentum_val = line.split(":", 1)[1].strip()
            # Color each coin's momentum
            parts = momentum_val.split("|")
            colored_parts = []
            for part in parts:
                part = part.strip()
                if "+" in part:
                    colored_parts.append(f"\033[92m{part}\033[0m")
                elif "-" in part:
                    colored_parts.append(f"\033[91m{part}\033[0m")
                else:
                    colored_parts.append(part)
            print(f"MOMENTUM: {' | '.join(colored_parts)}")
        elif line.startswith("PRESSURE:"):
            pressure_val = line.split(":", 1)[1].strip()
            # Parse score and label
            if "(" in pressure_val:
                score_part = pressure_val.split("(")[0].strip()
                try:
                    score = int(score_part)
                    if score > 55:
                        color = "\033[92m"  # Green for buying
                    elif score < 45:
                        color = "\033[91m"  # Red for selling
                    else:
                        color = "\033[93m"  # Yellow for neutral
                    print(f"PRESSURE: {color}{pressure_val}\033[0m")
                except ValueError:
                    print(f"PRESSURE: {pressure_val}")
            else:
                print(f"PRESSURE: {pressure_val}")
        elif line.startswith("FRESHNESS:"):
            freshness = line.split(":", 1)[1].strip()
            colors = {
                "FRESH": "\033[92m",
                "DEVELOPING": "\033[96m",
                "EXTENDED": "\033[93m",
                "EXHAUSTED": "\033[91m",
            }
            color = colors.get(freshness.upper(), "")
            print(f"FRESHNESS: {color}{freshness}\033[0m")
        elif line.startswith("REASON:"):
            reason = line.split(":", 1)[1].strip()
            print(f"REASON: \033[90m{reason}\033[0m")
        else:
            print(line)

    print()
    print(f"⚡ {tokens} tokens in {time_ms:.0f}ms")


async def interactive_mode(client: OllamaClient) -> None:
    """Run interactive testing mode."""

    print_header("AI STRATEGY TESTER - Interactive Mode")

    menu_choices = [
        "Test a strategy with a scenario",
        "Compare all strategies on one scenario",
        "Test one strategy on all scenarios",
        "List strategies and their descriptions",
        "Exit",
    ]

    while True:
        print()
        choice = await questionary.select(
            "What would you like to do?",
            choices=menu_choices,
            style=MENU_STYLE,
            use_arrow_keys=True,
            use_shortcuts=True,
        ).ask_async()

        if choice is None or choice == "Exit":
            print("\nGoodbye!")
            break
        elif choice == menu_choices[0]:
            await test_single(client)
        elif choice == menu_choices[1]:
            await compare_strategies(client)
        elif choice == menu_choices[2]:
            await test_all_scenarios(client)
        elif choice == menu_choices[3]:
            show_strategies()


def show_strategies() -> None:
    """Display all available strategies."""
    print_header("AVAILABLE STRATEGIES")

    for strategy in TradingStrategy:
        print(f"\n  {strategy.value.upper()}")
        print(f"  └─ {STRATEGY_DESCRIPTIONS[strategy]}")


def get_historical_data_by_scenario() -> dict[str, list[Path]]:
    """
    Scan historical data folder and return files organized by scenario.

    Returns:
        Dict mapping scenario name to list of CSV file paths
    """
    result = {}

    if not HISTORICAL_DATA_DIR.exists():
        return result

    for folder_name in SCENARIOS:
        folder_path = HISTORICAL_DATA_DIR / folder_name
        if folder_path.exists() and folder_path.is_dir():
            csv_files = sorted(folder_path.glob("*.csv"))
            if csv_files:
                result[folder_name] = csv_files

    return result


def show_scenarios() -> None:
    """Display available scenarios with their historical data files."""
    print("\nAvailable scenarios:")

    data_by_scenario = get_historical_data_by_scenario()

    for name, scenario in SCENARIOS.items():
        files = data_by_scenario.get(name, [])
        file_count = len(files)

        print(f"\n  {scenario['name']}")
        print(f"  └─ {scenario['description']}")
        print(f"     Folder: {name}/")
        if files:
            print(f"     Historical data: {file_count} file(s)")
            for f in files:
                print(f"       • {f.name}")
        else:
            print("     Historical data: (empty - add CSV files here)")


async def select_strategy() -> TradingStrategy | None:
    """Let user select a strategy using arrow keys."""
    strategies = list(TradingStrategy)
    choices = [
        questionary.Choice(
            title=f"{s.value}: {STRATEGY_DESCRIPTIONS[s]}",
            value=s,
        )
        for s in strategies
    ]

    return await questionary.select(
        "Select a strategy:",
        choices=choices,
        style=MENU_STYLE,
        use_arrow_keys=True,
    ).ask_async()


async def select_scenario() -> tuple[str, dict] | None:
    """Let user select a scenario using arrow keys. Returns (name, scenario_data)."""
    data_by_scenario = get_historical_data_by_scenario()

    choices = []
    for name, scenario in SCENARIOS.items():
        files = data_by_scenario.get(name, [])
        file_info = f" [{len(files)} files]" if files else ""
        choices.append(
            questionary.Choice(
                title=f"{scenario['name']} - {scenario['description']}{file_info}",
                value=(name, scenario),
            )
        )

    return await questionary.select(
        "Select a market scenario:",
        choices=choices,
        style=MENU_STYLE,
        use_arrow_keys=True,
    ).ask_async()


async def test_single(client: OllamaClient) -> None:
    """Test a single strategy with a single scenario."""
    strategy = await select_strategy()
    if strategy is None:
        return

    result = await select_scenario()
    if result is None:
        return
    scenario_name, scenario = result

    print_header(f"Testing: {strategy.value.upper()} on {scenario['name']}")
    await run_analysis(client, strategy, scenario)


async def compare_strategies(client: OllamaClient) -> None:
    """Compare all strategies on the same scenario."""
    result = await select_scenario()
    if result is None:
        return
    scenario_name, scenario = result

    print_header(f"Comparing ALL strategies on: {scenario['name']}")

    for strategy in TradingStrategy:
        print_section(f"Strategy: {strategy.value.upper()}")
        await run_analysis(client, strategy, scenario, show_prompt=False)
        print()


async def test_all_scenarios(client: OllamaClient) -> None:
    """Test one strategy on all scenarios."""
    strategy = await select_strategy()
    if strategy is None:
        return

    print_header(f"Testing {strategy.value.upper()} on ALL scenarios")

    for scenario in SCENARIOS.values():
        print_section(scenario["name"])
        await run_analysis(client, strategy, scenario, show_prompt=False)
        print()


async def main():
    parser = argparse.ArgumentParser(
        description="AI Strategy Tester - Experiment with trading AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_ai.py                      # Interactive mode
  python test_ai.py --list               # List strategies
  python test_ai.py -s momentum          # Quick test with momentum strategy
  python test_ai.py -s contrarian -c bullish_momentum  # Specific combo
        """,
    )
    parser.add_argument(
        "-s",
        "--strategy",
        choices=[s.value for s in TradingStrategy],
        help="Strategy to use",
    )
    parser.add_argument(
        "-c",
        "--scenario",
        choices=list(SCENARIOS.keys()),
        help="Market scenario to test",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List available strategies and exit",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare all strategies on the selected scenario",
    )

    args = parser.parse_args()

    if args.list:
        show_strategies()
        print()
        show_scenarios()
        return

    # Check Ollama
    print_header("AI STRATEGY TESTER")
    client = await check_ollama()
    if not client:
        return

    try:
        if args.strategy and args.scenario:
            # Direct mode: specific strategy + scenario
            strategy = TradingStrategy(args.strategy)
            scenario = SCENARIOS[args.scenario]

            print_header(f"{strategy.value.upper()} on {scenario['name']}")
            await run_analysis(client, strategy, scenario)

        elif args.strategy and args.compare:
            # Compare all strategies
            scenario = SCENARIOS.get(args.scenario, SCENARIOS["bullish_momentum"])
            print_header(f"Comparing strategies on {scenario['name']}")
            for strategy in TradingStrategy:
                print_section(strategy.value.upper())
                await run_analysis(client, strategy, scenario, show_prompt=False)

        elif args.strategy:
            # Quick test with default bullish scenario
            strategy = TradingStrategy(args.strategy)
            scenario = SCENARIOS["bullish_momentum"]

            print_header(f"Quick Test: {strategy.value.upper()}")
            await run_analysis(client, strategy, scenario)

        else:
            # Interactive mode
            await interactive_mode(client)

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
