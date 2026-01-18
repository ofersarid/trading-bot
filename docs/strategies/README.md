# Trading Strategies

This folder contains documentation for trading strategies implemented in the bot.

## Active Strategies

| Strategy | Status | Description |
|----------|--------|-------------|
| [Momentum Scalping v1](./momentum-scalping-v1.md) | Active | Short-term momentum-based scalping |

## Strategy Document Structure

Each strategy document should include:

1. **Overview** - Core premise and trading thesis
2. **Entry Logic** - When and how positions are opened
3. **Exit Logic** - Take profit, stop loss, and emergency exits
4. **Configuration** - Adjustable parameters and defaults
5. **Limitations** - Known weaknesses and risks
6. **Performance** - How to evaluate the strategy

## Adding New Strategies

When implementing a new strategy:

1. Create a new markdown file: `strategy-name-v1.md`
2. Document the logic before or alongside implementation
3. Reference the code files that implement it
4. Update this README with the new strategy

## Historical Strategies

Old Pine Script strategies (TradingView) are archived in `/Old/strategies/`.
