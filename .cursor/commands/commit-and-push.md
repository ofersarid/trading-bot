# Commit and Push with Executive Summary

Create a git commit with a product-focused executive summary and push to remote.

## Instructions

When this command is triggered:

### 1. Gather Context

Run these commands in parallel to understand the changes:

```bash
git status
git diff --staged
git diff
git log -5 --oneline
git branch --show-current
```

### 2. Stage Changes (if needed)

If there are unstaged changes, ask the user which files to stage, or stage all with:
```bash
git add -A
```

**Never stage:** `rspack.config.js`, `.env` files, credentials, or secrets.

### 3. Analyze Changes

Review all staged changes and identify:
- **User impact**: How does this improve the user experience?
- **Business value**: What problem does this solve? What capability does it enable?
- **Product improvement**: What can users do now that they couldn't before?

### 4. Generate Executive Summary

Create a commit message with this structure:

```
<type>: <concise title> (max 50 chars)

## Executive Summary
<2-3 sentences for leadership explaining the PRODUCT improvement.
Focus on USER VALUE and BUSINESS IMPACT only.
No technical details, no implementation specifics, no code references.
Write as if explaining to a non-technical stakeholder.>

## Changes
- <bullet points of what improved from user/product perspective>
```

**Types:** `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `style`

### 5. Commit

Use a HEREDOC to preserve formatting:

```bash
git commit -m "$(cat <<'EOF'
<commit message here>
EOF
)"
```

### 6. Push

After successful commit, attempt to push:

```bash
git push -u origin HEAD
```

**If push fails with permission error** (e.g., "Permission denied to OferSarid-Reco"):

1. Check available GitHub accounts:
   ```bash
   gh auth status
   ```

2. Identify the repo owner from the remote URL:
   ```bash
   git remote get-url origin
   ```

3. Switch to the repo owner's account:
   ```bash
   gh auth switch --user <repo-owner-username>
   ```

4. Push again:
   ```bash
   git push -u origin HEAD
   ```

5. Switch back to the original account:
   ```bash
   gh auth switch --user OferSarid-Reco
   ```

### 7. Report

After completion, report:
- Commit hash (short)
- Branch name
- Remote URL for the commit (if available)

## Example Output

```
feat: Add price alerts for portfolio positions

## Executive Summary
Users can now set custom price thresholds on their holdings and receive
instant notifications when prices cross those levels. This addresses our
most requested feature and helps traders act on market movements faster.

## Changes
- Users can create, edit, and delete price alerts from their portfolio
- Notifications are delivered even when the app is closed
- Alert history shows which alerts triggered and when
```
