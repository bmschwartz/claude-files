# Verdict Schema

> Read this when: consuming verdict blocks programmatically (e.g., from `/feature`) or understanding the structured output.

## Schema (v2)

The verdict block is a fenced YAML block appended at the end of every `REVIEW_SUMMARY.md`, wrapped in HTML comment markers for reliable parsing:

```yaml
<!-- VERDICT_START -->
verdict:
  schema_version: 2
  type: code | plan | spec
  decision: CONVERGED | NEEDS_FIXES | BLOCK
  timestamp: "YYYYMMDD-HHMMSS"
  round_dir: "<path to this round directory>"
  findings:
    critical: <int>
    important: <int>
    minor: <int>
    potential: <int>
  agreements:
    strong: <int>
    moderate: <int>
    single: <int>
  conflicts:
    detected: <int>
    resolved: <int>
    unresolved: <int>
  reviewers:
    total: <int>
    succeeded: <int>
    failed: <int>
    models: [<list of model identifier strings>]
  human_input_required:
    count: <int>
    items:
      - id: "NI-<N>"
        title: "<short title>"
        severity: CRITICAL | IMPORTANT
  previously_addressed: <int>
  learning_candidates:
    new: <int>
    recurrences: <int>
    promotions: <int>
    items:
      - id: "LC-<N>"
        type: new | recurrence | promotion
        title: "<short title>"
        category: "<category>"
        severity: critical | important
        scope: ["<glob>", ...]
        existing_learning_id: "L-<NNN>"  # present only for recurrence/promotion
        occurrences: <int>               # present only for recurrence/promotion
<!-- VERDICT_END -->
```

## Decision Logic

| Decision | Condition |
|----------|-----------|
| `BLOCK` | `findings.critical > 0` OR `conflicts.unresolved > 0` |
| `NEEDS_FIXES` | `findings.important > 0` OR `human_input_required.count > 0` |
| `CONVERGED` | Only minor/potential remain, no unresolved conflicts, no required human input |

## Field Notes

| Field | Code type | Plan/Spec type |
|-------|-----------|----------------|
| `human_input_required` | count: 0, items omitted | Populated from "Needs your input" section |
| `previously_addressed` | 0 | Count of filtered re-flagged items |
| `conflicts.resolved` | 0 in initial mode | Populated after deliberation |
| `agreements.*` | From agreement matrix | From agreement analysis |
| `learning_candidates` | Populated by Phase 4.7. Empty `items` if `--no-learn`. Absent if `--quick`. | Same as code type |

## Parsing

To extract the verdict block:
1. Find `<!-- VERDICT_START -->` marker
2. Read YAML content until `<!-- VERDICT_END -->`
3. Parse as YAML
4. Validate `schema_version: 2` (also accept `schema_version: 1` for backward compatibility — v1 lacks the `learning_candidates` field)

## What Callers Compute (not in verdict)

- **Convergence trend** — Compare `findings.critical + findings.important` across sequential invocations
- **Iteration count** — Caller tracks how many review rounds have run
- **Deferral status** — Caller decides which findings can be deferred
- **Safety caps** — Caller enforces maximum iteration limits

## Schema Version History

| Version | Changes |
|---------|---------|
| v1 | Initial schema |
| v2 | Added `learning_candidates` field (Phase 4.7 learning extraction) |
