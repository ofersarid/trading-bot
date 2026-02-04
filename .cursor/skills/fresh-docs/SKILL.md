---
name: fresh-docs
description: Review and update markdown documentation to ensure it matches the current codebase. Use when the user asks to review docs, check documentation freshness, verify READMEs are accurate, or after making code changes that might affect documentation.
---

# Fresh Docs Review

Systematically review all markdown documentation files to ensure they match the current codebase.

## Quick Start

1. Run the fresh-docs script to list all markdown files:

```bash
bash scripts/fresh-docs.sh
```

2. Review each file using the verification checklist below
3. Update files that are out of sync with the code

## Verification Checklist

For each markdown file, verify:

**Structure & Navigation**
- [ ] File still serves its original purpose
- [ ] Folder structure accurately described (if applicable)
- [ ] All file paths correct
- [ ] All internal links work

**Content Accuracy**
- [ ] Descriptions match actual code/implementation
- [ ] Tools and technologies listed are still in use
- [ ] No references to old/removed features

**Completeness**
- [ ] New features/files documented
- [ ] Removed features deleted from documentation
- [ ] Examples still valid

## Review Workflow

### 1. Initial Scan
- Run `bash scripts/fresh-docs.sh` to see all files
- Note which files were recently modified vs. old

### 2. Systematic Review
For each file:
- Read the full content
- Use Glob/Grep to verify current code structure matches documentation
- Compare documented vs. actual implementation
- Determine if updates are needed

### 3. Update Decisions

**Update if:**
- Project structure changed (new/removed files or folders)
- Tools or technologies added/removed/updated
- Feature descriptions inaccurate
- Links broken
- Examples outdated

**Keep if:**
- Content accurately reflects current state
- All paths and references valid

**Remove if:**
- Refers to deleted features or files
- Completely obsolete

### 4. Implementation

When updating:
1. Update file content to be accurate
2. Update folder README.md if that folder's contents changed
3. Update links in other files if paths changed
4. Keep consistent formatting
5. Document changes in commit message

## Files to Review

### Root Level
- **README.md** - Main project documentation with architecture and project structure

### Folder Documentation
Each folder should have a README.md:
- `docs/README.md`
- `prompts/README.md`
- `.claude/README.md`

### Detailed Documentation
- **docs/architecture.md** - Technical deep dive (less frequently updated)

## Special Considerations

### Architecture.md
- Less frequently updated (architectural changes are rarer)
- Examples can become outdated quickly
- Performance metrics may need verification

### README.md Files
- Updated frequently as code evolves
- Must always reflect current folder contents
- Should be concise but complete

### Prompt Files
- Actual working prompts used in production
- Changes affect n8n workflow behavior
- Updates should be synchronized with workflow changes

## Quick Git Commands

```bash
# Files modified recently
git log --oneline docs/ prompts/ README.md

# What code changed that might affect docs
git diff HEAD~1 --stat

# All markdown files
find . -type d -name ".*" -prune -o -type f -name "*.md" -print
```

## Key Question

For each file ask: "If a new developer read this, would they understand the project correctly?"
