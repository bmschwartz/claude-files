# Convergence Protocol

> Read this when: determining whether to stop reviewing or continue iterating.

## Verdict Decision Logic

The verdict block in `REVIEW_SUMMARY.md` contains a `decision` field computed as follows:

| Decision | Condition | Meaning |
|----------|-----------|---------|
| `BLOCK` | `findings.critical > 0` OR `conflicts.unresolved > 0` | Critical issues or unresolved reviewer disagreements. Must be addressed. |
| `NEEDS_FIXES` | `findings.important > 0` OR `human_input_required.count > 0` | Important issues remain or human decisions needed. Should be addressed. |
| `CONVERGED` | Only minor/potential remain, no unresolved conflicts, no required human input | Review is clean. Safe to proceed. |

## How Callers Use the Verdict

### Direct invocation (user runs `/review`)

The verdict informs the user's decision. The post-synthesis phase (fix application for code, gather-input for plan) runs automatically unless `--verdict-only`.

### Programmatic invocation (`/feature` calls `/review --verdict-only`)

The caller reads the verdict block and routes:

```
verdict.decision == CONVERGED  → proceed to next phase
verdict.decision == NEEDS_FIXES → fix findings, re-review (review-fix loop)
verdict.decision == BLOCK → fix critical findings or escalate to human
```

The caller tracks iteration count, convergence trend, and safety limits. `/review` does NOT track cross-iteration state — each invocation is stateless.

## Convergence Trend (computed by callers)

The verdict provides `findings.critical` and `findings.important` counts. Callers that iterate (like `/feature`) compare the **sum** of `findings.critical + findings.important` across invocations:

| Trend | Condition | Action |
|-------|-----------|--------|
| `improving` | Sum decreased vs prior iteration | Continue fixing |
| `stalled` | Sum unchanged (same total, even if individual severities shifted) | Escalate — fix approach may need rethinking |
| `degrading` | Sum increased | Escalate immediately |

## Quorum

Synthesis begins when **75% of reviewers** (rounded up) have completed. This balances speed (don't wait for stragglers) with coverage (enough perspectives for meaningful agreement analysis).

Late reviews (completing after synthesis) are appended as addenda rather than triggering re-synthesis.

## What `/review` Does NOT Track

These are caller responsibilities, not review-level concerns:

- **Iteration count** — How many review rounds have run
- **Convergence trend** — Whether findings are decreasing across rounds
- **Deferral rules** — Which severity levels can be deferred vs must-fix
- **Safety caps** — Maximum number of iterations before escalation
- **Spec-churn detection** — Whether spec changes are destabilizing convergence
