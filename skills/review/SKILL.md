---
name: review
description: Unified code and plan review with built-in Claude reviewers, optional multi-model analysis, file-relay deliberation, and structured verdicts. Extracts durable review learnings and injects them into future reviews. Reviews code diffs, implementation plans, or specs. Use when the user wants a code review, says "review my code", "check my changes", wants to validate a spec/plan, or when invoked by /feature during design or verification phases. Supports --quick for fast reviews, --external for multi-model, --focus for targeted analysis, and --verdict-only for programmatic consumption.
disable-model-invocation: true
argument-hint: "[--type code|plan|spec] [--quick] [--external] [--changed-only] [--focus <area>] [--verdict-only] [--no-learn] [--auto-learn] [--pr <number>] [files...]"
model: opus
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(git diff*, git log*, git branch*, git rev-parse*, git show*, git merge-base*, gh pr*, mkdir *, date *, which *, python3 */scripts/run_reviewers.py*)
---

# Review

> **v1.1.0** · Unified review skill with learning extraction.

A unified review skill that orchestrates parallel AI reviewers, synthesizes findings with conflict detection, optionally runs file-relay deliberation to resolve reviewer disagreements, and produces a structured verdict. Parameterized by `--type` to handle code diffs, implementation plans, and specs through the same pipeline.

## Arguments

`$ARGUMENTS` contains space-separated tokens. Parse to determine type, scope, and behavior.

### Type Selection

- `--type code` — Review code changes (default when no plan-root positional arg)
- `--type plan` — Review implementation plan documents
- `--type spec` — Review a specification only (subset of plan)
- **Inference:** If `$ARGUMENTS` contains two positional paths (project-root + plan-root), infer `plan`. Otherwise infer `code`.

### Code-Type Flags

| Flag | Effect |
|------|--------|
| _(no flags)_ | Review staged changes with internal Claude reviewers |
| `--quick` | Fast review, CRITICAL issues only, no subagents, no fix prompts, no persistence |
| `--external` | Enable multi-model review via `agent` CLI |
| `--models <list>` | Override default external models (implies `--external`) |
| `--count <N>` | Number of reviewer instances per model (default: 1) |
| `--unstaged` | Review unstaged changes |
| `--all` | Review both staged and unstaged |
| `file1 file2` | Review specific files |
| `HEAD~1` | Review last commit |
| `branch-name` | Review current vs specified branch |
| `--pr <number>` | Review a GitHub PR |
| `--changed-only` | Scope to files changed since last review round |
| `--focus <area>` | Focus synthesis on area (security, performance, tests) |
| `--skip-fix` | Show review but skip interactive fix prompts |
| `--skip-pre-commit` | Skip pre-commit checks |
| `--save` | Persist output (no-op in thorough mode) |
| `--track` | Create TodoWrite entries for each issue |
| `--dry-run` | Show config without running |

### Plan/Spec-Type Flags

| Flag | Effect |
|------|--------|
| `<project-root>` | Positional: root of codebase (required) |
| `<plan-root>` | Positional: root of plan directory (required) |
| `--models <list>` | Override default external models |
| `--count <N>` | Number of reviewer instances per model (default: 2) |
| `--changed-only` | Scope to plan docs modified since last review round |
| `--dry-run` | Show what would be reviewed without running |

### Shared Flags

| Flag | Effect |
|------|--------|
| `--verdict-only` | Produce REVIEW_SUMMARY.md + verdict, skip post-synthesis interaction |
| `--no-deliberation` | Skip deliberation even if conflicts detected |
| `--no-learn` | Skip learning extraction (Phase 4.7) entirely |
| `--auto-learn` | Auto-accept learning candidates without human gate |

**Default external models:** `composer-2-fast`, `gpt-5.4-medium-fast`, `gemini-3-flash`

---

## Live Context

- Agent CLI available: !`which agent 2>/dev/null && echo "yes" || echo "no"`
- Current branch: !`git branch --show-current 2>/dev/null || echo "detached"`
- Repository root: !`git rev-parse --show-toplevel 2>/dev/null || echo "not a git repo"`
- Git prefix (CWD relative to repo root): !`git rev-parse --show-prefix 2>/dev/null || echo ""`
- Staged files: !`git diff --cached --name-only 2>/dev/null`
- Unstaged files: !`git diff --name-only 2>/dev/null`

---

## Workspace Scoping

Reviewers receive the directory where `/review` was invoked, not the full git repository root. When invoked from a subdirectory, this structurally prevents cross-contamination via `--workspace` scoping. When invoked from the repository root, worktree directories are excluded via advisory prompt instructions (reviewers are instructed not to explore them, but this is not structurally enforced by the `--workspace` flag).

