---
name: git-review
description: Comprehensive code review with built-in Claude reviewers and optional multi-model analysis. Reviews staged changes, unstaged changes, specific files, commits, branches, or pull requests. Use when the user wants a code review, says "review my code", "check my changes", or wants to validate code quality before committing. Supports --quick for fast reviews, --external for multi-model, and --focus for targeted analysis.
disable-model-invocation: true
argument-hint: "[--quick] [--external] [--changed-only] [--focus <area>] [--pr <number>] [files...]"
---

# Git Code Review

> **v3.1.0**

A comprehensive code review command that uses built-in Claude `feature-dev:code-reviewer` agents by default. Optionally enables multi-model review with external AI models (`--external`) for cross-model agreement analysis. Understands codebase patterns and interactively applies fixes.

## Command Usage

### Default Behavior
- `/git-review` - Internal Claude review with persistent output + interactive fix application

### Modes
- `/git-review --quick` - Fast review, critical issues only, no subagents, no fix prompts
- `/git-review --skip-fix` - Show full review but skip interactive fix application

### Scope Options
- `/git-review` - Review all staged changes (default)
- `/git-review --unstaged` - Review unstaged changes only
- `/git-review --all` - Review both staged and unstaged changes
- `/git-review file1 file2` - Review specific files (regardless of staging)
- `/git-review HEAD~1` - Review the last commit
- `/git-review branch-name` - Review differences between current branch and specified branch
- `/git-review --pr <number>` - Review a GitHub pull request by number
- `/git-review --changed-only` - Scope review to files changed since the last review round in the current branch directory. Uses the most recent `_diff.patch` timestamp as the baseline. Falls back to full diff if no prior round exists.

### Focus Options
- `/git-review --focus security` - Focus on security issues only
- `/git-review --focus performance` - Focus on performance issues only
- `/git-review --focus tests` - Focus on test quality and coverage

**Note:** The focus filter is applied during synthesis, not during individual model reviews. All models perform a full review; the synthesizer filters results by focus area.

### Reviewer Options
- `/git-review --count 3` - Number of `feature-dev:code-reviewer` instances (default: `1`)
- `/git-review --external` - Enable multi-model review with external AI models via `agent` CLI
- `/git-review --models opus-4.6-thinking,gpt-5.3-codex-high` - Override default external models (implies `--external`)
- `/git-review --dry-run` - Show review configuration without running

**Default behavior (no `--external`):** Launches `<COUNT>` `feature-dev:code-reviewer` instances (default 1). Does not require `agent` CLI.

**With `--external`:** Also launches `<COUNT>` `code-review-executor` agents per external model. Requires `agent` CLI.

**Default external models:** `gemini-3.1-pro`, `gpt-5.4-high-fast`, `composer-1.5`

### Persistence & Tracking
- `/git-review --save` - Save review output (no-op in thorough mode which always persists)
- `/git-review --track` - Create TodoWrite entries for each issue found
- `/git-review --skip-pre-commit` - Skip pre-commit checks

Parse the arguments to determine behavior:
$ARGUMENTS

---

## Prerequisite Checks

Run these checks **in parallel** (all are independent). **Stop immediately** if any blocking check fails:

1. **Git repository:** `git rev-parse --is-inside-work-tree`. If fails → stop.
2. **Merge conflicts:** `git diff --check HEAD`. If conflicts found → stop.
3. **PR mode:** Verify `gh` CLI available. If not → stop.
4. **External mode:** Verify `agent` CLI installed. If not → stop.
5. **Empty diff:** If diff is empty → stop.
6. **Detached HEAD:** Warn and continue.

---

## Phase 0: Context Gathering

### Step 0a: Repository-specific Instructions
Read CLAUDE.md if it exists. Incorporate project-specific review guidelines.

### Step 0b: Feature Documentation
Look for spec docs in `.claude/docs/[feature-name]/`:
- **Single directory:** Use it.
- **Multiple:** Match by branch name, then by files in diff. If ambiguous, skip spec compliance.
- Read `PLAN.md` → extract current version path → read SPEC.md, KEY_DECISIONS.md, CHECKLIST.md, FIXTURES.md from that version directory.
- **Legacy fallback:** If no `PLAN.md`, read docs directly from the directory.

### Step 0c + Phase 1 (PARALLEL)

Launch **in parallel** in a single message:

**Step 0c — Explore Agent (thorough mode only):**
Launch `Explore` agent (`model: "opus"`) to find similar code patterns, error handling conventions, testing patterns, and related impacted code. Skip in `--quick` mode.

