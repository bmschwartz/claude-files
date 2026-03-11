# Plan Review: Multi-Model Analysis & Synthesis

> **v1.3.0** · Last updated 2026-03-04

## Changelog

| Version | Date | Changes |
|---------|------|---------|
|| 1.3.0 | 2026-03-04 | Strengthened reviewer prompt — added TDD verification, spec-claim codebase verification, LLM prompt effectiveness dimension, edge case combination testing. Dimensions expanded from 6 to 8. |
| 1.2.0 | 2026-02-13 | Built-in Opus reviewers — `--count` Opus subagents always run via Task tool alongside external models. `agent` CLI no longer a hard prerequisite (only needed for external models). Step 3 split into 3a (built-in) + 3b (external) + 3c (collect). |
| 1.1.0 | 2026-02-09 | Timestamped review folders — each round gets its own `reviews/<TIMESTAMP>/` directory with prompt, raw reviews, and summary. Added `REVIEW.md` at plan root linking to most recent round. |
| 1.0.0 | 2026-02-09 | Initial version — 8-step review process, plan-reviewer/review-synthesizer subagents, `--models`/`--count`/`--dry-run` flags, iterative review cycles with versioned plan snapshots |

---

Orchestrate a multi-model review of an implementation plan, then synthesize the results, gather user input, and update the plan documents.

This process is iterative — the user may choose to run another review cycle after the plan is updated.

## Arguments

`$ARGUMENTS` contains space-separated tokens:

1. **Project root** (required) — The root directory of the codebase the plan is about (e.g., `/Users/dev/my-project`). Reviewers need this to verify the plan against actual code.
2. **Plan root** (required) — The root directory of the plan (e.g., `.claude/docs/my-feature`). Contains `PLAN.md` at the root and versioned plan snapshots in `plans/`.

**Note:** Paths must not contain spaces. Use symlinks or relative paths if needed.

**Optional flags:**

- `--models <comma-separated-list>` — Override the default review models. Example: `--models composer-1.5,opus-4.6-thinking`
- `--count <N>` — Number of `plan-reviewer` subagents to spawn per model. Default: `2`.
- `--dry-run` — Show which documents would be reviewed, which models would be used, and how many subagents per model, without running any reviews. Useful for verifying setup before spending tokens.

**Built-in reviewers:**

- `--count` Opus subagents always run via the Task tool (no `agent` CLI required). These have native codebase access and deep analysis capabilities.

**Default external models** (when `--models` is not specified):

- `composer-1.5`
- `gpt-5.4-high-fast`
- `gemini-3.1-pro`

Parse `$ARGUMENTS` by splitting on whitespace. Extract any flags first, then treat the remaining positional tokens as project root and plan root. If fewer than two positional paths are provided, report an error and ask the user to provide both paths.

---

## Review Output Structure

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

| File | Purpose | Created by |
|------|---------|------------|
| `REVIEW.md` (plan root) | Links to the most recent review round's `REVIEW_SUMMARY.md` | Step 7 |
| `reviews/<TIMESTAMP>/` | Timestamped directory for a single review round | Step 2 |
| `reviews/<TIMESTAMP>/_review-prompt.md` | Prompt passed to each reviewer model (preserved as audit trail) | Step 2 |
| `reviews/<TIMESTAMP>/review-<MODEL>-<N>.md` | Raw review output from a single subagent (immutable) | `plan-reviewer` subagent |
| `reviews/<TIMESTAMP>/REVIEW_SUMMARY.md` | Synthesized summary for this round (updated in Step 7 with apply/skip status) | `review-synthesizer` subagent |

`<MODEL>` is the model identifier with `/` replaced by `-` (e.g., `opus-4.6-thinking`). Built-in Opus reviewers use the model identifier `opus-internal`. `<N>` is the 1-indexed instance number (e.g., `1`, `2`, `3`). `<TIMESTAMP>` uses `YYYYMMDD-HHMMSS` format and is shared across all files in a single round.

**Immutability rule:** Raw `review-<MODEL>-<N>.md` files must never be modified after creation. `REVIEW_SUMMARY.md` is updated with apply/skip status in Step 7 but raw review content is never changed.

