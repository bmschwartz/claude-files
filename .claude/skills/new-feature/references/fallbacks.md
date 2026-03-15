# Fallbacks

> Read this when: a tool or command is unavailable.

| Tool | Fallback |
|------|----------|
| `Explore` / `feature-dev:code-explorer` | `general-purpose` subagent with same objectives |
| `feature-dev:code-architect` | `Plan` subagent |
| `/plan-review` | Skip; user reviews spec manually at 2d gate |
| `/polish` | Inline cleanup: scan for dev artifact comments, low-value docstrings, LOW-impact tests. Commit before handoff. |
| `/git-review` | Fresh `Explore`/`general-purpose` subagent with adversarial prompt, diff, and SPEC.md. Write to `.claude/reviews/<sanitized-branch>/fallback-<timestamp>/REVIEW_SUMMARY.md` (follow `/git-review` sanitization rules). Update REVIEW.md. Present findings interactively (Apply/Skip). Convergence loop still applies. |
| `agent` CLI (for `--external`) | Run `/git-review` without `--external`. Note downgrade in CHECKPOINT.md Notes. |
