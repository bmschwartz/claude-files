# Git Code Review

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

### Other Options
- `/git-review --skip-pre-commit` - Skip pre-commit checks

Parse the arguments to determine behavior:
$ARGUMENTS

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

**Step 0c: Codebase Pattern Discovery**

For default (thorough) mode, launch an **Explore agent** to:
- Find similar code patterns in the files being modified
- Identify error handling conventions
- Understand testing patterns
- Find related code that might be impacted by these changes

For `--quick` mode, skip this step.

**Codebase Context Report:**
After exploration, briefly note:
```
### Patterns Detected
- Error handling: [pattern observed, e.g., "uses Result<T, E> pattern"]
- Testing: [convention, e.g., "co-located test files with .test.ts suffix"]
- Naming: [convention observed]

### Related Code
- `path/to/related.py` - [Why changes might affect it]
```

★ Insight ─────────────────────────────────────
Explain what patterns were discovered:
- Why these patterns exist in this codebase
- How they inform the review criteria
─────────────────────────────────────────────────

---

### Phase 1: Pre-commit Checks

(Skip if `--skip-pre-commit` is specified)

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

**Get the Diff:**
Execute a single git diff command based on arguments:
- `git diff --staged` for staged only
- `git diff` for unstaged only
- `git diff HEAD` for all changes

**Including untracked files:** For each new (untracked) file, use `git diff --no-index /dev/null <file>` to generate a diff without modifying the staging area. This is side-effect-free and safe if the process is interrupted.

**For Default (Thorough) Mode:**

1. Launch `feature-dev:code-reviewer` agent with:
   - The diff content
   - Codebase patterns discovered in Phase 0
   - Project-specific rules from CLAUDE.md

2. Combine agent findings with direct analysis

3. Categorize all issues by severity

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

### MINOR (Nice to have)
- Better variable/function names for clarity
- Opportunities to reduce complexity (extract methods, simplify conditionals)
- Missing documentation for complex logic
- Code duplication that could be refactored
- Outdated dependencies or deprecated API usage
- Consistent formatting and style
- **Pattern Opportunities**: Where existing utilities could be reused
- **Future Maintenance**: Complexity that will be hard to maintain

---

## Output Format

### Always Shown (regardless of --skip-fix):

#### 1. Summary
1-2 sentence summary of what the changes do.

#### 2. Codebase Context
Brief note on patterns detected and how changes align (thorough mode).

#### 3. Critical Issues
List with file:line references, WHY it's critical, and fix suggestion.

#### 4. Important Issues
List with file:line references and how to fix.

#### 5. Minor
Optional improvements for code quality.

#### 6. Insights
★ Insight blocks explaining key findings.

#### 7. Spec Compliance (if applicable)
If a related `.claude/docs/[feature-name]/` directory exists:
```
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
```

#### 8. Recommendation
- ✅ **APPROVE** - No critical issues, ready to commit
- ⚠️ **NEEDS_FIXES** - Has important issues that should be addressed
- 🚫 **BLOCK** - Has critical issues that must be fixed

#### 9. Next Steps (if NEEDS_FIXES or BLOCK)
Prioritized list of what to fix first.

---

## Phase 3: Interactive Fix Application

**(Skip ONLY if `--skip-fix` or `--quick` is specified)**

**⚠️ REQUIRED BEHAVIOR:** After showing the complete review, you MUST proceed to interactive fix application. Do NOT ask "Would you like me to apply fixes?" or similar open-ended questions. Instead, immediately begin prompting for each fixable issue using the `AskUserQuestion` tool.

**For each fixable issue (in order of severity: CRITICAL → IMPORTANT → MINOR):**

```
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
```

**REQUIRED: Use AskUserQuestion tool with these exact options:**

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

**After user responds:**
- **Apply**: Use Edit tool to apply the change, confirm "✅ Applied fix to [file:line]", move to next
- **Skip**: Confirm "⏭️ Skipped", move to next issue
- **Apply All**: Apply this fix and all remaining fixes without further prompts
- **Skip All**: End fix application phase, proceed to final summary

**Final Summary:**
```
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
```

---

## Review Approach

1. **Scan for CRITICAL issues first** - These must be fixed
2. **Consider broader context** - How do changes fit with existing code?
3. **Check edge cases** - Error scenarios, boundary conditions
4. **Verify intent** - Do changes accomplish their intended purpose?
5. **Consider maintainability** - Will future developers understand this?

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

---

## Spec Integration

If reviewing changes from a `/new-feature` workflow, follow the procedure in **Step 0b** above to discover and resolve feature documentation. Then:
1. Include detailed compliance status in output (see Section 7 format)
2. Flag any deviations from the planned approach

---

## Subagent Reference

Both agents below are **built-in Claude Code agent types** launched via the Task tool's `subagent_type` parameter. They do not require custom agent files in `.claude/agents/`.

| Mode | `Explore` agent | `feature-dev:code-reviewer` agent |
|------|-----------------|-----------------------------------|
| default | Yes | Yes |
| --quick | No | No |
| --skip-fix | Yes | Yes |

---

## Implementation Steps

1. Check if we're in a git repository
2. Parse arguments to determine mode and scope
3. **Phase 0**: Context Gathering
   - Read CLAUDE.md if present
   - For thorough mode: Launch Explore agent for pattern discovery
4. **Phase 1**: Pre-commit Checks (unless --skip-pre-commit)
   - Detect project type
   - Run checks in parallel
5. **Phase 2**: Code Review
   - Get diff with single git command
   - For thorough mode: Launch `feature-dev:code-reviewer` agent
   - Categorize all issues
   - Check for related spec files
6. **Output**: Show complete review with all sections
7. **Phase 3**: Interactive Fix Application **(REQUIRED unless --skip-fix or --quick)**
   - Do NOT ask "Would you like me to apply fixes?" - proceed directly to prompting
   - Use AskUserQuestion for EACH fixable issue (Apply/Skip/Apply All/Skip All)
   - Apply fixes as requested using Edit tool
   - Show final summary with applied/skipped counts

---

## Integration with Other Commands

- **`/new-feature`**: Review checks for feature documentation in `.claude/docs/[feature-name]/` (navigates via `PLAN.md` to the current plan version, with legacy flat-layout fallback) and validates:
  - Implementation against `SPEC.md` requirements
  - Design choices against `KEY_DECISIONS.md`
  - Task completion against `CHECKLIST.md`
  - Test coverage against `FIXTURES.md`
- Use `/git-review` during Phase 7 (Code Review) of the feature development process

---

## Key Principles

- **Include specific line numbers** when pointing out issues
- **Explain WHY** something is an issue, not just what
- **Provide concrete suggestions** for fixes
- **Consider codebase context** from exploration
- **Be constructive and educational** in feedback
- **Always proceed to interactive fix application** - Never end with "Would you like me to..." questions; use AskUserQuestion tool to prompt for each fix