---

## Step 0: Validate Inputs

1. **Prerequisite check:** Verify the `agent` CLI is installed by running `which agent`. If not found, warn: "The `agent` CLI is not found on PATH — external model reviews will be skipped. Only built-in Opus reviewers will run. Install the CLI from https://docs.cursor.com/agent for multi-model coverage." Set a flag to skip external models in Step 3.
2. Verify the project root directory exists.
3. Verify the plan root directory exists and contains `PLAN.md`.
4. Verify at least one versioned plan snapshot exists in `<PLAN_ROOT>/plans/`. If not, report an error: "No plan versions found. Run `/new-feature` first to create an initial plan."
5. Read `PLAN.md` and extract the current plan version directory from the `Current version:` line (e.g., `Current version: \`plans/20260209-143022/\``→ the current version directory is`<PLAN_ROOT>/plans/20260209-143022/`). Verify this directory exists.

If any validation fails, report the error clearly and stop.

---

## Step 1: Discover Plan Documents

Read all files in the current plan version directory (the one `PLAN.md` links point to). List the documents found and briefly summarize each.

The plan documents follow the `/new-feature` convention:

| Document           | Purpose                                                                 |
| ------------------ | ----------------------------------------------------------------------- |
| `SPEC.md`          | Full specification — requirements, implementation phases, iteration log |
| `README.md`        | Navigation guide — document index, quick start, code reference pattern  |
| `KEY_DECISIONS.md` | Quick reference — design decisions, trade-offs, rationale               |
| `CHECKLIST.md`     | Progress tracking — extracted tasks organized by phase                  |
| `PR_STRATEGY.md`   | PR planning — dependency graph, PR sequence, branch names               |
| `FIXTURES.md`      | Test ground truth — pytest fixtures, sample data, assertions            |

Not all documents may be present. Work with whatever exists.

**If `--dry-run` was specified:** Display the list of discovered documents, the number of built-in Opus reviewers, the external models that would be used, and how many subagents per model, then stop. Do not proceed to Step 2.

---

## Step 2: Create Review Round & Write Prompt

Generate the review round timestamp: `REVIEW_TIMESTAMP=$(date +%Y%m%d-%H%M%S)`

Create the round directory: `mkdir -p <PLAN_ROOT>/reviews/<REVIEW_TIMESTAMP>/`

Write the following review prompt to `<PLAN_ROOT>/reviews/<REVIEW_TIMESTAMP>/_review-prompt.md`. This file will be read by each `plan-reviewer` subagent and passed to the `agent` CLI. It is preserved in the round directory as an audit trail.

