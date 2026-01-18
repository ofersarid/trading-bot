---
name: Sync Documentation
description: Updates a documentation file to match the current state of the codebase
tags: [documentation, sync, maintenance]
---

# Sync Documentation Command

## Purpose

This command analyzes the current state of the codebase and updates a specified documentation file to reflect the actual implementation. The codebase is the source of truth.

---

## Prerequisites Check

**Required Input:** A markdown file from the `docs/` folder.

**If no file is provided, STOP immediately and prompt:**
> ⚠️ **No documentation file specified.**
> 
> Please provide a markdown file from the `docs/` folder to update.
> 
> **Available documentation files:**
> ```
> docs/
> ├── PRDs/
> │   ├── local_ai_integration.md
> │   ├── README.md
> │   └── system_architecture.md
> ├── setup-guide.md
> └── strategies/
>     ├── momentum-scalping-v1.md
>     └── README.md
> ```
> 
> **Usage:** Run this command with a specific file, e.g., `@docs/PRDs/system_architecture.md`

---

## Sync Process

### Step 1: Identify Document Type

Based on the file path and content, determine what kind of documentation it is:

| Path Pattern | Document Type | Primary Sources |
|--------------|--------------|-----------------|
| `docs/PRDs/*.md` | Architecture/PRD | Entire codebase structure, actual implementations |
| `docs/setup-guide.md` | Setup Guide | `requirements.txt`, `.env.example`, startup scripts |
| `docs/strategies/*.md` | Strategy Docs | Strategy implementation files, config |

---

### Step 2: Analyze Codebase

Gather current state information based on document type:

#### For Architecture/PRD Documents:

1. **Directory Structure**
   - Scan `bot/` for actual modules and packages
   - Compare against documented structure
   - Note new directories, removed directories, renamed items

2. **Component Status**
   - Check which components exist and are implemented
   - Identify stub vs. complete implementations
   - Note dependencies between components

3. **Development Phase Progress**
   - Check completion status of documented phases
   - Mark completed items based on actual code presence
   - Identify work-in-progress items

4. **Configuration Files**
   - Scan for actual config patterns vs. documented
   - Check environment variable usage
   - Verify file paths mentioned exist

5. **External Integrations**
   - Verify API endpoints documented match code
   - Check authentication patterns
   - Validate WebSocket/REST usage

#### For Setup Guides:

1. **Dependencies**
   - Compare `requirements.txt` against documented dependencies
   - Check version numbers
   - Note new/removed dependencies

2. **Environment Variables**
   - Scan codebase for `os.environ`, `os.getenv` calls
   - Compare against documented env vars
   - Check `.env.example` if exists

3. **Startup Process**
   - Analyze `start.sh`, `dev.sh`, main entry points
   - Document actual startup commands
   - Check for script changes

#### For Strategy Documents:

1. **Implementation Files**
   - Check if strategy code exists
   - Compare parameters/settings with docs
   - Verify formulas and logic descriptions

---

### Step 3: Generate Discrepancy Report

Present findings before making changes:

```markdown
## 📋 Documentation Sync Report

**File:** [path/to/doc.md]
**Analyzed:** [timestamp]

### Summary
- **Sections Matching:** X
- **Sections Outdated:** Y
- **Sections Missing Info:** Z

---

### ❌ Discrepancies Found

#### Directory Structure
**Documented:**
\`\`\`
bot/
├── ai/
├── trading/  ← Does not exist
└── utils/
\`\`\`

**Actual:**
\`\`\`
bot/
├── ai/
├── simulation/  ← New, not documented
├── ui/          ← New, not documented
└── core/        ← New, not documented
\`\`\`

#### Development Phases
- **Phase 1:** Documented as partial → Actually complete
- **Phase 4:** Documented as pending → Work in progress

#### Configuration
- Missing documented file: `config/settings.py`
- Actual config location: `bot/core/config.py`

---

### ✅ Sections Verified (No Changes Needed)
- External API endpoints
- Security considerations
- Cost estimation
```

---

### Step 4: Propose Updates

