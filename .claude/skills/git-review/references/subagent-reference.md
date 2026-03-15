# Subagent Reference

> Read this when: understanding which agents are used and when.

## Built-in Agents (via Agent tool's `subagent_type`)

| Agent | Purpose | When used | Model |
|-------|---------|-----------|-------|
| `Explore` | Codebase pattern discovery (Phase 0) | Always (thorough mode) | `opus` |
| `feature-dev:code-reviewer` | Built-in Claude code reviewer (× count) | Always (thorough mode) | `opus` |

## Custom Agents (from `.claude/agents/`)

| Agent | Purpose | When used | Model |
|-------|---------|-----------|-------|
| `code-review-executor` | Runs `agent` CLI for external model reviews | `--external` only | `haiku` (executor only — actual review model via `--models`) |
| `code-review-synthesizer` | Synthesizes all review findings into `REVIEW_SUMMARY.md` | Always (thorough mode) | `opus` |

## Mode × Agent Matrix

| Mode | `Explore` | `feature-dev:code-reviewer` | `code-review-executor` | `code-review-synthesizer` |
|------|-----------|----------------------------|------------------------|--------------------------|
| default (internal) | ✓ background | ✓ background (× count) | — | ✓ foreground |
| --external | ✓ background | ✓ background (× count) | ✓ background (per model × count) | ✓ foreground |
| --quick | — | — | — | — |
| --skip-fix | ✓ background | ✓ background (× count) | only with `--external` | ✓ foreground |
| --pr | ✓ background | ✓ background (× count) | only with `--external` | ✓ foreground |

## Model Selection Rationale

- **Explore → `opus`**: Maximum codebase understanding for pattern discovery.
- **feature-dev:code-reviewer → `opus`**: Most capable for reviewer with native codebase access.
- **code-review-executor → `haiku`**: Just a CLI runner — review intelligence comes from the external model.
- **code-review-synthesizer → `opus`**: Cross-referencing multiple reviews requires strong reasoning.
