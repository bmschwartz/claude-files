# Output Format (Code Type)

> Read this when: formatting the code review output for the user.

## Sections (always shown regardless of --skip-fix)

### 0. Change Overview
`git diff --stat` output showing files changed, insertions, deletions.

### 1. Summary
1-2 sentence summary of what the changes do. For `--pr` mode, include PR title and note whether description aligns with actual changes.

### 2. Codebase Context
Brief note on patterns detected and how changes align (thorough mode).

### 3. Dependency Changes (if applicable)
Newly added/removed/changed dependencies and vulnerability scan results.

### 4. Critical Issues
From `REVIEW_SUMMARY.md` (thorough) or direct analysis (quick). Each issue: file:line, agreement level, current code, suggested fix, explanation.

### 5. Important Issues
Same structured format.

### 6. Minor
Optional improvements for code quality.

### 7. Potential Issues
Low-confidence findings for human judgment (thorough mode only).

### 8. Agreement Overview (`--external` or `--count` > 1)
Brief summary of cross-reviewer agreement patterns.

### 9. Insights
Insight blocks explaining key findings.

### 10. Spec Compliance (if applicable)
If `.claude/docs/[feature-name]/` exists:

```
## Spec Compliance

Feature docs: `.claude/docs/user-search/`

### Requirements (from SPEC.md)
- Implements required endpoint
- Missing: Error handling for edge case X

### Key Decisions (from KEY_DECISIONS.md)
- Uses repository pattern as specified

### Checklist Status (from CHECKLIST.md)
- Phase 1: 5/5 complete
- Phase 2: 3/4 complete (missing: input validation tests)

### Test Coverage (from FIXTURES.md)
- Sample fixtures implemented
- Missing: edge case fixture for empty results
```

### 11. Recommendation
- **APPROVE** — No critical issues, ready to commit
- **NEEDS_FIXES** — Has important issues that should be addressed
- **BLOCK** — Has critical issues that must be fixed

### 12. Next Steps (if NEEDS_FIXES or BLOCK)
Prioritized list of what to fix first.

### 13. Review Artifacts (thorough mode only)
Note location of persisted review files and count of raw reviews.
