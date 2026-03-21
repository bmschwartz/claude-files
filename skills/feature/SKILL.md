---
name: feature
description: Orchestrates feature development with TDD + adversarial convergence via autonomous feedback loops. Explores codebase, writes specs, builds test-first, and converges via /review verdicts. Use when the user wants to implement a new feature, says "new feature", "I want to implement", "let's build", or describes functionality to add. Scales by feature tier (Light/Standard/Critical) with configurable autonomy.
disable-model-invocation: true
model: opus
allowed-tools: Read, Grep, Glob, Write, Edit, Bash(git *, mkdir *, date *)
---

# Feature Development

> **v1.0.0** · Ground-up redesign. Replaces `/new-feature` v3.0.0. Contract-based phases with autonomous feedback loops.

## Overview

Orchestrates feature development: **Explore → Design → Implement → Verify → Complete**. Each phase is a contract (receives/produces/invariants) defined in its own file under `phases/`. The orchestrator routes between phases, enforces safety gates, and manages loop limits. Review logic lives in `/review` — this skill calls it and reacts to its verdict.

## Arguments

```
/feature $ARGUMENTS
/feature --autonomy <guided|supervised|autonomous> $ARGUMENTS
/feature --grill $ARGUMENTS
/feature --no-grill $ARGUMENTS
```

### Design Interrogation (`--grill`)

After Requirements Gathering, `/grill-me` stress-tests the design before architecture begins. Tier defaults:

| Tier | Default | Override |
|------|---------|----------|
| **Light** | Skipped | `--grill` to enable |
| **Standard** | Offered (user chooses) | `--grill` / `--no-grill` |
| **Critical** | Mandatory | `--no-grill` to skip |

Independent of `--autonomy` — autonomy governs phase transitions and review loops, `--grill` governs design interrogation.

### Feature Tiers

Determine tier at the start. When ambiguous, start Light and escalate if complexity emerges.

> **Light tier guardrail:** Features touching auth, persistence/schema, external APIs, or security boundaries may NOT be classified as Light without explicit developer justification.

| Tier | When | Phases | Review | Default Autonomy |
|------|------|--------|--------|------------------|
| **Light** | ≤3 files, no new modules, low risk | Explore → Design → Implement → Complete | `/review --quick` in Complete only | `autonomous` |
| **Standard** | Typical feature | All phases | Full verify phase with `/review --external` | `supervised` |
| **Critical** | Security, data model, public API, financial | All phases + mandatory spec adversary | Full verify + tighter cap (2 iterations) | `guided` |

### Autonomy Modes

| Mode | Human Gates | Effect |
|------|-------------|--------|
| `guided` | Every phase transition + loop iterations + completion | Maximum oversight |
| `supervised` | Design approval + verify acceptance | Auto-advance on clean passes |
| `autonomous` | Design approval only | Auto-converge when only MINOR/POTENTIAL remain |

> **Guardrail:** CRITICAL findings always block convergence regardless of autonomy mode. Design approval requires human sign-off in all modes.

---

## Live Context

- Current branch: !`git branch --show-current 2>/dev/null || echo "detached"`
- Active breadcrumb: !`grep -r 'feature:' CLAUDE.md 2>/dev/null || echo "none"`
- Active checkpoints: !`ls .claude/docs/*/CHECKPOINT.md 2>/dev/null || echo "none"`

---

## Invariants (apply at all tiers)

- **Spec Supremacy:** Spec > tests > code. Hierarchy never inverts.
- **Red Before Green:** No implementation without a failing test that demanded it.
- **Anti-Slop:** First "correct" version assumed to contain hidden debt.
- **Fresh-Context Review:** Review always uses fresh subagent context — never self-review.
- **CLAUDE.md breadcrumb:** Always reflects current workflow state. Update on every state transition. Line-level edits only.
- **CHECKPOINT.md:** Single source of truth for "where am I?" Updated at every phase transition. Overwrite, not append. See [references/checkpoint.md](${CLAUDE_SKILL_DIR}/references/checkpoint.md).
- **Conditional re-reads:** At phase boundaries, re-read a doc only if recovering from compaction or its content may have changed.

---

## Core Flow

```
Explore → Design ←──────────────────── spec feedback ──┐
           ↓                                            │
     [human approves spec]                              │
           ↓                                            │
       Implement ──── TDD loop (autonomous) ────────────┤
           ↓                                            │
        Verify ──── review-fix loop (autonomous) ───────┘
           ↓
       Complete
```

**Three autonomous loops:**

1. **TDD Loop** (Implement phase): write test → red → implement → green → refactor → next test. No human gate. Safety: max N fix attempts per test.
2. **Review-Fix Loop** (Verify phase): code → `/review --verdict-only` → fix → re-review → converged. No human gate until cap or stall. Safety: max 3 rounds (2 for Critical), must show improving trend.
3. **Design Convergence Loop** (Design phase): draft spec → `/review --type spec --verdict-only` → revise → converged. Safety: max 2 rounds, then human gate.

---

## Phase Routing

