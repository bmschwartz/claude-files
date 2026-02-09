# Plan Review: Multi-Model Analysis & Synthesis

Orchestrate a multi-model review of an implementation plan, then synthesize the results, gather user input, and update the plan documents.

This process is iterative — the user may choose to run another review cycle after the plan is updated.

## Arguments

`$ARGUMENTS` contains space-separated tokens:

1. **Project root** (required) — The root directory of the codebase the plan is about (e.g., `/Users/dev/my-project`). Reviewers need this to verify the plan against actual code.
2. **Plan root** (required) — The root directory of the plan (e.g., `.claude/docs/my-feature`). Contains `PLAN.md` at the root and versioned plan snapshots in `plans/`.

**Note:** Paths must not contain spaces. Use symlinks or relative paths if needed.

**Optional flags:**

- `--models <comma-separated-list>` — Override the default review models. Example: `--models opus-4.6-thinking,gpt-5.2-codex-xhigh`
- `--count <N>` — Number of `plan-reviewer` subagents to spawn per model. Default: `2`.
- `--dry-run` — Show which documents would be reviewed, which models would be used, and how many subagents per model, without running any reviews. Useful for verifying setup before spending tokens.

**Default models** (when `--models` is not specified):
- `opus-4.6-thinking`
- `gpt-5.2-codex-xhigh`

Parse `$ARGUMENTS` by splitting on whitespace. Extract any flags first, then treat the remaining positional tokens as project root and plan root. If fewer than two positional paths are provided, report an error and ask the user to provide both paths.

---

## Review Output Structure

All review artifacts are stored in `<PLAN_ROOT>/reviews/`. The naming conventions below are shared between the `plan-reviewer` and `review-synthesizer` subagents:

| File | Purpose | Created by |
|------|---------|------------|
| `_review-prompt.md` | Prompt passed to each reviewer model | Step 2 (deleted in Step 8) |
| `review-<MODEL>-<N>-<TIMESTAMP>.md` | Raw review output from a single subagent (immutable once written) | `plan-reviewer` subagent |
| `REVIEW_SUMMARY.md` | Synthesized summary across all reviews (updated in Step 7 with apply/skip status) | `review-synthesizer` subagent |

`<MODEL>` is the model identifier with `/` replaced by `-` (e.g., `opus-4.6-thinking`). `<N>` is the 1-indexed instance number (e.g., `1`, `2`, `3`). `<TIMESTAMP>` uses `YYYYMMDD-HHMMSS` format and is shared across all reviews in a single run.

**Immutability rule:** Raw `review-*-<TIMESTAMP>.md` files must never be modified after creation. `REVIEW_SUMMARY.md` is a living document that is updated with apply/skip status in Step 7.

---

## Step 0: Validate Inputs

1. **Prerequisite check:** Verify the `agent` CLI is installed by running `which agent`. If not found, report the error: "The `agent` CLI is required but not found on PATH. Install it from https://docs.cursor.com/agent and try again." Stop.
2. Verify the project root directory exists.
3. Verify the plan root directory exists and contains `PLAN.md`.
4. Verify at least one versioned plan snapshot exists in `<PLAN_ROOT>/plans/`. If not, report an error: "No plan versions found. Run `/new-feature` first to create an initial plan."
5. Read `PLAN.md` and extract the current plan version directory from the `Current version:` line (e.g., `Current version: \`plans/20260209-143022/\`` → the current version directory is `<PLAN_ROOT>/plans/20260209-143022/`). Verify this directory exists.

If any validation fails, report the error clearly and stop.

---

## Step 1: Discover Plan Documents

Read all files in the current plan version directory (the one `PLAN.md` links point to). List the documents found and briefly summarize each.

The plan documents follow the `/new-feature` convention:

| Document | Purpose |
|----------|---------|
| `SPEC.md` | Full specification — requirements, implementation phases, iteration log |
| `README.md` | Navigation guide — document index, quick start, code reference pattern |
| `KEY_DECISIONS.md` | Quick reference — design decisions, trade-offs, rationale |
| `CHECKLIST.md` | Progress tracking — extracted tasks organized by phase |
| `PR_STRATEGY.md` | PR planning — dependency graph, PR sequence, branch names |
| `FIXTURES.md` | Test ground truth — pytest fixtures, sample data, assertions |

Not all documents may be present. Work with whatever exists.

**If `--dry-run` was specified:** Display the list of discovered documents, the models that would be used for review, and how many subagents per model, then stop. Do not proceed to Step 2.

---

## Step 2: Write the Review Prompt

Create the reviews directory if it doesn't exist: `mkdir -p <PLAN_ROOT>/reviews/`

Write the following review prompt to `<PLAN_ROOT>/reviews/_review-prompt.md`. This file will be read by each `plan-reviewer` subagent and passed to the `agent` CLI.

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

You also have access to the actual project codebase. Use it to verify that:
- Referenced file paths, modules, and APIs actually exist
- Proposed architectural patterns are consistent with the existing codebase
- Dependencies and integration points are accurately described
- Test strategies align with existing test patterns

Evaluate the plan on the following dimensions:

1. **Completeness** - Are there missing steps, unhandled edge cases, or gaps in the flow?
2. **Correctness** - Are there logical errors, wrong assumptions, or misuse of APIs/libraries? Do referenced code paths actually exist?
3. **Architecture** - Is the design sound? Are there better patterns or abstractions? Does it align with existing codebase conventions?
4. **Dependencies & Ordering** - Are tasks sequenced correctly? Are external dependencies identified?
5. **Risk** - What are the riskiest parts? What could block or derail implementation?
6. **Scalability & Performance** - Will this hold up under load? Any obvious bottlenecks?

