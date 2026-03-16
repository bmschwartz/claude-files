# Phase: Explore

> Context discovery before asking questions. Questions should be informed by what the codebase already tells us.

## Contract

- **Receives:** Feature description from user arguments
- **Produces:** Codebase Context Report (patterns, architecture, test commands, recommended approach)
- **Invariants:** At least one exploration agent completes successfully. Report includes test execution command.
- **Loops:** No
- **Exit condition:** Context report produced → proceed to Design

## Execution

### Standard/Critical tier

Launch **parallel agents** (`Agent` tool):

1. **Pattern Discovery** (`Explore`) — Find similar features, conventions, reusable utilities. Scan `.claude/docs/*/RETROSPECTIVE.md` for "Patterns to Reuse" and "Suggested Rules" from prior features. Incorporate relevant lessons.
2. **Architecture Context** (`Explore`) — Dependencies, integration points, test frameworks, config patterns.
3. **Deep Code Explorer** (`feature-dev:code-explorer`, Standard/Critical only) — Cross-subsystem execution paths, architecture layers, dependency chains.

### Light tier

Launch only agent 1. Combine pattern + architecture discovery in a single prompt.

## Output — Codebase Context Report

- Similar features and relevance (with file paths)
- Patterns to follow (with file paths)
- Architectural constraints
- **Test execution command** (used throughout Implement phase)
- Recommended approach
- Relevant lessons from prior retrospectives (if any)

## Then

Update CHECKPOINT.md: Phase: Explore, Status: active. Proceed to Design.
