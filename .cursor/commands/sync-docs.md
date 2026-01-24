---
name: Sync Documentation
description: Audits the entire docs folder against the codebase and proposes updates, deletions, or consolidations
tags: [documentation, sync, maintenance, audit]
---

# Sync Documentation Command

## Purpose

This command performs a comprehensive audit of the `docs/` folder against the current state of the codebase. It identifies documentation that is outdated, no longer relevant, or could be consolidated, then executes approved changes.

**The codebase is the source of truth.**

---

## Excluded Folders

The following folders are **excluded from this audit**:

| Folder | Reason |
|--------|--------|
| `docs/Team/` | CT-level discussion protocol - not subject to code sync |

---

## Step 1: Scan Documentation Structure

**Action:** List all documentation files in `docs/` (excluding `docs/Team/`).

For each file, record:
- File path
- File size
- Last modified date (from git)
- Document type (PRD, strategy, guide, README, etc.)

**Present the inventory:**

```
📁 Documentation Inventory
==========================

docs/
├── commands.md (626 lines)
├── setup-guide.md
├── PRDs/
│   ├── README.md
│   ├── local_ai_integration.md
│   └── system_architecture.md (1044 lines)
└── strategies/
    ├── README.md
    ├── momentum-calculation-methods.md
    └── momentum-scalping-v1.md

Total: X files (excluding docs/Team/)
```

---

## Step 2: Analyze Codebase Architecture

**Action:** Build a comprehensive map of the current codebase.

### 2.1 Directory Structure
Scan and document (focus on `bot/` as the primary source):
- All packages/modules in `bot/`
- Entry points (`start.sh`, `dev.sh`, main scripts)
- Configuration files (`pyproject.toml`, `requirements.txt`, etc.)
- Test structure (`tests/`)

**Present the architecture map before proceeding:**

```
📁 Codebase Architecture
========================

bot/
├── ai/           # AI integration, signal brain, interpreters
├── backtest/     # Backtesting engine and models
├── core/         # Core models, config, analysis
├── historical/   # Historical data fetching
├── hyperliquid/  # Exchange integration
├── indicators/   # Technical indicators (ATR, MACD, RSI, etc.)
├── signals/      # Signal detection and aggregation
├── simulation/   # Paper trading, simulation
├── tuning/       # Parameter tuning
└── ui/           # Terminal UI dashboard

Entry Points: start.sh, dev.sh, run_backtest.py
Config: pyproject.toml, requirements.txt
Tests: tests/
```

### 2.2 Component Inventory
For each module, identify:
- Public classes and their purposes
- Key functions and interfaces
- Integration points (APIs, WebSockets, external services)
- Configuration patterns

### 2.3 Feature Status
Determine what's implemented vs. planned:
- Working features (have tests, are imported/used)
- Partial implementations (stub code, TODOs)
- Deprecated code (unused, commented out)

---

## Step 3: Cross-Reference Analysis

**Action:** For each documentation file, analyze relevance against codebase.

### Analysis Criteria

| Criterion | Check |
|-----------|-------|
| **References Valid Code** | Do file paths, class names, function names exist? |
| **Describes Current Behavior** | Does documented behavior match implementation? |
| **Complete Coverage** | Are there undocumented features/modules? |
| **No Orphaned Content** | Does doc reference removed/deprecated code? |
| **Structural Accuracy** | Do directory trees match actual structure? |

### For Each Document, Determine:

1. **KEEP** - Content is accurate and relevant
2. **UPDATE** - Content exists but is outdated
3. **DELETE** - Content references things that no longer exist
4. **CONSOLIDATE** - Content overlaps with another document

---

## Step 4: Generate Audit Report

Present findings in a structured report:

