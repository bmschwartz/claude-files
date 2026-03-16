# Code Review Prompt Template

> This template generates `_review-prompt.md` for code review rounds. Fill in bracketed placeholders.

```
Review the code changes (diff) in this workspace. The diff file is at: <DIFF_PATH>

Read the entire diff before beginning your analysis. Then use the project codebase to understand context around the changes.

<If CLAUDE.md exists>
## Project Conventions (from CLAUDE.md)
<CLAUDE.md content>
</If>

## Codebase Patterns (from automated analysis)
<Phase 1 patterns discovered by Explore agent>

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
5. **Pattern Compliance** — Does the code follow established codebase patterns? Deviations risking correctness/security are CRITICAL; style deviations are IMPORTANT.
6. **Test Coverage** — Are changes tested? Do tests follow existing test patterns?
7. **Dependencies** — Are new dependencies safe? Major version bumps? Known CVEs?

## Severity Definitions

- **CRITICAL** (must fix): Security vulnerabilities, data loss risks, breaking API changes, crash-causing missing error handling, race conditions, memory leaks, incorrect business logic, pattern violations risking correctness/security, regression risk, new dependency CVEs
- **IMPORTANT** (should fix): Performance problems, pattern violations (style), missing validation, hardcoded values, incomplete implementations, test coverage gaps, accessibility violations, major version bumps
- **MINOR** (nice to have): Naming improvements, complexity reduction, missing docs for complex logic, code duplication, deprecated API usage, reuse opportunities
- **POTENTIAL** (low confidence): Issues where reviewer is uncertain — flagged for human judgment, listed separately from high-confidence findings

## Output Requirements

For each issue found:
- State the **severity** per the definitions above
- Provide the exact **file path and line number**
- Show the **current code** (the problematic snippet)
- Provide a **suggested fix** (concrete code)
- Explain **why** this is an issue

Only report issues with HIGH confidence. If you are uncertain, tag the issue as POTENTIAL rather than promoting it to a higher severity.

Finish with a **Prioritized Recommendations** section: a numbered list of the most important changes, ordered by impact. Tag each with severity.
```
