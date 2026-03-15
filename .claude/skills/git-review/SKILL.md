---
name: git-review
description: Comprehensive code review with built-in Claude reviewers and optional multi-model analysis. Reviews staged changes, unstaged changes, specific files, commits, branches, or pull requests. Use when the user wants a code review, says "review my code", "check my changes", or wants to validate code quality before committing. Supports --quick for fast reviews, --external for multi-model, and --focus for targeted analysis.
disable-model-invocation: true
argument-hint: "[--quick] [--external] [--focus <area>] [--pr <number>] [files...]"
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

Before starting, perform these checks. **Stop immediately** if any fail:

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
Execute the appropriate git diff command based on scope. For `--pr` mode, use `gh pr diff` + `gh pr view` for metadata. For untracked files, use `git diff --no-index /dev/null <file>`.

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

Launch all reviewers in parallel. See [references/review-execution.md](references/review-execution.md) for the full execution protocol including internal-only and external modes.

Key points:
- All reviewers run via `run_in_background: true`
- `feature-dev:code-reviewer` agents do NOT have Write tool access — the orchestrator must capture their output and write review files
- Report progress as each reviewer completes
- Continue with partial results if some reviewers fail (but stop if ALL fail)

### Step 2g: Review Synthesis (thorough mode only)

Launch `code-review-synthesizer` agent (from `.claude/agents/code-review-synthesizer.md`) in **foreground** with the round directory, successful review file paths, failed reviews, focus filter, and diff file.

The synthesizer reads all reviews, cross-references findings, applies agreement logic, categorizes by severity, applies focus filter, and writes `REVIEW_SUMMARY.md`.

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
  - [references/review-execution.md](references/review-execution.md) — Detailed review execution protocol
  - [references/subagent-reference.md](references/subagent-reference.md) — Agent types and mode × agent matrix

- **Templates:**
  - [templates/review-prompt.md](templates/review-prompt.md) — Prompt template for external model reviewers
