# Phase: Verify

> Calls /review, reacts to verdict, autonomous review-fix loop.

## Contract

- **Receives:** Implementation branch with passing tests, SPEC.md path, CHECKPOINT.md
- **Produces:** REVIEW_SUMMARY.md with CONVERGED verdict (or human-accepted remaining issues)
- **Invariants:** All tests pass before and after fixes. Verdict block exists. Convergence trend recorded.
- **Loops:** Yes — review-fix loop, max 3 rounds (2 for Critical tier)
- **Exit condition:** `verdict.decision == CONVERGED`, OR iteration cap with human acceptance, OR trend stalled/degrading with human decision
- **Human gate:** Only if escalating (cap hit, trend stuck, or CRITICAL at cap requiring acknowledgement)

**Light tier skips this phase entirely.**

## Review-Fix Loop

### Initial Review

Update CHECKPOINT.md: Phase: Verify, Convergence Iteration: 0.

Run `/review --type code --external --verdict-only`.

Read the verdict block from `REVIEW_SUMMARY.md` in the round directory reported by `/review`. The `verdict.round_dir` field contains the path. Parse the verdict between `<!-- VERDICT_START -->` and `<!-- VERDICT_END -->` markers.

### Triage

Extract `verdict.decision`, `verdict.findings.*`, `verdict.conflicts.unresolved`.

Record CRITICAL + IMPORTANT count in CHECKPOINT.md Notes (e.g., `Iteration 0 findings: N`).

**Deferral rules:**
- CRITICAL findings cannot be deferred. If skipped during fix, they remain unresolved and block convergence.
- IMPORTANT findings skipped count as deferred — record in CHECKPOINT.md Deferred Issues. Does not block convergence.

**Route:**
- `verdict.decision == CONVERGED` → Phase 5 (Complete). In `autonomous` mode, auto-proceed. In `supervised`, auto-proceed after first iteration. In `guided`, ask developer.
- `verdict.decision == BLOCK` or `NEEDS_FIXES` → If iteration 0, proceed to Fix (first iteration — cap checks can't fire yet). If iteration ≥ 1, proceed to Convergence Check.

### Fix

Fix CRITICAL findings. Fix IMPORTANT unless developer deferred.

**TDD applies to behavioral fixes:** changed logic, new code paths, altered API surface → write regression test first, verify Red, implement, verify Green. Non-behavioral fixes (formatting, naming, docs, dead code) → apply directly. When uncertain, write the test.

Run full test suite. If fixes require spec changes → Spec Feedback Loop → new implementation → restart Verify with `--changed-only`.

### Re-Review

Run `/review --type code --external --verdict-only --changed-only` (scoped to files changed since last round). If fixes touched >50% of files in scope, use full review instead.

Increment Convergence Iteration. Return to Triage.

### Convergence Check

Reached when CRITICAL or undeferred IMPORTANT remain at iteration ≥ 1.

**Trend:** Compare current CRITICAL + IMPORTANT count against prior iteration's count (from CHECKPOINT.md Notes). Update CHECKPOINT.md Convergence Trend:
- `improving` — count decreased
- `stalled` — count unchanged → **escalate immediately** (don't wait for cap)
- `degrading` — count increased → **escalate immediately**

**Iteration cap:** Standard: 3. Critical: 2. Cap triggers when Convergence Iteration ≥ cap.

**At cap, present options:**
- **Fix and review again** — extends cap by 1
- **Accept remaining issues** — document and proceed to Complete
- **I'll handle manually** — handoff, update CHECKPOINT to completed with manual-handoff mode

**Hard ceiling:** No feature exceeds `cap + 1` iterations total.

**If CRITICAL at cap:** "Accept remaining issues" requires explicit per-CRITICAL acknowledgement.

**Spec-churn escalation:** If 2+ iterations flagged `spec-triggered`, escalate regardless of count.

**If not capped and not escalated → proceed to Fix.**
