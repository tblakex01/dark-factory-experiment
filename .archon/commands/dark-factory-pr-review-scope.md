---
description: Dark Factory wrapper for archon-pr-review-scope that uses the deterministically captured PR number instead of $ARGUMENTS (which contains the issue number, not the PR number).
argument-hint: (receives $capture-pr-number.output as the PR number)
---

# PR Review Scope

**CRITICAL: The PR number for this review is #$capture-pr-number.output.**

Do NOT use $ARGUMENTS — that is the GitHub issue number, not the PR number.
The correct PR number has been deterministically captured and is: **#$capture-pr-number.output**

You can verify this by checking the file at `$ARTIFACTS_DIR/.pr-number`.

Now follow the full archon-pr-review-scope procedure below, but use PR **#$capture-pr-number.output** everywhere.

---

**Input**: #$capture-pr-number.output

---

## Your Mission

Verify the PR is in a reviewable state, gather all context needed for the parallel review agents, and prepare the artifacts directory structure.

---

## Phase 1: IDENTIFY - Determine PR

### 1.1 Get PR Number

The PR number is **$capture-pr-number.output**. Use this value directly.

```bash
PR_NUMBER=$capture-pr-number.output
echo "$PR_NUMBER" > $ARTIFACTS_DIR/.pr-number
```

### 1.2 Fetch PR Details

```bash
gh pr view $capture-pr-number.output --json number,title,body,url,headRefName,baseRefName,files,additions,deletions,changedFiles,state,author,isDraft,mergeable,mergeStateStatus
```

**Extract:**
- PR number and title
- Branch names (head -> base)
- Changed files list
- Addition/deletion counts
- Draft status
- Mergeable status

---

## Phase 2: VERIFY - Pre-Review Checks

### 2.1 Check for Merge Conflicts

```bash
gh pr view $capture-pr-number.output --json mergeable,mergeStateStatus --jq '.mergeable, .mergeStateStatus'
```

If conflicts exist, stop and report. Otherwise continue.

### 2.2 Check CI Status

```bash
gh pr checks $capture-pr-number.output --json name,state,conclusion --jq '.[] | "\(.name): \(.state) (\(.conclusion // "pending"))"'
```

### 2.3 Check Behind Base

```bash
PR_BASE=$(gh pr view $capture-pr-number.output --json baseRefName --jq '.baseRefName')
PR_HEAD=$(gh pr view $capture-pr-number.output --json headRefName --jq '.headRefName')
git fetch origin $PR_BASE --quiet
git fetch origin $PR_HEAD --quiet
BEHIND=$(git rev-list --count origin/$PR_HEAD..origin/$PR_BASE 2>/dev/null || echo "0")
```

### 2.4 Check Draft Status and PR Size

```bash
gh pr view $capture-pr-number.output --json isDraft,additions,deletions,changedFiles
```

---

## Phase 3: CONTEXT - Gather Review Context

### 3.1 Get Full Diff

```bash
gh pr diff $capture-pr-number.output
```

### 3.2 List Changed Files

```bash
gh pr view $capture-pr-number.output --json files --jq '.files[].path'
```

### 3.3 Check for CLAUDE.md and Workflow Artifacts

```bash
cat CLAUDE.md 2>/dev/null | head -100
ls -t $ARTIFACTS_DIR/../runs/*/plan-context.md 2>/dev/null | head -1
ls -t $ARTIFACTS_DIR/../runs/*/investigation.md 2>/dev/null | head -1
```

### 3.4 Identify New Abstractions

```bash
gh pr diff $capture-pr-number.output | grep "^+" | sed 's/^+//' | grep -E "(^interface |^export interface |^type |^abstract class |^export class )" | head -20
```

---

## Phase 4: PREPARE - Create Artifacts and Scope Manifest

```bash
mkdir -p $ARTIFACTS_DIR/review
```

Write `$ARTIFACTS_DIR/review/scope.md` with:
- PR title, URL, branch info
- Pre-review status table (conflicts, CI, behind base, draft, size)
- Changed files categorized by type
- Review focus areas
- CLAUDE.md rules
- Workflow context (scope limits, deviations)

---

## Success Criteria

- PR_IDENTIFIED: Valid open PR #$capture-pr-number.output found
- NO_CONFLICTS: No merge conflicts
- CONTEXT_GATHERED: Diff and file list available
- SCOPE_MANIFEST_WRITTEN: `$ARTIFACTS_DIR/review/scope.md` created
