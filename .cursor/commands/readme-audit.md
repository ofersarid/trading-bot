# README Audit

Scan all folders in the repository, audit README.md files against actual implementations, and update any that are outdated or inaccurate.

---

## Phase 1: Discovery

**Find all README.md files in the repository:**

1. Use the Glob tool with pattern `**/README.md`
2. For each README found, record:
   - Full path
   - Parent folder path

**Present discovery results:**

> **README Discovery Complete**
>
> Found X README.md files across the repository:
>
> | # | Path | Folder |
> |---|------|--------|
> | 1 | src/fixer/README.md | src/fixer/ |
> | 2 | ... | ... |

---

## Phase 2: Audit Each README

**For each README.md file, perform these checks:**

### Step 2.1: Read the README content

Read the full content of the README.md file.

### Step 2.2: Analyze the folder contents

1. Use the LS tool to list all files in the same folder as the README
2. For each code file (.ts, .tsx, .js, .jsx, .py, etc.):
   - Use the Read tool to read the file content
   - Use the Grep tool with pattern `^export` to identify exported functions, classes, types, and constants
   - Note the file's primary purpose based on its content
3. Use the LS tool to identify any subfolders

### Step 2.3: Compare README against implementation

Check for these discrepancies:

| Check | Description |
|-------|-------------|
| **File List Accuracy** | Does the README list files that exist? Are any files missing from the list? |
| **Export Accuracy** | Are documented exports still present in the code? Are new exports undocumented? |
| **Purpose Accuracy** | Does the README's description match what the code actually does? |
| **Architecture Accuracy** | Do any diagrams or flow descriptions match current implementation? |
| **Example Accuracy** | Do code examples use correct function signatures and imports? |
| **Subfolder Coverage** | Are subfolders mentioned if they exist? |

### Step 2.4: Assign audit status

For each README, assign one of these statuses:

| Status | Meaning |
|--------|---------|
| ✅ **Current** | README accurately describes implementation |
| ⚠️ **Minor Updates** | Small inaccuracies (typos, minor missing details) |
| 🔄 **Needs Update** | Significant sections outdated or missing |
| ❌ **Major Rewrite** | README substantially misrepresents implementation |

---

## Phase 3: Present Audit Report

**After auditing ALL README files, present the complete report:**

> **README Audit Report**
>
> **Summary:**
> - ✅ Current: X files
> - ⚠️ Minor Updates: X files
> - 🔄 Needs Update: X files
> - ❌ Major Rewrite: X files
>
> ---
>
> **Detailed Findings:**
>
> ### 1. `src/fixer/README.md` - 🔄 Needs Update
>
> **Issues Found:**
> - [ ] Missing documentation for `newFunction()` added in recent commits
> - [ ] File list shows `old-file.ts` which was deleted
> - [ ] Architecture diagram doesn't show new validation step
>
> **Suggested Changes:**
> - Add section documenting `newFunction()` with signature and purpose
> - Remove `old-file.ts` from file list
> - Update architecture diagram to include validation step
>
> ---
>
> ### 2. `src/lens/README.md` - ✅ Current
>
> No issues found.
>
> ---
>
> (Continue for all README files...)

**Ask for confirmation before proceeding:**

> **Ready to implement updates?**
>
> I found X README files that need updates.
> Would you like to proceed with implementing the changes?

Use AskQuestion tool with these exact parameters:

```
title: "Proceed with Updates"
questions:
  - id: "update_action"
    prompt: "How would you like to proceed with the README updates?"
    options:
      - id: "update_all"
        label: "Yes, update all files that need changes"
      - id: "review"
        label: "Let me review the report first"
      - id: "select"
        label: "Update specific files only (I'll tell you which)"
      - id: "cancel"
        label: "Cancel - don't make any changes"
```

**Based on user selection:**
- **update_all**: Proceed to Phase 4 with all flagged files
- **review**: Wait for user to review, then ask again
- **select**: Ask user which files to update, then proceed with only those
- **cancel**: End the audit without making changes

---

## Phase 4: Implement Updates

**If user approves updates:**

### Step 4.1: Create update checklist

Convert all issues into a numbered checklist:

> **Update Checklist**
>
> | # | File | Issue | Status |
> |---|------|-------|--------|
> | 1 | src/fixer/README.md | Add newFunction() docs | ⏳ Pending |
> | 2 | src/fixer/README.md | Remove old-file.ts | ⏳ Pending |
> | 3 | src/lens/README.md | Update diagram | ⏳ Pending |
> | ... | ... | ... | ... |

### Step 4.2: Process updates sequentially

For each update:

1. **Announce** which update is being implemented:
   > Implementing update #1: Adding documentation for `newFunction()` in `src/fixer/README.md`

2. **Read** the current README content

3. **Read** the relevant source files to understand the implementation

4. **Edit** the README with accurate, implementation-matching content

5. **Mark complete** and move to next:
   > ✅ Update #1 complete. Moving to #2...

### Step 4.3: Handle edge cases

**If a README needs major rewrite:**
- Present a proposed structure before writing
- Ask for confirmation on the approach
- Implement section by section

**If source code is ambiguous:**
- Note the ambiguity in the README
- Add a TODO comment for human review
- Continue with next update

---

## Phase 5: Summary Report

**After all updates are complete, present final summary:**

> **README Audit Complete**
>
> **Updates Applied:**
> - X README files updated
> - Y individual changes made
>
> **Files Modified:**
> | File | Changes |
> |------|---------|
> | src/fixer/README.md | Added 2 sections, updated 1 diagram |
> | src/lens/README.md | Fixed file list |
> | ... | ... |
>
> **Remaining TODOs:**
> - [ ] `src/complex/README.md` line 45: Needs human review of algorithm description
>
> **Next Steps:**
> - Review the changes in your IDE
> - Run any documentation linters if configured
> - Commit the changes when satisfied

---

## Verification Checklist

Before marking the audit complete, verify:

- [ ] All folders with 2+ files have a README.md (or note why not)
- [ ] All README file lists match actual files
- [ ] All documented exports exist in source code
- [ ] All code examples use correct current syntax
- [ ] All architecture diagrams reflect current flow
- [ ] No placeholder text like "TODO" or "TBD" remains (unless intentional)