For each dimension:
- Give a severity-tagged rating: CRITICAL / IMPORTANT / MINOR / GOOD
- Cite specific files and sections from the plan AND the codebase where relevant
- Provide concrete, actionable suggestions with enough detail to implement

Finish with a **Prioritized Recommendations** section: a numbered list of the most important changes, ordered by impact. Tag each with severity: CRITICAL, IMPORTANT, or MINOR.
```

---

## Step 3: Run Model Reviews via Subagents

Generate a single timestamp using `date +%Y%m%d-%H%M%S` and reuse it for all reviews in this run.

Use the models from `--models` if provided, otherwise the defaults: `opus-4.6-thinking`, `gpt-5.2-codex-xhigh`. Use the count from `--count` if provided, otherwise `2`.

For each model, use the **Task tool** to spawn `<COUNT>` `plan-reviewer` subagents **in the background** (e.g., 2 models × 2 count = 4 subagents). Each subagent receives a unique instance number `<N>` (1-indexed).

Task for each subagent:

```
Run a plan review using the Cursor `agent` CLI with the following parameters:

- Model: <MODEL>
- Instance number: <N>
- Review prompt file: <PLAN_ROOT>/reviews/_review-prompt.md (pass as the agent prompt)
- Plan directory: <CURRENT_PLAN_VERSION_DIR> (the agent should read all files here)
- Project root: <PROJECT_ROOT> (pass as the working directory so the agent can access the codebase)
- Write the review output to: <PLAN_ROOT>/reviews/review-<MODEL>-<N>-<TIMESTAMP>.md

If the CLI fails, retry once. If it fails again, write a brief error report to the output file explaining what went wrong (exit code, stderr, etc.) so downstream steps can identify the failure.
```

Run all subagents in parallel. As each completes, report progress to the user: "Review complete: `<MODEL>` instance `<N>` (`M` of `TOTAL` remaining)".

Wait for all of them to complete before proceeding.

**Error recovery:** After all subagents finish, verify that each expected review file (`review-<MODEL>-<N>-<TIMESTAMP>.md`) exists and is non-empty. For any that are missing or contain an error report:
- Note the failure prominently in your output (which model failed, why if known).
- **Continue with the remaining successful reviews.** Do not abort the entire process because one model failed.
- Pass the list of successful and failed reviews to Step 4 so the synthesizer knows what to work with.

---

## Step 4: Synthesize Reviews via Subagent

Use the **Task tool** to spawn a `review-synthesizer` subagent in the **foreground** with the following task:

```
Synthesize the plan reviews with the following parameters:
- Plan root: <PLAN_ROOT>
- Current plan version directory: <CURRENT_PLAN_VERSION_DIR>
- Timestamp: <TIMESTAMP>
- Review files: <list of successful review file paths>
- Failed reviews: <list of models that failed, if any>
```

The subagent will:
1. Read all successful review files from this run and the current plan version documents
2. Cross-reference findings and categorize every recommendation with severity tags into: **Auto-apply**, **Needs your input**, or **Unique insights**
3. Consult any prior `reviews/REVIEW_SUMMARY.md` to avoid re-surfacing already-addressed items
4. Write `<PLAN_ROOT>/reviews/REVIEW_SUMMARY.md`
5. Note any failed reviews at the top of the summary so the user is aware of reduced coverage
6. Return a status report with item counts per bucket and severity breakdown

Wait for the subagent to complete. Verify that `<PLAN_ROOT>/reviews/REVIEW_SUMMARY.md` exists.

---

## Step 5: Present Summary & Gather Input

Display the full contents of `<PLAN_ROOT>/reviews/REVIEW_SUMMARY.md` to the user.

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
   1. State which document you are updating and what changes will be made
   2. Apply the changes
   3. Briefly summarize what was modified in that document

After all documents are updated:
- Add a dated entry to the iteration log in `SPEC.md` (if it exists) noting the review round, models used, and summary of changes
- Do NOT modify any files in prior plan version directories
- Do NOT modify raw `review-*-<TIMESTAMP>.md` files

5. Update `<PLAN_ROOT>/PLAN.md` — change all links to point to `plans/<NEW_VERSION_TIMESTAMP>/` and update the `Current version:` line.

---

## Step 7: Summarize Diffs

Present a per-document summary of what changed between the previous plan version and the new one. For each modified document, show:
- Document name
- Number of changes applied
- Brief description of each change

Update `<PLAN_ROOT>/reviews/REVIEW_SUMMARY.md` to reflect what was actually applied (mark each item as applied or skipped with the user's rationale if provided).

---

## Step 8: Clean Up & Final Prompt

Delete `<PLAN_ROOT>/reviews/_review-prompt.md` (no longer needed).

Present the per-document diff summary, then ask the user:

> "The plan has been updated (version `<NEW_VERSION_TIMESTAMP>`). Would you like to run another round of plan review, or are you happy with the plan?"

- If the user wants **another round**: Summarize the current round in 3-5 bullet points. Re-read `PLAN.md` to discover the new current version path. Then go back to **Step 2** and repeat the entire process (new timestamp, fresh reviews against the now-updated plan version). Carry forward only the round summary, the updated `PLAN.md` path, and the new version timestamp — re-read plan documents fresh in Step 1.
- If the user is **satisfied**: confirm completion and end.
