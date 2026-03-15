# Review Criteria

> Read this when: performing direct analysis (quick mode) or understanding severity definitions.

## CRITICAL ISSUES (Must be fixed)
- Security vulnerabilities (SQL injection, XSS, exposed secrets, unsafe operations)
- Data loss risks or corruption possibilities
- Breaking changes to public APIs without proper deprecation
- Missing error handling that could crash the application
- Race conditions or deadlocks
- Memory leaks or resource exhaustion
- Incorrect business logic that violates core requirements
- **Pattern Violations (correctness/security)**: Code that contradicts established codebase patterns AND risks correctness or security (e.g., bypassing auth checks, ignoring validation patterns). Stylistic violations belong under IMPORTANT.
- **Regression Risk**: Changes that might break existing functionality
- **New Dependency Vulnerabilities**: Known CVEs in newly added dependencies

## IMPORTANT ISSUES (Should be fixed)
- Performance problems (N+1 queries, inefficient algorithms, unnecessary loops)
- **Pattern Violations (style/convention)**: Code that breaks established patterns without correctness/security risk
- Missing input validation or boundary checks
- Hardcoded values that should be configurable
- Incomplete implementations or TODO comments
- Test coverage gaps for critical functionality
- Accessibility violations
- **Inconsistent Style**: Deviates from patterns found in similar files
- **Missing Tests**: When similar features have tests but this doesn't
- **Major Version Bumps**: Dependencies with major version changes

## MINOR (Nice to have)
- Better variable/function names for clarity
- Opportunities to reduce complexity
- Missing documentation for complex logic
- Code duplication that could be refactored
- Outdated dependencies or deprecated API usage
- **Pattern Opportunities**: Where existing utilities could be reused
- **Future Maintenance**: Complexity that will be hard to maintain

## POTENTIAL ISSUES (Low confidence)
Issues where the reviewer is not fully certain but wants to flag for human judgment. Listed separately to avoid polluting high-confidence findings.
