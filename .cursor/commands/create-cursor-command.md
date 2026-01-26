# Create Cursor Command

An interactive workflow for creating high-quality Cursor commands through guided conversation.

---

## Step 1: Gather Requirements

**Ask the user:**

> **Let's create a new Cursor command.**
>
> Please describe what this command should do. Include:
> - What is the command's purpose?
> - What steps should it perform?
> - How should it interact with you (prompts, confirmations, etc.)?
> - Any specific format or output requirements?
>
> Take your time - the more detail you provide, the better the command will be.

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

## Step 2: Define Command Name

**Ask the user in chat:**

> **What should this command be called?**
>
> The command name will be used as `@command-name` to invoke it.
> Use lowercase with hyphens (e.g., `qa-test-plan`, `pr-review`, `debug-issue`).

**Wait for response, then use AskQuestion to confirm:**

```
AskQuestion:
  title: "Confirm Command Name"
  questions:
    - id: "confirm_name"
      prompt: "Command will be created at: .cursor/commands/Testing/Ofer/[command-name].md"
      options:
        - id: "confirm"
          label: "Looks good, proceed"
        - id: "change"
          label: "I want a different name"
```

**If user selects "change":** Ask for new name in chat and confirm again.

---

## Step 3: Draft the Command

**Tell the user:**

> **Drafting the command based on your requirements...**

**Create the command following this structure:**

1. Title and one-line description
2. Prerequisites/Setup (if needed)
3. Core steps (numbered, clear actions)
4. User interaction points (with exact prompts)
5. Cleanup (if temporary changes are made)
6. Summary/Report (if applicable)

**Write the command file to `.cursor/commands/Testing/Ofer/[command-name].md`**

**Then present summary and use AskQuestion:**

> **Draft Complete**
>
> I've created the command at `.cursor/commands/Testing/Ofer/[command-name].md`
>
> Here's a summary of what it does:
> - Step 1: [brief description]
> - Step 2: [brief description]
> - ...

```
AskQuestion:
  title: "Draft Review"
  questions:
    - id: "draft_action"
      prompt: "What would you like to do next?"
      options:
        - id: "show"
          label: "Show me the full command"
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
> | 1 | [requirement] | Yes/No | Step X |
> | 2 | [requirement] | Yes/No | Step Y |
> | ... |
>
> **Status:** [X of Y requirements addressed]

**If any gaps:**

> **I found gaps in the following requirements:**
> - #X: [requirement] - [what's missing]
>
> Fixing now...

**Fix the gaps and update the command file.**

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

**Review the command for clarity issues and report:**

> **Clarity Review**
>
> I've reviewed the command for clarity. Here's what I found:
>
> | Issue | Location | Fix Applied |
> |-------|----------|-------------|
> | [issue description] | Step X | [what was changed] |
> | ... |
>
> **Changes made:**
> - [Before -> After summary]

**If no issues found:**

> **Clarity Review: No issues found.**
> The command uses clear language, scannable structure, and explicit user prompts.

**Update the command file with clarity improvements.**

**Then use AskQuestion:**

```
AskQuestion:
  title: "Clarity Review Complete"
  questions:
    - id: "clarity_action"
      prompt: "What would you like to do?"
      options:
        - id: "show"
          label: "Show me the updated command"
        - id: "continue"
          label: "Continue to final verification"
```

---

## Step 6: Final Verification

**Run through final checks:**

> **Final Verification Checklist**
>
> - [ ] All requirements addressed
> - [ ] No vague language ("if needed", "as appropriate")
> - [ ] Clear user interaction points with exact prompts
> - [ ] Failure/error paths defined
> - [ ] Cleanup step included (if temporary changes are made)
> - [ ] Scannable format (tables, whitespace, blockquotes)
> - [ ] No nested code blocks
> - [ ] Each step has actionable instructions

**Present the results:**

> **Final Verification Results**
>
> Passed: X checks
> Failed: X checks (fixing now...)

**Fix any remaining issues.**

---

## Step 7: Complete

**Confirm completion:**

> **Command Created Successfully**
>
> **Name:** `@[command-name]`
> **Location:** `.cursor/commands/Testing/Ofer/[command-name].md`
>
> **What it does:**
> [One-paragraph summary]
>
> **To use it:**
> Type `@[command-name]` in any Cursor chat.

```
AskQuestion:
  title: "Command Complete"
  questions:
    - id: "next_action"
      prompt: "What would you like to do next?"
      options:
        - id: "test"
          label: "Test the command now"
        - id: "edit"
          label: "Make additional edits"
        - id: "done"
          label: "I'm done"
```
