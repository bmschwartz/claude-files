# Git Code Review

> **v3.1.0** · Last updated 2026-02-12

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 3.1.0 | 2026-02-12 | Internal-only default — built-in Claude `feature-dev:code-reviewer` is now the default reviewer (`--count` default: 1). `--external` flag opts into multi-model review with external models via `agent` CLI. `--count` controls reviewer instances in both modes. |
| 3.0.0 | 2026-02-12 | Multi-model review in thorough mode — external models via `agent` CLI + built-in Claude code-reviewer running in parallel. Persistent review output to `.claude/reviews/<branch>/<timestamp-scope>/` with `REVIEW_SUMMARY.md`. New custom agents: `code-review-executor`, `code-review-synthesizer`. Branch-organized review directories with sanitized naming. Cross-model agreement analysis. `--models`/`--count`/`--dry-run` flags. Removed diff splitting (each model reviews the full diff). Focus filter applied at synthesis only. |
| 2.0.0 | 2026-02-09 | Parallel Phase 0c/1, large diff protection, `git diff --stat` overview, `--pr` flag, dependency/vulnerability detection, confidence-based filtering, `--focus` flag, `--save`/`--track` flags, background parallel review agents, comprehensive error handling, model hints for subagents, structural fixes |
| 1.0.0 | 2026-02-09 | Initial version — phased review process, subagent exploration, interactive fix application, spec compliance |

---

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

**Note:** The focus filter is applied during synthesis, not during individual model reviews. All models perform a full review; the synthesizer filters results by focus area and lists out-of-focus issues separately.

### Reviewer Options
- `/git-review --count 3` - Number of `feature-dev:code-reviewer` instances to launch (default: `1`)
- `/git-review --external` - Enable multi-model review with external AI models via the `agent` CLI, in addition to the built-in Claude reviewers
- `/git-review --models opus-4.6-thinking,gpt-5.3-codex-high` - Override default external review models (implies `--external`)
- `/git-review --dry-run` - Show review configuration (scope, diff stats, models, agent count) without running any reviews

**Default behavior (no `--external`):** Launches `<COUNT>` `feature-dev:code-reviewer` instances (default 1) with Phase 0 codebase patterns, spec docs, and native codebase access. Does not require the `agent` CLI.

**With `--external`:** In addition to the Claude reviewers, launches `<COUNT>` `code-review-executor` agents per external model via the `agent` CLI. Requires the `agent` CLI to be installed.

**Default external models** (when `--external` is set and `--models` is not specified):

- `gemini-3.1-pro`
- `gpt-5.4-high-fast`
- `composer-1.5`

### Persistence Options
- `/git-review --save` - Save review output to `.claude/reviews/` (**no-op in thorough mode**, which always persists; useful for quick mode)
- `/git-review --track` - Create TaskCreate entries for each issue found

### Other Options
- `/git-review --skip-pre-commit` - Skip pre-commit checks

Parse the arguments to determine behavior:
$ARGUMENTS

---

## Review Output Structure

Thorough mode always persists review artifacts to `.claude/reviews/`, organized by branch and review round. Quick mode only persists when `--save` is specified.

### Directory Layout

```
.claude/reviews/
├── REVIEW.md                                         # → most recent review round (any branch)
├── feature--dark-mode/
│   ├── 20260212-143022-staged/                       # Internal-only (default)
│   │   ├── _diff.patch                               # The diff that was reviewed
│   │   ├── review-claude-code-1.md                   # Built-in Claude reviewer
│   │   └── REVIEW_SUMMARY.md                         # Synthesized summary
│   ├── 20260212-150000-staged/                       # With --external --count 2
│   │   ├── _review-prompt.md                         # Prompt sent to external models
│   │   ├── _diff.patch                               # The diff that was reviewed
│   │   ├── review-claude-code-1.md                   # Built-in Claude reviewer
│   │   ├── review-claude-code-2.md                   # Built-in Claude reviewer (instance 2)
│   │   ├── review-composer-1.5-1.md                  # External model instances
│   │   ├── review-composer-1.5-2.md
│   │   └── REVIEW_SUMMARY.md                         # Synthesized summary from all reviews
│   └── 20260212-160000-vs-master/
│       └── ...
├── ENG-123--user-auth/
│   └── 20260213-091500-staged/
│       └── ...
└── pr-456/
    └── 20260213-100000-pr-456/
        └── ...
```

### Branch Name Sanitization

The branch directory name is derived from the current git branch (or PR metadata):

1. Get the branch name: `git symbolic-ref --short HEAD 2>/dev/null`
2. **Sanitize:** Replace `/` with `--`. Strip characters that aren't alphanumeric, `-`, `_`, or `.`. Truncate to 100 characters.
3. **Detached HEAD:** Use `detached-$(git rev-parse --short HEAD)` (e.g., `detached-a1b2c3d`)
4. **PR mode:** Use the PR's head branch name from `gh pr view <number> --json headRefName`. If unavailable, fall back to `pr-<number>`.

### Scope Suffix

The timestamp directory includes a scope suffix for identification:

