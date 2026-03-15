# Review Output Structure

> Read this when: understanding the file layout or creating review round directories.

Each review round gets its own timestamped directory under `<PLAN_ROOT>/reviews/`. A `REVIEW.md` file at the plan root links to the most recent round.

```
<PLAN_ROOT>/
├── PLAN.md                              # → current plan version
├── REVIEW.md                            # → most recent review round
├── plans/
│   └── <PLAN_TIMESTAMP>/
└── reviews/
    ├── <ROUND_1_TIMESTAMP>/             # Round 1
    │   ├── _review-prompt.md            # Prompt used (preserved)
    │   ├── review-<MODEL>-<N>.md        # Raw review outputs
    │   └── REVIEW_SUMMARY.md            # Synthesis for this round
    └── <ROUND_2_TIMESTAMP>/             # Round 2
        ├── _review-prompt.md
        ├── review-<MODEL>-<N>.md
        └── REVIEW_SUMMARY.md
```

## File Reference

| File | Purpose | Created by |
|------|---------|------------|
| `REVIEW.md` (plan root) | Links to most recent round's `REVIEW_SUMMARY.md` | Step 7 |
| `reviews/<TIMESTAMP>/` | Timestamped directory for a single round | Step 2 |
| `_review-prompt.md` | Prompt passed to each reviewer (audit trail) | Step 2 |
| `review-<MODEL>-<N>.md` | Raw review output from a single subagent (immutable) | `plan-reviewer` subagent |
| `REVIEW_SUMMARY.md` | Synthesized summary (updated with apply/skip status in Step 7) | `review-synthesizer` subagent |

`<MODEL>`: model identifier with `/` → `-` (e.g., `opus-4.6-thinking`). Built-in reviewers use `opus-internal`.
`<N>`: 1-indexed instance number.
`<TIMESTAMP>`: `YYYYMMDD-HHMMSS` format.

**Immutability rule:** Raw `review-*.md` files must never be modified after creation. `REVIEW_SUMMARY.md` is updated with apply/skip status but raw content is never changed.
