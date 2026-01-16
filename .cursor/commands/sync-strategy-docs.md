---
name: Sync Strategy Documentation
description: Syncs strategy_overview.md with the actual Pine Script strategy code, ensuring documentation matches implementation
tags: [documentation, strategy, pinescript, sync]
---

# Sync Strategy Documentation Command

## Purpose

This command analyzes a Pine Script strategy file and updates the `strategy_overview.md` documentation to match the actual implementation. The strategy script is treated as the source of truth and is NEVER modified.

---

## Prerequisites Check

Before syncing, verify the following files exist in the specified folder:

1. **Pine Script Strategy File** (`.pine` extension)
   - Should contain a `strategy()` declaration
   - Should be the main strategy implementation

2. **Strategy Overview File** (`strategy_overview.md`)
   - Markdown documentation file
   - Will be updated to match the script

**If any required files are missing, STOP and prompt the user:**
> "⚠️ Missing required files in the strategy folder. Expected structure:
> ```
> strategies/[strategy_name]/
>   ├── [strategy_name].pine      ← Strategy script (source of truth)
>   └── strategy_overview.md      ← Documentation (will be updated)
> ```
>
> Please specify a valid strategy folder path."

---

## Sync Process

### Step 1: Analyze Strategy Script

Extract the following information from the `.pine` file:

#### **A. Constants & Defaults**
Search for `const` declarations:
- `DEFAULT_RISK_REWARD`
- `DEFAULT_USE_*` (break-even, trailing stop, etc.)
- `DEFAULT_TRAIL_OFFSET_R`
- `DEFAULT_SWING_LENGTH`
- `DEFAULT_MIN_FVG_PCT`
- `DEFAULT_FVG_ENTRY_PCT`
- Grade thresholds (A+, A, B, C)
- Any other `const` values

#### **B. Input Settings**
Search for `input.float()`, `input.bool()`, `input.int()`:
- Risk percentages per grade
- Strategy toggles (trailing stop, session filter, etc.)
- Timeframe settings
- Visual settings
- Extract: setting name, default value, tooltip/description

#### **C. Position Sizing Logic**
Look for sections that calculate:
- Position percentage based on grade
- Position value calculation
- Position quantity formula
- Risk per grade mapping

#### **D. Entry Logic**
Identify:
- Minimum criteria checks
- Quality factor calculations
- Entry conditions
- FVG retrace logic
- Setup detection sequence

#### **E. Exit Logic**
Find:
- Stop loss calculation method
- Take profit calculation method
- Trailing stop logic (if present)
- Break-even logic (if present)
- Exit condition descriptions

#### **F. Risk Management Rules**
Extract from header comments:
- Stop loss rules
- Position management approach
- Trailing/break-even strategy
- Risk reward targets

---

### Step 2: Compare with Overview Documentation

Read `strategy_overview.md` and identify sections to update:

#### **Sections to Check:**

1. **"Position Sizing Strategy"**
   - Compare grade percentages table with script constants
   - Update if defaults changed

2. **"Key Settings"**
   - Compare settings table with actual `input.*()` declarations
   - Add new settings, update defaults, remove obsolete ones

3. **"Entry Logic"**
   - Verify step-by-step matches script implementation
   - Update if entry sequence changed

4. **"Stop Loss & Take Profit"**
   - Check formulas match actual calculations in script
   - Update buffer percentages, calculation methods

5. **"Break-Even Logic" or "Trailing Stop Logic"**
   - Determine which is implemented in script
   - Replace entire section if strategy changed
   - Update with current logic description

6. **"Risk Management Rules" or similar intro section**
   - Update rules list to match script comments
   - Sync numbered rules with actual implementation

7. **"Minimum Criteria"**
   - Verify criteria list matches script checks
   - Update order and descriptions

8. **"Quality Factors"**
   - Check if all 5 factors match script implementation
   - Update descriptions if logic changed

---

### Step 3: Generate Update Report

Before making changes, create a report showing:

```markdown
## 📋 Sync Report

### Files Analyzed
- **Strategy Script:** [path/to/file.pine]
- **Documentation:** [path/to/strategy_overview.md]

### Discrepancies Found

#### ❌ Position Sizing (Risk %)
**Overview Says:** A+ = 50%, A = 40%, B = 25%, C = 10%
**Script Has:** A+ = 80%, A = 70%, B = 60%, C = 50%
**Action:** Update table in "Position Sizing Strategy" section

#### ❌ Trailing Stop Settings
**Overview Says:** "Break-Even Logic" section with break-even after BOS
**Script Has:** Trailing stop logic with 2R trail offset
**Action:** Replace entire section with trailing stop documentation

#### ❌ Key Settings Table
**Overview Missing:** "Trail Offset (R)" setting
**Script Has:** trail_offset_r = 2.0
**Action:** Add new row to Key Settings table

#### ✅ Entry Logic
**Status:** Matches - no changes needed

### Summary
- **Sections to Update:** 3
- **New Settings to Add:** 1
- **Sections to Remove:** 0
- **Sections Matching:** 5
```

---

### Step 4: Update Documentation

Apply changes to `strategy_overview.md`:

#### **Update Guidelines:**

1. **Preserve Structure**
   - Keep existing section order
   - Maintain markdown formatting
   - Keep header levels consistent

