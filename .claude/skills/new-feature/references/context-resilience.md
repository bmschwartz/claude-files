# Context Resilience

> Read this when: creating CHECKPOINT.md (Phase 2a), writing breadcrumbs, or recovering from compaction.

## CHECKPOINT.md Format

```markdown
# Checkpoint
Status: active
Phase: 3
Substep: 3c: Implement Minimum Code
Implementation Phase: 2 of 4
Convergence Iteration: 0
Convergence Trend: [N/A | improving | stalled | degrading]
Tests Completed: 0 of N
Test Command: pytest -xvs
Spec Version: plans/<YYYYMMDD-HHMMSS>/
Autonomy Mode: supervised
Deferred Issues: none
Notes: [1-2 sentences recovery context]
```

Status values: `active`, `shelved`, `abandoned`, `completed`.

## CLAUDE.md Breadcrumb

```
<!-- new-feature: [slug] --> ALWAYS read .claude/docs/[slug]/CHECKPOINT.md before continuing any work.
```

Shelved variant:
```
<!-- new-feature: [slug] (shelved) --> A shelved feature exists at .claude/docs/[slug]/. Read CHECKPOINT.md before starting new work.
```

Written at Phase 2a (earliest slug exists). Removed on completion. Line-level edits only. If CLAUDE.md doesn't exist, create with breadcrumb only.

## Compaction Recovery

**Primary:** Breadcrumb forces re-read of CHECKPOINT.md every turn (survives compaction).

**Phase boundary re-reads (conditional):** Re-read a doc only when recovering from compaction OR its content may have changed. Use Spec Version field and Iteration Log as change signals. Available docs by phase: 2a+ has CHECKPOINT + EXPLORATION; 2b+ adds SPEC; 2c+ adds CHECKLIST.

**Task descriptions as state carriers:** `TodoWrite` for each implementation phase should follow: `content: "Phase N: [name]"`, `activeForm: "Implementing Phase N: [name]"`. Include in the description: files involved, tests to write (from SPEC.md "Tests to Write First"), acceptance criteria, and current approach (from blueprint). This ensures a compacted model can recover context.

**Compaction indicators (fallback):** Can't recall file paths from Phase 0, reference spec in general terms, unsure of current substep → read CHECKPOINT.md to recover.