**Phase 1 — Pre-commit Checks** (skip if `--skip-pre-commit`):
Detect project type (Node.js/Python/Go/Rust) and run applicable checks in parallel (30s timeout each). Continue regardless of results.

---

## Phase 2: Code Review

### Step 2a: Get the Diff
Execute the appropriate git diff command based on scope. For `--pr` mode, use `gh pr diff` + `gh pr view` for metadata. For untracked files, use `git diff --no-index /dev/null <file>`. For `--changed-only` mode: resolve the most recent review round directory for this branch (see [references/output-structure.md](references/output-structure.md)). Find the `_diff.patch` file and use its modification timestamp as the baseline. Run `git diff` scoped to files modified after that timestamp (`git diff --name-only` filtered by commit date, then full diff on those files only). If no prior round exists, fall back to the default full-scope diff. If changed files exceed 50% of total files in the branch diff, warn and suggest full review instead.

### Step 2b: Change Overview
Show `git diff --stat` summary.

### Step 2c: Diff Size Warning
If diff exceeds **3,000 lines**, warn the user. For quick mode, limit to CRITICAL issues. Always offer file-specific review alternative.

**If `--dry-run`:** Display configuration summary and stop.

### Step 2d: Dependency Change Detection
Check for changes to dependency manifests (package.json, requirements.txt, go.mod, Cargo.toml, etc.). If found, show added/removed/changed dependencies. Run audit tools in background if available.

### Step 2e: Create Review Round (thorough mode only)

**Quick mode skips Steps 2e–2g.** Perform direct diff analysis focusing on CRITICAL issues only.

For thorough mode, create the review round directory. See [references/output-structure.md](references/output-structure.md) for directory layout and branch name sanitization rules.

1. Determine branch directory name and scope suffix
2. Generate timestamp: `REVIEW_TIMESTAMP=$(date +%Y%m%d-%H%M%S)`
3. Create `${ROUND_DIR}` and save `_diff.patch`
4. If `--external`: write `_review-prompt.md` using the template at [templates/review-prompt.md](templates/review-prompt.md)

### Step 2f: Review Execution (thorough mode only)

Launch all reviewers **in parallel** (`run_in_background: true`) in a single message:

**Internal reviewers (always):** Launch `<COUNT>` (default 1) `feature-dev:code-reviewer` agents (`model: "opus"`). Each receives: the full diff, codebase patterns from Phase 0, CLAUDE.md rules, feature spec docs (if available), PR metadata (if `--pr`). Include: "Only report issues with HIGH confidence. Tag uncertain issues as 'Potential Issue'. Return your complete review as your final message in markdown — do NOT attempt to write files." These reviewers have native codebase access (can read files, explore the project).

**IMPORTANT:** `feature-dev:code-reviewer` does NOT have the Write tool. After each completes, the **orchestrator** must capture its output and write it to `${ROUND_DIR}/review-claude-code-<N>.md`.

**External reviewers (with `--external`):** Also launch `<COUNT>` `code-review-executor` agents (from `.claude/agents/code-review-executor.md`) per external model. Each runs the `agent` CLI with the model, `_review-prompt.md`, `_diff.patch`, and project root. Output: `${ROUND_DIR}/review-<MODEL>-<N>.md`. If CLI fails, retry once; if it fails again, write error report to output file.

**Progress:** As each reviewer completes, report: "Review complete: `<reviewer>` instance `<N>` (`M` of `TOTAL` remaining)".

**Error recovery:** After reviewers finish: verify each expected review file exists and is non-empty. For missing/errored files, note failure and continue with successful reviews. **Zero-success guard:** If ALL reviews failed, stop — at least one is required for synthesis.

### Step 2g: Review Synthesis (thorough mode only)

**Quorum trigger:** Begin synthesis when **75% of reviewers** (rounded up) have completed — do not wait for all. If a straggler finishes while the synthesizer is still running, include its results. If it finishes after synthesis completes, append its findings as a **"Late Review"** addendum to `REVIEW_SUMMARY.md` rather than re-synthesizing.

Launch `code-review-synthesizer` agent (from `.claude/agents/code-review-synthesizer.md`) in **foreground** with the round directory, completed review file paths, failed/pending reviews, focus filter, and diff file.

The synthesizer reads all available reviews, cross-references findings, applies agreement logic, categorizes by severity, applies focus filter, and writes `REVIEW_SUMMARY.md`.