| Scope | Suffix | Example directory |
|-------|--------|-------------------|
| Staged (default) | `staged` | `20260212-143022-staged` |
| Unstaged | `unstaged` | `20260212-143022-unstaged` |
| All changes | `all` | `20260212-143022-all` |
| Branch comparison | `vs-<branch>` | `20260212-143022-vs-master` |
| PR review | `pr-<number>` | `20260212-143022-pr-456` |
| Commit review | `commit-<short-sha>` | `20260212-143022-commit-a1b2c3d` |
| Specific files | `files` | `20260212-143022-files` |

### File Reference

| File | Purpose | Created by |
|------|---------|------------|
| `REVIEW.md` (reviews root) | Links to the most recent review round | Step 2g |
| `<branch>/<timestamp-scope>/` | Timestamped directory for a single review round | Step 2e |
| `_review-prompt.md` | Prompt passed to each external model reviewer (audit trail, `--external` only) | Step 2e |
| `_diff.patch` | The diff that was reviewed (audit trail) | Step 2e |
| `review-claude-code-<N>.md` | Review from built-in Claude code-reviewer instance N | `feature-dev:code-reviewer` via Task tool |
| `review-<MODEL>-<N>.md` | Review from an external model instance (`--external` only, immutable) | `code-review-executor` agent |
| `REVIEW_SUMMARY.md` | Synthesized summary with severity-based issues and agreement analysis | `code-review-synthesizer` agent |

**Immutability rule:** Raw `review-*.md` files must never be modified after creation. `REVIEW_SUMMARY.md` may be updated with apply/skip status in Phase 3.

---

## Prerequisite Checks

Before starting any phase, perform these checks. **Stop immediately** if any fail:

1. **Git repository check:** Run `git rev-parse --is-inside-work-tree`. If it fails, report: "Not inside a git repository. Run this command from within a git repo." Stop.

2. **Merge conflict check:** Run `git diff --check HEAD` (or `git diff --check --staged`). If merge conflict markers are found, report: "Merge conflicts detected. Resolve conflicts before running a review." Stop.

3. **PR mode check (if `--pr` specified):** Verify `gh` CLI is available by running `which gh`. If not found, report: "The `gh` CLI is required for PR reviews but was not found. Install it from https://cli.github.com." Stop.

4. **Agent CLI check (only when `--external` is set):** Verify the `agent` CLI is installed by running `which agent`. If not found, report: "The `agent` CLI is required for external model reviews but was not found on PATH. Install it from https://docs.cursor.com/agent and try again. Remove `--external` to use internal Claude reviewers only." Stop.

5. **Empty diff check:** After determining scope, run the appropriate diff command. If the diff is empty (no output), report: "No changes found to review." and stop. For `--pr` mode, use `gh pr diff <number>` to check.

6. **Detached HEAD warning:** Run `git symbolic-ref --short HEAD 2>/dev/null`. If this fails (detached HEAD state), warn: "Detached HEAD detected — branch-based features (spec matching, branch name display) may not work correctly." Continue with the review.

---

## Review Process

### Phase 0: Context Gathering

**Purpose:** Understand codebase patterns before reviewing so pattern violations can be accurately detected.

**Step 0a: Check for Repository-specific Instructions**
1. Look for CLAUDE.md in the repository root
2. If it exists, read and incorporate project-specific review guidelines
3. Apply these rules in addition to standard review criteria

**Step 0b: Check for Feature Documentation**
1. Look for feature documentation directories in `.claude/docs/[feature-name]/`
   - **Single directory:** Use it.
   - **Multiple directories:** Match by current git branch name (e.g., branch `feat/user-search` matches `.claude/docs/user-search/`). If no branch match, check which directories contain files modified in the diff. If still ambiguous, list the candidates and skip spec compliance rather than guessing.
2. If found, resolve the current plan version:
   - **Versioned (preferred):** Read `PLAN.md` at the root, extract the path from the `Current version:` line (e.g., `plans/20260209-143022/`), then read documents from that subdirectory.
   - **Legacy fallback:** If no `PLAN.md` exists, read documents directly from `.claude/docs/[feature-name]/`.
3. Read the following files for review context:
   - `SPEC.md` - Requirements and implementation phases
   - `KEY_DECISIONS.md` - Design decisions to verify
   - `CHECKLIST.md` - Task completion status
   - `FIXTURES.md` - Test data definitions
4. Use this context to validate implementation against the spec

**Step 0c: Codebase Pattern Discovery + Step 1: Pre-commit Checks (PARALLEL)**

**IMPORTANT:** Step 0c and Phase 1 are **independent** of each other. Launch them **in parallel** using multiple Task/Bash tool calls in a single message. This saves 15-30 seconds of wall-clock time on every review.

~~~
┌─────────────────────────────────┐
│  Single message, parallel calls │
├────────────────┬────────────────┤
│ Step 0c:       │ Phase 1:       │
│ Explore agent  │ Pre-commit     │
│ (Task tool)    │ checks (Bash)  │
├────────────────┴────────────────┤
│  Both complete → Phase 2        │
└─────────────────────────────────┘
~~~

**Step 0c — Explore Agent (thorough mode only):**

