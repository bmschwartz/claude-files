# /polish — Comment Cleanup & Test Audit

> Semantic cleanup pass for committed work. Strips low-value comments and development artifacts, then audits tests by value tier.

## Overview

Unlike `/deslop-around` (which targets mechanical patterns like `console.log` and TODO), `/polish` targets **semantic slop**: comments that reference the development process, docstrings that restate the obvious, and tests that don't justify their existence.

Usable standalone or invoked automatically by `/new-feature-vdd` during the PR Handoff Gate.

## Arguments

- **Scope**: `branch` (default — committed-but-unpushed files) or a file path/glob
- **Mode**: `full` (default — comments + tests) or `comments-only` or `tests-only`

Parse from $ARGUMENTS or use defaults.

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

## Phase 2: Comment Cleanup

**Read each source file and test file in scope.** For each, identify and remove:

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

**Apply all comment removals.** Use `Edit` for each file — do not rewrite entire files. Commit comment cleanup separately: `chore: strip low-value comments and development artifacts`.

## Phase 3: Test Audit

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
- Tests that are nearly identical to another test (differ only in trivial input variation without using parameterization)
- Tests that would pass even with a subtly broken implementation (tautological)
- Tests where deleting them would leave zero production failures undetected

### Actions

1. **Remove LOW-value tests.** If multiple LOW tests cover similar ground, consider whether a single parameterized test would be better — if so, create it as a replacement. Otherwise, just delete.

2. **Evaluate MEDIUM tests.** For each MEDIUM test, decide:
   - **Keep** if it covers a genuinely distinct code path
   - **Consolidate** if 2+ MEDIUM tests differ only in input → convert to parameterized test
   - **Remove** if on reflection it's actually LOW (the initial classification was generous)

3. **Look for DRY opportunities across all remaining tests:**
   - 3+ tests sharing identical fixture/mock setup → extract shared fixture
   - Tests differing only in input/output → `@pytest.mark.parametrize` (or language equivalent)
   - Repeated assertion patterns → consider a helper assertion function only if it significantly reduces noise

4. **Run the full test suite** after all test changes to verify nothing broke.

5. **Commit test audit separately:** `chore: audit tests — remove low-value, consolidate duplicates`.

## Phase 4: Summary

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

## Non-Negotiable Constraints

1. **Never remove comments that explain *why*.** When in doubt, keep it.
2. **Never remove a HIGH-value test.** The audit only touches MEDIUM and LOW.
3. **Run tests after every change phase** (once after comment cleanup, once after test audit).
4. **Preserve behavior.** Comment removal must not change any code logic. Test removal must not leave critical paths uncovered.
5. **Minimal diffs.** Use `Edit` tool for surgical changes, not file rewrites.
6. **Two separate commits.** Comment cleanup and test audit are independent concerns.

## Standalone Usage

```
/polish                      # Full pass on branch diff (comments + tests)
/polish comments-only        # Only strip comments
/polish tests-only           # Only audit tests
/polish src/features/        # Scope to specific path
```

## Integration with /new-feature-vdd

When invoked from the PR Handoff Gate in `/new-feature-vdd`, `/polish` runs in `full` mode on the current PR's branch diff. The results are committed before presenting the PR to the developer for review.