Update `.claude/reviews/REVIEW.md` with the round link (newest first).

---

## Review Output

See [references/output-format.md](references/output-format.md) for the complete output format (sections 0-13). Key sections:

- **Change Overview** — `git diff --stat`
- **Summary** — 1-2 sentences
- **Critical/Important/Minor/Potential Issues** — from REVIEW_SUMMARY.md or direct analysis
- **Spec Compliance** — if feature docs exist
- **Recommendation** — APPROVE / NEEDS_FIXES / BLOCK

For review criteria definitions (CRITICAL/IMPORTANT/MINOR/POTENTIAL), see [references/review-criteria.md](references/review-criteria.md).

---

## Phase 3: Interactive Fix Application

**(Skip if `--skip-fix` or `--quick`)**

**REQUIRED BEHAVIOR:** After showing the review, proceed directly to fix application. Do NOT ask "Would you like me to apply fixes?" — immediately begin prompting for each fixable issue.

**Source:** Read structured issues from `${ROUND_DIR}/REVIEW_SUMMARY.md`.

**For each fixable issue (CRITICAL → IMPORTANT → MINOR):**

Show: location (file:line), severity, agreement level, current code, suggested fix, explanation.

**Use AskUserQuestion with these exact options:**

```
AskUserQuestion:
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

After processing all fixes, update `REVIEW_SUMMARY.md` with applied/skipped status and show summary.

---

## Phase 4: Post-Review Actions

- **Thorough mode:** Reviews already persisted (--save is no-op)
- **Quick mode + --save:** Save to `.claude/reviews/<timestamp>-review.md`
- **--track:** Create TodoWrite entries for each unresolved issue

---

## Review Approach

1. Scan for CRITICAL issues first
2. Consider broader context — how changes fit with existing code
3. Check edge cases — error scenarios, boundary conditions
4. Verify intent — do changes accomplish their purpose
5. Consider maintainability
6. Check dependencies — safe and necessary?
7. Note binary files separately

---

## Spec Integration

If reviewing changes from a `/new-feature` workflow, follow Step 0b to discover feature documentation and include spec compliance status in output.

---

## Agents

### Built-in (via Agent tool)

| Agent | Purpose | When used | Model |
|-------|---------|-----------|-------|
| `Explore` | Codebase pattern discovery (Phase 0) | Always (thorough mode) | `opus` |
| `feature-dev:code-reviewer` | Built-in Claude code reviewer (× count) | Always (thorough mode) | `opus` |

### Custom (from `.claude/agents/`)

| Agent | Purpose | When used | Model |
|-------|---------|-----------|-------|
| `code-review-executor` | Runs `agent` CLI for external model reviews | `--external` only | `haiku` (executor only — actual review model via `--models`) |
| `code-review-synthesizer` | Synthesizes all review findings into `REVIEW_SUMMARY.md` | Always (thorough mode) | `opus` |

### Mode × Agent Matrix

| Mode | `Explore` | `code-reviewer` | `code-review-executor` | `code-review-synthesizer` |
|------|-----------|-----------------|------------------------|--------------------------|
| default (internal) | ✓ background | ✓ background (× count) | — | ✓ foreground |
| --external | ✓ background | ✓ background (× count) | ✓ background (per model × count) | ✓ foreground |
| --quick | — | — | — | — |
| --skip-fix | ✓ background | ✓ background (× count) | only with `--external` | ✓ foreground |

---

## Key Principles

- **Multi-model coverage** — Different models catch different things
- **Specific line numbers** — Always include when pointing out issues
- **Explain WHY** — Not just what
- **Concrete suggestions** — Provide actual fix code
- **Always proceed to fix application** — Never end with open-ended questions
- **Separate confidence levels** — Don't mix confirmed with speculative
- **Parallelize** — Step 0c + Phase 1 concurrently; all reviewers in parallel
- **Fail gracefully** — Continue with partial results; zero-success guard stops
- **Always persist in thorough mode** — Every round creates an audit trail

## Additional Resources

- **References:**
  - [references/output-structure.md](references/output-structure.md) — Directory layout, branch sanitization, scope suffixes, file reference
  - [references/review-criteria.md](references/review-criteria.md) — CRITICAL/IMPORTANT/MINOR/POTENTIAL severity definitions
  - [references/output-format.md](references/output-format.md) — Complete output format (sections 0-13)

- **Templates:**
  - [templates/review-prompt.md](templates/review-prompt.md) — Prompt template for external model reviewers