For default (thorough) mode, launch an **Explore agent** (`subagent_type: "Explore"`, `model: "opus"`) to:
- Find similar code patterns in the files being modified
- Identify error handling conventions
- Understand testing patterns
- Find related code that might be impacted by these changes

For `--quick` mode, skip this step.

**Codebase Context Report:**
After exploration, briefly note:

~~~
### Patterns Detected
- Error handling: [pattern observed, e.g., "uses Result<T, E> pattern"]
- Testing: [convention, e.g., "co-located test files with .test.ts suffix"]
- Naming: [convention observed]

### Related Code
- `path/to/related.py` - [Why changes might affect it]
~~~

★ Insight ─────────────────────────────────────
Explain what patterns were discovered:
- Why these patterns exist in this codebase
- How they inform the review criteria
─────────────────────────────────────────────────

---

### Phase 1: Pre-commit Checks

(Launched **in parallel** with Step 0c — see above. Skip entirely if `--skip-pre-commit` is specified.)

**Smart Project Detection:**
Detect project type and available tooling:
- **Node.js**: Check package.json for lint, type-check, test scripts
- **Python**: Check for ruff.toml, pyproject.toml (ruff, mypy, pytest)
- **Go**: Check for golangci-lint configuration
- **Rust**: Check for clippy configuration

**Parallel Execution:**
Run all applicable checks in parallel with reasonable timeouts (30s max per check).

**Results Format:**
- ✅ All checks passed
- ⚠️ [N] issues found: [brief summary]
- ❌ Check failed: [which one and why]

Continue with code review regardless of pre-commit results.

---

### Phase 2: Code Review

**Step 2a: Get the Diff**

**For standard scopes**, execute a single git diff command based on arguments:
- `git diff --staged` for staged only
- `git diff` for unstaged only
- `git diff HEAD` for all changes
- `git diff <commit>` for commit review
- `git diff <branch>...HEAD` for branch comparison

**For `--pr` mode**, use the GitHub CLI:
1. `gh pr diff <number>` to get the diff content
2. `gh pr view <number> --json title,body,labels,baseRefName,headRefName` for PR metadata
3. Use the PR title and body as additional context for the review

**Including untracked files:** Discover untracked files with `git ls-files --others --exclude-standard`, then for each file use `git diff --no-index /dev/null <file>` to generate a diff without modifying the staging area. This is side-effect-free and safe if the process is interrupted.

**Step 2b: Change Overview**

Always show a `git diff --stat` summary first (or `gh pr diff <number> --stat` for PR mode). This gives an at-a-glance map of what changed:

~~~
#### Change Overview

 src/auth/middleware.ts | 45 ++++++----
 src/api/routes.ts     | 12 +++
 tests/auth.test.ts    | 88 ++++++++++++++++++
 3 files changed, 112 insertions(+), 33 deletions(-)
~~~

**Step 2c: Diff Size Warning**

Count total diff lines. If the diff exceeds **3,000 lines**:

1. **Warn the user:**
   ~~~
   Large diff detected: ~N lines across M files.
   Large diffs may reduce review quality — each model will review the full diff.
   ~~~

2. **For quick mode:** Continue with direct analysis but limit to CRITICAL issues.

3. **Always offer:** "Consider reviewing specific files for deeper analysis: `/git-review path/to/critical.ts`"

**Dry-run check:** If `--dry-run` was specified, display after this step:

**Without `--external`:**
~~~
### Dry Run Summary

**Scope:** staged changes
**Diff size:** ~N lines across M files
**Branch directory:** .claude/reviews/<sanitized-branch>/
**Round directory:** <timestamp-scope>/

**Reviewers:**
- 1× Claude `feature-dev:code-reviewer` (built-in)
- Total: 1 reviewer

**Focus filter:** None
~~~

**With `--external` (e.g., `--external --count 2`):**
~~~
### Dry Run Summary

**Scope:** staged changes
**Diff size:** ~N lines across M files
**Branch directory:** .claude/reviews/<sanitized-branch>/
**Round directory:** <timestamp-scope>/

**Reviewers:**
- 2× Claude `feature-dev:code-reviewer` (built-in)
- 2× `composer-1.5` (via agent CLI)
- Total: 4 parallel reviewers

**Focus filter:** None
~~~

Then stop. Do not proceed to Step 2d or beyond.

**Step 2d: Dependency Change Detection**

Check if the diff includes changes to dependency manifests:
- `package.json` / `package-lock.json` (Node.js)
- `requirements.txt` / `pyproject.toml` / `poetry.lock` (Python)
- `go.mod` / `go.sum` (Go)
- `Cargo.toml` / `Cargo.lock` (Rust)
- `Gemfile` / `Gemfile.lock` (Ruby)

If dependency changes are detected:

~~~
### Dependency Changes

**Added:**
- `new-package@1.2.3` - [brief description if inferrable]

**Removed:**
- `old-package@0.9.0`

**Version Changes:**
- `some-lib`: 2.0.0 → 3.0.0 (major version bump)
~~~

If available, run the appropriate audit tool **in the background** (do not block the review):
- Node.js: `npm audit --json` or `yarn audit --json`
- Python: `pip-audit` (if installed)
- Go: `govulncheck ./...` (if installed)
- Rust: `cargo audit` (if installed)

