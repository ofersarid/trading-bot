# Extract Trading Info from Transcript

Extract indicators, signals, and trading strategies from a parsed transcript JSON file.

---

## Input

The user must provide a `transcript.json` file path. If not provided, ask:

> **Which transcript.json file should I analyze?**
> Please provide the path to the transcript JSON file.

---

## Steps

### Step 1: Read and Validate the Input

1. Read the provided `transcript.json` file
2. Validate it contains an array of objects with `time` and `text` fields
3. If invalid, report the error and stop

### Step 2: Analyze the Transcript

Go through all transcript entries and extract:

**Indicators:**
- Name of each indicator mentioned (e.g., Volume Profile, VWAP, RSI, MACD)
- How the indicator is configured (settings, parameters)
- What the indicator shows or measures

**Signals:**
- Entry signals (what triggers a buy/long)
- Exit signals (what triggers a sell/close)
- Warning signals (what to avoid or be cautious about)
- High quality signal criteria (what makes a signal strong/reliable)
- Low quality signal criteria (what makes a signal weak/unreliable)

**Trading Strategies:**
- Complete trading setups or approaches described
- Rules for entries and exits
- Risk management guidelines mentioned
- Timeframes recommended

### Step 3: Create the Output File

Create a markdown file named `trading-info.md` in the **same folder** as the input `transcript.json`.

Use this structure:

```markdown
# Trading Info: [Video/Source Title]

> Extracted from transcript on [date]

---

## Indicators

### [Indicator Name]

**What it measures:** [brief description]

**How to use it:**
- [usage point 1]
- [usage point 2]

**Settings:** [if mentioned]

---

## Signals

### Entry Signals

| Signal | Condition | Notes |
|--------|-----------|-------|
| [name] | [when to enter] | [additional context] |

### Exit Signals

| Signal | Condition | Notes |
|--------|-----------|-------|
| [name] | [when to exit] | [additional context] |

### Warning Signs

- [what to avoid or watch out for]

### Signal Quality

**High Quality Signals (strong/reliable):**
- [criteria 1]
- [criteria 2]

**Low Quality Signals (weak/unreliable):**
- [criteria 1]
- [criteria 2]

---

## Trading Strategies

### [Strategy Name or Description]

**Setup:**
1. [step 1]
2. [step 2]

**Entry:** [when to enter]

**Exit:** [when to exit]

**Risk Management:** [if mentioned]

---

## Key Takeaways

- [main point 1]
- [main point 2]
- [main point 3]
```

### Step 4: Report Results

After creating the file, report:

> **Trading Info Extracted Successfully**
>
> | Metric | Value |
> |--------|-------|
> | Source | `[input file path]` |
> | Output | `[output file path]` |
> | Indicators Found | [count] |
> | Signals Found | [count] |
> | Strategies Found | [count] |

---

## Guidelines

- Keep descriptions simple and actionable
- Use bullet points over paragraphs
- Include specific numbers/values when mentioned in the transcript
- If something is unclear in the transcript, note it as "[unclear]" rather than guessing
- Focus on practical, tradeable information
