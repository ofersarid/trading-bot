# Create Cursor Rule

An interactive workflow for creating high-quality Cursor rules through guided conversation.

---

## Step 1: Gather Requirements

**Ask the user:**

> **Let's create a new Cursor rule.**
>
> Please describe what this rule should enforce or teach. Include:
> - What behavior or pattern should this rule guide?
> - When should this rule apply? (Always, or only for specific files?)
> - Any specific examples of good vs bad patterns?
>
> Take your time - the more detail you provide, the better the rule will be.

**Wait for the user's response.**

After receiving the description, **extract and present the requirements:**

> **I've extracted these requirements from your description:**
>
> | # | Requirement |
> |---|-------------|
> | 1 | [First requirement] |
> | 2 | [Second requirement] |
> | 3 | ... |

**Use the AskQuestion tool to confirm requirements:**

```
AskQuestion:
  title: "Requirements Confirmation"
  questions:
    - id: "confirm_requirements"
      prompt: "Did I capture all your requirements correctly?"
      options:
        - id: "yes"
          label: "Yes, all correct"
        - id: "add"
          label: "I need to add more requirements"
        - id: "change"
          label: "I need to change something"
```

**If user selects "add" or "change":** Ask them to describe what to add/change in chat, then re-present the updated requirements table and ask again.

**Keep iterating until user confirms "yes".**

---

## Step 2: Define Rule Scope and Name

**Use the AskQuestion tool to determine scope:**

```
AskQuestion:
  title: "Rule Scope"
  questions:
    - id: "scope"
      prompt: "When should this rule apply?"
      options:
        - id: "always"
          label: "Always apply to every conversation"
        - id: "file_specific"
          label: "Only when working with specific file types"
```

**If user selects "file_specific", ask in chat:**

> **Which file patterns should this rule apply to?**
>
> Examples:
> - `**/*.ts` - All TypeScript files
> - `**/*.tsx` - All React component files
> - `src/components/**/*.tsx` - Components in a specific folder
> - `**/*.test.ts` - All test files

**Wait for the file pattern response.**

**Then ask for the rule name in chat:**

> **What should this rule be called?**
>
> Use lowercase with hyphens (e.g., `typescript-error-handling`, `react-patterns`, `api-conventions`).
> The file will be created at `.cursor/rules/[rule-name].mdc`

**Wait for response, then use AskQuestion to confirm:**

```
AskQuestion:
  title: "Confirm Rule Configuration"
  questions:
    - id: "confirm_config"
      prompt: "Rule will be created at: .cursor/rules/[rule-name].mdc with [scope description]"
      options:
        - id: "confirm"
          label: "Looks good, proceed"
        - id: "change"
          label: "I want to change something"
```

**If user selects "change":** Ask what to change in chat and confirm again.

---

## Step 3: Draft the Rule

**Tell the user:**

> **Drafting the rule based on your requirements...**

**Create the rule following this structure:**

1. YAML frontmatter with:
   - `description`: Brief description of what the rule does
   - `globs`: File pattern (if file-specific)
   - `alwaysApply`: true/false
2. Title as H1
3. Concise explanation of the rule
4. Concrete examples showing good vs bad patterns (use ✅ and ❌)

**Rule quality guidelines:**
- Keep under 50 lines when possible
- One concern per rule
- Write like clear internal docs
- Include concrete examples

**Write the rule file to `.cursor/rules/[rule-name].mdc`**

**Then present summary and use AskQuestion:**

> **Draft Complete**
>
> I've created the rule at `.cursor/rules/[rule-name].mdc`
>
> **Configuration:**
> - Description: [description]
> - Scope: [Always Apply / File-specific: pattern]
>
> **Key points covered:**
> - [point 1]
> - [point 2]
> - ...

```
AskQuestion:
  title: "Draft Review"
  questions:
    - id: "draft_action"
      prompt: "What would you like to do next?"
      options:
        - id: "show"
          label: "Show me the full rule"
        - id: "continue"
          label: "Continue to verification"
```

---

## Step 4: Completeness Verification

**Present a requirements checklist:**

> **Completeness Check**
>
> Let's verify all your requirements are addressed:
>
> | # | Requirement | Addressed? | Where |
> |---|-------------|------------|-------|
> | 1 | [requirement] | Yes/No | [section] |
> | 2 | [requirement] | Yes/No | [section] |
> | ... |
>
> **Status:** [X of Y requirements addressed]

**If any gaps:**

> **I found gaps in the following requirements:**
> - #X: [requirement] - [what's missing]
>
> Fixing now...

**Fix the gaps and update the rule file.**

**Then use AskQuestion:**

> **All requirements now addressed.**

```
AskQuestion:
  title: "Completeness Verification"
  questions:
    - id: "completeness_action"
      prompt: "How would you like to proceed?"
      options:
        - id: "verify"
          label: "Re-check completeness"
        - id: "continue"
          label: "Continue to clarity review"
```

---

## Step 5: Clarity Review

**Review the rule for clarity issues and report:**

> **Clarity Review**
>
> I've reviewed the rule for clarity. Here's what I found:
>
> | Issue | Location | Fix Applied |
> |-------|----------|-------------|
> | [issue description] | [section] | [what was changed] |
> | ... |
>
> **Changes made:**
> - [Before -> After summary]

**If no issues found:**

> **Clarity Review: No issues found.**
> The rule uses clear language, scannable structure, and concrete examples.

**Update the rule file with clarity improvements.**

**Then use AskQuestion:**

```
AskQuestion:
  title: "Clarity Review Complete"
  questions:
    - id: "clarity_action"
      prompt: "What would you like to do?"
      options:
        - id: "show"
          label: "Show me the updated rule"
        - id: "continue"
          label: "Continue to final verification"
```

---

## Step 6: Final Verification

**Run through final checks:**

> **Final Verification Checklist**
>
> - [ ] All requirements addressed
> - [ ] Valid YAML frontmatter (description, globs/alwaysApply)
> - [ ] Rule is concise (under 50 lines preferred)
> - [ ] One concern per rule
> - [ ] Includes concrete examples with ✅ GOOD and ❌ BAD patterns
> - [ ] No vague language
> - [ ] File is `.mdc` format

**Present the results:**

> **Final Verification Results**
>
> Passed: X checks
> Failed: X checks (fixing now...)

**Fix any remaining issues.**

---

## Step 7: Complete

**Confirm completion:**

> **Rule Created Successfully**
>
> **Name:** `[rule-name]`
> **Location:** `.cursor/rules/[rule-name].mdc`
> **Scope:** [Always Apply / When working with: pattern]
>
> **What it enforces:**
> [One-paragraph summary]
>
> **How it works:**
> [Explanation of when Cursor will apply this rule]

```
AskQuestion:
  title: "Rule Complete"
  questions:
    - id: "next_action"
      prompt: "What would you like to do next?"
      options:
        - id: "test"
          label: "Test the rule by opening a matching file"
        - id: "edit"
          label: "Make additional edits"
        - id: "another"
          label: "Create another rule"
        - id: "done"
          label: "I'm done"
```