Report findings in a `### Vulnerability Check` subsection. If no audit tool is available, note: "No audit tool found — consider running `[tool]` manually."

**Step 2e: Create Review Round (thorough mode only)**

**For quick mode**, skip Steps 2e–2g entirely. Perform direct diff analysis without subagents, focusing on CRITICAL issues only.

**For thorough mode**, create the review round directory and prepare all review artifacts:

1. **Determine branch directory name** using the sanitization rules from the Review Output Structure section.

2. **Determine scope suffix** based on the review scope (see Scope Suffix table).

3. **Generate the review round timestamp:** `REVIEW_TIMESTAMP=$(date +%Y%m%d-%H%M%S)`

4. **Create the round directory:**
   ```
   BRANCH_DIR=<sanitized branch name>
   SCOPE_SUFFIX=<scope suffix>
   ROUND_DIR=".claude/reviews/${BRANCH_DIR}/${REVIEW_TIMESTAMP}-${SCOPE_SUFFIX}"
   mkdir -p "${ROUND_DIR}"
   ```

5. **Save the diff** to `${ROUND_DIR}/_diff.patch`.

6. **Write the external model review prompt (only when `--external` is set)** to `${ROUND_DIR}/_review-prompt.md`. This is the prompt passed to each `code-review-executor` subagent via the `agent` CLI. It is preserved as an audit trail. Skip this step when running internal-only reviews.

   The prompt should contain:

   ~~~
   Review the code changes (diff) in this workspace. The diff file is at: <DIFF_PATH>

   Read the entire diff before beginning your analysis. Then use the project codebase to understand context around the changes.

   <If CLAUDE.md exists>
   ## Project Conventions (from CLAUDE.md)
   <CLAUDE.md content>
   </If>

   ## Codebase Patterns (from automated analysis)
   <Phase 0 patterns discovered in Step 0c>

   <If spec docs exist>
   ## Feature Specification Context
   <SPEC.md content>
   <KEY_DECISIONS.md content>
   <CHECKLIST.md content>
   <FIXTURES.md content>
   </If>

   <If PR metadata exists>
   ## Pull Request Metadata
   - Title: <title>
   - Description: <body>
   - Labels: <labels>
   - Base branch: <base> → Head branch: <head>
   </If>

   ## Review Dimensions

   Evaluate the changes on:

   1. **Security** — SQL injection, XSS, exposed secrets, unsafe operations, command injection
   2. **Correctness** — Logic errors, wrong assumptions, misuse of APIs/libraries, regression risk
   3. **Error Handling** — Missing error handling that could crash, unhandled edge cases, resource leaks
   4. **Performance** — N+1 queries, inefficient algorithms, unnecessary allocations, missing caching
   5. **Pattern Compliance** — Does the code follow established codebase patterns? Deviations that risk correctness/security are CRITICAL; style deviations are IMPORTANT.
   6. **Test Coverage** — Are changes tested? Do tests follow existing test patterns?
   7. **Dependencies** — Are new dependencies safe? Major version bumps? Known CVEs?

   ## Output Requirements

   For each issue found:
   - State the **severity**: CRITICAL / IMPORTANT / MINOR / POTENTIAL
   - Provide the exact **file path and line number**
   - Show the **current code** (the problematic snippet)
   - Provide a **suggested fix** (concrete code)
   - Explain **why** this is an issue

   Only report issues with HIGH confidence. If you are uncertain, tag the issue as POTENTIAL rather than promoting it to a higher severity.

   Finish with a **Prioritized Recommendations** section: a numbered list of the most important changes, ordered by impact. Tag each with severity.
   ~~~

**Step 2f: Review Execution (thorough mode only)**

Launch all reviewers in parallel using the Task tool with `run_in_background: true`.

**Internal-only mode (default, no `--external`):**

~~~
┌──────────────────────────────────────────────┐
│         Single message, parallel calls        │
├──────────────┬──────────────┬────────────────┤
│  Claude      │  Claude      │  ...           │
│  code-review │  code-review │  (× count)     │
│  instance 1  │  instance 2  │                │
├──────────────┴──────────────┴────────────────┤
│        All complete → Step 2g (Synthesis)    │
└──────────────────────────────────────────────┘
~~~

Launch `<COUNT>` (default 1) `feature-dev:code-reviewer` agents (`model: "opus"`, `run_in_background: true`). Each instance receives:

- The full diff content
- Codebase patterns discovered in Phase 0
- Project-specific rules from CLAUDE.md
- Feature spec docs (if available) — SPEC.md, KEY_DECISIONS.md, CHECKLIST.md, FIXTURES.md
- PR metadata (if `--pr` mode)
- **Confidence threshold instruction:** "Only report issues with HIGH confidence. Pattern violations against the codebase patterns below carry extra weight. If you are uncertain about an issue, tag it separately as a 'Potential Issue' rather than mixing it with confirmed findings."
- **Output instruction:** "Return your complete review as your final message in markdown format. Do NOT attempt to write files — you do not have Write tool access."

**IMPORTANT — File writing:** The `feature-dev:code-reviewer` agent does NOT have the `Write` tool. After each agent completes, the **parent orchestrator** must capture the agent's returned output and write it to `${ROUND_DIR}/review-claude-code-<N>.md` using the Write tool. Do not ask the agent to write the file itself.

