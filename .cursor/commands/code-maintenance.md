---
name: Code Maintenance Review
description: Reviews codebase against project rules for cleanliness, health, and readability improvements
tags: [maintenance, code-quality, refactoring]
---

# Code Maintenance Review

## Purpose

This command performs a thorough code review focused on **maintaining a clean, healthy, and readable codebase**. It does NOT focus on bug detection (use Cursor's bug bot for that). Instead, it analyzes code against the project's established rules and patterns to identify:

- Code organization issues
- Structural improvements
- Readability enhancements
- Pattern compliance
- Technical debt

---

## Step 1: Load Project Rules

Read all rule files from `.cursor/rules/` directory:

1. **Scan the rules directory** for all `.mdc` files
2. **Parse each rule file** and extract:
   - Rule name/title
   - Key requirements and constraints
   - Code patterns (good vs bad examples)
   - Thresholds and limits (e.g., max file size, max method length)

**Rules to load:**
- `python-coding-guidelines.mdc` - File size limits, type hints, constants, docstrings
- `textual-ui-patterns.mdc` - App structure, reactive state, component patterns
- `dashboard-refactoring-plan.mdc` - Specific refactoring guidance for dashboard.py
- Any other `.mdc` files present

---

## Step 2: Scope Selection

Ask the user to specify the scope of the review:

> **What would you like to review?**
> 
> 1. **Full codebase** - Review all Python files in `bot/`
> 2. **Specific directory** - e.g., `bot/ui/`, `bot/core/`
> 3. **Specific file** - e.g., `bot/ui/dashboard.py`
> 4. **Changed files only** - Files modified according to `git status`

If no response is given, default to **option 4 (changed files only)**.

---

## Step 3: Code Analysis

For each file in scope, analyze against ALL loaded rules. Check for:

### From `python-coding-guidelines.mdc`:
- [ ] **File size**: Is file > 300 lines (excluding imports/docstrings)?
- [ ] **Method length**: Are any methods > 30 lines?
- [ ] **Type hints**: Do all functions have parameter and return type hints?
- [ ] **Magic numbers**: Are there unexplained numeric literals in logic?
- [ ] **CSS embedding**: Is there CSS embedded as Python strings?
- [ ] **Module docstrings**: Does each file have a module-level docstring?
- [ ] **Error handling**: Are there bare `except:` or silenced errors?
- [ ] **Async patterns**: Are WebSocket handlers thin and delegating?

### From `textual-ui-patterns.mdc`:
- [ ] **App class size**: Is the App class doing too much?
- [ ] **Reactive state**: Are reactive properties used appropriately?
- [ ] **Component communication**: Props at construction, messages for updates?
- [ ] **Update patterns**: Batch updates used? Throttling for high-frequency data?
- [ ] **CSS classes for state**: Using classes vs inline style changes?

### From `dashboard-refactoring-plan.mdc`:
- [ ] **Embedded CSS progress**: Has CSS been extracted to `theme.css`?
- [ ] **Data models extracted**: Are dataclasses in `core/models.py`?
- [ ] **Business logic separation**: Analysis code in `core/` vs `ui/`?
- [ ] **Component extraction**: Are UI panels in separate files?

### General Code Health:
- [ ] **Import organization**: Standard lib → third-party → local?
- [ ] **Dead code**: Unused imports, functions, or variables?
- [ ] **Naming conventions**: snake_case for functions/variables, PascalCase for classes?
- [ ] **Code duplication**: Similar logic repeated in multiple places?
- [ ] **Complexity**: Deeply nested conditionals or loops?

---

## Step 4: Generate Report

Present findings organized by the **rule that triggered them**:

### Report Format

```
# Code Maintenance Report
Generated: [date/time]
Scope: [what was reviewed]

## Summary
- Total files reviewed: X
- Files with issues: Y
- Total issues found: Z

---

## 📋 python-coding-guidelines.mdc

### File Size Violations (Max: 300 lines)

| File | Lines | Over By | Suggested Action |
|------|-------|---------|------------------|
| `bot/ui/dashboard.py` | 1195 | 895 | Extract CSS, models, analysis logic |

### Method Length Violations (Max: 30 lines)

| File | Method | Lines | Suggested Action |
|------|--------|-------|------------------|
| `bot/ui/dashboard.py` | `analyze_opportunity` | 45 | Extract helper methods |

### Missing Type Hints

| File | Function | Missing |
|------|----------|---------|
| `bot/core/utils.py` | `process_data` | Return type |

### Magic Numbers

| File | Line | Value | Context |
|------|------|-------|---------|
| `bot/ui/dashboard.py` | 234 | `0.3` | momentum threshold |

---

## 📋 textual-ui-patterns.mdc

### App Class Bloat

| Issue | Current State | Recommended |
|-------|---------------|-------------|
| `TradingDashboard` | 800+ lines | < 200 lines |

### Missing Reactive Properties

| File | Property | Recommendation |
|------|----------|----------------|
| `dashboard.py` | `balance` | Convert to `reactive()` |

---

## 📋 dashboard-refactoring-plan.mdc

### Extraction Progress

| Item | Status | Action Needed |
|------|--------|---------------|
| CSS to theme.css | ⚠️ Partial | Move remaining embedded CSS |
| Data models | ❌ Not started | Create `core/models.py` |
| Analysis logic | ❌ Not started | Create `core/analysis/` |

---

## 📋 General Code Health

### Dead Code
- `bot/utils.py:45` - Unused import `json`
- `bot/core/helpers.py:120` - Function `old_calc` never called

### Naming Issues
- `bot/ui/dashboard.py:78` - Variable `x` should be descriptive

### Code Duplication
- Momentum calculation duplicated in 3 locations
```

---

## Step 5: Prioritization

Categorize findings by effort/impact:

### 🟢 Quick Wins (< 5 min each)
- Add missing type hints
- Remove unused imports
- Fix naming issues
- Add module docstrings

### 🟡 Medium Effort (15-30 min each)
- Extract magic numbers to constants
- Split long methods into helpers
- Add error handling improvements

### 🔴 Larger Refactors (1+ hour each)
- Extract CSS to separate file
- Move data models to `core/models.py`
- Extract UI components
- Separate business logic from UI

---

## Step 6: Confirmation & Action

After presenting the report, ask:

> **How would you like to proceed?**
> 
> 1. **Fix Quick Wins** - Apply all green-category fixes automatically
> 2. **Fix specific category** - Choose which rule violations to address
> 3. **Fix specific file** - Focus on one file at a time
> 4. **Generate detailed plan** - Create a step-by-step refactoring plan
> 5. **Export report** - Save report to `.cursor/plans/code-maintenance-[date].md`
> 6. **Skip for now** - Review only, no changes

**Important:** Wait for explicit user confirmation before making ANY code changes.

---

## Step 7: Apply Fixes (If Confirmed)

When applying fixes:

1. **Show each change** before applying
2. **Group related changes** - e.g., all type hint additions together
3. **Test after each group** - Ensure code still runs
4. **Track progress** - Update the report as fixes are applied
5. **Create meaningful commits** - One commit per category of fixes

### Commit Message Format
```
refactor(<rule>): <brief description>

Applied code maintenance fixes for <rule-name>:
- <specific fix 1>
- <specific fix 2>
```

---

## Notes

- **Non-destructive**: This review doesn't change code without confirmation
- **Incremental**: Large refactors should be done in small, testable steps
- **Evidence-based**: All suggestions reference specific rules and line numbers
- **Collaborative**: User decides what to fix and when

---

## Example Usage

**Full review:**
> Run `code-maintenance` on the entire codebase

**Targeted review:**
> Run `code-maintenance` on `bot/ui/dashboard.py` only

**Pre-commit check:**
> Run `code-maintenance` on changed files before committing
