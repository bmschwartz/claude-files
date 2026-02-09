# Git Code Review

> **v2.0.0** · Last updated 2026-02-09

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2026-02-09 | Parallel Phase 0c/1, large diff protection, `git diff --stat` overview, `--pr` flag, dependency/vulnerability detection, confidence-based filtering, `--focus` flag, `--save`/`--track` flags, background parallel review agents, comprehensive error handling, model hints for subagents, structural fixes |
| 1.0.0 | 2026-02-09 | Initial version — phased review process, subagent exploration, interactive fix application, spec compliance |

---

A comprehensive code review command that uses subagents to understand codebase patterns, identify issues, and interactively apply fixes.

## Command Usage

### Default Behavior
- `/git-review` - Thorough review with subagents + interactive fix application

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

### Persistence Options
- `/git-review --save` - Save review output to `.claude/reviews/`
- `/git-review --track` - Create TaskCreate entries for each issue found

### Other Options
- `/git-review --skip-pre-commit` - Skip pre-commit checks

Parse the arguments to determine behavior:
$ARGUMENTS

---

## Prerequisite Checks

Before starting any phase, perform these checks. **Stop immediately** if any fail:

1. **Git repository check:** Run `git rev-parse --is-inside-work-tree`. If it fails, report: "Not inside a git repository. Run this command from within a git repo." Stop.

2. **Merge conflict check:** Run `git diff --check HEAD` (or `git diff --check --staged`). If merge conflict markers are found, report: "Merge conflicts detected. Resolve conflicts before running a review." Stop.

3. **PR mode check (if `--pr` specified):** Verify `gh` CLI is available by running `which gh`. If not found, report: "The `gh` CLI is required for PR reviews but was not found. Install it from https://cli.github.com." Stop.

4. **Empty diff check:** After determining scope, run the appropriate diff command. If the diff is empty (no output), report: "No changes found to review." and stop. For `--pr` mode, use `gh pr diff <number>` to check.

5. **Detached HEAD warning:** Run `git symbolic-ref --short HEAD 2>/dev/null`. If this fails (detached HEAD state), warn: "Detached HEAD detected — branch-based features (spec matching, branch name display) may not work correctly." Continue with the review.

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

**Step 2c: Diff Size Check**

Count total diff lines. If the diff exceeds **3,000 lines**:

1. **Warn the user:**
   ~~~
   Large diff detected: ~N lines across M files.
   Large diffs may reduce review quality.
   ~~~

2. **For thorough mode — split into file groups:**
   - Group files by directory/module (e.g., `src/auth/*`, `src/api/*`, `tests/*`)
   - Launch **parallel `feature-dev:code-reviewer` agents** (one per group) using `run_in_background: true`
   - Each agent reviews only its file group's portion of the diff
   - Combine results after all agents complete

3. **For quick mode:** Continue with direct analysis but limit to CRITICAL issues.

4. **Always offer:** "Consider reviewing specific files for deeper analysis: `/git-review path/to/critical.ts`"

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

**Step 2e: Code Review Execution**

**For Default (Thorough) Mode:**

1. Launch `feature-dev:code-reviewer` agent with:
   - The diff content (or file-group portion if split — see Step 2c)
   - Codebase patterns discovered in Phase 0
   - Project-specific rules from CLAUDE.md
   - **Confidence threshold instruction:** "Only report issues with HIGH confidence. Pattern violations against the codebase patterns below carry extra weight. If you are uncertain about an issue, tag it separately as a 'Potential Issue' rather than mixing it with confirmed findings."
   - **Focus filter (if `--focus` specified):** "Focus exclusively on [security|performance|tests] issues. Ignore other categories unless they are CRITICAL severity."

   For diffs under 3,000 lines, launch a single agent in the foreground.
   For diffs over 3,000 lines, launch multiple agents in the background (one per file group) and poll for completion.

2. Combine agent findings with direct analysis

3. Categorize all issues by severity, separating confirmed issues from potential issues

**For Quick Mode:**
- Direct diff analysis without subagents
- Focus on CRITICAL issues only
- Fast turnaround

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
List with file:line references, WHY it's critical, and fix suggestion.