These reviewers benefit from native Claude Code codebase access — they can read files, explore the project, and use all built-in tools beyond what the diff shows.

**External mode (with `--external`):**

~~~
┌──────────────────────────────────────────────────────────────┐
│                 Single message, parallel calls                │
├──────────────────┬──────────────────┬────────────────────────┤
│  Claude          │  External Model  │  External Model        │
│  code-reviewers  │  A × count       │  B × count             │
│  (× count)       │  (code-review-   │  (code-review-         │
│                  │  executor agents)│  executor agents)      │
├──────────────────┴──────────────────┴────────────────────────┤
│              All complete → Step 2g (Synthesis)              │
└──────────────────────────────────────────────────────────────┘
~~~

In addition to the Claude code-reviewers above, launch `<COUNT>` `code-review-executor` agents per external model (`run_in_background: true`). Each receives:

~~~
Run a code review using the Cursor `agent` CLI with the following parameters:

- Model: <MODEL>
- Instance number: <N>
- Review prompt file: ${ROUND_DIR}/_review-prompt.md
- Diff file: ${ROUND_DIR}/_diff.patch
- Project root: <PROJECT_ROOT> (pass as the workspace so the agent can access the codebase)
- Output directory: ${ROUND_DIR}
- Write the review output to: ${ROUND_DIR}/review-<MODEL>-<N>.md

If the CLI fails, retry once. If it fails again, write a brief error report to the output file.
~~~

**Progress tracking:** As each reviewer completes, report to the user: "Review complete: `<reviewer>` instance `<N>` (`M` of `TOTAL` remaining)".

Wait for all reviewers to complete before proceeding.

**Writing review files (internal reviewers):** After each `feature-dev:code-reviewer` agent completes, read its returned output from the Task tool result. If the output contains a substantive review (not empty or an error), write it to `${ROUND_DIR}/review-claude-code-<N>.md` using the Write tool. If the agent returned empty or errored output, note the failure.

**Error recovery:** After all reviewers finish and their outputs have been written, verify each expected review file exists and is non-empty. For any that are missing or contain an error report:

- Note the failure prominently in your output (which model/instance failed, why if known).
- **Continue with the remaining successful reviews.** Do not abort because one reviewer failed.
- Pass the list of successful and failed reviews to Step 2g.

**Zero-success guard:** If ALL reviews failed, report the errors and stop. Do not proceed to Step 2g. At least one successful review is required for synthesis.

**Step 2g: Review Synthesis (thorough mode only)**

Launch a `code-review-synthesizer` agent (custom agent from `.claude/agents/code-review-synthesizer.md`) in the **foreground** with:

~~~
Synthesize the code reviews with the following parameters:
- Review directory: ${ROUND_DIR}
- Successful review files: <list of successful review file paths>
- Failed reviews: <list of models that failed, if any>
- Focus filter: <focus value, or "None">
- Diff file: ${ROUND_DIR}/_diff.patch
~~~

The synthesizer will:

1. Read all successful review files and the diff
2. Cross-reference findings, apply agreement logic, and categorize by severity
3. Produce structured output with file:line, current code, suggested fix per issue
4. Apply focus filter (if specified) — main sections show in-focus issues, filtered section lists the rest
5. Write `${ROUND_DIR}/REVIEW_SUMMARY.md`
6. Return a status report with issue counts by severity and agreement breakdown

Wait for the synthesizer to complete. Verify that `${ROUND_DIR}/REVIEW_SUMMARY.md` exists.

**Update REVIEW.md:** Create or update `.claude/reviews/REVIEW.md` with the following structure:

~~~markdown
# Code Review History

Current review: `<BRANCH_DIR>/<TIMESTAMP-SCOPE>/`

## Review Rounds

| Round | Date | Branch | Scope | Models | Failures | Summary |
|-------|------|--------|-------|--------|----------|---------|
| N | YYYY-MM-DD | `<branch>` | staged | claude-code ×1 (or with --external: claude-code ×1, composer-1.5 ×2) | None | [REVIEW_SUMMARY.md](<branch>/<timestamp-scope>/REVIEW_SUMMARY.md) |
| ... | ... | ... | ... | ... | ... | ... |
~~~

Newest round first. Each row links to that round's `REVIEW_SUMMARY.md`.

---

## Review Criteria

### CRITICAL ISSUES (Must be fixed)
- Security vulnerabilities (SQL injection, XSS, exposed secrets, unsafe operations)
- Data loss risks or corruption possibilities
- Breaking changes to public APIs without proper deprecation
- Missing error handling that could crash the application
- Race conditions or deadlocks
- Memory leaks or resource exhaustion
- Incorrect business logic that violates core requirements
- **Pattern Violations (correctness/security)**: Code that contradicts established codebase patterns **and** risks correctness or security (e.g., bypassing a required auth check, ignoring a validation pattern that prevents injection). Pattern violations that are stylistic or conventional belong under IMPORTANT.
- **Regression Risk**: Changes that might break existing functionality
- **New Dependency Vulnerabilities**: Known CVEs in newly added dependencies

