# Workflow for new projects

## Specification Document

### Initial brainstorming
```
/grill-me I have an idea for a project in which... Output an artifact called docs/idea/IDEA.md.
/brainstorm Review `docs/idea/IDEA.md` and let's spec out the project. Create separate spec documents in `docs/idea/` for the various aspects of the project and a `docs/idea/INDEX.md` referencing the sub-spec files.
```

### Spec review 
```
/grill-me Review the design specs at `docs/idea/INDEX.md` and focus on cross-spec contradictions, missing edge cases, and general assumptions that haven't been validated.
/review --type spec `docs/idea/INDEX.md` [--external to include reviews from other models using the *CURSOR* `agent` CLI]
/grill-me One final pass to review the specs at `docs/idea/INDEX.md`
```
