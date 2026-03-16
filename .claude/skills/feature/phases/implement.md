# Phase: Implement

> TDD cycle with autonomous feedback loop.

## Contract

- **Receives:** Approved SPEC.md, CHECKLIST.md, test command, feature branch
- **Produces:** Passing tests + implementation for all spec phases, git commits per phase
- **Invariants:** Every line of implementation demanded by a failing test. Full suite passes after each phase.
- **Loops:** Yes — TDD micro-cycle per test, autonomous. Max N fix attempts per test before escalating.
- **Exit condition:** All implementation phases complete with passing tests

## Setup

Create feature branch `feat/[slug]`. Mark first phase task `in_progress`. Update CHECKPOINT.md: Phase: Implement, Implementation Phase: 1 of N.

## TDD Micro-Cycle

```
Write failing tests → Verify Red → Implement minimum → Verify Green → Repeat → Refactor → Phase complete
```

**Do NOT implement before confirming Red. Do NOT fix compile errors caused by missing implementation during Red — that IS valid Red.**

### Write Failing Tests (1-3 related tests per cycle)

Write next tests from SPEC.md "Tests to Write First." Follow project test patterns. Before running, reconcile tests written so far against spec.

### Verify Red

Run test command. **Valid Red:** assertion failures, missing-symbol compile errors. **Invalid Red:** syntax errors in test code, broken imports for existing modules, infra failures — fix those first.

If tests pass unexpectedly: (a) pre-existing behavior → note, continue; (b) tautological → fix test; (c) prior phase covers it → note. If ALL pass → behavior pre-exists, verify matches spec, skip to phase complete.

### Implement Minimum Code

Write the **minimum** to pass failing tests. No gold-plating.

### Verify Green

Run **full** test suite. If existing tests broke, fix implementation (not old tests, unless spec changed that behavior). Update CHECKPOINT.md Tests Completed. If more tests remain in this phase → return to Write Failing Tests.

**Early stability signal:** If 3 consecutive cycles achieve Green on first run, batch remaining tests (up to 5), implement, verify. If any fail, return to normal cycles. This batches cycle size when confidence is high — it does NOT skip the Red check.

### Refactor

Address SPEC.md Refactoring Notes. Extract duplication, improve naming, apply Explore patterns. Re-run full suite.

**Post-refactor self-check:**
- Traceability: every new abstraction exercised by an existing test — if not, inline it
- Test DRY: 3+ tests sharing setup → shared fixture
- Hygiene: TODO/FIXME/HACK, generic errors, over-broad exceptions, magic numbers, dead code → fix immediately

### Phase Complete

- `TodoWrite` → `completed`. Full test-plan reconciliation.
- Check off CHECKLIST.md items. Git commit: `feat([slug]): phase N — [name]`.
- Next phase exists → mark `in_progress`, continue. Last phase → Anti-Slop Subagent → Verify.

## Anti-Slop Subagent (after last implementation phase)

Launch a fresh `Explore` subagent to scan all code from Implement for: development artifact comments, low-value docstrings, restating comments, unnecessary abstractions, copy-paste duplication, and hygiene issues that survived self-check. Fix findings. Fresh context catches what self-review misses.

**After fixing Anti-Slop findings:** Re-run full test suite to verify fixes didn't break anything. Git commit: `refactor([slug]): anti-slop cleanup`.

## Spec Feedback Loop

Triggered when implementation reveals SPEC.md is wrong or incomplete. See the orchestrator's Spec Feedback Loop section for the full protocol.

## Safety Limits

- **Max fix attempts per test:** 5. If a single test can't go green after 5 implementation attempts, escalate to human.
- **Circuit breaker:** >3 spec revisions in one implementation phase → ask developer.
