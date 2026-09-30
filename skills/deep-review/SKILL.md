---
name: deep-review
description: Deep multi-model review pipeline with deliberation, structured verdicts, and learning extraction (invoke as /deep-review — not Cursor's built-in /review). Unified code and plan review with built-in reviewers, optional multi-model analysis via Task subagents (Cursor) or agent CLI (Claude Code), file-relay deliberation, and structured verdicts. Extracts durable review learnings and injects them into future reviews. Use when the user wants a code review, says "review my code", "check my changes", wants to validate a spec/plan, or when invoked by /feature during design or verification phases.
disable-model-invocation: true
argument-hint: "[--type code|plan|spec] [--quick] [--external] [--changed-only] [--focus <area>] [--verdict-only] [--no-learn] [--auto-learn] [--pr <number>] [files...]"
model: opus
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(git diff*, git log*, git branch*, git rev-parse*, git show*, git merge-base*, gh pr*, mkdir *, date *, which *, python3 */scripts/run_reviewers.py*, python3 */scripts/prepare_round.py*)
---

# Deep Review

> **v1.4.0** · Per-model prompts: every reviewer model gets the same rubric, delivered the way its vendor's official guidance recommends (section order, framing, exploration budget), from a profile in [references/model-profiles/](${CLAUDE_SKILL_DIR}/references/model-profiles/README.md). A model without a profile falls back to the shared baseline with a loud warning. External reviewers run with `stream-json`, so every run logs its tool calls and a timeout shows how far it got.
>
> **v1.3.0** · Speed pass: round setup is one `prepare_round.py` call; internal reviewers (`deep-reviewer`) write their own review files; `run_reviewers.py` enforces an external quorum with a straggler cut-off and no longer retries timeouts; leaner synthesis output; cheaper deliberation. Cursor external reviewers use Task subagents; agent CLI remains Claude Code default and Cursor fallback.

A unified deep-review skill that orchestrates parallel AI reviewers, synthesizes findings with conflict detection, optionally runs file-relay deliberation to resolve reviewer disagreements, and produces a structured verdict. Parameterized by `--type` to handle code diffs, implementation plans, and specs through the same pipeline.

## Host compatibility (Cursor vs Claude Code)

- **Skill directory:** `REVIEW_SKILL_DIR="${CLAUDE_SKILL_DIR:-$HOME/.claude/skills/deep-review}"`. Every `${CLAUDE_SKILL_DIR}/...` path below means `$REVIEW_SKILL_DIR/...`.
- **Invoke as `/deep-review`.** Cursor's built-in `/review` and `/multi-model-review` are separate, lighter workflows.
- **Questions:** use `AskQuestion` in Cursor, `AskUserQuestion` in Claude Code. Same options either way.
- **Internal reviewers:** use the custom `deep-reviewer` agent (user-level), which writes its own review file and reports its model ID. Claude Code: `model: opus` (the alias is kept on purpose; the model-ID check catches when it moves to a version the `opus` profile wasn't tuned for). Cursor: `model: inherit` (do not pass `opus` to Cursor's Task tool). Only if `deep-reviewer` is unavailable, fall back to `Explore` / `explore` and have the orchestrator write each returned review to its output path.
- **External reviewers:** On **Cursor**, launch readonly `generalPurpose` Task subagents in parallel (same mechanism as `/multi-model-review`, but with each model's `_review-prompt-<key>.md` and `review-*.md` outputs). On **Claude Code**, use `run_reviewers.py` + `agent` CLI. See [references/external-reviewers.md](${CLAUDE_SKILL_DIR}/references/external-reviewers.md). Pass `--agent-cli` to force agent CLI on Cursor.
- **Synthesizer:** launch the custom `review-synthesizer` agent (user-level), not Cursor's built-in synthesizer subagent type unless the custom agent is missing.

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
| _(no flags)_ | Review staged changes with multi-model review enabled (`--external` on by default) |
| `--quick` | Fast review, CRITICAL issues only, no subagents, no fix prompts, no persistence |
| `--external` | Enable multi-model external reviewers (**default: on**). Cursor: Task subagents. Claude Code: `agent` CLI |
| `--no-external` | Disable external reviewers; internal `deep-reviewer` reviewers only |
| `--agent-cli` | Force `agent` CLI for external reviewers (Cursor only; skips Task subagent path) |
| `--models <list>` | Override default external models (implies `--external`) |
| `--count <N>` | Number of reviewer instances per model (default: 1) |
| `--unstaged` | Review unstaged changes |
| `--all` | Review both staged and unstaged |
| `file1 file2` | Review specific files |
| `HEAD~1` | Review last commit |
| `branch-name` | Review current vs specified branch |
| `--pr <number>` | Review a GitHub PR |
| `--changed-only` | Scope to files changed since last review round |
| `--deep-explore` | Run a Phase 1 Explore pre-pass to discover codebase patterns and inject them into reviewer prompts. Off by default — reviewers already explore on their own; enable for unfamiliar codebases or very large diffs. |
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
| `--count <N>` | Number of reviewer instances per model (default: 1) |
| `--changed-only` | Scope to plan docs modified since last review round |
| `--dry-run` | Show what would be reviewed without running |

### Shared Flags

| Flag | Effect |
|------|--------|
| `--verdict-only` | Produce REVIEW_SUMMARY.md + verdict, skip post-synthesis interaction |
| `--no-deliberation` | Skip deliberation even if conflicts detected |
| `--no-learn` | Skip learning extraction (Phase 4.7) entirely |
| `--auto-learn` | Auto-accept learning candidates without human gate |

**Default external models:** `composer-2.5`, `gpt-5.6-terra-high`, `gemini-3.8-flash-high`, `grok-4.7-high`

Each model's prompt comes from its profile in [references/model-profiles/](${CLAUDE_SKILL_DIR}/references/model-profiles/README.md), keyed by the slug without its effort suffix (`gpt-5.6-terra-high` → `gpt-5.6-terra`). When you change a default model or pass a new one with `--models`, add its profile from the vendor's official guidance; until then it runs on the shared baseline and every review shows a warning.

> `grok-4.7-high` replaces `cursor-grok-4.6-high`, which was dropped from the defaults for never being the sole source of a CRITICAL/IMPORTANT finding and for frequent stragglers/timeouts. If 4.7 shows the same pattern, drop it and pass it via `--models` when wanted.
>
> Successful external reviewers finish in 3–9 minutes. `run_reviewers.py` uses `timeout_seconds: 480`, does not retry timeouts, and once 75% of externals have succeeded gives stragglers 90s before cutting them off (`quorum_fraction` / `quorum_grace_seconds` in `_reviewers-config.json`).

---

## Live Context

- Agent CLI available: !`which agent 2>/dev/null && echo "yes" || echo "no"`
- Cursor session: !`[ -n "$CURSOR_CONVERSATION_ID" ] && echo "yes" || echo "no"`
- Current branch: !`git branch --show-current 2>/dev/null || echo "detached"`
- Repository root: !`git rev-parse --show-toplevel 2>/dev/null || echo "not a git repo"`
- Git prefix (CWD relative to repo root): !`git rev-parse --show-prefix 2>/dev/null || echo ""`
- Staged files: !`git diff --cached --name-only 2>/dev/null`
- Unstaged files: !`git diff --name-only 2>/dev/null`

---

## Workspace Scoping

`prepare_round.py` computes all of the values below and reports them in its JSON output; this section documents the rules it applies.

Reviewers receive the directory where `/deep-review` was invoked, not the full git repository root. When invoked from a subdirectory, this structurally prevents cross-contamination via `--workspace` scoping. When invoked from the repository root, worktree directories are excluded via advisory prompt instructions (reviewers are instructed not to explore them, but this is not structurally enforced by the `--workspace` flag).

### Computing PROJECT_ROOT

- **`GIT_ROOT`**: `git rev-parse --show-toplevel`
- **`GIT_PREFIX`**: `git rev-parse --show-prefix` (CWD relative to git root; empty string if CWD == git root)
- **`PROJECT_ROOT`**: The current working directory (= `GIT_ROOT` when `GIT_PREFIX` is empty)

### Worktree Exclusion

- **`GIT_PREFIX` is empty** (CWD is git/worktree root): Set `EXCLUDE_DIRS` to `[".claude/worktrees"]` (advisory; communicated via prompt instructions)
- **`GIT_PREFIX` is non-empty** (CWD is a subdirectory): Set `EXCLUDE_DIRS` to `[]` — worktrees at `.claude/worktrees/` are outside `PROJECT_ROOT` already
- **Running from within a worktree** (`GIT_ROOT` is itself inside a `.claude/worktrees/` path): `PROJECT_ROOT` = CWD. Set `EXCLUDE_DIRS` to `[]`. Isolation is inherent.

### CLAUDE.md Discovery

Look for `CLAUDE.md` and `.claude/CLAUDE.md` in `PROJECT_ROOT` (`AGENTS.md` if neither exists). If not found and `PROJECT_ROOT != GIT_ROOT`, also check `GIT_ROOT` for a monorepo-level file. Cursor treats `CLAUDE.md` like `AGENTS.md`.

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

Workspace scoping is computed by `prepare_round.py` in Phase 2; report its decision from the script output (e.g., "Workspace scoped to python/services/agent-orchestration/ within /path/to/monorepo").

Run checks **in parallel** (all independent). Stop if any blocking check fails:
1. Git repository: `git rev-parse --is-inside-work-tree`
2. Merge conflicts: `git diff --check HEAD`
3. PR mode: verify `gh` CLI available
4. External mode: on **Cursor** (without `--agent-cli`), Task subagents are used — no agent CLI required. On **Claude Code** or with `--agent-cli`, verify `agent` CLI is installed; if missing and `--external` is on, warn and run internal reviewers only
5. Empty diff check (`prepare_round.py` also refuses an empty diff)
6. Detached HEAD: warn and continue

Do not read or transcribe CLAUDE.md — `prepare_round.py` inlines it. Identify spec docs for the change (e.g. `.claude/docs/[feature-name]/`, or ticket/spec files in `.claude/docs/` matching the branch or diff) and pass each as `--spec-file`.

Launch **in parallel**:
- **Explore agent** (thorough mode with `--deep-explore` only): find similar code patterns, error handling conventions, testing patterns, related impacted code. **Scope exploration to `PROJECT_ROOT`. Do not explore files outside this directory or in `EXCLUDE_DIRS`.** Skipped by default — Phase 3 `deep-reviewer` agents perform diff-driven exploration without needing this pre-pass. Opt in via `--deep-explore` for unfamiliar codebases or very large diffs where shared priming amortizes across reviewers. Write its findings to a file and pass it to `prepare_round.py` as `--patterns-file`, so Phase 2 runs after it.
- **Pre-commit checks** (skip if `--skip-pre-commit`): detect project type, run applicable checks (30s timeout each)

#### Plan/Spec type

Run checks **in parallel**:
1. Verify project root exists
2. Verify plan root exists and contains `PLAN.md`
3. Verify at least one versioned snapshot in `<plan-root>/plans/`
4. External mode: on Cursor without `--agent-cli`, Task subagents suffice. Otherwise verify `agent` CLI (warn if missing — internal reviewers only)

Read `PLAN.md`, extract current version path, verify directory exists. Read all plan documents in the current version directory.

**If `--changed-only`:** Compare file modification times against most recent `REVIEW_SUMMARY.md` timestamp. Only include documents modified after baseline. Always include `SPEC.md` (essential context). If all unchanged, report and stop.

**If `--dry-run`:** Display configuration and stop.

---

### Phase 2: Setup

**Contract:**
- **Receives:** Validated inputs, context report
- **Produces:** Round directory with one `_review-prompt-<key>.md` per reviewer model and (for code) `_diff.patch`
- **Invariants:** Round directory exists. Prompt files written. Diff captured (code type).

#### Code type

Run **one** Bash call. The script creates the round directory, captures `_diff.patch`, matches and injects learnings (including the staleness check), renders [references/code-review-prompt.md](${CLAUDE_SKILL_DIR}/references/code-review-prompt.md) through each reviewer model's profile into `_review-prompt-<key>.md`, and writes `_reviewers-config.json`:

```bash
python3 "${CLAUDE_SKILL_DIR:-$HOME/.claude/skills/deep-review}/scripts/prepare_round.py" --type code \
  --diff-args "<git diff args>" --scope-suffix <suffix> \
  [--branch-name <head-branch>] [--spec-file <path> ...] [--patterns-file <path>] \
  [--models <list>] [--count <N>] [--no-external] --context-stdin <<'CONTEXT'
<Change Context: 2-8 bullets — PR title/description/labels in PR mode, author decisions to respect, verification already done. Omit --context-stdin and the heredoc if there is nothing to add.>
CONTEXT
```

| Scope | `--diff-args` | `--scope-suffix` |
|-------|---------------|------------------|
| staged (default) | `--cached` | `staged` |
| `--unstaged` | `""` | `unstaged` |
| `--all` | `HEAD` | `all` |
| `HEAD~1` / commit `<sha>` | `<sha>~1 <sha>` | `commit-<short-sha>` |
| `branch-name` | `<branch>...HEAD` | `vs-<branch>` |
| `--pr <n>` | `<base>...HEAD` (after `git fetch origin <base>`; base from `gh pr view --json baseRefName`) | `pr-<n>`, plus `--branch-name` from `headRefName` |
| files | `HEAD -- <file> ...` | `files` |
| `--changed-only` | the delta range since the last round | `delta` |

The script adds `--relative` itself when `GIT_PREFIX` is non-empty and always matches learnings against repo-root-relative paths. Parse its stdout JSON: on `"status": "error"` stop and report. Otherwise show `diff_stat`, warn if `large_diff` (> 3,000 lines), call out `manifest_changes`, and report `learnings` (matched, omitted, expired) and `warnings`. If `profile_warnings` is non-empty, show each one prominently now and keep them for the synthesizer and the final output: those reviewers run on the untuned shared baseline. Keep `round_dir`, `internal_prompt_path`, `internal_profile`, `input_path`, `internal_outputs`, `external_outputs`, `reviewers_config_path` and `profile_warnings` for Phase 3.

With `--dry-run`, pass `--dry-run` to the script, display its output, and stop.

**Quick mode:** Do not run the script. Perform direct in-context analysis focusing on CRITICAL issues only. Skip all remaining phases.

#### Plan/Spec type

Run **one** Bash call:

```bash
python3 "${CLAUDE_SKILL_DIR:-$HOME/.claude/skills/deep-review}/scripts/prepare_round.py" --type <plan|spec> \
  --plan-input <plan version directory, or a single plan/spec file> [--plan-root <plan-root>] \
  [--models <list>] [--count <N>] [--no-external] [--context-stdin <<'CONTEXT' ... CONTEXT]
```

With `--plan-root`, the round directory is `<plan-root>/reviews/<timestamp>/`; otherwise it is `PROJECT_ROOT/.claude/reviews/<branch>/<timestamp>-<type>/`. The script renders [references/plan-review-prompt.md](${CLAUDE_SKILL_DIR}/references/plan-review-prompt.md) through the same model profiles and matches learnings against file paths referenced in the plan documents. Handle its JSON output as for code type.

---

### Phase 3: Review Execution

**Contract:**
- **Receives:** Round directory, prompt files, reviewer configuration
- **Produces:** `review-*.md` files in round directory
- **Invariants:** At least one review succeeds (zero-success guard stops the process)

Launch **all reviewers in parallel** in a single message: every internal `deep-reviewer` agent and (Claude Code) the background `run_reviewers.py` Bash call. On Cursor, set `run_in_background: true` on every Task call.

#### Internal reviewers (always in thorough mode)

Launch `<COUNT>` `deep-reviewer` agents with `run_in_background: true`. On **Claude Code**, `model: "opus"` (subagents inherit session effort — do not lower it). On **Cursor**, `model: "inherit"`, and pass `--internal-source cursor-internal` to `prepare_round.py` so the output names match.

Keep the agent prompt short — everything else is in the prompt file. Pass only paths:

```
mode: review
prompt file: <internal_prompt_path>
input: <input_path>
output path: <internal_outputs[N-1]>
workspace root: <PROJECT_ROOT> (explore only inside it)
excluded directories: <EXCLUDE_DIRS, or "none">
```

Do not paste the diff, CLAUDE.md or spec docs into the agent prompt. Each agent writes its own review file and replies with a one-line status, `<output path> | model <id> | <counts>` — **do not re-write its review**. If the file is missing or under 200 bytes when the agent reports done, mark that reviewer failed.

**Model check:** compare the reported model ID with `internal_profile.verified_against`. If they differ, add a profile warning: "Internal reviewer ran as `<reported>`, but the `opus` profile was tuned for `<verified_against>`; re-check references/model-profiles/opus.md against Anthropic's guidance for the new model." If the reply has no model ID, warn that the check could not run.

Fallback when `deep-reviewer` is unavailable: launch `Explore` / `explore` with the same paths, then write each returned review to its `internal_outputs` path.

#### External reviewers (when `--external` and not `--quick`)

Read [references/external-reviewers.md](${CLAUDE_SKILL_DIR}/references/external-reviewers.md) for the full protocol. Summary:

**Backend selection:**
- **Cursor** and not `--agent-cli` → **Task subagents** (preferred)
- **Claude Code** or `--agent-cli` → **`run_reviewers.py`** + agent CLI

**Shared setup:** already done — `prepare_round.py` wrote one task per `(model, instance)` to `_reviewers-config.json` and listed the output paths in `external_outputs`. The Cursor Task path uses the same tasks.

##### Cursor path — Task subagents

In the **same turn** as internal `deep-reviewer` Tasks, launch one Task per external `(model, instance)`:

```
Task(
  subagent_type: "generalPurpose",
  readonly: true,
  model: "<model slug>",
  run_in_background: true,
  prompt: <external reviewer prompt from external-reviewers.md>
)
```

**Mandatory:** all external Task calls fire together with internal `deep-reviewer` Tasks — never one-at-a-time.

When each Task completes, write its full response to the task's `output_path`. Track `success` / `failed` per reviewer. Invalid model slug → one retry with corrected slug, then `failed`.

##### Claude Code / `--agent-cli` path — agent CLI

`prepare_round.py` already wrote the config. Run it with the Bash tool's `run_in_background: true` — never in the foreground (it can run ~10 minutes):

```bash
python3 "${CLAUDE_SKILL_DIR:-$HOME/.claude/skills/deep-review}/scripts/run_reviewers.py" < "<ROUND_DIR>/_reviewers-config.json" > "<ROUND_DIR>/_external-results.json" 2> "<ROUND_DIR>/_external-progress.log"
```

You are notified when it exits; then parse `_external-results.json`. Each result: `status` (`success` | `retry_success` | `failed` | `cut_off`), `output_path`, `file_size`, optional `error`, and `telemetry` (tool-call counts, the last tool call, token usage; the full list is in `_log-<output stem>.jsonl`). `cut_off` means the reviewer was still running when the external quorum grace period expired. For a timed-out or cut-off reviewer, report its tool-call count and last tool call, which show whether it was over-exploring or just slow.

**If Cursor Task path partially fails:** retry failed reviewers once via Task; any still failing may fall back to a single-task `run_reviewers.py` call if `agent` is available and user did not forbid it.

#### Progress and error recovery

Report progress as each reviewer completes. For missing/errored review files, note failure and continue. **Zero-success guard:** If ALL reviews failed, stop immediately, report the error to the user (list each reviewer's failure reason), and do not proceed to synthesis. No verdict is produced.

---

### Phase 4: Synthesis

**Contract:**
- **Receives:** Completed review files, type, round directory
- **Produces:** `REVIEW_SUMMARY.md` with verdict block
- **Invariants:** Start trigger met. Every finding in exactly one section. Verdict block present.

**Start trigger:** Begin synthesis when the external run has exited (it enforces its own 75% quorum and straggler cut-off) **and** every internal reviewer has finished. Internal reviewers are the highest-signal source, so do not start without them — except: if an internal reviewer is still running 10 minutes after everything else finished, start without it and append its review as a **"Late Review"** addendum when it lands. On Cursor (Task externals), apply the same rule with a 75% quorum over the external Tasks.

Launch `review-synthesizer` agent in **foreground** with: type, mode `initial`, round directory, completed review file paths, failed reviews, diff/plan path, focus filter, and the prompt profile warnings (from `profile_warnings` plus the internal model check).

The synthesizer cross-references findings, categorizes them, detects conflicts (writing their rebuttal prompts), generates the verdict block, and writes `REVIEW_SUMMARY.md`. Verify it exists.

---

### Phase 4.5: Deliberation (conditional)

**Contract:**
- **Receives:** `REVIEW_SUMMARY.md` with `## Conflicts` section
- **Produces:** Updated `REVIEW_SUMMARY.md` with `## Deliberation Outcomes`, updated verdict
- **Invariants:** Max 1 deliberation round. Each conflict resolved or flagged unresolved.

**Skip if:** `--no-deliberation`, `--quick`, or no conflicts detected in Phase 4.

Read the full deliberation protocol at [protocols/deliberation.md](${CLAUDE_SKILL_DIR}/protocols/deliberation.md).

**Summary:**
1. The synthesizer has already written `rebuttal-<REVIEWER>-C<N>.md` for each conflict and listed them in its status report with a `code-checkable` flag. Only CRITICAL/IMPORTANT findings produce conflicts. Do not re-read the summary or write rebuttal prompts yourself.
2. **Code-checkable conflicts:** resolve directly — read the few files or run the one search needed and write `rebuttal-response-orchestrator-C<N>.md` with the evidence and conclusion. Do this while step 3 runs.
3. **Everything else:** launch all rebuttals in **one parallel batch**:
   - **Internal** (`claude-code-*`, `cursor-internal-*`, `opus-internal-*`): `deep-reviewer` with `mode: rebuttal`, the rebuttal file, and output path `rebuttal-response-<REVIEWER>-C<N>.md`
   - **External on Cursor:** Task(`generalPurpose`, `readonly: true`, original model) with the rebuttal file → write `rebuttal-response-*.md`
   - **External on Claude Code / `--agent-cli`:** **one** background `run_reviewers.py` call containing every external rebuttal task (`prompt_kind: "rebuttal"`, `quorum_fraction: 1.0`) — see [references/external-reviewers.md](${CLAUDE_SKILL_DIR}/references/external-reviewers.md)
4. Re-invoke the synthesizer in `re-synthesis` mode with the rebuttal response paths. It edits `REVIEW_SUMMARY.md` in place.
5. Verify `REVIEW_SUMMARY.md` replaced Conflicts with Deliberation Outcomes.

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

Show: location, severity, agreement, current code, suggested fix, explanation. MINOR issues are compact in the summary — take their current code and suggested fix from the review file named in their `Details:` line.

Use `AskQuestion` (Cursor) or `AskUserQuestion` (Claude Code):
```
prompt: "Apply this fix to [file:line]?"
options:
  - Apply — apply this fix and continue to next issue
  - Skip — skip this fix and continue to next issue
  - Apply All — apply this and all remaining fixes without prompting
  - Skip All — skip all remaining fixes
```

After processing, update `REVIEW_SUMMARY.md` with applied/skipped status.

#### Plan/Spec type — Gather Input & Apply

**Auto-apply override:** Ask if any Auto-apply items should be reviewed first.

**For each "Needs your input" item:** Use `AskQuestion` (Cursor) or `AskUserQuestion` (Claude Code) with options derived from the summary.

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
| `Explore` / `explore` | Codebase pattern discovery (Phase 1) | Thorough mode, code type, `--deep-explore` | opus (Claude Code) / inherit (Cursor) |
| `Explore` / `explore` | Fallback internal reviewer when `deep-reviewer` is unavailable | Thorough mode, all types | opus (Claude Code) / inherit (Cursor) |
| `generalPurpose` | External multi-model reviewer (× models × count) | Cursor + `--external` | per `--models` |

> Claude Code: `opus` is latest Opus; subagents inherit session effort (`xhigh` by default). Cursor internal reviewers use `inherit`. Cursor external reviewers use explicit model slugs on `generalPurpose` Tasks.

### Custom (from `agents/`)

| Agent | Purpose | When used | Model |
|-------|---------|-----------|-------|
| `deep-reviewer` | Internal reviewer (× count); writes its own `review-*.md`; answers rebuttals | Thorough mode, all types; deliberation | `opus` / `inherit` |
| `review-synthesizer` | Synthesizes findings into `REVIEW_SUMMARY.md` with verdict; writes rebuttal prompts | Thorough mode, all types | `sonnet` / `inherit` |

### Scripts (from `skills/deep-review/scripts/`)

| Script | Purpose | When used |
|--------|---------|-----------|
| `prepare_round.py` | Scoping, round dir, diff, learnings injection + staleness, per-model prompts from profiles, reviewer config | Phase 2, all types |
| `run_reviewers.py` | Runs `agent` CLI concurrently for external reviewers with `stream-json` telemetry; quorum cut-off | Claude Code Phase 3; Cursor with `--agent-cli`; deliberation |

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
  - [references/external-reviewers.md](${CLAUDE_SKILL_DIR}/references/external-reviewers.md) — Cursor Task vs agent CLI backends, launch rules, deliberation re-engagement
  - [references/code-review-prompt.md](${CLAUDE_SKILL_DIR}/references/code-review-prompt.md) — Code review prompt sections (the shared rubric) for all reviewers
  - [references/plan-review-prompt.md](${CLAUDE_SKILL_DIR}/references/plan-review-prompt.md) — Plan review prompt sections (the shared rubric) for all reviewers
  - [references/model-profiles/README.md](${CLAUDE_SKILL_DIR}/references/model-profiles/README.md) — Per-model profiles: format, keys, how to add or bump a model
  - [references/verdict-schema.md](${CLAUDE_SKILL_DIR}/references/verdict-schema.md) — Verdict block schema documentation (v2)
  - [references/output-structure.md](${CLAUDE_SKILL_DIR}/references/output-structure.md) — Directory layout, branch sanitization, scope suffixes
  - [references/output-format.md](${CLAUDE_SKILL_DIR}/references/output-format.md) — Complete code review output format (sections 0-13)
  - [references/learning-schema.md](${CLAUDE_SKILL_DIR}/references/learning-schema.md) — Learning file frontmatter specification
  - [references/learning-injection.md](${CLAUDE_SKILL_DIR}/references/learning-injection.md) — Scope matching and injection into prompts
