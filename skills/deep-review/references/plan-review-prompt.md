# Plan Review Prompt Template

> `scripts/prepare_round.py` renders one `_review-prompt-<key>.md` per reviewer model from the ```` ```section ```` blocks below, exactly as for [code-review-prompt.md](code-review-prompt.md). The section ids match that template, so one model profile serves both; `dimensions`, `severities` and the per-dimension fields in `output` stay word-for-word the same for every model.
>
> `{{INPUT_PATH}}` is the plan version directory (or single plan/spec file). `{{READ_BUDGET}}` and `{{DELIVERY}}` are filled as for code reviews. `{{CONTEXT_SECTIONS}}` is generated, in this order, omitting any that are empty: `## Workspace Scope` (subdirectory invocation), `## Excluded Directories`, `## Other Reviews` (always; the reviews folder to stay out of), `## Change Context` (`--context-stdin`), `## Known Project Learnings` (matched against file paths referenced in the plan documents, per [learning-injection.md](learning-injection.md)).

```section task
## Your task

Review the implementation plan at `{{INPUT_PATH}}` before it is built, and report what would make the implementation fail or need rework. A synthesizer, not a person, reads your review: it merges independent reviews of this plan from several model families and weighs each point by its evidence and by whether other reviewers raised it too. A point is useful when another engineer can check it against the plan and the code.

Read every plan document before you start. They follow these conventions, though not all may be present; evaluate what exists:
- SPEC.md: full specification (requirements, implementation phases, iteration log)
- README.md: navigation guide (document index, quick start, code reference pattern)
- KEY_DECISIONS.md: design decisions, trade-offs and rationale
- CHECKLIST.md: tasks organized by phase
- PR_STRATEGY.md: dependency graph, PR sequence, branch names
- FIXTURES.md: test ground truth (pytest fixtures, sample data, assertions)

If the workspace root has a CLAUDE.md, it holds the project's conventions; evaluate the plan's compliance with them. This is a read-only review: report, and leave changes to the plan's author.
```

```section context
{{CONTEXT_SECTIONS}}
```

```section dimensions
## Check the plan against the code

Plans most often go wrong in what they assume about the existing code, so check each claim in the codebase rather than taking the plan's word for it:
- **File paths and line numbers**: open each referenced file and confirm the cited lines say what the plan describes.
- **Function signatures and APIs**: confirm referenced functions, classes and methods exist with the assumed signatures.
- **Patterns and conventions**: read the actual code to confirm claims about architecture, naming and module organization.
- **Import paths**: confirm proposed imports point at real modules, and that "single call site" claims hold.
- **Test patterns**: confirm proposed tests fit the existing test infrastructure (fixtures, mocking, async handling, naming).

## What to evaluate

1. **Completeness**: missing steps, unhandled edge cases, gaps in the flow; input combinations, boundary cases and downstream effects.
2. **Correctness**: logical errors, wrong assumptions, API misuse; control flow, short-circuit paths and dead code.
3. **Architecture**: soundness, better patterns, consistency with codebase conventions, module boundaries, single responsibility.
4. **TDD structure**: if the plan uses TDD, whether tests are specific enough to fail meaningfully, test behavior rather than implementation, cover enough, and are clearly described.
5. **Dependencies and ordering**: whether tasks are sequenced correctly and external dependencies are identified.
6. **Risk**: the riskiest parts, blockers, regression risk, and prompt/LLM behavior risk where relevant.
7. **LLM prompt effectiveness** (when the plan changes LLM prompts): whether the new wording will reliably produce the intended behavior, conflicting instructions, whether every location is covered, and how it is tested.
8. **Scalability and performance**: whether it holds up under load, and obvious bottlenecks.
```

```section severities
## Severity

- **CRITICAL**: bugs, logic errors, security issues, or missing steps that would make the implementation fail
- **IMPORTANT**: architectural concerns, significant gaps, or issues that would cause rework later
- **MINOR**: style improvements, nice-to-haves, low-impact optimizations
- **POTENTIAL**: a concern you could not confirm against the plan or the code; it is listed separately for a human to judge

Use CRITICAL, IMPORTANT and MINOR for concerns the plan or the code confirms. When you suspect a problem you could not confirm, report it as POTENTIAL rather than giving it a higher severity.
```

```section exploration
## When to stop exploring

Stop exploring once every claim the plan makes about existing code has been checked and every dimension above has been assessed. Then write the review. Read a file before making a claim about it, and run independent reads and searches in parallel. {{READ_BUDGET}}
```

```section output
## Output

For each dimension give:
- A rating: CRITICAL / IMPORTANT / MINOR / POTENTIAL / GOOD
- The specific plan files and sections, and the codebase files, that support it
- Concrete, actionable suggestions with implementation detail

Give every concern in full and keep everything else short: no introduction and no restated summary. End with **Prioritized Recommendations**: a numbered list ordered by impact, each tagged with its severity.

{{DELIVERY}}
```
