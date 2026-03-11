# Feature Development with TDD + Adversarial Convergence

> **v2.2.0** · Adds Light tier guardrail, hard gate on Suggested Rules, restored 3e self-check, expanded Phase 4 convergence semantics. Based on v1↔v2 review feedback.

## Overview

Orchestrates feature development: **explore → spec → test-first → adversarial converge**. Process scales by feature tier.

### Feature Tiers

Determine tier at the start. When ambiguous, start Light and escalate if complexity emerges.

> **Light tier guardrail:** Features touching auth, persistence/schema, external APIs, or security boundaries may NOT be classified as Light without explicit developer justification. If the developer insists, log the justification in CHECKPOINT.md Notes.

| Tier | When | Phases | Adversarial | Default Autonomy |
|------|------|--------|-------------|------------------|
| **Light** | ≤3 files, no new modules, low risk | 0 (quick) → 1 (1 round) → 2 → 3 → 5 | Skip Phase 4; run `/git-review --quick` in 5d instead | `autonomous` |
| **Standard** | Typical feature | All phases | Full convergence | `supervised` |
| **Critical** | Security, data model, public API, financial | All phases + spec adversary (2b) | Full convergence + tighter cap (2 iterations before escalation) | `guided` |

**Autonomy levels** control human oversight at gates. Each tier defaults to its natural level; override with `--autonomy <mode>`:

| Mode | Human Gates | Effect |
|------|-------------|--------|
| `guided` | Every phase transition + convergence iterations + completion | Maximum oversight — every gate asks |
| `supervised` | Spec approval (2d) + convergence acceptance (4d) | Auto-advance on clean passes; minor spec clarifications proceed without asking |
| `autonomous` | Spec approval (2d) only | Auto-converge when only MINOR/POTENTIAL remain; skip completion review prompt |

> **Guardrail:** CRITICAL findings in Phase 4 always block convergence regardless of autonomy mode. `--autonomy` reduces ceremony, not safety. Phase 2d (spec approval) requires human approval in all modes.

### Invariants (apply at all tiers)

