# Kill the Dead

Scans the codebase for discrepancies, dead code, and unused imports. Groups findings by category and prompts for fixes.

---

## Step 1: Initialize Task Tracking

Create a todo list to track progress through each scan category:

```
TodoWrite:
  merge: false
  todos:
    - id: "readme-scan"
      content: "Scan README.md files vs actual code structure"
      status: "in_progress"
    - id: "dead-code-scan"
      content: "Find unused exports and dead code"
      status: "pending"
    - id: "unused-imports-scan"
      content: "Find unused imports"
      status: "pending"
```

---

## Step 2: README Discrepancy Scan

**Mark task as in_progress (already done in Step 1)**

### 2.1 Find All README Files

Search for all `README.md` files in the workspace.

### 2.2 For Each README, Check:

1. **File references** - Do files mentioned in the README actually exist?
2. **Export references** - Do exported functions/classes mentioned still exist?
3. **Structure accuracy** - Does the documented folder structure match reality?
4. **Code examples** - Do import paths in examples resolve correctly?

### 2.3 Compile README Discrepancies

Create a table of findings:

> **README Discrepancies Found**
>
> | README Location | Issue Type | Description |
> |-----------------|------------|-------------|
> | [path] | Missing file | References `foo.ts` which doesn't exist |
> | [path] | Wrong export | Documents `exportName` but it's not exported |
> | [path] | Outdated structure | Lists folder `X/` but it was renamed to `Y/` |

**If no discrepancies found:** Report "No README discrepancies found" and skip to Step 3.

### 2.4 Ask User About README Fixes

```
AskQuestion:
  title: "README Discrepancies"
  questions:
    - id: "fix_readme"
      prompt: "[X] README discrepancies found. How would you like to proceed?"
      options:
        - id: "fix_all"
          label: "Fix all README discrepancies"
        - id: "review"
          label: "Show me each one before fixing"
        - id: "skip"
          label: "Skip README fixes for now"
```

**If "fix_all":** Update all README files to match current code structure.

**If "review":** Present each discrepancy one at a time with AskQuestion for fix/skip.

**If "skip":** Continue to next category.

### 2.5 Update Todo

```
TodoWrite:
  merge: true
  todos:
    - id: "readme-scan"
      status: "completed"
    - id: "dead-code-scan"
      status: "in_progress"
```

---

## Step 3: Dead Code Scan

### 3.1 Run Knip Analysis

Check if `knip` is configured in the project. If available, run:

```bash
npx knip --reporter json
```

If knip is not available, perform manual analysis:
- Search for exported functions/classes/constants
- Check if they're imported anywhere else in the codebase
- Identify exports only used internally within the same file

### 3.2 Categorize Dead Code

Group findings:

> **Dead Code Found**
>
> | Category | File | Export | Last Modified |
> |----------|------|--------|---------------|
> | Unused export | src/utils.ts | `helperFn` | 30 days ago |
> | Unused file | src/old-feature.ts | (entire file) | 90 days ago |
> | Internal only | src/api.ts | `internalHelper` | 7 days ago |

**If no dead code found:** Report "No dead code found" and skip to Step 4.

### 3.3 Ask User About Dead Code

```
AskQuestion:
  title: "Dead Code Found"
  questions:
    - id: "fix_dead_code"
      prompt: "[X] dead code items found. How would you like to proceed?"
      options:
        - id: "remove_all"
          label: "Remove all dead code"
        - id: "remove_safe"
          label: "Remove only clearly unused items (skip internal-only)"
        - id: "review"
          label: "Review each item individually"
        - id: "skip"
          label: "Skip dead code removal for now"
```

**If "remove_all":** Remove all identified dead code.

**If "remove_safe":** Remove only exports with zero references (skip internal-only helpers).

**If "review":** Present each item with context and ask fix/skip.

**If "skip":** Continue to next category.

### 3.4 Update Todo

```
TodoWrite:
  merge: true
  todos:
    - id: "dead-code-scan"
      status: "completed"
    - id: "unused-imports-scan"
      status: "in_progress"
```

---

## Step 4: Unused Imports Scan

### 4.1 Find Unused Imports

Scan TypeScript/JavaScript files for:
- Imported modules never referenced in the file
- Type imports where the type is never used
- Namespace imports where no member is accessed
- Side-effect imports that may be unnecessary

### 4.2 Compile Import Issues

> **Unused Imports Found**
>
> | File | Unused Import | Type |
> |------|---------------|------|
> | src/component.tsx | `{ useState }` | Named import |
> | src/utils.ts | `import * as _ from 'lodash'` | Namespace import |
> | src/api.ts | `import type { User }` | Type import |

**If no unused imports found:** Report "No unused imports found" and skip to Step 5.

### 4.3 Ask User About Import Cleanup

```
AskQuestion:
  title: "Unused Imports Found"
  questions:
    - id: "fix_imports"
      prompt: "[X] unused imports found. How would you like to proceed?"
      options:
        - id: "remove_all"
          label: "Remove all unused imports"
        - id: "review"
          label: "Review files with most unused imports first"
        - id: "skip"
          label: "Skip import cleanup for now"
```

**If "remove_all":** Remove all unused imports from all files.

**If "review":** Sort files by count of unused imports, present each file's imports for review.

**If "skip":** Continue to summary.

### 4.4 Update Todo

```
TodoWrite:
  merge: true
  todos:
    - id: "unused-imports-scan"
      status: "completed"
```

---

## Step 5: Summary Report

Present final summary:

> **Kill the Dead Complete**
>
> | Category | Found | Fixed | Skipped |
> |----------|-------|-------|---------|
> | README discrepancies | X | X | X |
> | Dead code | X | X | X |
> | Unused imports | X | X | X |
>
> **Total:** X issues found, X fixed, X skipped

**If any items were skipped:**

> **Skipped items saved for later review.**
> Run `@kill-the-dead` again to revisit skipped items.

```
AskQuestion:
  title: "Scan Complete"
  questions:
    - id: "next_action"
      prompt: "What would you like to do next?"
      options:
        - id: "commit"
          label: "Commit the cleanup changes"
        - id: "review"
          label: "Review the changes before committing"
        - id: "done"
          label: "I'm done"
```

**If "commit":** Create a commit with message: "chore: cleanup dead code and unused imports"

**If "review":** Run `git diff` and show summary of changes.
