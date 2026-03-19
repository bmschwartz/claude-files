# Review Output Structure

> Read this when: creating review round directories (Phase 2) or understanding the file layout.

Thorough mode always persists review artifacts. Quick mode only persists when `--save` is specified.

## Directory Layout

### Code type

Review artifacts are written relative to `PROJECT_ROOT` (the directory where `/review` was invoked). When `PROJECT_ROOT == GIT_ROOT`, this is the repository root. When invoked from a subdirectory, artifacts live within that subdirectory so scoped external reviewers can access them.

```
PROJECT_ROOT/.claude/reviews/
├── REVIEW.md                                         # → most recent review round (any branch)
├── feature--dark-mode/
│   ├── 20260212-143022-staged/                       # Internal-only (default)
│   │   ├── _diff.patch                               # The diff that was reviewed
│   │   ├── review-claude-code-1.md                   # Built-in Claude reviewer
│   │   └── REVIEW_SUMMARY.md                         # Synthesized summary + verdict
│   ├── 20260212-150000-staged/                       # With --external --count 2
│   │   ├── _review-prompt.md                         # Prompt sent to external models
│   │   ├── _diff.patch
│   │   ├── review-claude-code-1.md
│   │   ├── review-claude-code-2.md
│   │   ├── review-composer-2-fast-1.md
│   │   ├── review-composer-2-fast-2.md
│   │   ├── REVIEW_SUMMARY.md
│   │   ├── rebuttal-composer-2-fast-1-C1.md             # Deliberation (if triggered)
│   │   └── rebuttal-response-composer-2-fast-1-C1.md
│   └── 20260212-160000-vs-master/
│       └── ...
└── pr-456/
    └── ...
```

### Plan/Spec type

```
<plan-root>/
├── PLAN.md
├── REVIEW.md                                         # → most recent review round
├── plans/
│   └── <plan-timestamp>/
└── reviews/
    └── <round-timestamp>/
        ├── _review-prompt.md
        ├── review-opus-internal-1.md
        ├── review-opus-internal-2.md
        ├── review-gemini-3-flash-1.md
        └── REVIEW_SUMMARY.md
```

## Branch Name Sanitization (code type)

1. Get branch name: `git symbolic-ref --short HEAD 2>/dev/null`
2. **Sanitize:** Replace `/` with `--`. Strip characters that aren't alphanumeric, `-`, `_`, or `.`. Truncate to 100 characters.
3. **Detached HEAD:** Use `detached-$(git rev-parse --short HEAD)`
4. **PR mode:** Use PR's head branch name from `gh pr view <number> --json headRefName`. Fallback: `pr-<number>`.

## Scope Suffix (code type)

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
| `REVIEW.md` | Links to most recent review round | Phase 5 |
| `_review-prompt.md` | Prompt passed to external models (audit trail) | Phase 2 |
| `_diff.patch` | The diff that was reviewed (audit trail, code type) | Phase 2 |
| `review-claude-code-<N>.md` | Review from built-in Claude reviewer (code) | Orchestrator writes after Explore agent completes |
| `review-opus-internal-<N>.md` | Review from built-in reviewer (plan/spec) | Orchestrator writes after Explore agent completes |
| `review-<MODEL>-<N>.md` | Review from external model (immutable) | `run_reviewers.py` script |
| `REVIEW_SUMMARY.md` | Synthesized summary + verdict block | `review-synthesizer` agent |
| `rebuttal-<REVIEWER>-C<N>.md` | Rebuttal prompt (deliberation) | Orchestrator |
| `rebuttal-response-<REVIEWER>-C<N>.md` | Reviewer response (deliberation) | Orchestrator / `run_reviewers.py` |

**Immutability rule:** Raw `review-*.md` files and `rebuttal-*.md` files must never be modified after creation. `REVIEW_SUMMARY.md` may be updated with apply/skip status in Phase 5.