```
Review the implementation plan documents in this workspace. Read every file thoroughly before beginning your analysis.

If a CLAUDE.md file exists in the workspace root, read it first for project-specific conventions and guidelines. Evaluate the plan's compliance with these conventions.

The plan documents follow these conventions:
- SPEC.md — Full specification: requirements, implementation phases, iteration log
- README.md — Navigation guide: document index, quick start, code reference pattern
- KEY_DECISIONS.md — Quick reference: design decisions, trade-offs, rationale
- CHECKLIST.md — Progress tracking: extracted tasks organized by phase
- PR_STRATEGY.md — PR planning: dependency graph, PR sequence, branch names
- FIXTURES.md — Test ground truth: pytest fixtures, sample data, assertions

Not all documents may be present. Evaluate what exists.

## Codebase Verification (CRITICAL)

You have access to the actual project codebase. **Actively verify every claim the plan makes about the codebase.** Do not take the plan's word for it. Specifically:

- **File paths & line numbers:** Open each referenced file and verify the code at the cited lines matches what the plan describes. Flag any stale or incorrect line references.
- **Function signatures & APIs:** Verify that referenced functions, classes, and methods exist with the signatures the plan assumes. Check parameter names, types, and return types.
- **Existing patterns & conventions:** Read the actual code to confirm the plan's claims about architectural patterns, naming conventions, and module organization. Flag any mischaracterizations.
- **Import paths:** Verify that proposed import changes reference the correct module paths and that claimed "single call site" assertions are actually true (search the codebase).
- **Test patterns:** Verify that proposed test approaches match the project's existing test infrastructure (fixtures, mocking patterns, async handling, test file naming).

## Evaluation Dimensions

Evaluate the plan on the following dimensions:

### 1. Completeness
Are there missing steps, unhandled edge cases, or gaps in the flow?

**Pay special attention to:**
- Input combination coverage: For functions with multiple optional parameters, does the plan test all meaningful combinations? (e.g., if a function takes `trigger` and `intent`, are all combinations of present/absent/specific-values covered?)
- Edge cases at boundaries: What happens with unexpected inputs, None values, or enum values the plan doesn't mention?
- Downstream effects: If the plan changes a function's output, are all consumers of that output accounted for?

### 2. Correctness
Are there logical errors, wrong assumptions, or misuse of APIs/libraries? Do referenced code paths actually exist?

**Pay special attention to:**
- Control flow: Does the plan correctly describe what happens at each branch point? Read the actual code to verify.
- Short-circuit paths: If the codebase has early-return conditions (e.g., returning before reaching modified code), does the plan account for them?
- Dead code: Would any proposed tests or changes be unreachable due to upstream short-circuits?

### 3. Architecture
Is the design sound? Are there better patterns or abstractions? Does it align with existing codebase conventions?

**Pay special attention to:**
- Pattern consistency: If the codebase has an established pattern for the type of change being made (e.g., a Strategy pattern, a factory function), does the plan follow it or deviate? If it deviates, is the deviation justified?
- Module boundaries: Does the plan put logic in the right modules, or does it leak responsibilities across boundaries?
- Single Responsibility: Does each proposed change have a clear, singular purpose?

### 4. TDD Structure
If the plan uses test-driven development (TDD-structured implementation phases with "Tests to Write First"):

- Are the proposed tests specific enough to fail meaningfully? Would they catch real bugs, or are they tautological?
- Do tests validate behavior (what the code does) rather than implementation (how it does it)?
- Is test coverage sufficient? Are there behaviors described in the spec that have no corresponding test?
- Are test descriptions clear enough to implement without ambiguity?

### 5. Dependencies & Ordering
Are tasks sequenced correctly? Are external dependencies identified?

### 6. Risk
What are the riskiest parts? What could block or derail implementation?

**Pay special attention to:**
- Regression risk: Could the proposed changes break existing behavior? Are there callers or consumers that the plan doesn't account for?
- Prompt/LLM behavior risk: If the plan modifies LLM prompts, consider whether the new prompt language will actually achieve the desired behavior. LLMs may interpret prompt changes differently than intended. Flag any prompt changes where the effect is ambiguous or could backfire.

### 7. LLM Prompt Effectiveness (when applicable)
If the plan modifies LLM system prompts or user prompts:

- Will the new prompt language reliably produce the intended behavior? Consider how LLMs prioritize system vs. user prompts, explicit vs. implicit instructions, and competing directives.
- Are there conflicting instructions between system prompts and user prompts that could confuse the model?
- Does the plan address ALL locations where relevant prompt text exists? (e.g., if fixing a "recency over intent" issue in one prompt, check whether the same issue exists in related prompts.)
- Are prompt changes tested? If not, flag the gap — prompt regressions are hard to detect without behavioral tests.

### 8. Scalability & Performance
Will this hold up under load? Any obvious bottlenecks?

## Output Format

For each dimension:
- Give a severity-tagged rating: CRITICAL / IMPORTANT / MINOR / GOOD
- Cite specific files and sections from the plan AND the codebase where relevant
- Provide concrete, actionable suggestions with enough detail to implement

Finish with a **Prioritized Recommendations** section: a numbered list of the most important changes, ordered by impact. Tag each with severity: CRITICAL, IMPORTANT, or MINOR.
```

---

## Step 3: Run Reviews

Use the `REVIEW_TIMESTAMP` generated in Step 2 for all review files in this round. Use the count from `--count` if provided, otherwise `2`.

Launch **both** built-in Opus reviewers and external model reviewers in parallel. All subagents run concurrently in a single batch.

### 3a: Built-in Opus Reviewers (always run)

