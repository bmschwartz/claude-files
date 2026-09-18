# Workflow for new projects

## Specification Document

### Initial brainstorming
```
/grill-me I have an idea for a project in which... Output an artifact called docs/DESIGN.md.
/brainstorm Review `docs/DESIGN.md` and let's spec out the project. Create separate spec documents in `.superpowers/specs` for the various aspects of the project and a `.superpowers/specs/SPEC.md` referencing the sub-spec files.
```

### Spec review 
```
/grill-me Review the design specs at `.superpowers/specs/SPEC.md` and focus on cross-spec contradictions, missing edge cases, and general assumptions that haven't been validated.
/deep-review --type spec `.superpowers/specs/SPEC.md` [--count N] [--external for cross-model reviewers via Task subagents on Cursor]
/grill-me One final pass to review the specs at `.superpowers/specs/SPEC.md` and update `docs/DESIGN.md` for consistency.
```

## Planning

### Write the plan
```
/writing-plans Review the design and specification in `docs/DESIGN.md` and `.superpowers/specs/SPEC.md`. Break down the project phases and sub-plans into manageable pieces for sub-agent driven development. Output the subplans to `.superpowers/plans` along with an index file `.superpowers/plans/PLAN.md` that summarizes and links out to the sub-plans.
```

### Review the plan
```
/deep-review --type plan . .superpowers/plans [--count N] [--external for cross-model reviewers via Task subagents on Cursor]
/grill-me Review the plan documents in `.superpowers/plans`
```
