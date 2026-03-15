# Integration Notes

> Read this when: interacting with /git-review or /plan-review during Phase 4 convergence.

- `/git-review --external` discovers spec docs via PLAN.md in `.claude/docs/[slug]/`. Branch `feat/<slug>` matches `.claude/docs/<slug>/`. Single-directory shortcut: when only one `.claude/docs/` dir exists, branch matching is skipped.
- `/plan-review` uses CRITICAL/IMPORTANT/MINOR/GOOD severities (no POTENTIAL). GOOD findings are informational and do not affect convergence triage (treat as equivalent to MINOR for convergence purposes). Creates new versioned snapshots automatically.
- `/deslop-around` is always available — no fallback needed. It is a prerequisite for this workflow.
- POTENTIAL is a `/git-review`-specific severity (low-confidence findings). `/plan-review` does not produce it. Convergence logic references POTENTIAL only in the context of `/git-review` output.
- Review directory paths: `/git-review` sanitizes branch names (`/` → `--`).

> **Note:** VDD's formal verification (purity boundaries, Kani/Dafny/TLA+) is intentionally omitted. For safety-critical features, add a Verification Strategy to the spec and formal hardening after implementation.
