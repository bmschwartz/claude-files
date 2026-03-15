---
name: plan-review
description: Multi-model review and synthesis of implementation plans. Orchestrates parallel AI reviews of spec documents, synthesizes findings, gathers user input, and updates plan documents. Use when the user wants to review a feature plan, validate a specification, or get multi-model analysis before implementation. Typically invoked from /new-feature during the spec approval phase.
disable-model-invocation: true
argument-hint: "<project-root> <plan-root> [--models <list>] [--count <N>] [--dry-run]"
---

# Plan Review: Multi-Model Analysis & Synthesis

> **v1.3.0**

Orchestrate a multi-model review of an implementation plan, then synthesize the results, gather user input, and update the plan documents.

This process is iterative — the user may choose to run another review cycle after the plan is updated.

## Arguments

`$ARGUMENTS` contains space-separated tokens:

1. **Project root** (required) — Root directory of the codebase (e.g., `/Users/dev/my-project`). Reviewers need this to verify plan against actual code.
2. **Plan root** (required) — Root directory of the plan (e.g., `.claude/docs/my-feature`). Contains `PLAN.md` and versioned snapshots in `plans/`.

**Note:** Paths must not contain spaces.

**Optional flags:**
- `--models <comma-separated-list>` — Override default review models
- `--count <N>` — Number of `plan-reviewer` subagents per model (default: `2`)
- `--dry-run` — Show what would be reviewed without running

**Built-in reviewers:** `--count` Opus subagents always run via Agent tool (no `agent` CLI required). Native codebase access.

**Default external models:** `composer-1.5`, `gpt-5.4-high-fast`, `gemini-3.1-pro`

Parse `$ARGUMENTS` by splitting on whitespace. Extract flags first, then treat remaining positional tokens as project root and plan root.

---

## Review Output Structure

See [references/output-structure.md](references/output-structure.md) for the full directory layout and file reference.

---

## Step 0: Validate Inputs

1. **Agent CLI check:** Verify `agent` CLI with `which agent`. If not found, warn that external model reviews will be skipped. Only built-in Opus reviewers will run.
2. Verify project root exists.
3. Verify plan root exists and contains `PLAN.md`.
4. Verify at least one versioned snapshot in `<PLAN_ROOT>/plans/`.
5. Read `PLAN.md`, extract current version path from `Current version:` line, verify directory exists.

If any validation fails, report clearly and stop.

---

## Step 1: Discover Plan Documents

Read all files in the current plan version directory. List and summarize each.

Expected documents (not all may be present):

| Document | Purpose |
|----------|---------|
| `SPEC.md` | Full specification — requirements, phases, iteration log |
| `README.md` | Navigation guide |
| `KEY_DECISIONS.md` | Design decisions, trade-offs, rationale |
| `CHECKLIST.md` | Progress tracking by phase |
| `PR_STRATEGY.md` | PR planning — dependency graph, sequence |
| `FIXTURES.md` | Test ground truth — fixtures, sample data |

**If `--dry-run`:** Display discovered documents, reviewer counts, and models, then stop.

---

## Step 2: Create Review Round & Write Prompt

1. Generate timestamp: `REVIEW_TIMESTAMP=$(date +%Y%m%d-%H%M%S)`
2. Create: `mkdir -p <PLAN_ROOT>/reviews/<REVIEW_TIMESTAMP>/`
3. Write review prompt to `_review-prompt.md` using the template at [templates/review-prompt.md](templates/review-prompt.md). This is preserved as an audit trail.

---

## Step 3: Run Reviews

Launch **both** built-in and external reviewers in parallel.

### 3a: Built-in Opus Reviewers (always run)

Launch `<COUNT>` Agent tool subagents **in background** with `model: opus`:

```
You are a plan reviewer.
1. Read the review prompt at <PLAN_ROOT>/reviews/<REVIEW_TIMESTAMP>/_review-prompt.md
2. Read all plan documents in <CURRENT_PLAN_VERSION_DIR>/
3. The project codebase is at <PROJECT_ROOT> — verify file paths, APIs, and patterns
4. Write your review to: <PLAN_ROOT>/reviews/<REVIEW_TIMESTAMP>/review-opus-internal-<N>.md
```