### Computing PROJECT_ROOT

- **`GIT_ROOT`**: `git rev-parse --show-toplevel`
- **`GIT_PREFIX`**: `git rev-parse --show-prefix` (CWD relative to git root; empty string if CWD == git root)
- **`PROJECT_ROOT`**: The current working directory (= `GIT_ROOT` when `GIT_PREFIX` is empty)

### Worktree Exclusion

- **`GIT_PREFIX` is empty** (CWD is git/worktree root): Set `EXCLUDE_DIRS` to `[".claude/worktrees"]` (advisory; communicated via prompt instructions)
- **`GIT_PREFIX` is non-empty** (CWD is a subdirectory): Set `EXCLUDE_DIRS` to `[]` — worktrees at `.claude/worktrees/` are outside `PROJECT_ROOT` already
- **Running from within a worktree** (`GIT_ROOT` is itself inside a `.claude/worktrees/` path): `PROJECT_ROOT` = CWD. Set `EXCLUDE_DIRS` to `[]`. Isolation is inherent.

### CLAUDE.md Discovery

Look for CLAUDE.md in `PROJECT_ROOT`. If not found and `PROJECT_ROOT != GIT_ROOT`, also check `GIT_ROOT` for a monorepo-level CLAUDE.md.

---

## Phase Contracts

Each phase declares what it receives, produces, and guarantees. The orchestrator checks contracts, not step numbers. On compaction recovery, re-read only what the current phase contract requires.

---

### Phase 1: Context

**Contract:**
- **Receives:** Parsed arguments, type
- **Produces:** Validated inputs, context report
- **Invariants:** All required inputs exist and are valid. At least one reviewable target exists.

#### Code type

**First:** Compute workspace scoping (`GIT_ROOT`, `GIT_PREFIX`, `PROJECT_ROOT`, `EXCLUDE_DIRS`) per the Workspace Scoping section. Report the scoping decision (e.g., "Workspace scoped to python/services/agent-orchestration/ within /path/to/monorepo"). All subsequent phases use `PROJECT_ROOT` as the working scope.

Then run checks **in parallel** (all independent). Stop if any blocking check fails:
1. Git repository: `git rev-parse --is-inside-work-tree`
2. Merge conflicts: `git diff --check HEAD`
3. PR mode: verify `gh` CLI available
4. External mode: verify `agent` CLI installed
5. Empty diff check
6. Detached HEAD: warn and continue

Read CLAUDE.md per the CLAUDE.md Discovery rules in Workspace Scoping. Look for spec docs in `.claude/docs/[feature-name]/` (match by branch name or diff files).

Launch **in parallel**:
- **Explore agent** (thorough mode only): find similar code patterns, error handling conventions, testing patterns, related impacted code. **Scope exploration to `PROJECT_ROOT`. Do not explore files outside this directory or in `EXCLUDE_DIRS`.**
- **Pre-commit checks** (skip if `--skip-pre-commit`): detect project type, run applicable checks (30s timeout each)

#### Plan/Spec type

Run checks **in parallel**:
1. Verify project root exists
2. Verify plan root exists and contains `PLAN.md`
3. Verify at least one versioned snapshot in `<plan-root>/plans/`
4. Check `agent` CLI availability (warn if not found — only built-in reviewers will run)

Read `PLAN.md`, extract current version path, verify directory exists. Read all plan documents in the current version directory.

**If `--changed-only`:** Compare file modification times against most recent `REVIEW_SUMMARY.md` timestamp. Only include documents modified after baseline. Always include `SPEC.md` (essential context). If all unchanged, report and stop.

**If `--dry-run`:** Display configuration and stop.

---

### Phase 2: Setup

**Contract:**
- **Receives:** Validated inputs, context report
- **Produces:** Round directory with `_review-prompt.md` and (for code) `_diff.patch`
- **Invariants:** Round directory exists. Prompt file written. Diff captured (code type).

#### Code type

