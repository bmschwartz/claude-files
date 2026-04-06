# Workflow for new projects

## Specification Document

### Initial brainstorming
```
/grill-me I have an idea for a project in which... Output an artifact called docs/DESIGN.md.
/brainstorm Review `docs/DESIGN.md` and let's spec out the project. Create separate spec documents in `docs/superpowers/specs` for the various aspects of the project and a `docs/superpowers/specs/SPEC.md` referencing the sub-spec files.
```

### Spec review 
```
/grill-me Review the design specs at `docs/superpowers/specs/SPEC.md` and focus on cross-spec contradictions, missing edge cases, and general assumptions that haven't been validated.
/review --type spec `docs/superpowers/specs/SPEC.md` [--count N] [--external to include reviews from other models using the *CURSOR* `agent` CLI]
/grill-me One final pass to review the specs at `docs/superpowers/specs/SPEC.md` and update `docs/DESIGN.md` for consistency.
```

## Planning

### Write the plan
```
/writing-plans Review the design and specification in `docs/DESIGN.md` and `docs/superpowers/specs/SPEC.md`. Break down the project phases and sub-plans into manageable pieces for sub-agent driven development. Output the subplans to `docs/superpowers/plans` along with an index file `docs/superpowers/plans/PLAN.md` that summarizes and links out to the sub-plans.
```

### Review the plan
```
/review --type plan . docs/superpowers/plans [--count N] [--external to include reviews from other models using the *CURSOR* `agent` CLI]
/grill-me Review the plan documents in `docs/superpowers/plans`
```