### 3b: External Model Reviewers (when agent CLI available)

Skip if `agent` CLI not found. For each external model, spawn `<COUNT>` `plan-reviewer` subagents **in background**:

```
Run a plan review using the Cursor `agent` CLI:
- Model: <MODEL>, Instance: <N>
- Review prompt: <PLAN_ROOT>/reviews/<REVIEW_TIMESTAMP>/_review-prompt.md
- Plan directory: <CURRENT_PLAN_VERSION_DIR>
- Project root: <PROJECT_ROOT>
- Output: <PLAN_ROOT>/reviews/<REVIEW_TIMESTAMP>/review-<MODEL>-<N>.md

If CLI fails, retry once. If it fails again, write error report to output file.
```

### 3c: Wait and Collect

Report progress as each completes. Continue with successful reviews if some fail. **Zero-success guard:** Stop if ALL fail.

---

## Step 4: Synthesize Reviews

Launch `review-synthesizer` subagent (from `.claude/agents/review-synthesizer.md`) in **foreground**:

```
Synthesize plan reviews:
- Plan root: <PLAN_ROOT>
- Current version: <CURRENT_PLAN_VERSION_DIR>
- Round directory: <PLAN_ROOT>/reviews/<REVIEW_TIMESTAMP>/
- Successful reviews: <list of paths>
- Failed reviews: <list of failed models>
```

The synthesizer cross-references findings and categorizes into: **Auto-apply**, **Needs your input**, **Unique insights**. Writes `REVIEW_SUMMARY.md`. Verify it exists.

---

## Step 5: Present Summary & Gather Input

Display `REVIEW_SUMMARY.md` to the user.

**Auto-apply override:** Ask if any Auto-apply items should be reviewed first.

**For each "Needs your input" item:** Use `AskUserQuestion` with options derived from the summary (Option A / Option B / Skip).

Wait for all responses before proceeding.

---

## Step 6: Apply Changes to Plan (New Version)

1. Generate new timestamp: `NEW_VERSION_TIMESTAMP=$(date +%Y%m%d-%H%M%S)`
2. Create: `mkdir -p <PLAN_ROOT>/plans/<NEW_VERSION_TIMESTAMP>/`
3. Copy current version files to new directory
4. Apply changes per-document:
   - Auto-apply items (minus any vetoed in Step 5)
   - User-decided items
   - Unique insights marked for auto-apply
5. Add iteration log entry to SPEC.md noting review round, models, and summary of changes
6. Update `PLAN.md` links to point to new version
7. Create/update `REVIEW.md` (see Step 7)

**Do NOT modify files in prior version directories or raw review files.**

---

## Step 7: Summarize & Update REVIEW.md

Present per-document summary of changes. Update `REVIEW_SUMMARY.md` with applied/skipped status.

Create/update `<PLAN_ROOT>/REVIEW.md`:

```markdown
# [Feature Name] Reviews

Current review: `reviews/<REVIEW_TIMESTAMP>/`

## Review Rounds

| Round | Date | Models | Plan version reviewed | Summary |
|-------|------|--------|-----------------------|---------|
| N | YYYY-MM-DD | <models> | `plans/<PLAN_TIMESTAMP>/` | [REVIEW_SUMMARY.md](reviews/<REVIEW_TIMESTAMP>/REVIEW_SUMMARY.md) |
```

Newest round first. Each row links to that round's summary.

---

## Step 8: Final Prompt

Present the diff summary, then ask:

> "The plan has been updated (version `<NEW_VERSION_TIMESTAMP>`). Would you like to run another round of plan review, or are you happy with the plan?"

- **Another round:** Summarize current round in 3-5 bullets. Re-read `PLAN.md` for new version. Go to **Step 2**. Carry forward only the round summary and new paths — re-read plan docs fresh.
- **Satisfied:** Confirm completion and end.

## Additional Resources

- [references/output-structure.md](references/output-structure.md) — Directory layout and file reference
- [templates/review-prompt.md](templates/review-prompt.md) — Review prompt template with all 8 evaluation dimensions