```markdown
# 📋 Documentation Audit Report

**Generated:** [timestamp]
**Scope:** docs/ (excluding docs/Team/)
**Files Analyzed:** X

---

## Summary

| Status | Count | Files |
|--------|-------|-------|
| ✅ Current | X | file1.md, file2.md |
| ⚠️ Needs Update | X | file3.md, file4.md |
| 🗑️ Delete Candidate | X | file5.md |
| 🔀 Consolidate | X | file6.md → file7.md |

---

## ⚠️ Documents Needing Updates

### docs/PRDs/system_architecture.md

**Issues Found:**

| Line(s) | Issue | Current | Actual |
|---------|-------|---------|--------|
| 45-60 | Directory structure outdated | Shows `bot/trading/` | Actually `bot/simulation/` |
| 120 | Missing module | - | `bot/signals/detectors/` exists |
| 340 | Dead reference | `bot/core/utils.py` | File doesn't exist |

**Recommended Actions:**
1. Update directory structure tree
2. Add documentation for new `signals/detectors/` module
3. Remove references to deleted files

---

### docs/strategies/momentum-scalping-v1.md

**Issues Found:**

| Line(s) | Issue | Current | Actual |
|---------|-------|---------|--------|
| 78 | Parameter changed | `threshold: 0.3` | Code uses `0.25` |
| 150-180 | Missing indicator | - | RSI detector added |

**Recommended Actions:**
1. Update parameter values
2. Document new RSI integration

---

## 🗑️ Deletion Candidates

### docs/old-feature.md (if exists)

**Reason:** References `bot/legacy/` module which was removed in commit abc123.

**Verification:** No imports or references to this feature exist in codebase.

---

## 🔀 Consolidation Candidates

### Merge: momentum-calculation-methods.md → momentum-scalping-v1.md

**Reason:**
- `momentum-calculation-methods.md` contains reference material used only by `momentum-scalping-v1.md`
- Content would be better as a section within the strategy doc

**Proposed Structure:**
```
momentum-scalping-v1.md
├── Overview
├── Strategy Logic
├── Calculation Methods (← merged from momentum-calculation-methods.md)
└── Configuration
```

---

## ✅ Current Documents (No Changes Needed)

- `docs/setup-guide.md` - All instructions verified
- `docs/commands.md` - Matches available commands

---

## 📝 Missing Documentation

| Component | Location | Suggested Doc |
|-----------|----------|---------------|
| Signal detectors | `bot/signals/detectors/` | Add to system_architecture.md |
| Backtest engine | `bot/backtest/engine.py` | New: docs/backtesting.md or section in PRD |
```

---

## Step 5: Request Approval

Before making changes, present options:

> **Documentation Audit Complete**
>
> **Proposed Changes:**
> - 📝 Update: X documents
> - 🗑️ Delete: X documents
> - 🔀 Consolidate: X documents
>
> **How would you like to proceed?**
>
> | Option | Description |
> |--------|-------------|
> | **1. Apply all** | Execute all proposed changes |
> | **2. Review each** | Step through each change for individual approval |
> | **3. Updates only** | Only apply updates, skip deletions/consolidations |
> | **4. Specific files** | Choose which files to process |
> | **5. Export report** | Save report to `.cursor/plans/docs-audit-[date].md` |
> | **6. Cancel** | No changes |

**Wait for explicit user confirmation before proceeding.**

---

## Step 6: Execute Approved Changes

### For Updates:

1. **Show the specific changes** before applying:
   - Display current text vs. proposed text
   - Include line numbers for context

2. **Apply edits** to fix each identified issue:
   - Update directory structure trees to match actual `bot/` layout
   - Fix file path references (e.g., `bot/trading/` → `bot/simulation/`)
   - Update parameter values to match code defaults
   - Add new sections for undocumented features
   - Remove references to deleted/renamed code

3. **Preserve document style:**
   - Match existing header levels and formatting
   - Keep consistent tone and voice
   - Maintain table formats where used

### For Deletions:

1. **Confirm deletion** one more time for each file
2. **Check for references** - warn if other docs link to this file
3. **Delete the file**
4. **Update any READMEs** that listed the deleted file

### For Consolidations:

1. **Show the merge plan** - what goes where
2. **Merge content** into target document
3. **Delete source document**
4. **Update cross-references** in other docs

---

## Step 7: Final Report

After executing changes:

```
✅ Documentation Sync Complete

📊 Changes Applied:
  ✏️  Updated: docs/PRDs/system_architecture.md
      - Fixed directory structure (lines 45-60)
      - Added signals/detectors documentation
      - Removed dead references

  ✏️  Updated: docs/strategies/momentum-scalping-v1.md
      - Updated threshold parameter
      - Added RSI detector section

  🗑️  Deleted: (none)

  🔀  Consolidated: (none)

📁 Documentation Status:
  - Total docs: X
  - Up to date: X (100%)

💡 Recommendations:
  - Consider adding dedicated backtesting documentation
  - Strategy docs could include more code examples
```

---

## Edge Cases

### Large-Scale Outdated Documentation
If >50% of docs need significant updates:
- Warn user about scope
- Suggest prioritizing critical docs (PRDs, setup guide)
- Offer to create a phased plan

### Ambiguous Deletions
If unsure whether content is still relevant:
- Mark as "Review Recommended" instead of "Delete"
- Ask user for clarification
- Never auto-delete without explicit confirmation

### Circular References
If consolidation would create circular references:
- Flag the issue
- Suggest alternative organization
- Let user decide structure

### New Features Without Docs
If code exists without documentation:
- List in "Missing Documentation" section
- Offer to generate stub documentation
- Prioritize by feature importance

---

## Usage

**Run full audit:**
```
@sync-docs
```

**The command will:**
1. Scan all docs (excluding Team/)
2. Analyze current codebase
3. Generate comparison report
4. Propose changes
5. Execute approved changes
