# Resume/Shelve/Abandon Protocol

> Read this when: a CLAUDE.md breadcrumb is found at startup, or the user requests to shelve/abandon.

## Startup Breadcrumb Handling (Phase 0)

Read CLAUDE.md for `<!-- new-feature: ... -->` breadcrumbs.

**Active breadcrumb found:** Prior session interrupted. Ask: Resume (Recommended) | Start fresh | Abandon.
- **Resume:** Read CHECKPOINT.md for substep. If missing, ask user: "Start fresh, abandon, or recover from other artifacts?" Re-read only artifacts that exist at the recorded substep. Jump directly — skip Phase 0/1.
- **Start fresh / Abandon:** Check `git status` first — if dirty, ask developer about uncommitted work. Fresh: shelve previous, proceed Phase 0. Abandon: mark abandoned, remove breadcrumb, proceed Phase 0.

**Shelved breadcrumb found:** Ask: Resume shelved | Start fresh.
- **Resume:** Check git status. Set CHECKPOINT.md active, update breadcrumb, jump to recorded substep.
- **Fresh:** Leave shelved artifacts intact. Multiple shelved breadcrumbs can coexist.

**Multiple breadcrumbs:** Active takes precedence. Multiple active = corruption — list all, ask user, shelve/abandon others.

**No breadcrumb:** Clean start.

## Exit Protocol (available at any phase)

**Phases 0-1** (no checkpoint): Stop. Only Abandon available.

**Phase 2a onward:**

| Option | Action |
|--------|--------|
| **Restart from spec** | New version snapshot (if one exists), log restart, mark tasks `[superseded]`, CHECKPOINT → Phase 2a, jump to 2a. Exploration retained. |
| **Shelve** | CHECKPOINT status → shelved, breadcrumb → shelved variant, stop. |
| **Abandon** | CHECKPOINT status → abandoned, remove breadcrumb, stop. Files left as-is. |