#### 5. Important Issues
List with file:line references and how to fix.

#### 6. Minor
Optional improvements for code quality.

#### 7. Potential Issues
Low-confidence findings for human judgment (thorough mode only).

#### 8. Insights
★ Insight blocks explaining key findings.

#### 9. Spec Compliance (if applicable)
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

#### 10. Recommendation
- ✅ **APPROVE** - No critical issues, ready to commit
- ⚠️ **NEEDS_FIXES** - Has important issues that should be addressed
- 🚫 **BLOCK** - Has critical issues that must be fixed

#### 11. Next Steps (if NEEDS_FIXES or BLOCK)
Prioritized list of what to fix first.

---

## Phase 3: Interactive Fix Application

**(Skip ONLY if `--skip-fix` or `--quick` is specified)**

**⚠️ REQUIRED BEHAVIOR:** After showing the complete review, you MUST proceed to interactive fix application. Do NOT ask "Would you like me to apply fixes?" or similar open-ended questions. Instead, immediately begin prompting for each fixable issue using the `AskUserQuestion` tool.

**For each fixable issue (in order of severity: CRITICAL → IMPORTANT → MINOR):**

~~~
## Issue 1 of N: [Issue Title]

**Location:** path/to/file.ts:45
**Severity:** CRITICAL / IMPORTANT / MINOR

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

### Review Persistence (if `--save` specified)

Save the complete review output to a timestamped file:

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
1. Include detailed compliance status in output (see Section 9 format)
2. Flag any deviations from the planned approach

---

## Subagent Reference

All agents below are **built-in Claude Code agent types** launched via the Task tool's `subagent_type` parameter. They do not require custom agent files in `.claude/agents/`.

| Mode | `Explore` agent | `feature-dev:code-reviewer` agent | Model hint |
|------|-----------------|-----------------------------------|------------|
| default | Yes (background) | Yes (foreground or background for large diffs) | Explore: `opus`, code-reviewer: `opus` |
| --quick | No | No | — |
| --skip-fix | Yes (background) | Yes (foreground or background for large diffs) | Explore: `opus`, code-reviewer: `opus` |
| --pr | Yes (background) | Yes | Explore: `opus`, code-reviewer: `opus` |

**Model selection rationale:**
- **All agents → `opus`**: Use the most capable model for maximum review quality across all subagents.

---

## Implementation Steps

1. **Prerequisite Checks** (see section above)
   - Verify git repo, no merge conflicts, non-empty diff
   - For `--pr` mode: verify `gh` CLI available
   - For detached HEAD: warn and continue
2. **Parse arguments** to determine mode, scope, and flags
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
   - Check diff size; split into file groups if >3,000 lines (Step 2c)
   - Detect dependency changes and run audit tools in background (Step 2d)
   - Launch code review — single or multi-agent depending on diff size (Step 2e)
     - Pass `--focus` filter and confidence threshold to agent prompt
   - Categorize all issues (confirmed vs. potential)
   - Check for spec compliance
6. **Output**: Show complete review with all sections (0 through 11)
7. **Phase 3**: Interactive Fix Application **(REQUIRED unless --skip-fix or --quick)**
   - Do NOT ask "Would you like me to apply fixes?" — proceed directly to prompting
   - Use AskUserQuestion for EACH fixable issue (Apply/Skip/Apply All/Skip All)
   - Apply fixes as requested using Edit tool
   - Show final summary with applied/skipped counts
8. **Phase 4**: Post-Review Actions
   - If `--save`: persist review to `.claude/reviews/`
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

---

## Key Principles

- **Include specific line numbers** when pointing out issues
- **Explain WHY** something is an issue, not just what
- **Provide concrete suggestions** for fixes
- **Consider codebase context** from exploration
- **Be constructive and educational** in feedback
- **Always proceed to interactive fix application** - Never end with "Would you like me to..." questions; use AskUserQuestion tool to prompt for each fix
- **Separate confidence levels** - Don't mix high-confidence findings with speculative ones
- **Parallelize where possible** - Step 0c + Phase 1 always run concurrently; large diffs split across agents
- **Fail gracefully** - Check prerequisites upfront; warn on edge cases rather than crashing mid-review
