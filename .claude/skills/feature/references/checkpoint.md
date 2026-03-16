# Context Resilience

> Read this when: creating CHECKPOINT.md, writing breadcrumbs, recovering from compaction, or handling resume/shelve/abandon.

## CHECKPOINT.md Format

```markdown
# Checkpoint
Status: active
Phase: Implement
Substep: TDD micro-cycle (Verify Red)
Implementation Phase: 2 of 4
Convergence Iteration: 0
Convergence Trend: [N/A | improving | stalled | degrading]
Tests Completed: 3 of 8
Test Command: pytest -xvs
Spec Version: plans/<YYYYMMDD-HHMMSS>/
Autonomy Mode: supervised
Deferred Issues: none
Notes: [1-2 sentences recovery context]
```

Status values: `active`, `shelved`, `abandoned`, `completed`.

## CLAUDE.md Breadcrumb

```
<!-- feature: [slug] --> ALWAYS read .claude/docs/[slug]/CHECKPOINT.md before continuing any work.
```

Shelved variant:
```
<!-- feature: [slug] (shelved) --> A shelved feature exists at .claude/docs/[slug]/. Read CHECKPOINT.md before starting new work.
```

Written at Design phase (earliest slug exists). Removed on completion. Line-level edits only. If CLAUDE.md doesn't exist, create with breadcrumb only.

Also check for legacy `<!-- new-feature: ... -->` and `<!-- new-feature-vdd: ... -->` breadcrumbs from prior skill versions. Treat identically — same resume/shelve/abandon options apply. Offer to clean up legacy markers.

## Compaction Recovery

**Primary:** Breadcrumb forces re-read of CHECKPOINT.md every turn (survives compaction).

**Phase boundary re-reads (conditional):** Re-read a doc only when recovering from compaction OR its content may have changed. Use Spec Version field and Iteration Log as change signals.

**Task descriptions as state carriers:** `TodoWrite` for each implementation phase should include: files involved, tests to write, acceptance criteria, current approach. This ensures a compacted model can recover context.

**Compaction indicators (fallback):** Can't recall file paths from Explore, reference spec in general terms, unsure of current phase → read CHECKPOINT.md to recover.

## Resume/Shelve/Abandon Protocol

### Startup Breadcrumb Handling

**Active breadcrumb found:** Prior session interrupted. Ask: Resume (Recommended) | Start fresh | Abandon.
- **Resume:** Read CHECKPOINT.md for phase/substep. If missing, ask user. Re-read only artifacts that exist at recorded phase. Jump directly — skip Explore.
- **Start fresh / Abandon:** Check `git status` first — if dirty, ask about uncommitted work. Fresh: shelve previous, proceed to Explore. Abandon: mark abandoned, remove breadcrumb, proceed to Explore.

**Shelved breadcrumb found:** Ask: Resume shelved | Start fresh.
- **Resume:** Check git status. Set CHECKPOINT.md active, update breadcrumb, jump to recorded phase.
- **Fresh:** Leave shelved artifacts intact. Multiple shelved breadcrumbs can coexist.

**Multiple breadcrumbs:** Active takes precedence. Multiple active = corruption — list all, ask user, shelve/abandon others.

### Exit Protocol (available at any phase)

**Explore phase** (no checkpoint): Stop. Only Abandon available.

**Design phase onward:**

| Option | Action |
|--------|--------|
| **Restart from spec** | New version snapshot, log restart, CHECKPOINT → Design, jump to Design |
| **Shelve** | CHECKPOINT status → shelved, breadcrumb → shelved variant, stop |
| **Abandon** | CHECKPOINT status → abandoned, remove breadcrumb, stop |
