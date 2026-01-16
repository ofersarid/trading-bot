# Transcript to Skeleton

Convert a raw YouTube trading video transcript into a structured strategy skeleton.

## Instructions

Read the provided `raw.txt` transcript and extract a clear, actionable trading strategy skeleton.

### Output Format

Write to the corresponding `skeleton.md` file with this structure:

```markdown
# [Strategy Name]

> Source: [YouTube video title/author if mentioned]

## Overview
Brief 1-2 sentence summary of the strategy concept.

## Key Concepts
Define any trading terms or concepts essential to understanding the strategy.

## Entry Rules
Precise conditions that must ALL be met to enter a trade:
- [ ] Condition 1
- [ ] Condition 2
- ...

### Long Entry
Specific conditions for long/buy entries.

### Short Entry
Specific conditions for short/sell entries.

## Exit Rules

### Take Profit
- Target 1: ...
- Target 2: ... (if applicable)

### Stop Loss
- Placement: ...
- Adjustment rules: ... (if any)

## Filters / Confirmations
Optional conditions that improve win rate:
- Filter 1
- Filter 2

## Timeframe
- Recommended: ...
- Works on: ...

## Visual Reference
Describe what the setup looks like on a chart (for implementation reference).

## Notes
- Edge cases, warnings, or nuances from the video
- Things the author emphasized
```

### Extraction Guidelines

1. **Be precise** - Extract specific numbers, ratios, and conditions (e.g., "close above the 20 EMA" not "price above moving average")
2. **Separate opinions from rules** - Only include concrete, testable rules in Entry/Exit sections
3. **Flag ambiguity** - If the video is vague on a rule, note it in the Notes section with `[UNCLEAR]`
4. **Preserve trader's logic** - Include WHY behind rules when explained (helps with refinement)
5. **Ignore fluff** - Skip intros, outros, promotions, tangents

### Example Transformation

**Raw transcript snippet:**
> "...so what we're looking for is the last bearish candle before that big push up, that's your order block. You want to see price come back down to it and then look for a bullish engulfing or something like that..."

**Skeleton output:**
```markdown
## Entry Rules
### Long Entry
- [ ] Identify bullish impulse move (significant upward price movement)
- [ ] Mark the last bearish candle before the impulse as the Order Block
- [ ] Wait for price to retrace back to the Order Block zone
- [ ] Enter on bullish confirmation candle (e.g., bullish engulfing) at the Order Block
```
