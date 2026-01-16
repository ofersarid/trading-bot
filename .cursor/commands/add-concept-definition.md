---
name: Add Concept Definition
description: Analyze screenshots explaining a trading concept and add a structured definition to concepts.md (coupled with transcript)
tags: [trading, concepts, documentation, learning]
---

# Add Concept Definition Command

## Purpose

This command helps you document trading concepts in a structured, LLM-optimized format. The definitions serve as building blocks for understanding more complex concepts.

**Key principle:** The transcript and `concepts.md` are always coupled together in the same directory.

## Prerequisites

**Required:**
- One or more screenshots explaining the concept you want to document
- Transcript file (`.txt`) from the video/course the screenshots are from

**File Structure:**
The `concepts.md` file lives in the **same directory** as the transcript:
```
YouTube/
  └── [Channel Name]/
      └── [Video Title]/
          ├── transcript.txt     ← raw transcript from the video
          └── concepts.md        ← concepts extracted from this video
```

Each video has its own folder containing both files as siblings.

**If transcript is missing, STOP and prompt:**
> "📚 Please attach the transcript file (`.txt`) along with your screenshot(s).
>
> The transcript is required because `concepts.md` is stored in the same directory as the transcript.
>
> Drag and drop both files into the chat, then run this command again."

**If no images are attached, STOP and prompt:**
> "📚 Please attach screenshot(s) explaining the trading concept you want to document.
>
> These could be:
> - Chart annotations showing the pattern
> - Educational diagrams
> - Examples from videos or courses
>
> Drag and drop the files into the chat, then run this command again."

---

## Step 1: Analyze the Images

Analyze all attached images and identify:

1. **Visual Elements**
   - Price action patterns (candles, wicks, bodies)
   - Key price levels (support, resistance, highs, lows)
   - Annotations, arrows, labels, or highlights
   - Any text or explanations visible in the images

2. **Pattern Recognition**
   - What market structure is being shown?
   - What is the before/after relationship?
   - What triggers or conditions are illustrated?

3. **Context Clues**
   - Timeframe (if visible)
   - Asset type (if visible)
   - Market conditions (trending, ranging, volatile)

---

## Step 2: Locate Transcript Section & Determine concepts.md Path

From the transcript file path, determine where `concepts.md` should be:
- **Transcript path:** e.g., `YouTube/Mind Math Money/MASTER Candlestick Patterns in 125 Minutes/transcript.txt`
- **Concepts path:** `YouTube/Mind Math Money/MASTER Candlestick Patterns in 125 Minutes/concepts.md` (sibling file)

### Smart Transcript Search

The transcript is structured into **sections**, each with a title. Match the slide/screenshot title to a section title in the transcript.

1. **Extract the slide title** from the screenshot (visible text, heading, or topic name)

2. **Search transcript for section titles:**
   - Transcripts have section titles that mark topic changes (e.g., "How to Read Candlestick Charts", "Candlestick Strength", "The Doji Pattern")
   - Find the section title that matches or closely relates to the slide title
   - **Section = all content from that title until the next section title**

3. **Present the located section** to the user:

> **📄 Transcript Section Found:**
> 
> **Section Title:** [Matched title from transcript]
> **Lines [X-Y]:**
> ```
> [Full section content from title until next section title]
> ```
> 
> **Is this the correct section? (Yes/No)**
> - If wrong, tell me the correct section title to search for

4. **Iterate until user confirms** the correct section is found

**IMPORTANT:** Do NOT proceed to Step 3 until user confirms the transcript section.

The verified section provides the full context the instructor gave about this concept.

---

## Steps 3-4: Present Understanding & Iterate Until Confirmed

**Step 3:** Present your understanding using this format (incorporate transcript context if available):

> **📖 My Understanding of: [CONCEPT NAME]**
>
> **What it is:**
> [1-2 sentence definition]
>
> **Key characteristics:**
> - [Bullet points of defining features]
>
> **How to identify it:**
> - [Visual/structural criteria]
>
> **When it occurs:**
> - [Market conditions or context]
>
> **Why it matters:**
> - [Significance for trading decisions]
>
> ---
> **Is this understanding correct?**
> - ✅ Yes, proceed
> - ❌ No, here's what's wrong: [explain]
> - 🔄 Partially correct, but: [clarify]

**Step 4:** Iterate until user confirms:
- If user says "No" or provides clarification → revise understanding → ask again
- If user says "Yes" → proceed to Step 5

**IMPORTANT:** Do NOT proceed to Step 5 until user explicitly confirms understanding is correct.

---

## Step 5: Add or Update Concept Definition

