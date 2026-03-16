# Review Output Structure

> Read this when: creating review round directories (Step 2e) or understanding the file layout.

Thorough mode always persists review artifacts to `.claude/reviews/`, organized by branch and review round. Quick mode only persists when `--save` is specified.

## Directory Layout

```
.claude/reviews/
├── REVIEW.md                                         # → most recent review round (any branch)
├── feature--dark-mode/
│   ├── 20260212-143022-staged/                       # Internal-only (default)
│   │   ├── _diff.patch                               # The diff that was reviewed
│   │   ├── review-claude-code-1.md                   # Built-in Claude reviewer
│   │   └── REVIEW_SUMMARY.md                         # Synthesized summary
│   ├── 20260212-150000-staged/                       # With --external --count 2
│   │   ├── _review-prompt.md                         # Prompt sent to external models
│   │   ├── _diff.patch                               # The diff that was reviewed
│   │   ├── review-claude-code-1.md                   # Built-in Claude reviewer
│   │   ├── review-claude-code-2.md                   # Built-in Claude reviewer (instance 2)
│   │   ├── review-composer-1.5-1.md                  # External model instances
│   │   ├── review-composer-1.5-2.md
│   │   └── REVIEW_SUMMARY.md                         # Synthesized summary from all reviews
│   └── 20260212-160000-vs-master/
│       └── ...
├── ENG-123--user-auth/
│   └── ...
└── pr-456/
    └── ...
```

## Branch Name Sanitization

1. Get branch name: `git symbolic-ref --short HEAD 2>/dev/null`
2. **Sanitize:** Replace `/` with `--`. Strip characters that aren't alphanumeric, `-`, `_`, or `.`. Truncate to 100 characters.
3. **Detached HEAD:** Use `detached-$(git rev-parse --short HEAD)`
4. **PR mode:** Use PR's head branch name from `gh pr view <number> --json headRefName`. Fallback: `pr-<number>`.

## Scope Suffix

| Scope | Suffix | Example |
|-------|--------|---------|
| Staged (default) | `staged` | `20260212-143022-staged` |
| Unstaged | `unstaged` | `20260212-143022-unstaged` |
| All changes | `all` | `20260212-143022-all` |
| Branch comparison | `vs-<branch>` | `20260212-143022-vs-master` |
| PR review | `pr-<number>` | `20260212-143022-pr-456` |
| Commit review | `commit-<short-sha>` | `20260212-143022-commit-a1b2c3d` |
| Specific files | `files` | `20260212-143022-files` |
| Changed only | `delta` | `20260212-143022-delta` |

## File Reference

| File | Purpose | Created by |
|------|---------|------------|
| `REVIEW.md` (reviews root) | Links to most recent review round | Step 2g |
| `_review-prompt.md` | Prompt passed to external models (audit trail, `--external` only) | Step 2e |
| `_diff.patch` | The diff that was reviewed (audit trail) | Step 2e |
| `review-claude-code-<N>.md` | Review from built-in Claude code-reviewer instance N | Orchestrator writes after agent completes |
| `review-<MODEL>-<N>.md` | Review from external model instance (`--external` only, immutable) | `code-review-executor` agent |
| `REVIEW_SUMMARY.md` | Synthesized summary with severity-based issues and agreement analysis | `code-review-synthesizer` agent |

**Immutability rule:** Raw `review-*.md` files must never be modified after creation. `REVIEW_SUMMARY.md` may be updated with apply/skip status in Phase 3.
