---
name: polish
description: Semantic cleanup pass for committed work. Strips low-value comments and development artifacts, then audits tests by value tier. Use when the user wants to clean up code quality, remove development comments, audit test value, or prepare code for review. Also invoked automatically by /feature during the Complete phase.
disable-model-invocation: true
argument-hint: "[comments-only|tests-only] [path/glob]"
---

# /polish — Comment Cleanup & Test Audit

> Semantic cleanup pass for committed work. Strips low-value comments and development artifacts, then audits tests by value tier.

## Overview

Unlike `/deslop-around` (which targets mechanical patterns like `console.log` and TODO), `/polish` targets **semantic slop**: comments that reference the development process, docstrings that restate the obvious, and tests that don't justify their existence.

Usable standalone or invoked automatically by `/feature` during the Complete phase.

## Arguments

- **Scope**: `branch` (default — committed-but-unpushed files) or a file path/glob
- **Mode**: `full` (default — comments + tests) or `comments-only` or `tests-only`

Parse from $ARGUMENTS or use defaults.

---

## Phase 1: Determine Scope

Identify files to analyze:

**Branch scope (default):**
```bash
BASE_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")
git diff --name-only origin/${BASE_BRANCH}..HEAD
```

**Path scope:** Use the provided path/glob directly.

Separate files into two groups:
- **Source files** — implementation code (for comment cleanup)
- **Test files** — files matching test naming conventions for the project (for test audit)

If no files are in scope, report "Nothing to polish" and stop.

---

## Phase 2: Comment Analysis

**Read each source file and test file in scope.** For each, **identify but do not yet apply** the following categories of removable comments:

### Development Artifact Comments (highest priority)
- References to plan phases, micro-cycles, spec details (e.g., "Phase 1:", "Micro-cycle 2:", "Per the spec...", "Implementation phase N")
- References to the development workflow or process (e.g., "Added during convergence", "Required by SPEC.md", "TDD red-green cycle")
- References to review findings (e.g., "Fixed per review feedback", "Addressed CRITICAL finding")

### Low-Value Docstrings
- Top-of-file docstrings that merely restate the module name or its obvious purpose
- Function/method docstrings that only restate the function name, parameter names, or obvious types
- Class docstrings that add no information beyond the class name
- **Keep:** Docstrings for public APIs, non-obvious behavior, complex parameters, or important caveats

### Restating Comments
- Comments that describe what the next line of code does when the code is self-evident (e.g., `# increment counter` before `counter += 1`)
- Comments that restate a function call's purpose when the function name is descriptive
- Section-divider comments that add no information (e.g., `# --- Helper Functions ---` when the functions are obviously helpers)
- **Keep:** Comments explaining *why* (business logic rationale, non-obvious constraints, workaround explanations)

### Excessive Inline Documentation
- Parameter descriptions in docstrings where the type annotation + name are sufficient
- Return value descriptions that restate the function name (e.g., `Returns: The user's name` for `get_user_name()`)
- **Keep:** Descriptions for parameters with non-obvious constraints, side effects, or valid value ranges

**Output:** Collect all findings into a structured report (do NOT apply yet — see Phase 4).

---

## Phase 3: Test Analysis

**Read each test file in scope.** For every test function/method, classify it:

### HIGH — Core behavior; failure = broken feature in production
- Tests the primary happy path
- Tests critical error handling (authentication, authorization, data integrity)
- Tests business logic that directly serves the feature's purpose
- Tests integration points where failure would be user-visible

### MEDIUM — Secondary paths; important but not catastrophic
- Tests for secondary edge cases with reasonable likelihood
- Tests for non-critical validation
- Tests for internal helper behavior where the helper is reused

### LOW — Defensive edge cases, unlikely scenarios, low-signal assertions
- Tests for extremely unlikely input combinations
- Tests that assert on static content, constant values, or string formatting
- Tests that are nearly identical to another test (differ only in trivial input variation without parameterization)
- Tests that would pass even with a subtly broken implementation (tautological)
- Tests where deleting them would leave zero production failures undetected

### Proposed Actions (do NOT apply yet)

For each test, propose one of:
- **Keep** — HIGH tests, or MEDIUM tests covering distinct code paths
- **Consolidate** — 2+ MEDIUM/LOW tests differing only in input → parameterized test
- **Remove** — LOW tests with no unique coverage

**Also identify DRY opportunities:**
- 3+ tests sharing identical fixture/mock setup → propose shared fixture extraction
- Repeated assertion patterns → propose helper assertion (only if significantly reduces noise)