Launch `<COUNT>` Task tool subagents **in the background** with `model: opus`. These always run regardless of whether the `agent` CLI is available.

Task for each built-in subagent:

```
You are a plan reviewer. Your job is to thoroughly review an implementation plan.

1. Read the review prompt at <PLAN_ROOT>/reviews/<REVIEW_TIMESTAMP>/_review-prompt.md and follow its instructions exactly.
2. Read all plan documents in <CURRENT_PLAN_VERSION_DIR>/.
3. The project codebase is at <PROJECT_ROOT> — use it to verify file paths, APIs, and patterns referenced in the plan.
4. Write your complete review to: <PLAN_ROOT>/reviews/<REVIEW_TIMESTAMP>/review-opus-internal-<N>.md
```

### 3b: External Model Reviewers (when agent CLI available)

**Skip this subsection** if the `agent` CLI was not found in Step 0.

Use the models from `--models` if provided, otherwise the default: `composer-1.5,gpt-5.3-codex-high,gemini-3.1-pro`.

For each external model, use the **Task tool** to spawn `<COUNT>` `plan-reviewer` subagents **in the background**. Each subagent receives a unique instance number `<N>` (1-indexed).

Task for each external subagent:

```
Run a plan review using the Cursor `agent` CLI with the following parameters:

- Model: <MODEL>
- Instance number: <N>
- Review prompt file: <PLAN_ROOT>/reviews/<REVIEW_TIMESTAMP>/_review-prompt.md (pass as the agent prompt)
- Plan directory: <CURRENT_PLAN_VERSION_DIR> (the agent should read all files here)
- Project root: <PROJECT_ROOT> (pass as the working directory so the agent can access the codebase)
- Write the review output to: <PLAN_ROOT>/reviews/<REVIEW_TIMESTAMP>/review-<MODEL>-<N>.md

If the CLI fails, retry once. If it fails again, write a brief error report to the output file explaining what went wrong (exit code, stderr, etc.) so downstream steps can identify the failure.
```

### 3c: Wait and Collect

Run all subagents (3a + 3b) in parallel. As each completes, report progress to the user: "Review complete: `<MODEL>` instance `<N>` (`M` of `TOTAL` remaining)".

Wait for all of them to complete before proceeding.

**Error recovery:** After all subagents finish, verify that each expected review file in `reviews/<REVIEW_TIMESTAMP>/` exists and is non-empty. For any that are missing or contain an error report:

- Note the failure prominently in your output (which model failed, why if known).
- **Continue with the remaining successful reviews.** Do not abort the entire process because one model failed.
- Pass the list of successful and failed reviews to Step 4 so the synthesizer knows what to work with.

**Zero-success guard:** If ALL reviews failed, report the errors and stop. Do not proceed to Step 4. At least one successful review is required for synthesis.

---

## Step 4: Synthesize Reviews via Subagent

Use the **Task tool** to spawn a `review-synthesizer` subagent in the **foreground** with the following task:

```
Synthesize the plan reviews with the following parameters:
- Plan root: <PLAN_ROOT>
- Current plan version directory: <CURRENT_PLAN_VERSION_DIR>
- Review round directory: <PLAN_ROOT>/reviews/<REVIEW_TIMESTAMP>/
- Review files: <list of successful review file paths>
- Failed reviews: <list of models that failed, if any>
```

The subagent will:

1. Read all successful review files from this run and the current plan version documents
2. Cross-reference findings and categorize every recommendation with severity tags into: **Auto-apply**, **Needs your input**, or **Unique insights**
3. Write `<PLAN_ROOT>/reviews/<REVIEW_TIMESTAMP>/REVIEW_SUMMARY.md`
5. Note any failed reviews at the top of the summary so the user is aware of reduced coverage
6. Return a status report with item counts per bucket and severity breakdown

Wait for the subagent to complete. Verify that `<PLAN_ROOT>/reviews/<REVIEW_TIMESTAMP>/REVIEW_SUMMARY.md` exists.

---

## Step 5: Present Summary & Gather Input

Display the full contents of `<PLAN_ROOT>/reviews/<REVIEW_TIMESTAMP>/REVIEW_SUMMARY.md` to the user.

