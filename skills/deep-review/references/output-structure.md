# Review Output Structure

> Read this when: creating review round directories (Phase 2) or understanding the file layout.

Thorough mode always persists review artifacts. Quick mode only persists when `--save` is specified.

## Directory Layout

### Code type

Review artifacts are written relative to `PROJECT_ROOT` (the directory where `/deep-review` was invoked). When `PROJECT_ROOT == GIT_ROOT`, this is the repository root. When invoked from a subdirectory, artifacts live within that subdirectory so scoped external reviewers can access them.

```
PROJECT_ROOT/.claude/reviews/
├── REVIEW.md                                         # → most recent review round (any branch)
├── feature--dark-mode/
│   ├── 20260212-143022-staged/                       # Internal-only (default)
│   │   ├── _diff.patch                               # The diff that was reviewed
│   │   ├── review-claude-code-1.md                   # Built-in Claude reviewer
│   │   └── REVIEW_SUMMARY.md                         # Synthesized summary + verdict
│   ├── 20260212-150000-staged/                       # With --external --count 2
│   │   ├── _review-prompt-opus.md                    # One prompt per reviewer model
│   │   ├── _review-prompt-composer-2.5.md
│   │   ├── _review-prompt-gpt-5.6-terra.md
│   │   ├── _review-prompt-gemini-3.8-flash.md
│   │   ├── _diff.patch
│   │   ├── _reviewers-config.json                    # run_reviewers.py config
│   │   ├── _external-results.json                    # run_reviewers.py stdout (with telemetry)
│   │   ├── _external-progress.log                    # run_reviewers.py stderr
│   │   ├── _log-review-composer-2.5-1.jsonl ...      # Tool-call log per external reviewer
│   │   ├── review-claude-code-1.md
│   │   ├── review-claude-code-2.md
│   │   ├── review-composer-2.5-1.md
│   │   ├── review-composer-2.5-2.md
│   │   ├── review-gpt-5.6-terra-high-1.md
│   │   ├── review-gpt-5.6-terra-high-2.md
│   │   ├── review-gemini-3.8-flash-high-1.md
│   │   ├── review-gemini-3.8-flash-high-2.md
│   │   ├── REVIEW_SUMMARY.md
│   │   ├── rebuttal-composer-2.5-1-C1.md             # Deliberation (if triggered)
│   │   └── rebuttal-response-composer-2.5-1-C1.md
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
        ├── _review-prompt-opus.md
        ├── _review-prompt-gemini-3.8-flash.md
        ├── review-opus-internal-1.md
        ├── review-opus-internal-2.md
        ├── review-gemini-3.8-flash-high-1.md
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
| `_review-prompt-<key>.md` | Prompt for one reviewer model, rendered from its profile (audit trail of what each model received) | `prepare_round.py` (Phase 2) |
| `_diff.patch` | The diff that was reviewed (audit trail, code type) | `prepare_round.py` (Phase 2) |
| `_reviewers-config.json` | External reviewer tasks and runner settings | `prepare_round.py` (Phase 2) |
| `_external-results.json` / `_external-progress.log` | Runner result JSON (with per-reviewer telemetry) / progress log | `run_reviewers.py` (Phase 3) |
| `_log-<output stem>.jsonl` | One line per tool call of an external reviewer or rebuttal: time, duration, tool, target | `run_reviewers.py` |
| `review-claude-code-<N>.md` | Review from internal Claude reviewer (code) | `deep-reviewer` agent |
| `review-opus-internal-<N>.md` | Review from internal reviewer (plan/spec) | `deep-reviewer` agent |
| `review-<MODEL>-<N>.md` | Review from external model (immutable) | Task subagent (Cursor) or `run_reviewers.py` (Claude Code / `--agent-cli`) |
| `REVIEW_SUMMARY.md` | Synthesized summary + verdict block | `review-synthesizer` agent |
| `rebuttal-<REVIEWER>-C<N>.md` | Rebuttal prompt (deliberation) | `review-synthesizer` |
| `rebuttal-response-<REVIEWER>-C<N>.md` | Reviewer response (deliberation) | `deep-reviewer`, Task subagent or `run_reviewers.py` |
| `rebuttal-response-orchestrator-C<N>.md` | Direct resolution of a code-checkable conflict | Orchestrator |

**Immutability rule:** Raw `review-*.md` files and `rebuttal-*.md` files must never be modified after creation. `REVIEW_SUMMARY.md` may be updated with apply/skip status in Phase 5.
