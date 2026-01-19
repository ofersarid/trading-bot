---
name: Make a Rule
description: Creates or updates a project rule based on patterns discovered during the current session
tags: [rules, meta, code-quality]
---

# Make a Rule

## Purpose

This command captures coding patterns, fixes, and improvements from the current session and converts them into reusable project rules. It ensures that lessons learned during development are codified for future reference and enforcement.

---

## Step 1: Analyze Session Context

Review the recent conversation to identify:

1. **What was being fixed or improved?**
   - Bug fixes that reveal missing guidelines
   - Refactoring patterns that should be standardized
   - Code smells that were addressed
   - Architectural decisions made

2. **What pattern emerged?**
   - A "do this, not that" situation
   - A threshold or limit (e.g., max lines, max complexity)
   - A structural requirement (e.g., where files should go)
   - A naming convention
   - An anti-pattern to avoid

3. **Why does this matter?**
   - Prevents future bugs
   - Improves readability
   - Maintains consistency
   - Reduces technical debt

**Output a summary:**
> **Pattern Detected:** [Brief description]
>
> **Context:** [What triggered this - the fix/improvement that was made]
>
> **Proposed Rule:** [One-sentence rule statement]

---

## Step 2: Check Existing Rules

Scan `.cursor/rules/` for existing rules that might cover this pattern:

1. **Read all `.mdc` files** in the rules directory
2. **Search for related keywords** from the detected pattern
3. **Categorize the match:**
   - **Exact match**: Rule already exists and covers this
   - **Partial match**: Existing rule could be extended
   - **No match**: New rule needed

**If exact match found:**
> "This pattern is already covered by `[rule-file].mdc` in the section about [topic]. No changes needed."
>
> *Show the relevant section from the existing rule.*

**If partial match found:**
> "Found related rule in `[rule-file].mdc`. Recommend updating the [section] to include this pattern."
>
> *Show the existing section and proposed addition.*

**If no match found:**
> "No existing rule covers this pattern. Recommend creating a new rule or adding a new section to `[most-relevant-file].mdc`."

---

## Step 3: Propose Rule Changes

Based on Step 2, propose one of:

### Option A: Update Existing Rule

Show the proposed diff:

```markdown
## [Existing Section Name]

### [New Subsection if needed]

[Existing content...]

+ ### [New Pattern Name]
+
+ [Description of what to do/not do]
+
+ ```python
+ # Good
+ [example of correct pattern]
+
+ # Bad
+ [example of incorrect pattern]
+ ```
```

### Option B: Create New Rule File

If the pattern doesn't fit existing rules, propose a new `.mdc` file:

```markdown
# [Rule Category Name]

## [Pattern Name]

[Description of what this rule enforces and why]

### Requirements

- [Requirement 1]
- [Requirement 2]

### Examples

```python
# Good
[correct example]

# Bad
[incorrect example]
```

### Rationale

[Why this matters - what problems it prevents]
```

---

## Step 4: Confirmation

Ask the user:

> **Proposed rule change:**
>
> - **Action:** [Create new / Update existing]
> - **File:** `[filename].mdc`
> - **Section:** [New section / Updated section name]
>
> **Preview:**
> [Show the exact content that will be added/changed]
>
> **Proceed?**
> 1. Yes, apply this change
> 2. Modify the proposed rule first
> 3. Skip - don't create a rule for this

**Wait for explicit confirmation before making changes.**

---

## Step 5: Apply Changes

If confirmed:

1. **Create or update the rule file** in `.cursor/rules/`
2. **Verify the file is valid** (proper markdown, no syntax errors)
3. **Check if `code-maintenance.md` needs updating**

---

## Step 6: Update Code Maintenance Command

After creating/updating a rule, check if the `code-maintenance.md` command needs to be updated:

**Check for:**
- Is the new rule file listed in Step 1 (Load Project Rules)?
- Are there new checklist items needed in Step 3 (Code Analysis)?
- Are there new report sections needed in Step 4?

**If updates needed, propose:**

```markdown
### From `[new-rule-file].mdc`:
- [ ] **[Check name]**: [Description of what to check]
- [ ] **[Check name]**: [Description of what to check]
```

**Ask for confirmation** before updating `code-maintenance.md`.

---

## Step 7: Summary

After all changes are applied:

> **Rule Created/Updated:**
> - File: `[filename].mdc`
> - Section: [section name]
> - Pattern: [brief description]
>
> **Code Maintenance Updated:** [Yes/No]
> - Added checks for: [list of new checks]
>
> **Next time you run `code-maintenance`, it will check for this pattern.**

---

## Rule Writing Guidelines

When writing rules, follow these principles:

### Be Specific
- Include concrete thresholds (e.g., "max 30 lines" not "keep methods short")
- Show real code examples, not abstract descriptions

### Be Actionable
- Rules should be checkable (can verify pass/fail)
- Include "what to do instead" for every "don't do this"

### Be Justified
- Explain WHY the rule exists
- Reference real problems it prevents

### Be Organized
- Group related rules in the same file
- Use consistent heading structure
- Include a table of contents for long files

---

## Example Session-to-Rule Flow

**Session context:**
> User was fixing a bug where WebSocket handlers were doing too much work, causing UI lag.

**Pattern detected:**
> WebSocket message handlers should be thin - just parse and delegate to specific handlers.

**Proposed rule addition to `python-coding-guidelines.mdc`:**

```markdown
### Async Patterns

#### WebSocket Handling
- Keep message handlers thin - parse and delegate
- Use `@work` decorator for long-running background tasks
- Don't mix sync and async without clear boundaries

```python
# Good: Thin handler that delegates
async def process_message(self, data: dict) -> None:
    channel = data.get("channel")
    handlers = {
        "allMids": self.handle_prices,
        "trades": self.handle_trades,
    }
    handler = handlers.get(channel)
    if handler:
        await handler(data)

# Bad: Fat handler doing everything
async def process_message(self, data: dict) -> None:
    if data.get("channel") == "allMids":
        # 50 lines of price processing...
    elif data.get("channel") == "trades":
        # 50 lines of trade processing...
```
```

---

## Notes

- Rules should be living documents - update them as patterns evolve
- Prefer extending existing rules over creating new files
- Keep rules focused - one file per major concern area
- Rules are for patterns, not one-off fixes