1. Get diff via appropriate git command based on scope. **If `GIT_PREFIX` is non-empty**, add `--relative` to the git diff command to produce paths relative to `PROJECT_ROOT` and filter to only in-scope changes. For PR mode, determine the base branch (e.g., `gh pr view --json baseRefName -q .baseRefName`), ensure it is fetched locally (`git fetch origin <base-branch>`), then use `git diff <base-branch>...HEAD --relative` instead of `gh pr diff` (which does not support `--relative`).
2. Show `git diff --stat` summary
3. If diff > 3,000 lines, warn user
4. Check dependency manifest changes
5. Create round directory under `PROJECT_ROOT` per [references/output-structure.md](${CLAUDE_SKILL_DIR}/references/output-structure.md) (i.e., `PROJECT_ROOT/.claude/reviews/<branch>/<timestamp>-<scope>/`)
6. Save `_diff.patch`
7. Write `_review-prompt.md` using [references/code-review-prompt.md](${CLAUDE_SKILL_DIR}/references/code-review-prompt.md)
8. **Inject learnings:** Read [references/learning-injection.md](${CLAUDE_SKILL_DIR}/references/learning-injection.md). Scan `.claude/learnings/` for active learnings matching diff file paths. **Note:** Always use repo-root-relative file paths for learning scope matching (i.e., `git diff --name-only` without `--relative`, even when `GIT_PREFIX` is non-empty). The `--relative` flag only applies to the diff captured in step 1, not to the paths used for learning injection. If matches found, append the `## Known Project Learnings` section to `_review-prompt.md` per the injection format. Cap at 10. Run the staleness check on all evaluated learnings.

**Quick mode:** Skip steps 5-8. Perform direct in-context analysis focusing on CRITICAL issues only. Skip all remaining phases.

#### Plan/Spec type

1. Generate timestamp: `REVIEW_TIMESTAMP=$(date +%Y%m%d-%H%M%S)`
2. Create: `mkdir -p <plan-root>/reviews/<REVIEW_TIMESTAMP>/`
3. Write `_review-prompt.md` using [references/plan-review-prompt.md](${CLAUDE_SKILL_DIR}/references/plan-review-prompt.md)
4. **Inject learnings:** Read [references/learning-injection.md](${CLAUDE_SKILL_DIR}/references/learning-injection.md). Scan `.claude/learnings/` for active learnings matching plan document file paths. If matches found, append the `## Known Project Learnings` section to `_review-prompt.md` per the injection format. Cap at 10. Run the staleness check on all evaluated learnings.

---

### Phase 3: Review Execution

**Contract:**
- **Receives:** Round directory, prompt file, reviewer configuration
- **Produces:** `review-*.md` files in round directory
- **Invariants:** At least one review succeeds (zero-success guard stops the process)

Launch **all reviewers in parallel** (`run_in_background: true`) in a single message:

#### Internal reviewers (always in thorough mode)

Launch `<COUNT>` `Explore` agents (`model: "opus"`, `subagent_type: "Explore"`). Each receives the review prompt content, the target (diff or plan docs), codebase patterns from Phase 1, CLAUDE.md rules, and spec docs if available. **Include workspace scoping:** "Your workspace is scoped to {PROJECT_ROOT}. Only explore files within this directory." When `EXCLUDE_DIRS` is non-empty, append: "Do not explore these directories: {EXCLUDE_DIRS joined by comma}."

**IMPORTANT:** `Explore` agents cannot write files. After each completes, the **orchestrator** captures its output and writes it to `review-<source>-<N>.md` in the round directory. Source is `claude-code` for code type, `opus-internal` for plan/spec type.

#### External reviewers (with `--external` or when `agent` CLI available for plan/spec)

Build a JSON configuration object with one task per (model, instance) combination. Each task specifies: `model`, `instance`, `type`, `project_root` (**set to `PROJECT_ROOT`**, not `GIT_ROOT`), `review_prompt_path`, `output_path` (`<ROUND_DIR>/review-<MODEL>-<N>.md`), `input_path` (diff file or plan directory), `input_type` (`diff` or `plan_dir`), and `exclude_dirs` (**set to `EXCLUDE_DIRS`**; omit or pass `[]` when empty). Model names must match `[a-zA-Z0-9._-]+`. Each `(model, instance)` pair must be unique. At the top level of the JSON config (not per-task), include `timeout_seconds` (default 300), `retry_count` (default 1), `retry_delay_seconds` (default 10).