Once understanding is confirmed:

1. **Check for existing concept** in `concepts.md` (same directory as transcript):
   - Search for the concept name (exact match and variations)
   - Search for similar concepts that might cover the same idea
   
   **If concept already exists, STOP and inform the user:**
   > "⚠️ This concept already exists in `concepts.md`:
   > 
   > [Show existing definition]
   > 
   > Would you like to:
   > - **Update** - Merge new information into the existing definition
   > - **Replace** - Overwrite with the new definition
   > - **Skip** - Keep existing, don't change anything
   > - **Rename** - Add as a distinct variant with different name"
   
   **Wait for user's choice before proceeding.**

2. **If updating existing concept:**
   - Merge new characteristics, criteria, or context into the existing definition
   - Preserve information that's still accurate
   - Show the merged result for user approval before saving

3. **If adding new concept:**
   - Group concepts by context and relativity (not alphabetically)
   - Place new concept near related concepts
   - If a new category/group is needed, create a section header (e.g., `### Market Structure`, `### Price Action Patterns`)
   - If file is empty, add as first entry and consider what group it belongs to

4. **Add/Update the definition** using the LLM-Optimized Format below

---

## LLM-Optimized Definition Format

Use this exact structure for each concept:

```markdown
## [CONCEPT NAME]

**Definition:** [Single sentence definition - precise and parseable]

**Characteristics:**
- [Key feature 1]
- [Key feature 2]
- [Key feature 3]

**Identification Criteria:**
1. [Specific condition 1]
2. [Specific condition 2]
3. [Specific condition 3]

**Context:** [When/where this typically occurs]

**Trading Implication:** [What action or expectation this suggests]

**Related Concepts:** [Links to other concepts if applicable]

---
```

### Format Guidelines

1. **Definition:** Must be a single, complete sentence that could stand alone
2. **Characteristics:** Observable features, not interpretations
3. **Identification Criteria:** Numbered, specific, verifiable conditions
4. **Context:** Market conditions where concept is relevant
5. **Trading Implication:** Direct, actionable insight
6. **Related Concepts:** Cross-references to build knowledge graph

### LLM Optimization Principles

- Use consistent terminology across all definitions
- Avoid ambiguous pronouns (specify what "it" refers to)
- Include both positive criteria (what IS) and negative (what is NOT)
- Keep definitions atomic - one concept per entry
- Use quantifiable terms when possible ("two or more" not "several")
- Structure for pattern matching (consistent section headers)

---

## Example Output

```markdown
## Break of Structure (BOS)

**Definition:** A Break of Structure occurs when price closes beyond a significant swing high (bullish BOS) or swing low (bearish BOS), confirming trend continuation.

**Characteristics:**
- Requires a candle CLOSE beyond the level, not just a wick
- Confirms the existing trend direction
- Creates a new swing point for future reference

**Identification Criteria:**
1. Identify the most recent significant swing high or swing low
2. Wait for a candle to CLOSE beyond that level
3. In an uptrend, BOS = close above prior swing high
4. In a downtrend, BOS = close below prior swing low

**Context:** Occurs in trending markets; validates continuation of the prevailing trend.

**Trading Implication:** BOS confirms trend strength; traders may look for entries on pullbacks after BOS.

**Related Concepts:** Change of Character (CHoCH), Market Structure, Swing Highs/Lows

---
```

---

## Workflow Summary

```
USER attaches screenshot(s) + transcript (required)
           │
           ▼
Step 1: AI analyzes images
           │
           ▼
Step 2: AI determines concepts.md path (same dir as transcript)
        AI locates transcript section
        "Is this the correct section?" ◄──────────┐
           │                                      │
           ├── USER: "No" ──► AI searches again ──┘
           │
           └── USER: "Yes"
                  │
                  ▼
Step 3: AI presents understanding (images + transcript context)
           │
           ▼
Step 4: AI asks "Is this correct?" ◄───────────┐
           │                                    │
           ├── USER: "No" / clarifies ──► AI revises
           │
           └── USER: "Yes"
                  │
                  ▼
Step 5: AI checks for existing concept in concepts.md
           │
           ├── Exists ──► Ask: Update/Replace/Skip/Rename
           │
           └── New ──► Add to concepts.md
```

---

## Notes

- One concept per command invocation (keeps definitions atomic)
- If user shows multiple concepts in screenshots, ask which to document first
- **Transcript + concepts.md are coupled** - They always live in the same directory
- **Never duplicate concepts** - Step 5 checks for existing concepts and offers Update/Replace/Skip/Rename options
- **Updates are supported** - Existing concepts can be enriched with new information from additional sources