2. **Update Content**
   - Replace outdated values with current ones
   - Add missing settings/features
   - Remove deprecated sections
   - Update examples to match current logic

3. **Maintain Clarity**
   - Keep explanations simple and clear
   - Use tables for structured data
   - Include examples where helpful
   - Preserve ASCII diagrams if still relevant

4. **Document Changes**
   - Note what was updated in each section
   - Preserve version-specific notes if present

---

## Specific Section Update Rules

### **Position Sizing Table Update**

If grade percentages changed:
```markdown
| Grade | Quality Factors | Position % | Example ($100 equity) |
|-------|-----------------|------------|----------------------|
| A+    | 5/5             | [from script] | $[calculate] position |
| A     | 4/5             | [from script] | $[calculate] position |
| B     | 3/5             | [from script] | $[calculate] position |
| C     | 2/5             | [from script] | $[calculate] position |
```

### **Key Settings Table Update**

Add/update rows based on script `input.*()` declarations:
```markdown
| Setting | Default | Purpose |
|---------|---------|---------|
| [Setting Name] | [Default from script] | [Tooltip or description] |
```

### **Trailing Stop vs Break-Even**

If script has `use_trailing_stop`:
```markdown
## Trailing Stop Logic

After first BOS confirms direction in your favor:
- **Trailing stop activates** automatically
- Stop loss trails price by a configurable offset (default: [from script]R)
  - **For longs:** Stop trails below the high by [offset]× initial risk
  - **For shorts:** Stop trails above the low by [offset]× initial risk
- Stop only moves in favorable direction (never against you)
- Locks in profits while giving the trade room to run
- Take profit target remains unchanged
```

If script has `use_break_even`:
```markdown
## Break-Even Logic

After first BOS confirms direction in your favor:
- Move stop loss to entry price
- Keep take profit target unchanged
```

### **Stop Loss & Take Profit Update**

Update formulas to match script calculations:
```markdown
| Direction | Stop Loss | Take Profit |
|-----------|-----------|-------------|
| **Long**  | [Formula from script] | Entry + (Risk × R:R ratio) |
| **Short** | [Formula from script] | Entry - (Risk × R:R ratio) |
```

---

## Output Format

After syncing, provide:

### **1. Confirmation Message**
```
✅ Strategy documentation synced successfully!

Updated: strategies/[name]/strategy_overview.md
Source: strategies/[name]/[name].pine
```

### **2. Change Summary**
```
📝 Changes Applied:
  ✏️  Updated Position Sizing percentages
  ✏️  Replaced Break-Even with Trailing Stop section
  ➕  Added Trail Offset setting to Key Settings
  ✅  Verified Entry Logic (no changes needed)
  ✅  Verified Quality Factors (no changes needed)
```

### **3. Recommendations**
```
💡 Recommendations:
  - Review the updated "Trailing Stop Logic" section
  - Consider adding examples for new trail offset values
  - No breaking changes detected
```

---

## Edge Cases to Handle

### **1. Multiple .pine files in folder**
- Ask user which file is the main strategy
- Or default to file with same name as folder

### **2. Overview has custom sections**
- Only update standard sections (listed above)
- Preserve custom sections untouched
- Note them in the report

### **3. Script uses non-standard structure**
- Extract what's available
- Note missing standard components
- Suggest standardization

### **4. Major structural changes**
- If >50% of overview needs rewriting
- Ask user if they want to proceed
- Offer to backup original overview

---

## Example Usage Flow

**User provides folder:**
```
strategies/choch_fvg_v1/
```

**Command execution:**
1. ✅ Finds `choch_fvg_strategy_v1.pine`
2. ✅ Finds `strategy_overview.md`
3. 🔍 Analyzes script for constants, inputs, logic
4. 📊 Compares with documentation
5. 📋 Shows discrepancy report
6. ⚠️  Asks: "Update documentation with these changes? (3 sections will be modified)"
7. ✅ User confirms
8. ✏️  Updates `strategy_overview.md`
9. ✅ Shows change summary

---

## Important Notes

- **NEVER modify the .pine strategy file** - it is the source of truth
- **Always backup** the overview before major changes (mention this to user)
- **Preserve user customizations** - only update standard sections
- **Validate markdown** after changes to ensure proper formatting
- **Test links and references** if overview has internal links

---

## Search Strategy

### **For Constants:**
```
grep pattern: "^const\\s+(float|int|bool|string)\\s+\\w+"
```

### **For Inputs:**
```
grep pattern: "input\\.(float|bool|int|string)\\("
```

### **For Position Sizing:**
```
look for: "risk_pct_", "position_pct", "grade"
```

### **For Exit Logic:**
```
look for: "strategy.exit", "use_break_even", "use_trailing_stop", "trailing"
```

### **For Quality Factors:**
```
look for: "quality_score", "GRADE_", comments about "factors"
```

---

## Validation Checklist

After updating, verify:
- [ ] All tables are properly formatted
- [ ] Code blocks have correct syntax highlighting
- [ ] Numbers and percentages are consistent
- [ ] Examples calculate correctly
- [ ] Section headers use proper levels
- [ ] Links (if any) still work
- [ ] ASCII diagrams (if any) are intact
- [ ] File ends with proper newline
