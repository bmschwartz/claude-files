# Learning Extraction Protocol

> Read this when: executing Phase 4.7 (learning extraction) after synthesis/deliberation.

## Position in Pipeline

Phase 4.7 runs **after** Phase 4.5 (deliberation) completes or is skipped, and **before** the `--verdict-only` gate that controls Phase 5. This positioning ensures learnings are always extracted, even when `/feature` calls `/deep-review --verdict-only`.

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

Run `python3 ${CLAUDE_SKILL_DIR}/scripts/learnings.py list --status active --json`. It prints every active learning in the project's shared store as `{"id", "path", "fields", "body"}`; promoted and expired learnings are not candidates for recurrence matching.

`[]` means the store has no learnings yet, or that the main checkout hasn't been migrated (a warning on stderr says so). Either way, every candidate is `new`.

**The store.** Every checkout of a project (the main checkout and each worktree) shares one store at `~/.claude/projects/<main-checkout slug>/learnings/`; `python3 ${CLAUDE_SKILL_DIR}/scripts/learnings.py paths` prints it, the main checkout's `CLAUDE.md` and whether this session is in a worktree. Each checkout's `.claude/learnings` is a symlink to it (the script re-links a stale worktree copy). Never read, scan or write learning files directly: IDs are only collision-free when the script assigns them under its lock.

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

Present each candidate to the user via `AskQuestion` (Cursor) or `AskUserQuestion` (Claude Code):

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
    description: "Save this learning to the project's learnings store"
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

The calling skill (e.g., `/feature`) is responsible for presenting the human gate and persisting accepted learnings. This keeps `/deep-review`'s contract clean: extract candidates, let the caller decide when and how to gate them.

#### `--auto-learn` mode

Auto-accept all candidates:
- `new` → write learning file
- `recurrence` → update existing learning file
- `promotion` → promote to CLAUDE.md and update learning file

No human gate. Log each action.

### Step 6: Persist

Every write goes through `python3 ${CLAUDE_SKILL_DIR}/scripts/learnings.py`. Write the text you drafted to a file in the round directory first; the script reads it from there. Exit code 2 means the script refused and wrote nothing (the message says why); exit code 3 means the store lock timed out. Neither fails the review (see Error Handling).

**New learnings:**
1. Write `<round dir>/_learning-draft-<n>.md`: frontmatter with `title`, `category`, `severity`, `scope`, `tags` and `source` (per [references/learning-schema.md](${CLAUDE_SKILL_DIR}/references/learning-schema.md)), then the `## Finding`, `## Context` and `## Mitigation` body sections. Leave out `id`, `occurrences`, `first_seen`, `last_seen`, `status`, `promoted_to` and `_staleness_count`: the script sets them.
2. Run `python3 ${CLAUDE_SKILL_DIR}/scripts/learnings.py new --draft <round dir>/_learning-draft-<n>.md`. It prints the assigned ID.

**Recurrences:**
1. Write `<round dir>/_learning-draft-<n>.md` with the new finding's text only (no frontmatter).
2. Run `python3 ${CLAUDE_SKILL_DIR}/scripts/learnings.py recur <id> --draft <that file> --round-dir <round dir> [--scope <glob> ...]`, passing `--scope` for each new glob the finding's files need. The script appends a `## Recurrence — <date> (<round dir>)` section, increments `occurrences`, updates `last_seen` and merges the globs.

**Promotions:**
1. Run `python3 ${CLAUDE_SKILL_DIR}/scripts/learnings.py paths` and read the file at `main_claude_md` (the main checkout's `CLAUDE.md`, even from a worktree). Record its SHA-256 (`shasum -a 256 <file>`).
2. Write the complete revised file to `<round dir>/_claude-md-revised.md`: either a new section, or a rewrite of the section that already covers this pattern. Show the user the diff against the file you read at the promotion gate.
3. Run `python3 ${CLAUDE_SKILL_DIR}/scripts/learnings.py promote <id> --claude-md <round dir>/_claude-md-revised.md --expect-sha <sha> --heading "<section heading>"`. If it refuses because `CLAUDE.md` changed since you read it, re-read the file, redo the edit and run it again.
4. **In the main checkout**, the script writes `CLAUDE.md` and marks the learning `promoted` in one locked step. **In a worktree** it can't write the main checkout's `.claude/`: it queues the promotion in the store, applies the rule to this worktree's own `CLAUDE.md` (when that copy matched the main one), sets `promotion_pending` and leaves the learning `active` until the rule lands. Tell the user the promotion is queued.

**Applying queued promotions (main checkout only).** When `prepare_round.py` warns about pending promotions, or the user asks, run `python3 ${CLAUDE_SKILL_DIR}/scripts/learnings.py apply-promotions --dry-run`, show the user the diff it prints, and ask before applying. On a yes, run `python3 ${CLAUDE_SKILL_DIR}/scripts/learnings.py apply-promotions --expect-sha <the expect-sha line from the dry run>`. A promotion whose lines conflict with later edits stays pending: redo it with `promote` from the main checkout.

**Index:** `LEARNINGS.md` is rebuilt by every command that writes; never edit it.

## Error Handling

- **Never fail the review over a learnings issue.** If `learnings.py` exits 2 (refused) or 3 (store lock timed out), or any step in this phase errors: warn with a log message and continue to Phase 5 (or exit if `--verdict-only`).
- **Partial persistence is acceptable.** If 3 of 5 candidates are saved before an error, keep the 3 and warn about the remaining 2.
- **Malformed existing learning files:** `learnings.py list` skips a file it can't parse and warns on stderr; `recur` and `promote` refuse it. Don't delete it; report it to the user.
