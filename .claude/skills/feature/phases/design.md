# Phase: Design

> Spec writing + adversarial spec review + design convergence loop.

## Contract

- **Receives:** Codebase Context Report from Explore, feature description
- **Produces:** Approved SPEC.md + supporting documents in `.claude/docs/[slug]/plans/<timestamp>/`, PLAN.md, CHECKPOINT.md
- **Invariants:** Human approves spec (hard gate in all autonomy modes). Spec quality gates pass.
- **Loops:** Yes — design convergence loop (max 2 rounds), then human gate
- **Exit condition:** Human explicitly approves the spec

## Execution

### 1. Requirements Gathering

**Adaptive rounds** — ask until the spec can be written with confidence:
1. Core Requirements: desired behavior, success criteria, consumers
2. Design Preferences: trade-offs, edge case priorities, error handling
3. Completeness Checks: confirm remaining ambiguities

**Light tier:** Collapse to 1 round. Draft spec with explicit assumptions for gaps.

**Backstop:** After 5 rounds with no new critical requirements, draft spec with stated assumptions.

### 2. Architecture Design

1. **Derive feature slug** from description (lowercase, hyphens). Collision check: if `.claude/docs/[slug]/` exists, increment suffix (`-v2`, `-v3`, ..., cap at `-v9`).
2. **Initialize state:** Create `.claude/docs/[slug]/`, write CHECKPOINT.md (Phase: Design, Status: active), write CLAUDE.md breadcrumb per [references/checkpoint.md](${CLAUDE_SKILL_DIR}/references/checkpoint.md).
3. **Persist exploration:** Write `.claude/docs/[slug]/EXPLORATION.md`.
4. **Architecture blueprint:** Launch `feature-dev:code-architect` (or `Plan` for Light tier).

**Blueprint output:** Files to create/modify, component boundaries, data flow, build sequence, testing strategy, risk table.

### 3. Generate SPEC.md

Create `.claude/docs/[slug]/plans/<YYYYMMDD-HHMMSS>/SPEC.md` using the template at [references/spec-template.md](${CLAUDE_SKILL_DIR}/references/spec-template.md).

**TDD additions per phase:**
- `#### Tests to Write First` — test descriptions with impact tier (HIGH/MEDIUM/LOW). Target ≥50% HIGH, ≤25% LOW.
- `#### Refactoring Notes` — cleanup expected after green

**Spec quality gates** (apply mechanically before review). **Light tier:** Gates 1 and 4 only.
1. Signature Tracing: trace full parameter chain for every modified/called function
2. Draft Syntax: LLM prompts, DB queries, API calls must include draft text
3. Error Path Enumeration: success path, domain failure, infrastructure failure per operation
4. Convention Cross-Check: test naming, imports, assertions vs project CLAUDE.md
5. Data Quality: explicit handling for missing/null/empty/malformed from external sources
6. Test DRY: 3+ tests sharing setup → shared fixture
7. Comment Policy: docstrings only for public APIs and non-obvious behavior

**Critical tier — Spec Adversary:** Launch parallel `Explore` subagent that attempts to break the spec. Incorporate findings before continuing.

### 4. Generate Supporting Documents

Generate **in parallel** from SPEC.md:
- **Always:** CHECKLIST.md (with TDD test/implementation grouping), README.md
- **Conditionally:** KEY_DECISIONS.md (high-impact decisions only), PR_STRATEGY.md (multi-PR only), FIXTURES.md (explicit test fixture data only)
- **Light tier:** CHECKLIST.md and README.md only

Generate `PLAN.md` last (references other documents).

### 5. Design Convergence Loop (optional)

**Standard/Critical tier:** Optionally run `/review --type spec --verdict-only` on the spec.

If `verdict.decision != CONVERGED`: revise spec based on findings, re-review. Max 2 rounds. If still not converged, proceed to human gate with findings noted.

### 6. Human Gate

Present spec to user: **Approve and start (Recommended)** | **Run /review --type plan** | **I have changes**

- `/review --type plan`: invoke with project-root + plan-root. After completion, re-read PLAN.md for updated version, update CHECKPOINT.md Spec Version. Re-prompt gate.
- Changes: incorporate, update docs, re-prompt gate.
- Approved: `TodoWrite` for each implementation phase. Proceed to Implement.

**Gate:** Human has explicitly approved the spec.