For each discrepancy, show the proposed change:

```markdown
### Proposed Changes

#### 1. Update Directory Structure
**Current (lines 356-420):**
[Show current documented structure]

**Proposed:**
[Show corrected structure matching codebase]

#### 2. Update Development Phase Checklist
**Current:**
- [ ] Basic WebSocket connection

**Proposed:**
- [x] Basic WebSocket connection (implemented in `bot/hyperliquid/websocket_manager.py`)

#### 3. Add Missing Component
**Add new section for UI Dashboard:**
[Proposed content based on actual implementation]
```

---

### Step 5: Request Confirmation

Before making changes, ask:

> **Ready to update the documentation.**
> 
> Changes will affect:
> - X sections updated
> - Y new sections added
> - Z lines modified
> 
> **Options:**
> 1. **Apply all changes** - Update the entire document
> 2. **Review changes one-by-one** - Approve each section individually
> 3. **Apply specific sections** - Choose which sections to update
> 4. **Export diff only** - Show changes without applying
> 
> Which would you like?

---

### Step 6: Apply Updates

When updating the documentation:

1. **Preserve Style**
   - Match existing formatting (headers, tables, code blocks)
   - Keep consistent voice and tone
   - Maintain document structure

2. **Update Metadata**
   - Update "Last Updated" date if present
   - Bump version number if applicable
   - Update "Status" if relevant

3. **Add Context**
   - Include file paths where implementations live
   - Add code snippets from actual implementation when helpful
   - Link related documentation

4. **Track Changes**
   - Note what was updated at the bottom (if document has changelog)
   - Use clear commit messages

---

## Document-Specific Update Rules

### For `system_architecture.md`:

1. **Directory Structure Section**
   - Must exactly match actual `bot/` structure
   - Include "(coming soon)" for planned directories
   - Remove directories that no longer exist

2. **Development Phases**
   - Check off items that have implementations
   - Mark partial implementations with notes
   - Keep unchecked items that are truly pending

3. **Component Specifications**
   - Add new components that exist in code
   - Update interfaces based on actual method signatures
   - Remove components that were never built

4. **Code Examples**
   - Ensure class/function signatures match actual code
   - Update configuration examples from real config files

### For `setup-guide.md`:

1. **Installation Steps**
   - Verify each command works
   - Update package versions
   - Fix file paths

2. **Configuration**
   - Match actual env var names
   - Update default values
   - Add new required variables

### For `local_ai_integration.md`:

1. **AI Components**
   - Check actual prompt files exist
   - Verify model names and versions
   - Update API usage patterns

---

## Output Format

After syncing, provide:

### Confirmation
```
✅ Documentation updated successfully!

Updated: docs/PRDs/system_architecture.md
Version: 1.2 → 1.3
Last Updated: January 18, 2026
```

### Change Summary
```
📝 Changes Applied:
  ✏️  Updated directory structure (added simulation/, ui/, core/)
  ✏️  Marked Phase 1 as complete
  ✏️  Updated Phase 4 progress
  ➕  Added UI Dashboard component specification
  ➕  Added session state management section
  🗑️  Removed outdated trading/ directory reference
```

### Recommendations
```
💡 Recommendations:
  - Consider adding API examples for new endpoints
  - The simulation section could use more detail
  - Phase 5 (Testnet) is now unblocked
```

---

## Edge Cases

### Large Structural Changes
If >30% of the document needs rewriting:
- Warn the user about scope of changes
- Suggest creating a new version instead of updating
- Offer to backup original first

### Missing Implementations
If documentation describes components that don't exist:
- Mark them clearly as "Planned" or "Coming Soon"
- Or suggest removing them if abandoned

### Conflicting Information
If code contradicts documentation in significant ways:
- Ask user which is correct (docs or code)
- Don't assume code is always right for design decisions

---

## Example Usage

**Sync architecture documentation:**
```
@sync-docs @docs/PRDs/system_architecture.md
```

**Sync setup guide:**
```
@sync-docs @docs/setup-guide.md
```
