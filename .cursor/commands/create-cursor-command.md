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
>
> **Did I capture everything correctly?**
> - Reply **"yes"** to continue
> - Reply **"add: [missing requirement]"** to add more
> - Reply **"change #X: [correction]"** to fix something

**Keep iterating until user confirms "yes".**

---

## Step 2: Define Command Name

**Ask the user:**

> **What should this command be called?**
>
> The command name will be used as `@command-name` to invoke it.
> Use lowercase with hyphens (e.g., `qa-test-plan`, `pr-review`, `debug-issue`).

**Wait for response, then confirm:**

> **Command will be created at:**
> `.cursor/commands/Testing/Ofer/[command-name].md`
>
> Reply **"yes"** to confirm or provide a different name.

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

**Then present it:**

> **Draft Complete**
>
> I've created the command at `.cursor/commands/Testing/Ofer/[command-name].md`
>
> Here's a summary of what it does:
> - Step 1: [brief description]
> - Step 2: [brief description]
> - ...
>
> Reply **"show"** to see the full command, or **"continue"** to proceed to verification.

---

## Step 4: Completeness Verification

**Present a requirements checklist:**

> **Completeness Check**
>
> Let's verify all your requirements are addressed:
>
> | # | Requirement | Addressed? | Where |
> |---|-------------|------------|-------|
> | 1 | [requirement] | ✅/❌ | Step X |
> | 2 | [requirement] | ✅/❌ | Step Y |
> | ... |
>
> **Status:** [X of Y requirements addressed]

**If any gaps (❌):**

> **I found gaps in the following requirements:**
> - #X: [requirement] - [what's missing]
>
> Fixing now...

**Fix the gaps and update the command file.**

**Then ask:**

> **All requirements now addressed.**
>
> Reply **"verify"** to re-check, or **"continue"** to proceed to clarity review.

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
> - [Before → After summary]

**If no issues found:**

> **Clarity Review: No issues found.**
> The command uses clear language, scannable structure, and explicit user prompts.

**Update the command file with clarity improvements.**

**Then ask:**

> Reply **"show"** to see the updated command, or **"continue"** to finalize.

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
> ✅ Passed: X checks
> ❌ Failed: X checks (fixing now...)

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
>
> **Want to test it now?** Open a new chat and try `@[command-name]`