### IMPORTANT ISSUES (Should be fixed)
- Performance problems (N+1 queries, inefficient algorithms, unnecessary loops)
- **Pattern Violations (style/convention)**: Code that breaks established patterns without a correctness or security risk (e.g., deviating from naming conventions, not using project-standard error wrapping)
- Missing input validation or boundary checks
- Hardcoded values that should be configurable
- Incomplete implementations or TODO comments
- Test coverage gaps for critical functionality
- Accessibility violations
- **Inconsistent Style**: Deviates from patterns found in similar files
- **Missing Tests**: When similar features have tests but this doesn't
- **Major Version Bumps**: Dependencies with major version changes that may introduce breaking changes

### MINOR (Nice to have)
- Better variable/function names for clarity
- Opportunities to reduce complexity (extract methods, simplify conditionals)
- Missing documentation for complex logic
- Code duplication that could be refactored
- Outdated dependencies or deprecated API usage
- Consistent formatting and style
- **Pattern Opportunities**: Where existing utilities could be reused
- **Future Maintenance**: Complexity that will be hard to maintain

### POTENTIAL ISSUES (Low confidence)
Issues where the reviewer is not fully certain but wants to flag for human judgment. These are listed separately to avoid polluting the high-confidence findings.

---

## Output Format

### Always Shown (regardless of --skip-fix):

#### 0. Change Overview
`git diff --stat` output showing files changed, insertions, deletions.

#### 1. Summary
1-2 sentence summary of what the changes do. For `--pr` mode, also include the PR title and a note on whether the PR description aligns with the actual changes.

#### 2. Codebase Context
Brief note on patterns detected and how changes align (thorough mode).

#### 3. Dependency Changes (if applicable)
Newly added/removed/changed dependencies and vulnerability scan results.

#### 4. Critical Issues
From `REVIEW_SUMMARY.md` (thorough mode) or direct analysis (quick mode). Each issue includes file:line, agreement level, current code, suggested fix, and explanation.

#### 5. Important Issues
From `REVIEW_SUMMARY.md` or direct analysis. Same structured format.

#### 6. Minor
Optional improvements for code quality.

#### 7. Potential Issues
Low-confidence findings for human judgment (thorough mode only).

#### 8. Agreement Overview (`--external` mode only, or when `--count` > 1)
Brief summary of cross-reviewer agreement patterns — how many issues had strong/moderate/single agreement.

#### 9. Insights
★ Insight blocks explaining key findings.

#### 10. Spec Compliance (if applicable)
If a related `.claude/docs/[feature-name]/` directory exists:

~~~
## Spec Compliance

Feature docs: `.claude/docs/user-search/`

### Requirements (from SPEC.md)
- ✅ Implements required endpoint
- ✅ Follows planned data structure
- ⚠️ Missing: Error handling for edge case X

### Key Decisions (from KEY_DECISIONS.md)
- ✅ Uses repository pattern as specified
- ✅ Follows naming conventions

### Checklist Status (from CHECKLIST.md)
- Phase 1: 5/5 complete
- Phase 2: 3/4 complete (missing: input validation tests)

### Test Coverage (from FIXTURES.md)
- ✅ Sample fixtures implemented
- ⚠️ Missing: edge case fixture for empty results
~~~

#### 11. Recommendation
- ✅ **APPROVE** - No critical issues, ready to commit
- ⚠️ **NEEDS_FIXES** - Has important issues that should be addressed
- 🚫 **BLOCK** - Has critical issues that must be fixed

#### 12. Next Steps (if NEEDS_FIXES or BLOCK)
Prioritized list of what to fix first.

#### 13. Review Artifacts (thorough mode only)
Note the location of persisted review files:

**Internal-only (default):**
~~~
Review artifacts saved to: `.claude/reviews/<branch>/<timestamp-scope>/`
- REVIEW_SUMMARY.md — synthesized findings
- 1 raw review file (claude-code ×1)
~~~

**With `--external`:**
~~~
Review artifacts saved to: `.claude/reviews/<branch>/<timestamp-scope>/`
- REVIEW_SUMMARY.md — synthesized findings
- N raw review files (claude-code ×1, composer-1.5 ×2, etc.)
~~~

---

## Phase 3: Interactive Fix Application

**(Skip ONLY if `--skip-fix` or `--quick` is specified)**

**⚠️ REQUIRED BEHAVIOR:** After showing the complete review, you MUST proceed to interactive fix application. Do NOT ask "Would you like me to apply fixes?" or similar open-ended questions. Instead, immediately begin prompting for each fixable issue using the `AskUserQuestion` tool.

**Source of issues:** In thorough mode, read the structured issues from `${ROUND_DIR}/REVIEW_SUMMARY.md`. Each issue has file:line, current code, suggested fix, severity, and agreement level. Present them using the format below.

**For each fixable issue (in order of severity: CRITICAL → IMPORTANT → MINOR):**

~~~
## Issue 1 of N: [Issue Title]

**Location:** path/to/file.ts:45
**Severity:** CRITICAL / IMPORTANT / MINOR
**Agreement:** Strong (3/5 reviewers) / Moderate (2/5) / Single