- **Spec Supremacy:** Spec > tests > code. Hierarchy never inverts.
- **Red Before Green:** No implementation without a failing test that demanded it.
- **Anti-Slop:** First "correct" version assumed to contain hidden debt.
- **Fresh-Context Review:** Adversarial review always uses fresh subagent context — never self-review in the main orchestrator.
- **CLAUDE.md breadcrumb:** Always reflects current workflow state (active/shelved/none). Update on every state transition. Never rewrite the full file — line-level edits only.
- **CHECKPOINT.md:** Single source of truth for "where am I?" Updated at every phase/substep transition. Overwrite, not append.
- **Conditional re-reads:** At phase boundaries, re-read a state doc only if (a) recovering from compaction, or (b) its version/content may have changed (check CHECKPOINT.md's Spec Version field or Iteration Log entries as change signals). Skip re-reads of unchanged docs to save tokens.

### Roles

| Role | Entity | Function |
|------|--------|----------|
| **Architect** | Human Developer | Vision, domain expertise, acceptance authority |
| **Builder** | Claude Code (main context) | Spec, tests, implementation under TDD constraints |
| **Adversary** | `/git-review --external` or fresh subagent | Review with iterative convergence |

---

## Core Flow

```
Phase 0 → 1 → 2 (spec + review gate) → 3 (TDD per phase) → 4 (adversarial convergence) → 5 (completion)
                                              ↑                        |
                                              └── spec feedback loop ──┘
```

---

## Phase 0: Codebase Exploration

**Purpose:** Gather context BEFORE asking questions. Questions should be informed by what the codebase already tells us.

**Startup:** Read CLAUDE.md for existing breadcrumbs. Handle resume/shelve/abandon per [Appendix A](#appendix-a-resumeshelveabandon-protocol).

**Launch parallel agents** (`Agent` tool):

1. **Pattern Discovery** (`Explore`) — similar features, conventions, reusable utilities. Also scan `.claude/docs/*/RETROSPECTIVE.md` for "Patterns to Reuse" and "Suggested Rules" from prior features — incorporate relevant lessons into the context report. (Opportunistic: skip if no retrospective files exist.)
2. **Architecture Context** (`Explore`) — dependencies, integration points, test frameworks, config patterns
3. **Deep Code Explorer** (`feature-dev:code-explorer`) — **Standard/Critical only.** Cross-subsystem execution paths, architecture layers, dependency chains

**Light tier:** Launch only agent 1. Combine pattern + architecture discovery in a single prompt.

**Output — Codebase Context Report:**
- Similar features and relevance
- Patterns to follow (with file paths)
- Architectural constraints
- **Test execution command** (used throughout Phase 3)
- Recommended approach

---

## Phase 1: Focused Discovery

**Purpose:** Ask the human what the codebase can't tell us.

**Adaptive rounds** — ask until the spec can be written with confidence:
1. **Core Requirements:** Desired behavior, success criteria, consumers
2. **Design Preferences:** Trade-offs, edge case priorities, error handling, UX
3. **Completeness Checks:** Confirm remaining ambiguities. Continue until you can answer: (a) what success looks like, (b) main edge cases, (c) acceptance criteria, (d) implementation phases

**Light tier:** Collapse to 1 round. Draft spec with explicit assumptions for gaps.

**Backstop:** After 5 rounds with no new critical requirements, draft spec with stated assumptions and ask: "Proceed with these assumptions, or clarify further?"

---

## Phase 2: Specification + Review Gate

### 2a: Architecture Design

1. **Derive feature slug** from description (lowercase, hyphens, drop only articles/prepositions). Collision check: if `.claude/docs/[slug]/` exists from a prior workflow (completed, abandoned, or shelved), append `-v2`.
2. **Initialize state:** Create `.claude/docs/[slug]/`, write CHECKPOINT.md (Phase: 2, Substep: 2a, Status: active), write CLAUDE.md breadcrumb.
3. **Persist exploration:** Write `.claude/docs/[slug]/EXPLORATION.md` summarizing Phase 0 findings + Phase 1 requirements.
4. **Architecture blueprint:** Launch `feature-dev:code-architect` (or `Plan` for Light tier) with exploration findings + requirements.

**Blueprint output:** Files to create/modify, component boundaries, data flow, build sequence, testing strategy, risk table (Pattern Deviation, Dependency Impact, Testing Coverage + applicable: Security, Performance, Integration, Data Migration).

### 2b: Generate SPEC.md

Update CHECKPOINT.md: Substep: 2b.

Create `.claude/docs/[slug]/plans/<YYYYMMDD-HHMMSS>/SPEC.md`. Update CHECKPOINT.md `Spec Version` to point to this timestamp directory — this is the baseline for conditional re-reads, compaction recovery, and the spec feedback loop.

**SPEC.md structure:** Follow the template in `new-feature.md` Phase 4 (SPEC.md structure section). Add these **TDD-specific additions** to each Implementation Phase:
- `#### Tests to Write First` — test descriptions with impact tier (HIGH/MEDIUM/LOW per `/polish` Phase 3 definitions). Target ≥50% HIGH, ≤25% LOW.
- `#### Refactoring Notes` — cleanup expected after green

**Spec quality gates** (apply mechanically before review — these mirror `/plan-review` dimensions and catch issues before investing in multi-model review). **Light tier:** Apply gates 1 and 4 only; skip 2, 3, 5, 6, 7.
1. **Signature Tracing:** Trace full parameter chain for every modified/called function. Grep actual signatures.
2. **Draft Syntax:** LLM prompts, DB queries, API calls, DSL syntax must include draft text — not abstract descriptions.
3. **Error Path Enumeration:** Per operation: success path, domain failure, infrastructure failure.
4. **Convention Cross-Check:** Test naming, imports, assertion formats, logging vs. project CLAUDE.md.
5. **Data Quality:** Explicit handling for missing/null/empty/malformed values from external sources.
6. **Test DRY:** 3+ tests sharing setup → shared fixture. Input-only variation → parameterize (see `/polish` Phase 3 for consolidation patterns).
7. **Comment Policy:** Docstrings only for public APIs and non-obvious behavior (see `/polish` Phase 2 for what constitutes low-value).

**Critical tier — Spec Adversary:** Launch a parallel `general-purpose` subagent that attempts to break the spec: find ambiguities, missing edge cases, unstated assumptions, conflicting requirements. Incorporate findings before 2c. This shifts adversarial pressure earlier — cheaper to fix specs than code.

### 2c: Generate Supporting Documents

Update CHECKPOINT.md: Substep: 2c.

Generate supporting documents using the templates in `new-feature.md` (Supporting Document Templates section). TDD-specific modification to CHECKLIST.md: label groups within each phase as `#### Tests (complete before implementation)` and `#### Implementation (only after all tests pass)`.

**Always:** CHECKLIST.md, README.md. **Conditionally:** KEY_DECISIONS.md (high-impact decisions only), PR_STRATEGY.md (multi-PR only — see [Appendix C](#appendix-c-multi-pr-workflow)). **Not generated:** FIXTURES.md — SPEC.md's "Tests to Write First" sections serve as test data source of truth. **Light tier:** Skip KEY_DECISIONS.md and PR_STRATEGY.md; generate only CHECKLIST.md and README.md.

**Generate PLAN.md** at doc root linking to current version.

### 2d: Review Gate

Update CHECKPOINT.md: Substep: 2d.

Present spec to user with options: **Run /plan-review (Recommended)** | **Approve and start** | **I have changes**.

- `/plan-review`: invoke with `<project-root> .claude/docs/[slug]` (both positional args required — see `plan-review.md`). After it completes, re-read PLAN.md for updated version path and update CHECKPOINT.md `Spec Version` to the new timestamp directory. Re-prompt gate.
- Changes: incorporate, update docs, re-prompt gate.
- Approved: `TaskCreate` for each implementation phase. Proceed to Phase 3.

**Gate:** User has explicitly approved the spec.

---

## Phase 3: TDD Implementation

**Purpose:** Build via phase-gated TDD. Every line demanded by a failing test.

**Setup:** Create feature branch `feat/[slug]`. Mark first phase task `in_progress`. Update CHECKPOINT.md: Phase: 3, Substep: 3a, Implementation Phase: 1 of N. For multi-PR, see [Appendix C](#appendix-c-multi-pr-workflow).

```
┌─────────────────────────────────────────────────────┐
│  TDD MICRO-CYCLE (1-3 related tests per cycle):     │
│  3a: Write failing tests  →  3b: Verify Red         │
│  3c: Implement minimum    →  3d: Verify Green        │
│  Repeat until all phase tests exist  →  3e: Refactor │
│  3f: Mark phase complete + git checkpoint            │
│                                                      │
│  Do NOT implement before confirming Red.             │
│  Do NOT fix compile errors caused by missing         │
│  implementation during Red — that IS valid Red.      │
└─────────────────────────────────────────────────────┘
```

### 3a: Write Failing Tests
Write next 1-3 tests from SPEC.md's "Tests to Write First." Follow project test patterns. Before running, reconcile all tests written so far against spec (flag any unmatched test; don't require all spec tests yet).

### 3b: Verify Red
Run test command. Valid Red: assertion failures, missing-symbol compile errors. Invalid Red: syntax errors in test code, broken imports for existing modules, infra failures — fix those first.

If tests pass unexpectedly: (a) tests pre-existing behavior → note, continue; (b) tautological → fix test; (c) prior phase covers it → note. If ALL tests pass → behavior pre-exists. Verify matches spec intent, skip to 3f.

### 3c: Implement Minimum Code
Write the **minimum** to pass failing tests. No gold-plating.

### 3d: Verify Green
Run **full** test suite. If existing tests broke, fix implementation (not old tests, unless spec explicitly changed that behavior). Update CHECKPOINT.md `Tests Completed` to reflect tests written so far in the current implementation phase. If more tests remain in this phase → return to 3a.

### 3e: Refactor
Address SPEC.md Refactoring Notes. Extract duplication, improve naming, apply Phase 0 patterns. Re-run full suite.

**Post-refactor self-check** (lightweight — done in-context before the fresh anti-slop subagent):
- **Traceability:** Every new abstraction must be exercised by an existing test. If not → inline it (premature).
- **Test DRY:** 3+ tests sharing setup → shared fixture. Input-only variation → parameterize.
- **Hygiene scan:** TODO/FIXME/HACK markers, generic error messages, over-broad exception handling, magic numbers, dead code paths. Fix immediately — don't leave for the anti-slop subagent.

### 3f: Mark Phase Complete
- `TaskUpdate` → `completed`. Full test-plan reconciliation (every spec test has a corresponding test case).
- Check off CHECKLIST.md items. Git commit: `feat([slug]): phase N — [name]`.
- Next phase exists → mark `in_progress`, continue. Last phase → proceed to Phase 4.

### Anti-Slop Subagent (between Phase 3 and Phase 4)

Launch a fresh `Explore` subagent to scan all code written in Phase 3 for the patterns defined in `/polish` Phase 2 (development artifact comments, low-value docstrings, restating comments) plus: unnecessary abstractions, copy-paste duplication, and any hygiene issues that survived the 3e self-check. Fix findings. Fresh context catches what self-review misses — the 3e self-check handles the obvious, this catches the subtle.

### Spec Feedback Loop

Triggered when implementation reveals SPEC.md is wrong or incomplete. See [Appendix B](#appendix-b-spec-feedback-loop) for full protocol. Key rules:
- Significant changes (acceptance criteria, phases, public API, security, scope) → new version snapshot + developer approval (hard gate)
- Minor clarifications → edit in place, log in Iteration Log, proceed
- Circuit breaker: >3 spec revisions in one phase → ask developer to continue, re-scope, or return to Phase 2

**Pre-Phase-4 gate:** If all phases resolved via "behavior pre-existed" with no net code changes, skip the anti-slop subagent and Phase 4 → Phase 5 with "feature pre-existed" path.

---

## Phase 4: Adversarial Convergence

**Purpose:** Adversarial review with iterative convergence. **Light tier skips this phase entirely.**

### 4a: Initial Review
Update CHECKPOINT.md: Phase: 4. **First entry:** set Convergence Iteration: 0. **Spec-triggered re-entry** from 4c: add +1 penalty to the counter before reviewing (spec churn during convergence is expensive — one spec-triggered cycle costs 2 iterations total). Run `/git-review --external`.

`/git-review` applies its standard review criteria (see `git-review.md` Review Criteria section). **VDD-specific additions** for the adversary to emphasize beyond standard criteria: spec compliance (every SPEC.md requirement has a traceable test+implementation pair), test necessity audit ("if this test were deleted, what production failure goes undetected?"), test impact classification per `/polish` Phase 3 tiers.

### 4b: Triage
Locate REVIEW_SUMMARY.md using `/git-review`'s review output structure (see `git-review.md` Directory Layout + Branch Name Sanitization): resolve via `.claude/reviews/<sanitized-branch>/` → newest timestamp directory. Applied findings are resolved. Triage Skipped findings.

**Deferral rules:**
- **CRITICAL findings cannot be deferred.** If a CRITICAL was "Skipped" during interactive fix, it remains unresolved and blocks convergence until addressed or the developer explicitly accepts it via the 4d escalation prompt.
- **IMPORTANT findings** skipped during interactive prompts count as deferred — record in CHECKPOINT.md Deferred Issues and document in the completion summary. Deferred IMPORTANT does not block convergence.

**Convergence test:**
- **Only MINOR/POTENTIAL/deferred-IMPORTANT remain → Converged.** In `autonomous` mode, auto-proceed to Phase 5. In `supervised` mode, auto-proceed after the first iteration if no CRITICAL/IMPORTANT remain. In `guided` mode, ask developer before proceeding.
- **CRITICAL or undeferred IMPORTANT remain →** if Convergence Iteration = 0, proceed directly to **4c** (first iteration — 4d checks are guaranteed no-ops). If Convergence Iteration ≥ 1, proceed to **4d** (convergence check) before fixing.

### 4c: Fix + Re-Review Loop
Fix CRITICAL findings. Fix IMPORTANT unless developer explicitly deferred. **TDD applies to behavioral fixes:** changed logic, new code paths, altered API surface → write regression test first, verify Red, implement, verify Green. Non-behavioral fixes (formatting, naming, docs, dead code) → apply directly. When uncertain, write the test.

Run full test suite. If fixes require spec changes → Spec Feedback Loop → new implementation phase → return to 4a (costs 2 convergence iterations as spec-churn deterrent). **Note:** If the post-spec-reentry review converges (only MINOR/POTENTIAL remain in 4b), proceed to Phase 5 regardless of iteration count — the cap gates further fix cycles, not convergence that already succeeded. A second spec issue during convergence escalates to the developer regardless of iteration count.

Run `/git-review --external` for re-review (never `--quick` for convergence — quick mode produces no REVIEW_SUMMARY.md, breaking the triage protocol). Increment Convergence Iteration. **Return to 4b** to triage the new REVIEW_SUMMARY.md — the convergence test there determines whether to converge (Phase 5) or route through 4d for the convergence cap/quality check before continuing fixes.

### 4d: Convergence Check

**Reached from 4b** when CRITICAL or undeferred IMPORTANT findings remain. This step enforces quality trends and iteration caps before returning to 4c for fixes.

**Quality signal:** Record CRITICAL + IMPORTANT count at every iteration (including iteration 0 — store the baseline in CHECKPOINT.md Notes as `Iteration 0 findings: N`). Update CHECKPOINT.md `Convergence Trend` starting at iteration 1: `improving` if count decreased vs. previous, `stalled` if unchanged, `degrading` if increased (leave `N/A` at iteration 0). **If stalled or degrading, escalate immediately** — don't wait for the cap: "Review quality not converging — [N] issues unchanged. Fix approach may need rethinking."

**Iteration cap:** Standard: 3 iterations. Critical tier: 2 iterations. Cap triggers when Convergence Iteration ≥ cap (not exactly equal — spec re-entries can cause the counter to skip values). When cap reached, present options: **Fix and review again** (extends cap by 1) | **Accept remaining issues** (document and proceed) | **I'll handle manually** (handoff — update CHECKPOINT.md status to `completed` with `Completion Mode: manual-handoff`, remove breadcrumb, present summary, stop orchestration). **If CRITICAL findings remain at cap:** the "Accept remaining issues" option requires the developer to explicitly acknowledge each unresolved CRITICAL by name — list them in the prompt. This satisfies the guardrail ("CRITICAL findings always block convergence") by requiring explicit human sign-off rather than silent acceptance.

**If not capped and not escalated → proceed to 4c** to fix remaining issues.

**Gate:** Only MINOR/POTENTIAL/deferred-IMPORTANT remain, OR developer explicitly accepts remaining issues.

---

## Phase 5: Completion

### 5a: Cleanup
Run `/deslop-around:deslop-around apply` (mechanical) then `/polish` (semantic). Skip if no changes since last cleanup (multi-PR mode). **Constraint for `/polish`:** Do not delete tests that trace to SPEC.md "Tests to Write First" entries — consolidation (parameterization) is allowed, deletion is not. This preserves the spec-to-test traceability verified in Phase 3f and Phase 4.

### 5b: Final Test Run
Full suite. All tests must pass.

### 5c: Checklist
- [ ] All SPEC.md success criteria met
- [ ] All tests passing
- [ ] Phase 4 gate satisfied (or skipped per tier/pre-existing-feature)
- [ ] Iteration Log reflects final state
- [ ] CHECKLIST.md fully checked off

### 5d: Quick Final Check (conditional)
If any code changes after last review → run `/git-review --quick`. CRITICAL found → full `/git-review --external`, return to Phase 4a. **Light tier:** This is the only review — run `/git-review --quick` here regardless. If `--quick` finds CRITICAL, escalate: present findings to developer with options: **Fix and re-run --quick** | **Enter full Phase 4** (override Light skip) | **Accept and proceed** (requires explicit per-CRITICAL acknowledgement, same as 4d guardrail).

### 5e: Summary + Retrospective
Present: what was built, files changed, test coverage, TDD compliance, convergence status, deferred issues, spec changes, next steps.

**Retrospective — write `.claude/docs/[slug]/RETROSPECTIVE.md`:**

```markdown
# Retrospective: [Feature Name]

## Metrics
- Phases: N | Spec revisions: N | Convergence iterations: N
- Findings fixed: N CRITICAL, N IMPORTANT | Autonomy: <mode>

## What Went Well
- [Patterns or decisions that saved time or prevented issues]

## Surprises
- [Spec assumptions that were wrong; edge cases the spec missed]

## Patterns to Reuse
- [Reusable patterns, utilities, testing strategies discovered]

## Suggested Rules
- [Additions to CLAUDE.md — e.g., "Convention: always validate X before Y"]
```

Source data: CHECKPOINT.md → metrics; SPEC.md Iteration Log → revision count + surprises; REVIEW_SUMMARY.md → findings counts + "What Went Well." **Light tier:** Phase 4 is skipped and 5d uses `--quick` (no REVIEW_SUMMARY.md). Report only CRITICAL count from `--quick` output; note "IMPORTANT/MINOR not assessed (quick review mode)" in the Metrics section. Omit convergence metrics (iterations, trend) from the retrospective. In `supervised`/`autonomous` mode, generate automatically. In `guided` mode, present draft and ask developer for additions.

After writing, present any "Suggested Rules" entries to the developer for approval before adding to CLAUDE.md — **this is a hard gate in all autonomy modes** to prevent instruction creep. This closes the compounding loop: the project gets smarter with each feature, but only with human curation.

**Cleanup:** CHECKPOINT.md status → `completed`. Remove this feature's CLAUDE.md breadcrumb (preserve others).

---

## Usage

```
/new-feature-vdd [brief description]
/new-feature-vdd --autonomy <guided|supervised|autonomous> [brief description]
```

Autonomy defaults to tier (Light→autonomous, Standard→supervised, Critical→guided). Override with `--autonomy`.

Examples: `/new-feature-vdd user search preferences endpoint` · `/new-feature-vdd --autonomy guided add PDF export` · `/new-feature-vdd refactor auth for OAuth`

---

## Tool Reference

| Phase | Tool / Agent | Purpose |
|-------|-------------|---------|
| 0 | `Explore` (×2, or ×1 Light) | Pattern + architecture discovery |
| 0 | `feature-dev:code-explorer` (Standard/Critical) | Deep execution path tracing |
| 2a | `feature-dev:code-architect` or `Plan` (Light) | Architecture blueprint |
| 2b | `general-purpose` (Critical only) | Spec adversary |
| 2d | `/plan-review` (optional) | Multi-model spec review |
| 3→4 | `Explore` subagent | Anti-slop scan (fresh context) |
| 4 | `/git-review --external` | Adversarial review + convergence |
| 5a | `/deslop-around` → `/polish` | Cleanup passes |
| 5d | `/git-review --quick` | Post-convergence sanity check |
| 5e | `RETROSPECTIVE.md` generation | Cross-feature learning — metrics, patterns, suggested rules |

---

## Appendix A: Resume/Shelve/Abandon Protocol

### Startup Breadcrumb Handling (Phase 0)

Read CLAUDE.md for `<!-- new-feature-vdd: ... -->` breadcrumbs.

**Active breadcrumb found:** Prior session interrupted. Ask: Resume (Recommended) | Start fresh | Abandon.
- **Resume:** Read CHECKPOINT.md for substep. If missing, ask user: "Start fresh, abandon, or recover from other artifacts?" Re-read only artifacts that exist at the recorded substep. Jump directly — skip Phase 0/1.
- **Start fresh / Abandon:** Check `git status` first — if dirty, ask developer about uncommitted work. Fresh: shelve previous, proceed Phase 0. Abandon: mark abandoned, remove breadcrumb, proceed Phase 0.

**Shelved breadcrumb found:** Ask: Resume shelved | Start fresh.
- **Resume:** Check git status. Set CHECKPOINT.md active, update breadcrumb, jump to recorded substep.
- **Fresh:** Leave shelved artifacts intact. Multiple shelved breadcrumbs can coexist.

**Multiple breadcrumbs:** Active takes precedence. Multiple active = corruption — list all, ask user, shelve/abandon others.

**No breadcrumb:** Clean start.

### Exit Protocol (available at any phase)

**Phases 0-1** (no checkpoint): Stop. Only Abandon available.

**Phase 2a onward:**

| Option | Action |
|--------|--------|
| **Restart from spec** | New version snapshot (if one exists), log restart, mark tasks `[superseded]`, CHECKPOINT → Phase 2a, jump to 2a. Exploration retained. |
| **Shelve** | CHECKPOINT status → shelved, breadcrumb → shelved variant, stop. |
| **Abandon** | CHECKPOINT status → abandoned, remove breadcrumb, stop. Files left as-is. |

---

## Appendix B: Spec Feedback Loop

Triggered when implementation reveals SPEC.md is wrong or incomplete.

1. **Stop** at current substep. Document: spec says X, reality requires Y.
2. **Significant change** (alters acceptance criteria, adds/removes phases, changes public API/schema, affects security/NFRs, adds scope): new version snapshot in `plans/<new-timestamp>/`, update PLAN.md + CHECKPOINT.md Spec Version, notify developer via `AskUserQuestion` — **hard gate, do not resume without approval**.
3. **Minor clarification** (parameter naming, clarifying existing behavior, internal refactor): edit in place, add Iteration Log entry, proceed.
4. **Default:** If unclear, treat as significant.
5. Update CHECKLIST.md and tasks if phases changed.
6. **Resume point:** Tests affected → 3a. Implementation approach only → 3c. Cosmetic/docs → current substep.
7. **Circuit breaker:** >3 revisions in one phase → ask: continue | re-scope | return to Phase 2.

---

## Appendix C: Multi-PR Workflow

**Applies only when PR_STRATEGY.md exists** (generated in 2c for features spanning multiple PRs).

PR_STRATEGY.md must group Implementation Phases per PR with branch names: `feat/<slug>--<slice>`. Execute Phases 3 + 4 + PR Handoff Gate sequentially per PR. Track current PR in CHECKPOINT.md Notes.

### PR Handoff Gate (after Phase 4 converges, non-final PRs)

1. Run `/deslop-around:deslop-around apply` then `/polish`.
2. Ask developer: **PR good — continue** | **I made changes** | **Shelve remaining**.
   - Continue: update CHECKPOINT, branch next PR (stacked if dependent, from main if independent), return to Phase 3.
   - Changes: pull/detect changes, run `/git-review --quick` as sanity check, re-prompt gate.
   - Shelve: CHECKPOINT → shelved, breadcrumb → shelved variant, stop.

---

## Appendix D: Context Resilience

### CHECKPOINT.md Format

```markdown
# Checkpoint
Status: active
Phase: 3
Substep: 3c: Implement Minimum Code
Implementation Phase: 2 of 4
Convergence Iteration: 0
Convergence Trend: [N/A | improving | stalled | degrading]
Tests Completed: 0 of N
Test Command: pytest -xvs
Spec Version: plans/<YYYYMMDD-HHMMSS>/
Autonomy Mode: supervised
Deferred Issues: none
Notes: [1-2 sentences recovery context]
```

Status values: `active`, `shelved`, `abandoned`, `completed`.

### CLAUDE.md Breadcrumb

```
<!-- new-feature-vdd: [slug] --> ALWAYS read .claude/docs/[slug]/CHECKPOINT.md before continuing any work.
```

Shelved variant:
```
<!-- new-feature-vdd: [slug] (shelved) --> A shelved feature exists at .claude/docs/[slug]/. Read CHECKPOINT.md before starting new work.
```

Written at Phase 2a (earliest slug exists). Removed on completion. Line-level edits only. If CLAUDE.md doesn't exist, create with breadcrumb only.

### Compaction Recovery

**Primary:** Breadcrumb forces re-read of CHECKPOINT.md every turn (survives compaction).

**Phase boundary re-reads (conditional):** Re-read a doc only when recovering from compaction OR its content may have changed. Use Spec Version field and Iteration Log as change signals. Available docs by phase: 2a+ has CHECKPOINT + EXPLORATION; 2b+ adds SPEC; 2c+ adds CHECKLIST.

**Task descriptions as state carriers:** `TaskCreate` for each implementation phase should follow: `content: "Phase N: [name]"`, `activeForm: "Implementing Phase N: [name]"`. Include in the description: files involved, tests to write (from SPEC.md "Tests to Write First"), acceptance criteria, and current approach (from blueprint). This ensures a compacted model can recover context.

**Compaction indicators (fallback):** Can't recall file paths from Phase 0, reference spec in general terms, unsure of current substep → read CHECKPOINT.md to recover.

---

## Appendix E: Fallbacks

| Tool | Fallback |
|------|----------|
| `Explore` / `feature-dev:code-explorer` | `general-purpose` subagent with same objectives |
| `feature-dev:code-architect` | `Plan` subagent |
| `/plan-review` | Skip; user reviews spec manually at 2d gate |
| `/polish` | Inline cleanup: scan for dev artifact comments, low-value docstrings, LOW-impact tests. Commit before handoff. |
| `/git-review` | Fresh `Explore`/`general-purpose` subagent with adversarial prompt, diff, and SPEC.md. Write to `.claude/reviews/<sanitized-branch>/fallback-<timestamp>/REVIEW_SUMMARY.md` (follow `git-review.md` sanitization rules). Update REVIEW.md. Present findings interactively (Apply/Skip). Convergence loop still applies. |
| `agent` CLI (for `--external`) | Run `/git-review` without `--external`. Note downgrade in CHECKPOINT.md Notes. |

---

## Appendix F: Integration Notes

- `/git-review --external` discovers spec docs via PLAN.md in `.claude/docs/[slug]/`. Branch `feat/<slug>` matches `.claude/docs/<slug>/`. Single-directory shortcut: when only one `.claude/docs/` dir exists, branch matching is skipped.
- `/plan-review` uses CRITICAL/IMPORTANT/MINOR/GOOD severities (no POTENTIAL). GOOD findings are informational and do not affect convergence triage (treat as equivalent to MINOR for convergence purposes). Creates new versioned snapshots automatically.
- Review directory paths: `/git-review` sanitizes branch names (`/` → `--`).

> **Note:** VDD's formal verification (purity boundaries, Kani/Dafny/TLA+) is intentionally omitted. For safety-critical features, add a Verification Strategy to the spec and formal hardening after implementation.