**Auto-apply override:** Before applying changes, ask:

> "Are there any **Auto-apply** items you want to review or skip before I apply them?"

If the user flags any, move those items to the **Needs your input** bucket.

**Gather input on flagged items:** For each item in the **Needs your input** section, use `AskUserQuestion` with options derived from the summary:

```
AskUserQuestion:
  question: "<item title> — <brief context>"
  header: "Item N"
  options:
    - label: "Option A"
      description: "<approach and trade-offs from summary>"
    - label: "Option B"
      description: "<approach and trade-offs from summary>"
    - label: "Skip"
      description: "Defer this decision — do not apply any change"
```

Wait for the user to respond to all items before proceeding. Do NOT move to Step 6 until the user has weighed in on all flagged items.

---

## Step 6: Apply Changes to Plan (New Version)

Create a new plan version:

1. Generate a new timestamp for this version: `NEW_VERSION_TIMESTAMP=$(date +%Y%m%d-%H%M%S)`
2. Create directory: `mkdir -p <PLAN_ROOT>/plans/<NEW_VERSION_TIMESTAMP>/`
3. Copy all files from the current plan version directory into the new version directory: `cp -r <CURRENT_PLAN_VERSION_DIR>/* <PLAN_ROOT>/plans/<NEW_VERSION_TIMESTAMP>/`
4. Apply changes to the files **in the new version directory only**:
   - **Auto-apply items** from the agreement bucket (minus any the user vetoed in Step 5)
   - **User-decided items** based on the input gathered in Step 5
   - **Unique insights** that were marked for auto-apply

**Apply changes per-document.** For each plan document that needs modification:

1.  State which document you are updating and what changes will be made
2.  Apply the changes
3.  Briefly summarize what was modified in that document

After all documents are updated:

- Add a dated entry to the iteration log in `SPEC.md` (if it exists) noting the review round, models used, and summary of changes
- Do NOT modify any files in prior plan version directories
- Do NOT modify raw `review-*-<TIMESTAMP>.md` files

5. Update `<PLAN_ROOT>/PLAN.md` — change all links to point to `plans/<NEW_VERSION_TIMESTAMP>/` and update the `Current version:` line.
6. Create or update `<PLAN_ROOT>/REVIEW.md` — link to the current review round's summary (see Step 7 for the full template).

---

## Step 7: Summarize Diffs & Update REVIEW.md

Present a per-document summary of what changed between the previous plan version and the new one. For each modified document, show:

- Document name
- Number of changes applied
- Brief description of each change

Update `<PLAN_ROOT>/reviews/<REVIEW_TIMESTAMP>/REVIEW_SUMMARY.md` to reflect what was actually applied (mark each item as applied or skipped with the user's rationale if provided).

Create or update `<PLAN_ROOT>/REVIEW.md` with the following structure:

```markdown
# [Feature Name] Reviews

Current review: `reviews/<REVIEW_TIMESTAMP>/`

## Review Rounds

| Round | Date | Models | Plan version reviewed | Summary |
|-------|------|--------|-----------------------|---------|
| N | YYYY-MM-DD | <models used> (failures noted) | `plans/<PLAN_TIMESTAMP>/` | [REVIEW_SUMMARY.md](reviews/<REVIEW_TIMESTAMP>/REVIEW_SUMMARY.md) |
| ... | ... | ... | ... | ... |
```

Newest round first. Each row links to that round's `REVIEW_SUMMARY.md`. This gives a quick overview of all review rounds with audit trail.

---

## Step 8: Final Prompt

Present the per-document diff summary, then ask the user:

> "The plan has been updated (version `<NEW_VERSION_TIMESTAMP>`). Would you like to run another round of plan review, or are you happy with the plan?"

- If the user wants **another round**: Summarize the current round in 3-5 bullet points. Re-read `PLAN.md` to discover the new current version path. Then go back to **Step 2** and repeat the entire process (new review round timestamp, fresh reviews against the now-updated plan version). Carry forward only the round summary, the updated `PLAN.md` path, and the new plan version timestamp — re-read plan documents fresh in Step 1.
- If the user is **satisfied**: confirm completion and end.