**Current Code:**
```[language]
[the problematic code]
```

**Suggested Fix:**
```[language]
[the fixed code]
```

**Why:** [Explanation of why this fix is recommended, referencing codebase patterns if relevant]
~~~

**REQUIRED: Use AskUserQuestion tool with these exact options:**

~~~
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
~~~

**After user responds:**
- **Apply**: Use Edit tool to apply the change, confirm "✅ Applied fix to [file:line]", move to next
- **Skip**: Confirm "⏭️ Skipped", move to next issue
- **Apply All**: Apply this fix and all remaining fixes without further prompts
- **Skip All**: End fix application phase, proceed to final summary

**Update REVIEW_SUMMARY.md:** After all fixes are processed, update `${ROUND_DIR}/REVIEW_SUMMARY.md` to reflect what was actually applied — mark each issue as "Applied" or "Skipped" (with user's rationale if provided).

**Final Summary:**

~~~
## Fix Application Summary

Applied: 3 fixes
Skipped: 2 fixes

Applied:
- src/handlers/user.ts:45 - Added null check
- src/api/routes.ts:123 - Fixed SQL injection
- src/utils/format.ts:67 - Improved error handling

Skipped:
- src/config.ts:12 - Hardcoded value (user chose to skip)
- src/types.ts:34 - Naming suggestion (user chose to skip)
~~~

---

## Phase 4: Post-Review Actions

### Review Persistence

**Thorough mode:** Reviews are always persisted to `.claude/reviews/<branch>/<timestamp-scope>/` as part of Step 2e–2g. The `--save` flag is a no-op. Report: "Review persisted to `.claude/reviews/<branch>/<timestamp-scope>/`"

**Quick mode (if `--save` specified):** Save the review output to a flat file:

1. Create directory if needed: `mkdir -p .claude/reviews/`
2. Write the review to `.claude/reviews/<YYYYMMDD-HHMMSS>-review.md`
3. Include all output sections (Change Overview through Fix Application Summary)
4. Report: "Review saved to `.claude/reviews/<timestamp>-review.md`"

### Issue Tracking (if `--track` specified)

Create TaskCreate entries for each issue found (applied fixes are excluded):

1. For each **unapplied** issue (skipped or not yet fixed):
   - Use `TaskCreate` with:
     - `subject`: "[SEVERITY] file:line - Issue title"
     - `description`: Full issue details including current code, suggested fix, and explanation
     - `activeForm`: "Fixing [issue title]"
2. Report: "Created N tasks for unresolved issues. Use `TaskList` to view them."

---

## Review Approach

1. **Scan for CRITICAL issues first** - These must be fixed
2. **Consider broader context** - How do changes fit with existing code?
3. **Check edge cases** - Error scenarios, boundary conditions
4. **Verify intent** - Do changes accomplish their intended purpose?
5. **Consider maintainability** - Will future developers understand this?
6. **Check dependencies** - Are new dependencies safe and necessary?
7. **Assess binary files** - If the diff includes binary files, note them separately rather than attempting to review their contents

---

## Insight Integration

Throughout the review, provide educational insights:

★ Insight ─────────────────────────────────────
- Why this pattern matters in this codebase
- Trade-offs in the suggested approach
- How similar issues were solved elsewhere in the codebase
─────────────────────────────────────────────────

**Include insights when:**
- Identifying pattern violations (explain the pattern)
- Suggesting fixes (explain why this approach)
- For complex issues (provide context)
- When dependency changes introduce risk (explain the risk)

---

## Spec Integration

If reviewing changes from a `/new-feature` workflow, follow the procedure in **Step 0b** above to discover and resolve feature documentation. Then:
1. Include detailed compliance status in output (see Section 10 format)
2. Flag any deviations from the planned approach

---

## Subagent Reference

### Built-in Agents (launched via Task tool's `subagent_type` parameter)

| Agent | Purpose | When used | Model hint |
|-------|---------|-----------|------------|
| `Explore` | Codebase pattern discovery (Phase 0) | Always (thorough mode) | `opus` |
| `feature-dev:code-reviewer` | Built-in Claude code reviewer (× count) | Always (thorough mode) | `opus` |

### Custom Agents (from `.claude/agents/`)

| Agent | Purpose | When used | Model |
|-------|---------|-----------|-------|
| `code-review-executor` | Runs `agent` CLI for external model reviews | `--external` only | `haiku` (executor only — the actual review model is specified via `--models`) |
| `code-review-synthesizer` | Synthesizes all review findings into structured `REVIEW_SUMMARY.md` | Always (thorough mode) | `opus` |

### Mode × Agent Matrix

| Mode | `Explore` | `feature-dev:code-reviewer` | `code-review-executor` | `code-review-synthesizer` |
|------|-----------|----------------------------|------------------------|--------------------------|
| default (internal) | ✓ background | ✓ background (× count) | — | ✓ foreground |
| --external | ✓ background | ✓ background (× count) | ✓ background (per model × count) | ✓ foreground |
| --quick | — | — | — | — |
| --skip-fix | ✓ background | ✓ background (× count) | only with `--external` | ✓ foreground |
| --pr | ✓ background | ✓ background (× count) | only with `--external` | ✓ foreground |

**Model selection rationale:**
- **Explore → `opus`**: Maximum codebase understanding for pattern discovery.
- **feature-dev:code-reviewer → `opus`**: Most capable model for the reviewer with native codebase access.
- **code-review-executor → `haiku`**: The executor is just a CLI runner — it doesn't need intelligence, only reliable command execution. The actual review intelligence comes from the external model specified via `--models`.
- **code-review-synthesizer → `opus`**: Cross-referencing multiple reviews, resolving conflicts, and producing structured output requires strong reasoning.

---

## Implementation Steps

1. **Prerequisite Checks** (see section above)
   - Verify git repo, no merge conflicts, non-empty diff
   - For `--pr` mode: verify `gh` CLI available
   - For `--external` mode: verify `agent` CLI available
   - For detached HEAD: warn and continue
2. **Parse arguments** to determine mode, scope, and flags (including `--external`, `--models`, `--count`, `--dry-run`)
3. **Phase 0**: Context Gathering
   - Read CLAUDE.md if present (Step 0a)
   - Check for feature documentation (Step 0b)
   - **In a single message, launch in parallel:**
     - Step 0c: Explore agent for pattern discovery (thorough mode, `model: "opus"`)
     - Phase 1: Pre-commit checks (unless `--skip-pre-commit`)
4. **Wait for both** Step 0c and Phase 1 to complete
5. **Phase 2**: Code Review
   - Get diff (Step 2a) — use `gh pr diff` for PR mode
   - Show Change Overview via `git diff --stat` (Step 2b)
   - Check diff size and warn if >3,000 lines (Step 2c)
   - **If `--dry-run`:** show configuration summary and stop
   - Detect dependency changes and run audit tools in background (Step 2d)
   - Create review round directory, save diff (Step 2e). If `--external`, also write review prompt.
   - **Launch all reviewers in parallel** (Step 2f):
     - N× `feature-dev:code-reviewer` (Claude, background, default count: 1)
     - If `--external`: N× `code-review-executor` per external model (background)
   - Wait for all reviewers to complete
   - **Write internal review files:** For each `feature-dev:code-reviewer` agent, capture its returned output and write it to `${ROUND_DIR}/review-claude-code-<N>.md` (the agent cannot write files itself)
   - Verify outputs, handle failures
   - **Launch synthesizer** (Step 2g): `code-review-synthesizer` (foreground)
   - Update `.claude/reviews/REVIEW.md` with round link
6. **Output**: Show complete review with all sections (0 through 13)
   - Sections 4–7 drawn from `REVIEW_SUMMARY.md`
   - Section 8 summarizes cross-model agreement
   - Check for spec compliance
7. **Phase 3**: Interactive Fix Application **(REQUIRED unless --skip-fix or --quick)**
   - Read structured issues from `REVIEW_SUMMARY.md`
   - Do NOT ask "Would you like me to apply fixes?" — proceed directly to prompting
   - Use AskUserQuestion for EACH fixable issue (Apply/Skip/Apply All/Skip All)
   - Apply fixes as requested using Edit tool
   - Update `REVIEW_SUMMARY.md` with applied/skipped status
   - Show final summary with applied/skipped counts
8. **Phase 4**: Post-Review Actions
   - Thorough mode: reviews already persisted (no-op for `--save`)
   - Quick mode + `--save`: persist to `.claude/reviews/`
   - If `--track`: create TaskCreate entries for unresolved issues

---

## Integration with Other Commands

- **`/new-feature`**: Review checks for feature documentation in `.claude/docs/[feature-name]/` (navigates via `PLAN.md` to the current plan version, with legacy flat-layout fallback) and validates:
  - Implementation against `SPEC.md` requirements
  - Design choices against `KEY_DECISIONS.md`
  - Task completion against `CHECKLIST.md`
  - Test coverage against `FIXTURES.md`
- Use `/git-review` during Phase 7 (Code Review) of the feature development process
- Use `/git-review --pr <number>` for reviewing pull requests before merge
- **`/plan-review`**: Shares the multi-model review pattern but uses separate agents (`plan-reviewer` + `review-synthesizer`). The code review agents (`code-review-executor` + `code-review-synthesizer`) are intentionally decoupled to allow independent evolution.

---

## Key Principles

- **Multi-model coverage (with `--external`)** - Different models catch different things; cross-model agreement boosts confidence
- **Include specific line numbers** when pointing out issues
- **Explain WHY** something is an issue, not just what
- **Provide concrete suggestions** for fixes
- **Consider codebase context** from exploration
- **Be constructive and educational** in feedback
- **Always proceed to interactive fix application** - Never end with "Would you like me to..." questions; use AskUserQuestion tool to prompt for each fix
- **Separate confidence levels** - Don't mix high-confidence findings with speculative ones
- **Parallelize where possible** - Step 0c + Phase 1 concurrently; all reviewers launched in parallel
- **Fail gracefully** - Check prerequisites upfront; continue with partial results if some models fail; zero-success guard stops the process
- **Always persist in thorough mode** - Every review round creates an audit trail in `.claude/reviews/`
- **Decoupled agents** - Code review agents are separate from plan review agents to evolve independently
