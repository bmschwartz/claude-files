# Spec Feedback Loop

> Read this when: implementation reveals SPEC.md is wrong or incomplete.

1. **Stop** at current substep. Document: spec says X, reality requires Y.
2. **Significant change** (alters acceptance criteria, adds/removes phases, changes public API/schema, affects security/NFRs, adds scope): new version snapshot in `plans/<new-timestamp>/`, update PLAN.md + CHECKPOINT.md Spec Version, notify developer via `AskUserQuestion` — **hard gate, do not resume without approval**.
3. **Minor clarification** (parameter naming, clarifying existing behavior, internal refactor): edit in place, add Iteration Log entry, proceed.
4. **Default:** If unclear, treat as significant.
5. Update CHECKLIST.md and tasks if phases changed.
6. **Resume point:** Tests affected (including changes that affect both tests and implementation) → 3a. Implementation approach only (no test changes needed) → 3c. Cosmetic/docs → current substep.
7. **Circuit breaker:** >3 revisions in one phase → ask: continue | re-scope | return to Phase 2.
