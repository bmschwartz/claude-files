# Learning Extraction Protocol

> Read this when: executing Phase 4.7 (learning extraction) after synthesis/deliberation.

## Position in Pipeline

Phase 4.7 runs **after** Phase 4.5 (deliberation) completes or is skipped, and **before** the `--verdict-only` gate that controls Phase 5. This positioning ensures learnings are always extracted, even when `/feature` calls `/review --verdict-only`.

```
Phase 4: Synthesis → Phase 4.5: Deliberation → Phase 4.7: Learning Extraction → Phase 5: Post-Synthesis
                                                                                  ↑
                                                                          --verdict-only gate
```

## Skip Conditions

Skip this phase entirely if:
- `--no-learn` flag is set
- `--quick` mode is active (quick mode skips all persistence)

## Algorithm

### Step 1: Collect Candidates from REVIEW_SUMMARY.md

Parse all findings from the structured severity sections (Critical Issues, Important Issues) of `REVIEW_SUMMARY.md`.

**Extraction criteria — a finding qualifies as a learning candidate if BOTH:**
1. Severity >= IMPORTANT (skip MINOR and POTENTIAL — too noisy for durable lessons)
2. Agreement >= Moderate (skip Single findings — insufficient confidence for persistence)

For each qualifying finding, extract:
- Title (from the finding heading)
- Severity (CRITICAL or IMPORTANT)
- Agreement level (Strong or Moderate)
- File paths mentioned (for scope generation)
- Description (for the Finding body)
- Category inference: map from review dimension → learning category:
  - Security → `security`
  - Correctness / Error Handling → `correctness`
  - Pattern Compliance → `pattern-violation`
  - Performance → `performance`
  - Test Coverage → `test-gap`
  - Architecture / Dependencies → `architecture`

### Step 2: Load Existing Learnings

If `.claude/learnings/` exists, read all `L-*.md` files. Parse frontmatter from each. Filter to `status: active` only (promoted and expired are not candidates for recurrence matching).

If `.claude/learnings/` does not exist, treat as empty set (all candidates will be `new`).

### Step 3: Recurrence Detection

For each candidate from Step 1, compare against each existing active learning from Step 2.

**Two items match if they describe the same underlying issue pattern.** This requires LLM judgment — exact string matching is insufficient because wording varies across reviews. Use these signals:

1. **Category match** — Same category is a strong signal but not required (a finding might be categorized differently across reviews)
2. **Scope overlap** — The candidate's file paths overlap with the learning's scope globs
3. **Semantic similarity** — The finding description addresses the same class of problem

**Pre-filter** to reduce comparisons: only compare candidates against learnings that share the same category OR have overlapping scope. Skip obviously unrelated pairs.

**Classification:**
- **Match found → `recurrence`:** Record the existing learning's ID. New occurrences count = existing `occurrences + 1`.
- **Match found AND new occurrences count >= 3 → `promotion`:** Superset of recurrence. This learning has been seen enough times to warrant CLAUDE.md rule promotion.
- **No match → `new`:** This is a novel pattern.

### Step 4: Generate Scope

For each `new` candidate, generate scope globs from the finding's file paths:
- Use the directory containing the file(s), not the exact file path (too narrow)
- Use a glob pattern that captures sibling files of the same type
- Example: finding in `src/api/handlers/users.ts` → scope `src/api/handlers/**/*.ts`
- Keep scope as specific as possible. Never generate `**/*`.

For `recurrence` candidates, check if the new finding's files fall outside the existing learning's scope. If so, suggest expanding the scope.

### Step 5: Route by Mode

#### Interactive mode (no `--verdict-only`, no `--auto-learn`)

Present each candidate to the user via `AskUserQuestion`:

**For `new` candidates:**
```
question: "Save this as a project learning?"
header: "New Learning Candidate (1/N)"
description: |
  [TITLE]
  Category: [category] | Severity: [severity] | Agreement: [agreement]
  Scope: [generated scope globs]

  Finding: [finding summary]
options:
  - label: "Save"
    description: "Save this learning to .claude/learnings/"
  - label: "Edit Scope"
    description: "Save with modified scope (you'll be asked for the scope)"
  - label: "Skip"
    description: "Don't save this learning"
  - label: "Save All"
    description: "Save this and all remaining candidates"
  - label: "Skip All"
    description: "Skip all remaining candidates"
```

**For `recurrence` candidates:**
```
question: "Update existing learning with new occurrence?"
header: "Recurrence Detected (M/N)"
description: |
  Matches: [existing learning ID] - [existing title]
  Previous occurrences: [count] → New: [count + 1]
  Last seen: [existing last_seen]

  New finding: [finding summary]
options:
  - label: "Update"
    description: "Increment occurrences and update last_seen"
  - label: "Skip"
    description: "Don't update this learning"
  - label: "Update All"
    description: "Update this and all remaining recurrences"
```

**For `promotion` candidates (in addition to the recurrence prompt):**
```
question: "Promote this learning to a CLAUDE.md rule?"
header: "Promotion Candidate"
description: |
  [existing learning ID] - [title] has been seen [occurrences] times.
  This pattern is recurring enough to warrant a permanent rule.

  Suggested rule: [generated rule text based on the learning's Finding + Mitigation]
options:
  - label: "Promote"
    description: "Add rule to CLAUDE.md and mark learning as promoted"
  - label: "Keep as Learning"
    description: "Keep tracking as a learning, don't promote yet"
  - label: "Raise Threshold"
    description: "Keep as learning, require 5 occurrences before asking again"
```

#### `--verdict-only` mode

Do **NOT** write any learning files. Instead, embed all candidates in the verdict block as the `learning_candidates` field (see [references/verdict-schema.md](${CLAUDE_SKILL_DIR}/references/verdict-schema.md)).

The calling skill (e.g., `/feature`) is responsible for presenting the human gate and persisting accepted learnings. This keeps `/review`'s contract clean: extract candidates, let the caller decide when and how to gate them.

#### `--auto-learn` mode

Auto-accept all candidates:
- `new` → write learning file
- `recurrence` → update existing learning file
- `promotion` → promote to CLAUDE.md and update learning file

No human gate. Log each action.

### Step 6: Persist

For each accepted learning:

**New learnings:**
1. Determine next ID: scan `.claude/learnings/L-*.md`, find highest NNN, increment by 1
2. Create `.claude/learnings/` directory if it doesn't exist
3. Write `L-<NNN>.md` with full frontmatter (per [references/learning-schema.md](${CLAUDE_SKILL_DIR}/references/learning-schema.md)) and body sections
4. Set `occurrences: 1`, `first_seen` and `last_seen` to today, `status: active`

**Recurrences:**
1. Read the existing learning file
2. Increment `occurrences`
3. Update `last_seen` to today
4. If the new finding's files are outside existing scope: merge the new scope glob into the `scope` list
5. Write updated file

**Promotions:**
1. Append the rule to CLAUDE.md with a comment: `# From learning L-<NNN>`
2. Update the learning file: set `status: promoted`, set `promoted_to` to reference the CLAUDE.md entry
3. Increment `occurrences` and update `last_seen`

**Update LEARNINGS.md index:**
Create or update `.claude/learnings/LEARNINGS.md` per the format in [references/learning-schema.md](${CLAUDE_SKILL_DIR}/references/learning-schema.md). Regenerate the full table from all learning files (newest `last_seen` first).

## Error Handling

- **Never fail the review over a learnings issue.** If `.claude/learnings/` cannot be created, if a learning file can't be written, or if any step in this phase errors: warn with a log message and continue to Phase 5 (or exit if `--verdict-only`).
- **Partial persistence is acceptable.** If 3 of 5 candidates are saved before an error, keep the 3 and warn about the remaining 2.
- **Malformed existing learning files:** If a learning file in `.claude/learnings/` can't be parsed, skip it for recurrence matching but don't delete it. Log a warning.
