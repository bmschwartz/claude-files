# Code Review Prompt Template

> `scripts/prepare_round.py` fills this template to produce `_review-prompt.md`. Only the fenced block is used. Do not hand-write the prompt.
>
> `{{DIFF_PATH}}` is the round's `_diff.patch`. `{{CONTEXT_SECTIONS}}` is generated, in this order, omitting any that are empty:
> 1. `## Workspace Scope` — when invoked from a subdirectory (`GIT_PREFIX` non-empty)
> 2. `## Excluded Directories` — when `EXCLUDE_DIRS` is non-empty
> 3. `## Change Context` — orchestrator-supplied text (`--context-stdin`): PR metadata, author decisions, verification already done
> 4. `## Project Conventions (from <path>)` — CLAUDE.md / .claude/CLAUDE.md (AGENTS.md if neither exists)
> 5. `## Codebase Patterns (from automated analysis)` — `--patterns-file`, only with `--deep-explore`
> 6. `## Feature Specification Context` — each `--spec-file`
> 7. `## Known Project Learnings` — matched learnings per [learning-injection.md](learning-injection.md)

```
Review the code changes (diff) in this workspace. The diff file is at: {{DIFF_PATH}}

Read the entire diff before beginning your analysis. Then use the project codebase to understand context around the changes.

{{CONTEXT_SECTIONS}}

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
