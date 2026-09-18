# Synthesis Protocol

> Read this when: understanding how the review-synthesizer cross-references findings and determines agreement.

## Cross-Referencing Rules

Two findings are "the same" if they meet BOTH criteria:
1. **Same location:** Same file + line within ~5 lines (code), or same document section (plan/spec)
2. **Same problem:** Describe the same issue, even if worded differently

When merging duplicate findings, preserve the most detailed description and note all source reviewers.

## Agreement Thresholds

| Level | Criteria | Confidence boost |
|-------|----------|------------------|
| **Strong** | Flagged by reviewers from ≥2 different models | High regardless of individual certainty |
| **Moderate** | Flagged by multiple instances of same model, no cross-model | High if concrete (specific location + code reference) |
| **Single** | Only one reviewer raised it | Retain reviewer's own confidence |

## Severity Definitions

### CRITICAL (must fix)
- **Code:** Security vulnerabilities, data loss, breaking API changes, crashes, race conditions, memory leaks, incorrect business logic, pattern violations risking correctness/security, regression risk, new dependency CVEs
- **Plan/Spec:** Bugs, logic errors, security issues, missing steps that would cause implementation to fail

### IMPORTANT (should fix)
- **Code:** Performance problems, pattern violations (style), missing validation, hardcoded values, test coverage gaps, major version bumps
- **Plan/Spec:** Architectural concerns, significant gaps, issues causing rework later

### MINOR (nice to have)
- **Code:** Naming improvements, complexity reduction, docs, duplication, reuse opportunities
- **Plan/Spec:** Style improvements, nice-to-haves, low-impact optimizations

### POTENTIAL (low confidence)
Issues where the reviewer is uncertain — flagged for human judgment. Available for all types.

**Severity disagreements:** When reviewers assign different severities to the same finding, use the higher severity.

## Plan/Spec Bucketing

For plan/spec type, findings are additionally categorized into buckets:
- **Auto-apply** — Multiple reviewers agree. High confidence. Apply without user input.
- **Needs your input** — Reviewers contradict each other, propose incompatible approaches, or the suggestion is significant enough to warrant human decision.
- **Unique insights** — Single reviewer. Auto-apply if clearly beneficial and low-risk; otherwise needs input.

## Focus Filtering (code type only)

When a focus filter is specified, the synthesizer splits findings into "in focus" (main sections) and "out of focus" (Filtered Issues table with severity, location, and title only).