**Output:** Collect all classifications and proposed actions (do NOT apply yet — see Phase 4).

---

## Phase 4: Confirmation Gate

**Present all findings to the user for approval before making any changes.**

### Comment Findings

Show a summary grouped by file:

```
## Comment Cleanup Findings

### src/auth/middleware.ts
1. [DEV ARTIFACT] Line 23: "# Added during Phase 2 convergence" → Remove
2. [LOW-VALUE DOC] Lines 45-48: Docstring restates function name `validate_token` → Remove
3. [RESTATING] Line 67: "# Check if token is expired" before `if token.is_expired()` → Remove

### src/api/routes.ts
4. [DEV ARTIFACT] Line 12: "# Per SPEC.md requirement 3.2" → Remove
```

### Test Findings

Show the classification table and proposed actions:

```
## Test Audit Findings

### tests/test_auth.py
| Test | Classification | Proposed Action | Rationale |
|------|---------------|-----------------|-----------|
| test_login_success | HIGH | Keep | Primary happy path |
| test_login_empty_password | HIGH | Keep | Critical validation |
| test_login_whitespace_only | LOW | Remove | Covered by empty password test |
| test_login_unicode_password | MEDIUM | Keep | Distinct code path |
| test_login_very_long_password | LOW | Consolidate | Merge with max-length parameterized |

### DRY Opportunities
- tests/test_auth.py: 4 tests share identical mock user setup → extract `mock_user` fixture
```

### Approval

Use `AskUserQuestion` to get approval:

```
AskUserQuestion:
  question: "I've identified [N] comment removals across [M] files and [X] test changes. Review the findings above — would you like to proceed?"
  header: "Polish"
  options:
    - label: "Apply all (Recommended)"
      description: "Apply all proposed comment removals and test changes"
    - label: "Comments only"
      description: "Apply only comment removals, skip test changes"
    - label: "Let me pick"
      description: "I'll tell you which specific changes to apply or skip"
    - label: "Cancel"
      description: "Don't apply any changes"
```

- **Apply all:** Proceed to Phase 5 with all changes.
- **Comments only:** Apply only comment cleanup in Phase 5, skip test changes.
- **Let me pick:** Wait for the user to specify which numbered items to apply or skip. Then proceed with the approved subset.
- **Cancel:** Stop without making changes.

---

## Phase 5: Apply Approved Changes

### Comment Cleanup (if approved)

Apply all approved comment removals using `Edit` for each file — do not rewrite entire files.

Run the test suite to verify comment removal didn't break anything.

Commit: `chore: strip low-value comments and development artifacts`.

### Test Audit (if approved)

Apply approved test changes:
1. Remove approved LOW-value tests. Create parameterized replacements where proposed.
2. Apply approved MEDIUM test consolidations.
3. Apply approved DRY improvements (shared fixtures, parameterization).

Run the **full test suite** to verify nothing broke.

Commit: `chore: audit tests — remove low-value, consolidate duplicates`.

---

## Phase 6: Summary

Present results:

```
## Polish Summary

### Comments Removed
- [count] development artifact comments (plan references, process notes)
- [count] low-value docstrings
- [count] restating/obvious comments

### Tests Audited
| Classification | Count | Action |
|---------------|-------|--------|
| HIGH | N | Kept |
| MEDIUM | N | Kept: X, Consolidated: Y, Removed: Z |
| LOW | N | Removed: X, Replaced with parameterized: Y |

### DRY Improvements
- [count] shared fixtures extracted
- [count] test groups parameterized

### Verification
- Tests: [pass/fail]
```

---

## Non-Negotiable Constraints

1. **Never remove comments that explain *why*.** When in doubt, keep it.
2. **Never remove a HIGH-value test.** The audit only touches MEDIUM and LOW.
3. **Run tests after every change phase** (once after comment cleanup, once after test audit).
4. **Preserve behavior.** Comment removal must not change any code logic. Test removal must not leave critical paths uncovered.
5. **Minimal diffs.** Use `Edit` tool for surgical changes, not file rewrites.
6. **Two separate commits.** Comment cleanup and test audit are independent concerns.
7. **Always confirm before applying.** Never remove or change anything without user approval in Phase 4.

---

## Standalone Usage

```
/polish                      # Full pass on branch diff (comments + tests)
/polish comments-only        # Only strip comments
/polish tests-only           # Only audit tests
/polish src/features/        # Scope to specific path
```

## Integration with /feature

When invoked from the Complete phase of `/feature`, `/polish` runs in `full` mode on the current PR's branch diff. In this context, the confirmation gate still applies — findings are presented before any changes are made.