Run the reviewer script:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/run_reviewers.py" <<< '<JSON_CONFIG>'
```

Parse the JSON output from stdout. Each result has `status` (`success`, `retry_success`, or `failed`), `output_path`, and `file_size`. Failed reviewers are noted for the zero-success guard and synthesis metadata. Progress lines appear on stderr.

#### Progress and error recovery

Report progress as each reviewer completes. For missing/errored review files, note failure and continue. **Zero-success guard:** If ALL reviews failed, stop immediately, report the error to the user (list each reviewer's failure reason), and do not proceed to synthesis. No verdict is produced.

---

### Phase 4: Synthesis

**Contract:**
- **Receives:** Completed review files, type, round directory
- **Produces:** `REVIEW_SUMMARY.md` with verdict block
- **Invariants:** 75% quorum met. Every finding in exactly one section. Verdict block present.

**Quorum trigger:** Begin synthesis when **75% of reviewers** (rounded up) have completed. If a straggler finishes while the synthesizer is running, include its results. If it finishes after, append as a **"Late Review"** addendum.

Launch `review-synthesizer` agent in **foreground** with: type, mode `initial`, round directory, completed review file paths, failed reviews, diff/plan path, and focus filter.

The synthesizer cross-references findings, categorizes them, detects conflicts, generates the verdict block, and writes `REVIEW_SUMMARY.md`. Verify it exists.

---

### Phase 4.5: Deliberation (conditional)

**Contract:**
- **Receives:** `REVIEW_SUMMARY.md` with `## Conflicts` section
- **Produces:** Updated `REVIEW_SUMMARY.md` with `## Deliberation Outcomes`, updated verdict
- **Invariants:** Max 1 deliberation round. Each conflict resolved or flagged unresolved.

**Skip if:** `--no-deliberation`, `--quick`, or no conflicts detected in Phase 4.

Read the full deliberation protocol at [protocols/deliberation.md](${CLAUDE_SKILL_DIR}/protocols/deliberation.md).

**Summary:**
1. Read conflicts from `REVIEW_SUMMARY.md`
2. For each conflict, write `rebuttal-<REVIEWER>-C<N>.md` with the opposing position and specific question
3. Launch targeted reviewer: Explore agent for internal reviewers, or `run_reviewers.py` script for external (build a single-task JSON config with the rebuttal prompt as `review_prompt_path`)
4. Capture response to `rebuttal-response-<REVIEWER>-C<N>.md`
5. Re-invoke synthesizer in `re-synthesis` mode with rebuttal files
6. Verify updated `REVIEW_SUMMARY.md` replaces Conflicts with Deliberation Outcomes

**Cap:** 1 round. Unresolved conflicts → `verdict.conflicts.unresolved > 0` → `decision: BLOCK`.

---

### Phase 4.7: Learning Extraction

**Contract:**
- **Receives:** `REVIEW_SUMMARY.md` with verdict block
- **Produces:** Learning files in `.claude/learnings/` (interactive mode) or `learning_candidates` in verdict block (`--verdict-only` mode)
- **Invariants:** Never fails the review. Existing learnings never deleted (only updated or expired).

**Skip if:** `--no-learn` or `--quick`.

Read the full extraction protocol at [protocols/learning-extraction.md](${CLAUDE_SKILL_DIR}/protocols/learning-extraction.md).

**Summary:**
1. Parse findings from REVIEW_SUMMARY.md (severity >= IMPORTANT, agreement >= Moderate)
2. Load existing learnings from `.claude/learnings/`
3. Match candidates against existing learnings (LLM-assisted recurrence detection)
4. **Interactive mode** (no `--verdict-only`, no `--auto-learn`): present candidates via human gate — Save | Skip | Edit scope. For 3+ occurrence promotions, offer CLAUDE.md rule promotion.
5. **`--verdict-only` mode:** Embed candidates in verdict block as `learning_candidates` field. Do not write learning files — the calling skill handles persistence.
6. **`--auto-learn` mode:** Auto-accept all candidates, auto-promote promotions.
7. Persist accepted learnings: write/update learning files, update `.claude/learnings/LEARNINGS.md` index.

---

### Phase 5: Post-Synthesis

**Contract:**
- **Receives:** `REVIEW_SUMMARY.md` with verdict
- **Produces:** Applied fixes (code) or updated plan (plan/spec). Updated REVIEW.md index.
- **Invariants:** Skipped if `--verdict-only`. Verdict block preserved.

**Skip if `--verdict-only`.** When invoked by `/feature`, always use `--verdict-only` — the caller handles post-synthesis actions.

#### Code type — Interactive Fix Application

**(Skip if `--skip-fix` or `--quick`)**

Read structured issues from `REVIEW_SUMMARY.md`. For each fixable issue (CRITICAL → IMPORTANT → MINOR):

Show: location, severity, agreement, current code, suggested fix, explanation.

