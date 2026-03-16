# Multi-PR Workflow

> Read this when: PR_STRATEGY.md exists (generated in 2c for features spanning multiple PRs).

PR_STRATEGY.md must group Implementation Phases per PR with branch names: `feat/<slug>--<slice>`. Execute Phases 3 + 4 + PR Handoff Gate sequentially per PR. Track current PR in CHECKPOINT.md Notes.

## PR Handoff Gate (after Phase 4 converges, non-final PRs)

1. Run `/deslop-around:deslop-around apply` then `/polish`.
2. Ask developer: **PR good — continue** | **I made changes** | **Shelve remaining**.
   - Continue: update CHECKPOINT, branch next PR (stacked if dependent, from main if independent), return to Phase 3.
   - Changes: pull/detect changes, run `/git-review --quick` as sanity check, re-prompt gate.
   - Shelve: CHECKPOINT → shelved, breadcrumb → shelved variant, stop.
