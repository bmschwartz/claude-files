# Code Review Prompt Template

> `scripts/prepare_round.py` renders one `_review-prompt-<key>.md` per reviewer model from the ```` ```section ```` blocks below. Only those blocks are used; do not hand-write the prompt.
>
> **The rubric is the same for every model.** `dimensions`, `severities` and the per-finding fields in `output` define what the synthesizer compares across reviewers, so a model profile may reorder sections and add text around them but never changes their wording. See [model-profiles/README.md](model-profiles/README.md).
>
> The blocks appear in the default order. Placeholders:
> - `{{INPUT_PATH}}` — the round's `_diff.patch`
> - `{{READ_BUDGET}}` — the advisory exploration budget, scaled by diff size and the profile's `budget_scale`; empty when the profile sets `budget: none`
> - `{{DELIVERY}}` — how to hand back the review: write to the output path (internal `deep-reviewer`) or return it as the final message (external agent CLI)
> - `{{CONTEXT_SECTIONS}}` — generated, in this order, omitting any that are empty:
>   1. `## Workspace Scope` — when invoked from a subdirectory (`GIT_PREFIX` non-empty)
>   2. `## Excluded Directories` — when `EXCLUDE_DIRS` is non-empty
>   3. `## Other Reviews` — always: stay out of the reviews folder (apart from the input), which holds other reviewers' output; reviewers that read each other's work make cross-model agreement meaningless
>   4. `## Change Context` — orchestrator-supplied text (`--context-stdin`): PR metadata, author decisions, verification already done
>   5. `## Project Conventions (from <path>)` — CLAUDE.md / .claude/CLAUDE.md (AGENTS.md if neither exists)
>   6. `## Codebase Patterns (from automated analysis)` — `--patterns-file`, only with `--deep-explore`
>   7. `## Feature Specification Context` — each `--spec-file`
>   8. `## Known Project Learnings` — matched learnings per [learning-injection.md](learning-injection.md)

```section task
## Your task

Review the code changes in the diff at `{{INPUT_PATH}}` and report the defects a careful senior reviewer would want fixed before merge. A synthesizer, not a person, reads your review: it merges independent reviews of this same diff from several model families and weighs each finding by its evidence and by whether other reviewers found it too. A finding is useful when another engineer can verify it from what you wrote, and a real issue you leave out is lost.

Read the whole diff first, then use the codebase in this workspace to check what the changes depend on. This is a read-only review: inspect and report, and leave the fixes to the author.
```

```section context
{{CONTEXT_SECTIONS}}
```

```section dimensions
## What to check

1. **Security**: injection (SQL, command, XSS), exposed secrets, unsafe operations
2. **Correctness**: logic errors, wrong assumptions, misuse of APIs or libraries, regressions
3. **Error handling**: failures that could crash or corrupt state, unhandled edge cases, resource leaks
4. **Performance**: N+1 queries, inefficient algorithms, unnecessary allocations, missing caching
5. **Pattern compliance**: whether the change follows the patterns this codebase already uses; compare it with sibling code
6. **Test coverage**: whether the changes are tested, and whether the tests follow the existing test patterns
7. **Dependencies**: whether new or upgraded dependencies are safe (major version bumps, known CVEs)
```

```section severities
## Severity

- **CRITICAL** (must fix): security vulnerabilities, data-loss risks, breaking API changes, missing error handling that can crash, race conditions, memory leaks, incorrect business logic, pattern violations that risk correctness or security, regression risk, CVEs in new dependencies
- **IMPORTANT** (should fix): performance problems, style-level pattern violations, missing validation, hardcoded values, incomplete implementations, test coverage gaps, accessibility violations, major version bumps
- **MINOR** (nice to have): naming, complexity reduction, missing docs for complex logic, duplication, deprecated API usage, reuse opportunities
- **POTENTIAL** (low confidence): a problem you suspect but could not confirm from the code; it is listed separately for a human to judge

Use CRITICAL, IMPORTANT and MINOR for issues the code confirms. When you suspect a problem you could not confirm, report it as POTENTIAL rather than giving it a higher severity.
```

```section exploration
## When to stop exploring

Stop exploring once every changed hunk has been checked against what it depends on: its callers, the existing pattern it follows or departs from, and the tests that cover it. Then write the review. Read a file before making a claim about it, and run independent reads and searches in parallel. {{READ_BUDGET}}
```

```section output
## Output

For each issue give:
- **Severity**, per the definitions above
- **Location**: the exact file path and line number
- **Current code**: the problematic snippet
- **Suggested fix**: concrete code
- **Why** it is a problem

Give every finding in full and keep everything else short: no introduction, no restated summary, no sections with nothing in them. End with **Prioritized Recommendations**: a numbered list of the most important changes, ordered by impact, each tagged with its severity.

{{DELIVERY}}
```