Use `AskUserQuestion`:
```
question: "Apply this fix to [file:line]?"
header: "Fix 1/N"
options:
  - label: "Apply"
    description: "Apply this fix and continue to next issue"
  - label: "Skip"
    description: "Skip this fix and continue to next issue"
  - label: "Apply All"
    description: "Apply this and all remaining fixes without prompting"
  - label: "Skip All"
    description: "Skip all remaining fixes"
```

After processing, update `REVIEW_SUMMARY.md` with applied/skipped status.

#### Plan/Spec type — Gather Input & Apply

**Auto-apply override:** Ask if any Auto-apply items should be reviewed first.

**For each "Needs your input" item:** Use `AskUserQuestion` with options derived from the summary.

After all responses:
1. Create new plan version: `mkdir -p <plan-root>/plans/<NEW_TIMESTAMP>/`
2. Copy current version files
3. Apply auto-apply items (minus vetoed) + user-decided items + approved unique insights
4. Add iteration log entry to SPEC.md
5. Update `PLAN.md` links

#### Update REVIEW.md (both types)

Create/update the REVIEW.md index file at the appropriate location (`PROJECT_ROOT/.claude/reviews/REVIEW.md` for code, `<plan-root>/REVIEW.md` for plan/spec). Newest round first, linking to each round's summary.

---

## Review Output (code type)

See [references/output-format.md](${CLAUDE_SKILL_DIR}/references/output-format.md) for the complete output format. Key sections: Change Overview, Summary, Critical/Important/Minor/Potential Issues, Spec Compliance, Recommendation (APPROVE / NEEDS_FIXES / BLOCK).

---

## Agents

### Built-in (via Agent tool)

| Agent | Purpose | When used | Model |
|-------|---------|-----------|-------|
| `Explore` | Codebase pattern discovery (Phase 1) | Thorough mode, code type | `opus` |
| `Explore` | Built-in reviewer (× count, read-only) | Thorough mode, all types | `opus` |

### Custom (from `agents/`)

| Agent | Purpose | When used | Model |
|-------|---------|-----------|-------|
| `review-synthesizer` | Synthesizes findings into `REVIEW_SUMMARY.md` with verdict | Thorough mode, all types | `opus` |

### Scripts (from `skills/review/scripts/`)

| Script | Purpose | When used |
|--------|---------|-----------|
| `run_reviewers.py` | Runs `agent` CLI concurrently for all external reviewers | Phase 3 external, Phase 4.5 external deliberation |

---

## Key Principles

- **Multi-model coverage** — Different models catch different things
- **Structured verdicts** — Machine-readable decisions, not prose parsing
- **File-relay deliberation** — Resolve conflicts through targeted re-engagement, not full re-review
- **Fail gracefully** — Continue with partial results; zero-success guard stops
- **Always persist in thorough mode** — Every round creates an audit trail
- **Immutability** — Raw `review-*.md` files never modified after creation
- **Learnings accumulate** — Durable patterns extracted from reviews improve future reviews without manual curation

## Additional Resources

- **Protocols:**
  - [protocols/synthesis.md](${CLAUDE_SKILL_DIR}/protocols/synthesis.md) — Cross-referencing rules, agreement thresholds, severity definitions
  - [protocols/deliberation.md](${CLAUDE_SKILL_DIR}/protocols/deliberation.md) — File-relay conflict resolution protocol
  - [protocols/convergence.md](${CLAUDE_SKILL_DIR}/protocols/convergence.md) — Verdict decision logic, when to stop reviewing
  - [protocols/learning-extraction.md](${CLAUDE_SKILL_DIR}/protocols/learning-extraction.md) — Learning extraction and recurrence detection (Phase 4.7)

- **References:**
  - [references/code-review-prompt.md](${CLAUDE_SKILL_DIR}/references/code-review-prompt.md) — Code review prompt template for external reviewers
  - [references/plan-review-prompt.md](${CLAUDE_SKILL_DIR}/references/plan-review-prompt.md) — Plan review prompt template for external reviewers
  - [references/verdict-schema.md](${CLAUDE_SKILL_DIR}/references/verdict-schema.md) — Verdict block schema documentation (v2)
  - [references/output-structure.md](${CLAUDE_SKILL_DIR}/references/output-structure.md) — Directory layout, branch sanitization, scope suffixes
  - [references/output-format.md](${CLAUDE_SKILL_DIR}/references/output-format.md) — Complete code review output format (sections 0-13)
  - [references/learning-schema.md](${CLAUDE_SKILL_DIR}/references/learning-schema.md) — Learning file frontmatter specification
  - [references/learning-injection.md](${CLAUDE_SKILL_DIR}/references/learning-injection.md) — Scope matching and injection into prompts