Read the phase contract file for the current phase. Check its receives/produces/invariants. Route to the next phase when the current phase's exit conditions are met.

| Phase | Contract file | Exit condition |
|-------|--------------|----------------|
| Explore | [phases/explore.md](${CLAUDE_SKILL_DIR}/phases/explore.md) | Context report produced |
| Design | [phases/design.md](${CLAUDE_SKILL_DIR}/phases/design.md) | Human approves spec |
| Implement | [phases/implement.md](${CLAUDE_SKILL_DIR}/phases/implement.md) | All tests pass, all phases complete |
| Verify | [phases/verify.md](${CLAUDE_SKILL_DIR}/phases/verify.md) | `/review` verdict: CONVERGED (or cap with human acceptance) |
| Complete | [phases/complete.md](${CLAUDE_SKILL_DIR}/phases/complete.md) | PR ready, retrospective written |

**Light tier:** Skip Verify phase. Run `/review --type code --quick` in Complete instead. If that quick review finds CRITICAL issues, Light tier may **escalate**: the developer chooses between fix-and-rerun-quick, entering full Verify (one-time tier override), or accepting with per-CRITICAL acknowledgement. Escalation to Verify does not reclassify the feature — it runs one Verify cycle and returns to Complete.

**Pre-existing feature path:** If all implementation phases resolve via "behavior pre-existed" with no net code changes, skip Verify → Complete with "feature pre-existed" path.

---

## Startup

Read CLAUDE.md for breadcrumbs. If found, handle per [references/checkpoint.md](${CLAUDE_SKILL_DIR}/references/checkpoint.md) resume protocol:
- **Active breadcrumb:** Ask: Resume (Recommended) | Start fresh | Abandon
- **Shelved breadcrumb:** Ask: Resume shelved | Start fresh
- **No breadcrumb:** Clean start → Explore phase

---

## Spec Feedback Loop

Triggered when implementation reveals SPEC.md is wrong or incomplete. Can occur during Implement or Verify phases.

1. Stop at current point. Document: spec says X, reality requires Y.
2. **Significant change** (acceptance criteria, phases, public API, security, scope): new version snapshot, update PLAN.md + CHECKPOINT.md, **hard gate — do not resume without developer approval**. After approval, **resume at the current phase and substep** — do not return to Design. The spec change is applied in place; the current phase continues with the updated spec.
3. **Minor clarification**: edit in place, log in Iteration Log, proceed.
4. Default: treat as significant.
5. **Circuit breaker:** >3 revisions in a single implementation phase (counter resets per phase) → ask developer: continue | re-scope | return to Design.
6. After spec change in Verify: restart Verify with `--changed-only`.

---

## Roles

| Role | Entity | Function |
|------|--------|----------|
| **Architect** | Human Developer | Vision, domain expertise, acceptance authority |
| **Builder** | Claude Code (main context) | Spec, tests, implementation under TDD constraints |
| **Reviewer** | `/review` skill (fresh context) | Review with structured verdicts |

---

## Tool Reference

> **Note:** `Explore` and `Plan` are **built-in Claude Code subagent types** (passed via `subagent_type` parameter to the Agent tool). They are not custom agent files in `agents/`. `Explore` specializes in codebase search/analysis; `Plan` specializes in architecture planning.

| Phase | Tool / Agent | Purpose |
|-------|-------------|---------|
| Explore | `Explore` (×2, or ×1 Light) | Pattern + architecture discovery |
| Explore | `feature-dev:code-explorer` (Standard/Critical) | Deep execution path tracing |
| Design | `/grill-me` (conditional) | Design interrogation before architecture |
| Design | `feature-dev:code-architect` or `Plan` (Light) | Architecture blueprint |
| Design | `Explore` (Critical — mandatory) | Spec adversary (read-only) |
| Design | `/review --type spec` (optional) | Multi-model spec review |
| Implement | `Explore` subagent | Anti-slop scan (fresh context) |
| Verify | `/review --type code --external --verdict-only` | Adversarial review + convergence |
| Complete | `/deslop-around:deslop-around apply` → `/polish` | Cleanup |
| Complete | `/review --type code --quick` (Light) or conditional | Post-cleanup review guard |

## Additional Resources

- **Phases:** Read when entering each phase
  - [phases/explore.md](${CLAUDE_SKILL_DIR}/phases/explore.md)
  - [phases/design.md](${CLAUDE_SKILL_DIR}/phases/design.md)
  - [phases/implement.md](${CLAUDE_SKILL_DIR}/phases/implement.md)
  - [phases/verify.md](${CLAUDE_SKILL_DIR}/phases/verify.md)
  - [phases/complete.md](${CLAUDE_SKILL_DIR}/phases/complete.md)

- **References:** Read when the situation arises
  - [references/checkpoint.md](${CLAUDE_SKILL_DIR}/references/checkpoint.md) — CHECKPOINT.md format, breadcrumbs, compaction recovery, resume/shelve/abandon
  - [references/spec-template.md](${CLAUDE_SKILL_DIR}/references/spec-template.md) — SPEC.md template with TDD additions
