# Plan Review Prompt Template

> This template generates `_review-prompt.md` for each reviewer. Fill in bracketed placeholders.

```
Review the implementation plan documents in this workspace. Read every file thoroughly before beginning your analysis.

If a CLAUDE.md file exists in the workspace root, read it first for project-specific conventions and guidelines. Evaluate the plan's compliance with these conventions.

The plan documents follow these conventions:
- SPEC.md — Full specification: requirements, implementation phases, iteration log
- README.md — Navigation guide: document index, quick start, code reference pattern
- KEY_DECISIONS.md — Quick reference: design decisions, trade-offs, rationale
- CHECKLIST.md — Progress tracking: extracted tasks organized by phase
- PR_STRATEGY.md — PR planning: dependency graph, PR sequence, branch names
- FIXTURES.md — Test ground truth: pytest fixtures, sample data, assertions

Not all documents may be present. Evaluate what exists.

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

## Output Format

For each dimension:
- Severity-tagged rating: CRITICAL / IMPORTANT / MINOR / GOOD
- Cite specific files and sections from the plan AND the codebase
- Concrete, actionable suggestions with implementation detail

Finish with a **Prioritized Recommendations** section: numbered list ordered by impact, tagged with severity.
```
