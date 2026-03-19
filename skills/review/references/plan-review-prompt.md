# Plan Review Prompt Template

> This template generates `_review-prompt.md` for plan/spec review rounds. Fill in bracketed placeholders.

```
Review the implementation plan documents in this workspace. Read every file thoroughly before beginning your analysis.

<If workspace is scoped (GIT_PREFIX is non-empty)>
## Workspace Scope
This review is scoped to a subdirectory of a larger repository. Focus your codebase verification on the code within this workspace.
</If>

<If EXCLUDE_DIRS is non-empty>
## Excluded Directories
Do not explore or reference code in these directories: <EXCLUDE_DIRS comma-separated>
They contain unrelated code from other work-in-progress branches.
</If>

If a CLAUDE.md file exists in the workspace root, read it first for project-specific conventions and guidelines. Evaluate the plan's compliance with these conventions.

The plan documents follow these conventions:
- SPEC.md — Full specification: requirements, implementation phases, iteration log
- README.md — Navigation guide: document index, quick start, code reference pattern
- KEY_DECISIONS.md — Quick reference: design decisions, trade-offs, rationale
- CHECKLIST.md — Progress tracking: extracted tasks organized by phase
- PR_STRATEGY.md — PR planning: dependency graph, PR sequence, branch names
- FIXTURES.md — Test ground truth: pytest fixtures, sample data, assertions

Not all documents may be present. Evaluate what exists.

<If project learnings matched>
## Known Project Learnings

The following patterns have been identified in prior reviews of this codebase. Evaluate whether the proposed plan addresses or risks repeating these patterns:

<Numbered list of matched learnings per injection format from learning-injection.md>

When evaluating the plan, cross-reference against these known patterns. Plans that proactively address known learnings should be noted positively. Plans that risk repeating known issues should be flagged with the learning ID.
</If>

## Codebase Verification (CRITICAL)

You have access to the actual project codebase. **Actively verify every claim the plan makes about the codebase.** Do not take the plan's word for it. Specifically:

- **File paths & line numbers:** Open each referenced file and verify the code at cited lines matches what the plan describes.
- **Function signatures & APIs:** Verify referenced functions, classes, and methods exist with assumed signatures.
- **Existing patterns & conventions:** Read actual code to confirm claims about architecture, naming, module organization.
- **Import paths:** Verify proposed imports reference correct module paths and "single call site" assertions are true.
- **Test patterns:** Verify proposed test approaches match existing infrastructure (fixtures, mocking, async handling, naming).

## Evaluation Dimensions

### 1. Completeness
Missing steps, unhandled edge cases, gaps in flow? Pay attention to input combination coverage, boundary edge cases, and downstream effects.

### 2. Correctness
Logical errors, wrong assumptions, misuse of APIs? Pay attention to control flow verification, short-circuit paths, and dead code.

### 3. Architecture
Sound design? Better patterns available? Consistent with codebase conventions? Check pattern consistency, module boundaries, single responsibility.

### 4. TDD Structure
If plan uses TDD: Are tests specific enough to fail meaningfully? Do they validate behavior vs implementation? Sufficient coverage? Clear descriptions?

### 5. Dependencies & Ordering
Tasks sequenced correctly? External dependencies identified?

### 6. Risk
Riskiest parts? Blockers? Regression risk and prompt/LLM behavior risk if applicable.

### 7. LLM Prompt Effectiveness (when applicable)
If plan modifies LLM prompts: Will new language reliably produce intended behavior? Conflicting instructions? All locations covered? Tested?

### 8. Scalability & Performance
Will this hold up under load? Obvious bottlenecks?

## Severity Definitions

- **CRITICAL**: Bugs, logic errors, security issues, or missing steps that would cause implementation to fail
- **IMPORTANT**: Architectural concerns, significant gaps, or issues that would cause rework later
- **MINOR**: Style improvements, nice-to-haves, or low-impact optimizations
- **POTENTIAL**: Low-confidence concerns — flagged for human judgment

## Output Format

For each dimension:
- Severity-tagged rating: CRITICAL / IMPORTANT / MINOR / POTENTIAL / GOOD
- Cite specific files and sections from the plan AND the codebase
- Concrete, actionable suggestions with implementation detail

Finish with a **Prioritized Recommendations** section: numbered list ordered by impact, tagged with severity.
```
