# Phase: Complete

> PR prep, cleanup, retrospective, and suggested rules.

## Contract

- **Receives:** Converged implementation (from Verify) or clean implementation (Light tier)
- **Produces:** Clean code, passing tests, retrospective, updated CHECKPOINT.md (completed)
- **Invariants:** All tests pass. CHECKLIST.md fully checked. Breadcrumb removed.
- **Loops:** No (but may re-enter Verify if post-cleanup review finds CRITICAL)
- **Exit condition:** PR ready, retrospective written, breadcrumb removed

## Cleanup

1. Run `/deslop-around:deslop-around apply` (mechanical cleanup)
2. Run `/polish` (semantic cleanup)

**Constraint for `/polish`:** Do not delete tests that trace to SPEC.md "Tests to Write First" — consolidation (parameterization) is allowed, deletion is not.

## Post-Cleanup Review Guard

**Skip review if:** Verify phase converged with zero CRITICAL and the only changes since last review are from deslop/polish (cleanup-only).

**Run `/review --type code --quick` when:**
- **Light tier** — this is the only review, run regardless
- Any non-cleanup code changes were made after last review

**If CRITICAL found:**
- **Standard/Critical tier:** Run full `/review --type code --external`, return to Verify phase
- **Light tier:** Present findings, offer: **Fix and re-run --quick** | **Enter full Verify** (override Light skip) | **Accept and proceed** (requires per-CRITICAL acknowledgement)

## Final Test Run

Full test suite. All tests must pass.

## Checklist Verification

- [ ] All SPEC.md success criteria met
- [ ] All tests passing
- [ ] Verify phase gate satisfied (or skipped per tier / pre-existing feature)
- [ ] Iteration Log reflects final state
- [ ] CHECKLIST.md fully checked off

## Summary + Retrospective

Present: what was built, files changed, test coverage, TDD compliance, convergence status, deferred issues, spec changes, next steps.

**Retrospective:** Generate `.claude/docs/[slug]/RETROSPECTIVE.md`:

```markdown
# [Feature Name] Retrospective

## Metrics
- Implementation phases: N
- TDD cycles: N (M red-green on first attempt)
- Review iterations: N (trend: improving/stalled/N/A)
- Spec revisions: N (M significant, K minor)
- Total findings: N critical, M important resolved
- Deferred issues: [list or "none"]

## What Went Well
- [Patterns that worked, good decisions]

## What Was Difficult
- [Surprises, blockers, spec changes needed]

## Review Learnings
- Learnings created during this feature: [list IDs or "none"]
- Learnings matched during reviews: [list IDs or "none"]
- Promotions to CLAUDE.md: [list or "none"]

## Patterns to Reuse
- [Patterns discovered that other features should use]

## Suggested Rules
- [Proposed additions to CLAUDE.md for future features]
```

**Light tier:** Omit convergence metrics (no Verify phase). Note "IMPORTANT/MINOR not assessed (quick review mode)."

**Suggested Rules gate:** Present any "Suggested Rules" to the developer for approval before adding to CLAUDE.md — **hard gate in all autonomy modes** to prevent instruction creep.

**Deferred learning candidates:** When `/review --verdict-only` returned verdicts containing `learning_candidates.items` during this feature's Verify phase, process them now. Check `.claude/learnings/LEARNINGS.md` for any learnings whose `source.feature` matches this feature's slug, and check verdict blocks from this feature's review rounds for unprocessed `learning_candidates`. For each candidate: present to developer with Save | Skip | Edit scope options (unless `autonomous` mode, in which case auto-accept). Write accepted learnings to `.claude/learnings/` per the review skill's `references/learning-schema.md`. Populate the retrospective's "Review Learnings" section with the results.

## Wrap-Up

- CHECKPOINT.md status → `completed`
- Remove this feature's CLAUDE.md breadcrumb (preserve others)

## Multi-PR Workflow

If PR_STRATEGY.md exists (multi-PR feature):
1. After Verify converges for a PR slice: run cleanup, then present PR Handoff Gate
2. Ask: **PR good — continue** | **I made changes** | **Shelve remaining**
3. Continue: branch next PR (stacked if dependent, from main if independent), return to Implement
4. Track current PR in CHECKPOINT.md Notes
