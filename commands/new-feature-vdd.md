# Feature Development with TDD + Adversarial Convergence

> **v1.0.0** · Merged from `new-feature.md` (exploration-first, tool-integrated) and `vdd.md` (TDD discipline, adversarial convergence). Applies VDD's adversarial convergence principles without formal verification.

## Overview

This command orchestrates feature development using an **explore → spec → test-first → adversarial converge** pipeline. It combines codebase-aware exploration with strict TDD discipline and iterative adversarial review.

**Core principles:**
- **Spec Supremacy:** The spec is the highest authority below the human developer. Tests serve the spec. Code serves the tests.
- **Red Before Green:** No implementation code exists without a failing test that demanded it.
- **Anti-Slop Bias:** The first "correct" version is assumed to contain hidden debt. Trust is earned through adversarial survival.
- **Fresh Context:** Each adversarial review uses fresh subagent context for the review itself — no relationship drift, no accumulated goodwill. The main orchestrator retains prior context for continuity but does not perform the adversarial assessment.

> **Note:** VDD's formal verification architecture (purity boundaries, provable properties, Kani/Dafny/TLA+) is intentionally omitted for general use. For safety-critical, financial, or security-critical features, consider adding a Verification Strategy to the spec and formal hardening steps after implementation.

**Roles (mapped to Claude Code primitives):**

| Role | Entity | Function |
|------|--------|----------|
| **Architect** | Human Developer | Strategic vision, domain expertise, acceptance authority |
| **Builder** | Claude Code (main context) | Spec authorship, test generation, implementation under TDD constraints |
| **Tracker** | Claude Code (main context) | Progress tracking via `TaskCreate` / `TaskUpdate` / `TaskList` |
| **Adversary** | `/git-review --external` (with convergence loop) | Code review with iterative refinement until convergence (fallback: fresh `Explore` or `general-purpose` subagent) |

## Process Flow

```
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ Phase 0:         │    │ Phase 1:         │    │ Phase 2:         │
│ Codebase         │ →  │ Focused          │ →  │ Spec +           │
│ Exploration      │    │ Discovery        │    │ Review Gate      │
│ (2-3 agents)     │    │ (adaptive)       │    │ (/plan-review)   │
└──────────────────┘    └──────────────────┘    └──────────┬───────┘
                                                           │
                                    ┌──────────────────────┘
                                    │ approved + TaskCreate
                                    ▼
                        ┌──────────────────────┐
                   ┌──→ │ Phase 3: TDD         │ ←─── spec change
                   │    │ Implementation       │      (new phase)
                   │    │                      │
                   │    │  ┌─── per phase ───┐ │
                   │    │  │ Write tests     │ │
                   │    │  │ Verify Red      │ │
                   │    │  │ Implement       │ │
                   │    │  │ Verify Green    │ │
                   │    │  │ Refactor+check  │ │
                   │    │  └────────┬────────┘ │
                   │    │     spec  │           │
                   │    │     issue?├──→ update SPEC.md
                   │    │           │   (notify if significant)
                   │    │           │   resume at 3a/3c/current
                   │    │           │   *>3 revisions → ask user
                   │    └─────┬─────────────────┘
                   │          │ all phases done
                   │          ▼
                   │    ┌──────────────────────┐
                   │    │ Phase 4: Adversarial │
                   │    │ Convergence          │
                   │    │                      │
                   │    │  /git-review ──→ triage
                   │    │       ▲          │
                   │    │       │   CRITICAL│
                   │    │       │  IMPORTANT│
                   │    │       │     ▼     │ only MINOR/
                   │    │   re-review ← fix │ POTENTIAL/
                   │    │   (default 3×)    │ deferred?
                   │    │                   │──→ converged
                   │    │                   │
                   │    │  spec issue? ─────┘
                   │    └───────┬──┘
                   │            │
                   └────────────┘  (spec change requiring
                                    new implementation)
                              │ converged / accepted
                              ▼
                        ┌──────────────────┐
                        │ Phase 5:         │
                        │ Completion       │
                        │ (final tests +   │
                        │  summary)        │
                        └──────────────────┘
```

---

## Context Resilience (Compaction Recovery)

Long-running feature development will trigger auto-compaction, compressing earlier messages. The following protocols ensure the workflow can recover gracefully.

**Checkpoint File:** Maintain `.claude/docs/[feature-name]/CHECKPOINT.md` as a **current-state snapshot** (not a log — each update overwrites the previous):

```markdown
# Checkpoint

Status: active
Phase: 3
Substep: 3c: Implement Minimum Code
Implementation Phase: 2 of 4
Convergence Iteration: 0
Tests Completed: 0 of N
Test Command: pytest -xvs
Spec Version: plans/<YYYYMMDD-HHMMSS>/
Deferred Issues: none
Notes: [1-2 sentences of recovery context, e.g. "3 of 5 tests passing, remaining 2 need the user fixture from Phase 1"]
```

Status values: `active` (in progress), `shelved` (paused for later), `abandoned` (stopped), `completed` (finished).

**Update CHECKPOINT.md at every phase transition, substep transition, and convergence iteration.** This is the single source of truth for "where am I?" after compaction. Historical context lives elsewhere: spec changes in SPEC.md's Iteration Log, progress in TaskList, code changes in git history.

**CLAUDE.md breadcrumb (compaction-proof — primary recovery mechanism):** Since CLAUDE.md is loaded into every conversation turn (surviving compaction), this command writes a breadcrumb line to the project's CLAUDE.md at the start of Phase 2a (immediately after slug derivation — the earliest point where the feature slug exists) and removes it on completion or manual handoff. The breadcrumb format:

```
<!-- new-feature-vdd: [feature-name] --> ALWAYS read .claude/docs/[feature-name]/CHECKPOINT.md before continuing any work. This file contains your current phase, substep, and implementation state.
```

When a feature is shelved (see Exit Protocol), the breadcrumb changes to:
```
<!-- new-feature-vdd: [feature-name] (shelved) --> A shelved feature exists at .claude/docs/[feature-name]/. Read CHECKPOINT.md there to see its state before starting new work.
```

This ensures the model unconditionally re-reads the checkpoint every turn, even after heavy compaction erases the original command instructions. The cost is one small file read; the benefit is guaranteed state recovery. **When writing or removing breadcrumbs, never rewrite the entire file; perform line-level insert, replace, or delete for breadcrumb lines only** — CLAUDE.md may contain the developer's project instructions. **If CLAUDE.md does not exist**, create it with only the breadcrumb line — do not add any other content.

**Re-read protocol (belt-and-suspenders):** At each major phase boundary, re-read all state docs that exist at that point. From Phase 2a onward (when checkpoint is initialized), read CHECKPOINT.md and EXPLORATION.md. From Phase 2b onward, also read SPEC.md (resolve the current plan version from `PLAN.md` as primary authority; fall back to CHECKPOINT.md's Spec Version field only if `PLAN.md` is missing). From Phase 2c onward, also read CHECKLIST.md. Do not rely on conversation memory for spec details, test commands, or progress state. This supplements the breadcrumb — the breadcrumb handles mid-phase compaction, this handles phase boundaries.

**Task descriptions as state carriers:** When creating tasks via `TaskCreate`, include enough context in the description that a compacted model can understand the task without prior conversation: what files are involved, what tests to write, what the acceptance criteria are.

**Compaction indicators (fallback detection):** If the breadcrumb was somehow missing, these heuristics indicate compaction occurred: (1) you cannot recall specific file paths or function names from Phase 0 exploration, (2) you reference the spec in general terms rather than quoting specific requirements, (3) you are unsure which implementation phase or substep you are in. If any apply, read CHECKPOINT.md to recover current position, re-read the active SPEC.md version, check `TaskList` for progress, and resume from the recorded substep.

---

## Phase 0: Codebase Exploration

**Purpose:** Gather deep context BEFORE asking questions so that questions are informed, and the spec is grounded in codebase reality.

**Startup: Check for existing breadcrumb.** Read the project's CLAUDE.md and look for any `<!-- new-feature-vdd: ... -->` breadcrumb.

- **If an `active` breadcrumb is found** (no `(shelved)` tag): A prior session was interrupted mid-workflow. Read the CHECKPOINT.md referenced in the breadcrumb to recover state.
  ```
  AskUserQuestion:
    question: "Found an in-progress feature: [feature-name] (Phase [N], Substep [X]). How would you like to proceed?"
    header: "Resume"
    options:
      - label: "Resume where it left off (Recommended)"
        description: "Continue from the recorded checkpoint. Skips exploration and spec phases."
      - label: "Start fresh (new feature)"
        description: "Shelve the previous feature and begin a new feature from Phase 0."
      - label: "Abandon the previous feature"
        description: "Mark the previous feature as abandoned, clean up, and begin a new feature."
  ```
  - If **resume**: re-read CHECKPOINT.md first to determine the substep. If CHECKPOINT.md is missing (possible corrupted state), ask the user: "Checkpoint file is missing. Start fresh, abandon, or try to recover from other artifacts (SPEC.md, CHECKLIST.md)?" Then re-read only artifacts that exist at that substep: Phase 2a has the feature slug, CHECKPOINT.md, and EXPLORATION.md; Phase 2b+ has SPEC.md; Phase 2c+ has CHECKLIST.md; Phase 2d+ has tasks in `TaskList`. Jump directly to the recorded phase and substep. Do not re-run Phase 0 or Phase 1.
  - If **start fresh** or **abandon**: Before modifying any state, check for uncommitted changes (`git status`). If the working tree is dirty, ask the developer whether to commit, stash, or proceed with dirty state — do not silently switch context with uncommitted work. Then: for **start fresh**, update the previous CHECKPOINT.md status to `shelved`, replace the breadcrumb with the shelved variant (preserving the previous feature for future resumption), then proceed with Phase 0 for the new feature. For **abandon**, update the previous CHECKPOINT.md status to `abandoned`, remove the breadcrumb, proceed with Phase 0 for the new feature.

- **If a `(shelved)` breadcrumb is found**: A feature was explicitly shelved.
  ```
  AskUserQuestion:
    question: "Found a shelved feature: [feature-name] (Phase [N], Substep [X]). How would you like to proceed?"
    header: "Shelved"
    options:
      - label: "Resume the shelved feature"
        description: "Un-shelve and continue from the recorded checkpoint."
      - label: "Start fresh (new feature)"
        description: "Keep the shelved feature as-is and begin a new feature."
  ```
  - If **resume**: Before modifying any state, check for uncommitted changes (`git status`). If the working tree is dirty, ask the developer whether to commit, stash, or proceed — do not silently switch context with uncommitted work. Then update CHECKPOINT.md status to `active`, replace the `(shelved)` breadcrumb with the active breadcrumb format, re-read state docs, and jump to the recorded phase/substep.
  - If **start fresh**: Before modifying any state, check for uncommitted changes (`git status`). If the working tree is dirty, ask the developer whether to commit, stash, or proceed. Then leave the shelved breadcrumb and artifacts intact, proceed with Phase 0 for the new feature. (Multiple shelved breadcrumbs can coexist — one per shelved feature. The active breadcrumb, if any, takes precedence for recovery.)

- **If multiple breadcrumbs found**: If both active and shelved breadcrumbs exist, the active one takes precedence — handle it first using the active breadcrumb flow above. If multiple active breadcrumbs exist (corruption or concurrent sessions), list all active features (name + phase/substep from each CHECKPOINT.md) and ask the user which to resume; shelve or abandon the others. If multiple shelved breadcrumbs exist, list all shelved features and ask which to resume or whether to start fresh.

- **If no breadcrumb found**: Clean start. Proceed with exploration.

**Launch Agents in Parallel** (via the `Agent` tool with the specified `subagent_type`):

1. **Pattern Discovery Agent** (`Explore` subagent)
   - Find similar features in the codebase
   - Identify coding conventions and architectural patterns
   - Look for reusable utilities or abstractions

2. **Architecture Context Agent** (`Explore` subagent)
   - Map relevant dependencies and integration points
   - Identify testing patterns and frameworks used
   - Find configuration patterns

3. **Deep Code Explorer** (`feature-dev:code-explorer` subagent) — launch only for features spanning multiple subsystems, cross-cutting concerns, or unclear execution paths.
   - Trace execution paths through relevant subsystems
   - Map architecture layers and abstraction boundaries
   - Document dependency chains end-to-end

**After exploration, provide a Codebase Context Report** covering:
- Similar features found and how they're relevant
- Patterns to follow (with file paths)
- Architectural constraints discovered
- **Test execution command** (e.g., `pytest`, `npm test`, `cargo test`) — this will be used throughout Phase 3
- Recommended approach based on findings

★ Insight ─────────────────────────────────────
Provide insights about what was discovered:
- Why certain patterns exist in the codebase
- Trade-offs observed in similar implementations
- Conventions that should be followed
─────────────────────────────────────────────────

---

## Phase 1: Focused Discovery

**Purpose:** Ask the human developer what the codebase can't tell us. No artificial cap on questions — ask until the spec can be written with confidence.

**Adaptive Rounds:**

**Round 1: Core Requirements**
- "What specific behavior or outcome are you trying to achieve?"
- "What does success look like for this feature?"
- "Who or what consumes this?" (if not obvious from exploration)

**Round 2: Design Preferences & Edge Cases**
Based on Round 1 and exploration findings:
- Trade-off preferences (performance vs. simplicity, flexibility vs. speed-to-ship)
- Edge case priorities (what matters most?)
- Error handling philosophy for this feature
- User experience expectations

**Round 3+: Completeness Checks**
After mentally drafting the spec, identify any remaining gaps:
- "Before I write the spec, I want to confirm X because it affects Y..."
- Resolve remaining ambiguities about critical requirements
- Continue until confident the spec can be written airtight

**Guidelines:**
- Every question must be informed by Phase 0 exploration — never ask what the codebase already answered
- Each question should explain *why* the answer matters for the spec
- Gate condition: **"enough clarity to write an airtight spec"** — not a question count. Concretely: you can answer (a) what success looks like, (b) what the main edge cases are, (c) what the acceptance criteria are, and (d) what the implementation phases are
- **Backstop:** If after 5 rounds of questions no new critical requirements have emerged, draft the spec with explicit assumptions for any remaining ambiguities and present to the user: "Proceed with these assumptions, or clarify further?"

---

## Phase 2: Specification + Review Gate

**Purpose:** Produce the spec, get human approval, and optionally run multi-model plan review. This is the single most important phase — everything downstream depends on spec quality.

### 2a: Architecture Design

**Derive `[feature-name]` slug immediately** from the user's description (e.g., "user search preferences endpoint" → `user-search-preferences-endpoint`). Slug algorithm: lowercase → trim → replace non-alphanumeric characters (except hyphens) with `-` → collapse consecutive dashes → strip leading/trailing dashes. Drop only articles and prepositions, not nouns. If the generated slug differs from a prior breadcrumb or existing branch, confirm with the user. This slug is used for directory paths, branch names, and breadcrumbs from this point forward — it must be established before any artifacts are created. Create the docs directory `.claude/docs/[feature-name]/` if it doesn't exist. **Slug collision check:** If `.claude/docs/[feature-name]/` already exists and belongs to a prior workflow (check for a CHECKPOINT.md with status `abandoned` or `completed`, or a shelved breadcrumb for a different feature), append a suffix (e.g., `-v2`) to the new slug to avoid state corruption.

**Initialize state tracking immediately** after deriving the slug: create `CHECKPOINT.md` (see Context Resilience section) with Phase: 2, Substep: 2a, Status: active, and write the CLAUDE.md breadcrumb. This ensures compaction recovery works from the earliest spec-generation phases, when large amounts of text make compaction likely. **Persist exploration context:** Write a brief `.claude/docs/[feature-name]/EXPLORATION.md` summarizing Phase 0 findings (patterns, conventions, test command, architecture context) and Phase 1 requirements. This file is the recovery source if the session is interrupted before SPEC.md is created in 2b.

Launch `feature-dev:code-architect` agent (or `Plan` for lighter features — use `Plan` when the feature touches ≤3 files and has no new modules) with:
- All exploration findings from Phase 0
- All requirements from Phase 1

**Expected output — Implementation Blueprint:**
- Files to create and modify (with line references)
- Component boundaries and data flow
- Build sequence in dependency order
- Testing strategy (frameworks, patterns to follow)
- **Risk subsection** — structured table with Level (Low/Medium/High) and Mitigation columns. Required rows: Pattern Deviation, Dependency Impact, Testing Coverage. Include as applicable: Security, Performance, Integration, Data Migration. Add a feasibility conclusion

★ Insight ─────────────────────────────────────
Explain the architectural decisions:
- Why this structure was chosen
- How it aligns with existing patterns
- Trade-offs made and alternatives considered
─────────────────────────────────────────────────

### 2b: Generate SPEC.md

Update CHECKPOINT.md: Phase: 2, Substep: 2b.

Using the `[feature-name]` slug derived in Phase 2a, create `.claude/docs/[feature-name]/plans/<YYYYMMDD-HHMMSS>/SPEC.md`. After creating SPEC.md, update CHECKPOINT.md's `Spec Version` to `plans/<YYYYMMDD-HHMMSS>/`.

**SPEC.md must contain these sections:**

1. **Feature Overview** — concise description and purpose
2. **Codebase Context** — similar implementations, patterns to follow, constraints discovered
3. **Discovery Summary** — key findings from exploration and Q&A (questions asked, answers received, requirements derived)
4. **Requirements** — functional (checkboxes with priority) and non-functional (performance, security, scalability)
5. **Implementation Phases** — each phase must be TDD-structured:
   ```
   ### Phase N: [Name]
   **Complexity:** Low/Medium/High
   **Dependencies:** [What must be completed first]

   #### Tests to Write First
   - [ ] Test: [description of what it validates]
   - [ ] Test: [description]

   #### Implementation Tasks
   - [ ] `path/to/file.py` — [specific change]
   - [ ] `path/to/file.py` — [specific change]

   #### Refactoring Notes
   - [Any cleanup expected after green]
   ```
6. **Testing Strategy** — unit, integration, and manual testing approach
7. **Success Criteria** — checkboxes for what "done" means
8. **Iteration Log** — table tracking spec changes during implementation (initially empty)

**Spec Quality Gates (apply before presenting for review):**

These checks address recurring issues found in multi-model plan reviews. Apply them mechanically before moving to 2c:

1. **Signature Tracing:** For every function being modified or called, trace the full parameter chain: caller → function signature → callee. List each parameter at each hop. Verify no parameter names or types are assumed without checking the actual codebase. A simple grep for the function signature prevents the most common critical finding.

2. **Draft Syntax Requirement:** Plans involving LLM prompts, database queries, API calls, or domain-specific syntax MUST include draft text/syntax in the first version. Abstract descriptions (e.g., "add a filter for X" or "add guidance for intent override") are insufficient — reviewers cannot validate correctness without seeing exact wording or query syntax.

3. **Error Path Enumeration:** For every operation in the plan, list: (a) success path, (b) expected domain failure, (c) infrastructure/IO failure. If only one failure mode is listed, justify why others don't apply. Two operations = two distinct failure paths (e.g., embedding failure AND bulk_write failure).

4. **Convention Cross-Check:** Before finalizing, verify test file naming, import patterns, assertion value formats, and logging conventions against the project's CLAUDE.md. Pragmatic deviations from conventions are the most commonly flagged "easy catch" in reviews.

5. **Data Quality Assumptions:** When the plan reads data from a database or external source, explicitly state handling for missing, null, empty, and malformed field values. Never assume clean data — state the filter or guard.

6. **Test Impact Classification:** After listing all tests in "Tests to Write First," classify each as:
   - **HIGH** — Core behavior; failure = broken feature in production
   - **MEDIUM** — Secondary paths; important but not catastrophic if missed
   - **LOW** — Defensive edge cases, unlikely scenarios, static content assertions

   Target: ≥50% HIGH, ≤25% LOW. If the ratio is inverted, the plan may be over-testing edge cases while under-testing core behavior. LOW-impact tests that vary only in input/output should use parameterization.

7. **Test DRY Check:** If 3+ tests share the same fixture/mock construction, define a shared fixture in the plan's Testing Strategy section. If tests vary only in input and expected output, specify `@pytest.mark.parametrize` (or language equivalent) rather than individual test functions.

8. **Comment/Docstring Policy:** Only prescribe docstrings for public API functions or functions with non-obvious parameters/return values. Do not plan docstrings for simple helpers, one-line functions, or internal methods where the name is self-documenting. Comments should explain *why*, not *what*.

### 2c: Generate Supporting Documents

Update CHECKPOINT.md: Phase: 2, Substep: 2c.

**Always generate:**
- `CHECKLIST.md` — extracted tasks organized by phase, with labeled groups within each phase: `#### Tests (complete before implementation)` and `#### Implementation (only after all tests pass)`. Check off test items only after 3b (Red verified). Check off implementation items only after 3d (Green verified).
- `README.md` — navigation guide to the document set with quick start instructions

**Conditionally generate:**
- `KEY_DECISIONS.md` — only if the feature involves high-impact decisions (public API design, security model, persistence/data model shape, irreversible architectural choices). Table format: Decision | Choice | Rationale
- `PR_STRATEGY.md` — only if the feature spans multiple PRs. Must include: dependency graph, PR sequence, branch names (convention: `feat/<slug>--<slice>`), and an explicit mapping of which Implementation Phases belong to each PR

**Not generated:** `FIXTURES.md` — SPEC.md's "Tests to Write First" sections serve as the test data source of truth. If `/git-review` finds a pre-existing FIXTURES.md, it will use it.

**Generate `PLAN.md` at the doc root** linking to the current version:
```markdown
# [Feature Name] Plan

Current version: `plans/<timestamp>/`

## Documents
- [SPEC.md](plans/<timestamp>/SPEC.md) — Full specification (TDD-structured)
- [CHECKLIST.md](plans/<timestamp>/CHECKLIST.md) — Implementation tasks
- [README.md](plans/<timestamp>/README.md) — Navigation guide
_(Only list documents that were actually created)_
```

### 2d: Review Gate

Update CHECKPOINT.md: Phase: 2, Substep: 2d.

**Anti-slop applies to specs too.** If `/plan-review` is skipped, the human developer must actively look for ambiguous language, missing edge cases, and unstated assumptions — not just confirm that the spec "looks right."

Present the spec to the user:

```
AskUserQuestion:
  question: "Spec and supporting docs are ready at .claude/docs/[feature-name]/. Review them and choose how to proceed."
  header: "Spec review"
  options:
    - label: "Run /plan-review (Recommended)"
      description: "Multi-model analysis of the plan. Catches spec issues before implementation investment."
    - label: "Approve and start implementation"
      description: "Spec looks good. Begin TDD implementation."
    - label: "I have changes"
      description: "I'll describe what needs to change before proceeding."
```

- If **`/plan-review`**: invoke `/plan-review <project_root> .claude/docs/[feature-name]` (use the repository root as `<project_root>`). **Note:** `/plan-review` does not support paths containing spaces. If the project root contains spaces, use a relative path (e.g., `.`) or create a temporary symlink to a space-free path. After review completes, re-read `PLAN.md` to get the updated current version path — `/plan-review` creates new versioned snapshots and updates `PLAN.md` automatically. Do not create additional version snapshots for changes already handled by `/plan-review`. After revisions are made, re-prompt this gate.
- If **changes requested**: incorporate them, update docs, re-prompt this gate.
- If **approved**: use `TaskCreate` to create a task for each implementation phase from CHECKLIST.md (each task should note it begins with writing failing tests). Proceed to Phase 3.

**Gate:** User has explicitly approved the spec.

---

## Phase 3: TDD Implementation

**Purpose:** Build the feature using phase-gated TDD. Every line of code must be demanded by a failing test.

**Before starting, check for multi-PR strategy:** If `PR_STRATEGY.md` exists (generated in Phase 2c), read it. `PR_STRATEGY.md` must explicitly group which Implementation Phases belong to each PR and specify branch names using the convention `feat/<slug>--<slice>` (e.g., `feat/user-search--api`, `feat/user-search--ui`). Execute Phases 3, 4, and the **PR Handoff Gate** sequentially for each PR defined in the strategy. Track the current PR in CHECKPOINT.md's Notes field (e.g., "PR 2 of 3: feat/user-search--ui"). The PR Handoff Gate (see section after Phase 4) pauses after each PR converges so the developer can review and modify it before the next PR begins. If no `PR_STRATEGY.md` exists, proceed with a single branch as below.

**Update state tracking:**
- **Create a feature branch:**
  - **Single-PR mode:** `git checkout -b feat/[feature-name]` (use the feature slug). This ensures `/git-review` in Phase 4 can match the spec directory.
  - **Multi-PR mode:** `git checkout -b <branch-from-PR_STRATEGY>` for the current PR only. Since split branches (e.g., `feat/<slug>--api`) won't match the slug exactly, `/git-review` relies on the single-directory shortcut (see Integration Notes). If multiple `.claude/docs/` directories exist, ensure only one is active or `/git-review` may fail to locate the spec.
  - If already on the correct feature branch, skip.
- Use `TaskUpdate` to mark the first phase task as `in_progress`
- Update `CHECKPOINT.md`: Phase: 3, Substep: 3a, Implementation Phase: 1 of N

```
┌─────────────────────────────────────────────────────────┐
│  TDD DISCIPLINE — applies to every substep below        │
│                                                         │
│  Work in micro-cycles of 1-3 related tests:             │
│  1. Write a small cluster of failing tests (3a).        │
│  2. Run tests. Confirm they FAIL — Red (3b).            │
│  3. Write MINIMUM code to make them pass (3c).          │
│  4. Run tests. Confirm ALL pass — Green (3d).           │
│  5. Repeat 1-4 until all tests for this phase exist.    │
│  6. Refactor. Run tests again (3e).                     │
│                                                         │
│  Do NOT write implementation before confirming Red.     │
│  You MUST wait for test execution results confirming    │
│  failure BEFORE writing any implementation code.        │
└─────────────────────────────────────────────────────────┘
```

### For Each Implementation Phase in SPEC.md:

#### 3a: Write Failing Tests

Write the next 1-3 failing tests from SPEC.md's "Tests to Write First" list for this phase. Follow the testing patterns and frameworks discovered in Phase 0. Work in small clusters to prevent large batch-green jumps where implementation for one test accidentally satisfies another.

**Test-plan reconciliation (cumulative):** Before running tests, compare all tests written **so far in this phase** against the "Tests to Write First" list in SPEC.md. Verify that every test written maps to a spec item, and flag any written test that does not. Do not require all spec-listed tests to exist yet — that is enforced at phase completion (3f). This keeps micro-cycles incremental while ensuring nothing drifts from the spec.

#### 3b: Verify Red

Run the project's test command (discovered in Phase 0). Confirm the new tests **fail as expected**. Valid Red includes assertion failures and, in typed/compiled languages, compilation or type errors caused by referencing not-yet-implemented symbols (e.g., missing function, unresolved import for code you haven't written yet). Invalid Red includes syntax errors in test code, misconfigured test runners, broken imports for *existing* modules, or infrastructure failures — fix those before proceeding. **CRITICAL: Do NOT attempt to fix compilation/type errors during Verify Red if they are caused by missing implementation.** Accept the failure as valid Red and proceed to 3c. LLMs have a natural reflex to fix compilation errors — resist it here; the missing symbols will be implemented in 3c. If the test command itself fails (infrastructure error), diagnose and fix: common causes are missing dependencies, changed test configuration, or broken test runner. Update CHECKPOINT.md's Test Command field if the command changed.

**If any new tests pass without implementation:** investigate each passing test individually. For each, determine whether (a) it tests pre-existing behavior (acceptable — note and continue), (b) it is tautological or testing the wrong thing (fix the test), or (c) a prior phase's implementation already covers it (acceptable — note it). Only proceed to 3c once all unexpectedly-passing tests are resolved.

**If ALL tests for a phase pass without new implementation:** the behavior already exists. Verify it matches the spec intent (not just the test assertions). If confirmed, skip 3c-3e and proceed directly to **3f** to finalize the phase (reconciliation, checklist, git checkpoint). Add a note to the task: "behavior pre-existed." If tests were written in 3a, they are new files and should be committed at 3f even if no implementation was needed. Only skip the git checkpoint if truly no files were created or modified in this micro-cycle. Update the Iteration Log.

#### 3c: Implement Minimum Code

Write the **minimum** implementation to make the failing tests pass. Do not gold-plate. Do not add behavior beyond what the tests demand.

#### 3d: Verify Green

Run the **full** test suite. All tests — new and existing — must pass.

**If existing tests broke:** Fix the implementation, not the old tests (unless the spec explicitly changes existing behavior and the old tests are now wrong).

**Micro-cycle loop:** If more tests remain in this phase's "Tests to Write First" list, return to **3a** for the next micro-cycle. Only proceed to **3e** (Refactor) when all tests for this phase have been written and pass.

#### 3e: Refactor

Clean up the implementation:
- Consult the **Refactoring Notes** from SPEC.md for this phase — address noted items
- Extract duplication
- Improve naming
- Optimize where the spec requires it
- Apply patterns from Phase 0 findings

Re-run the full test suite after refactoring.

**Anti-slop self-check:** Before marking this phase complete, scan for: generic error messages, placeholder comments (TODO/FIXME/HACK), over-broad exception handling, magic numbers, dead code, unnecessary abstractions, copy-pasted blocks, extraneous docstrings (restating function names or obvious parameters), comments that restate what code already says, and **development artifact comments** — any comment or docstring referencing plan phases, micro-cycles, spec details, the development process, or review findings (e.g., "Phase 1:", "Micro-cycle 2:", "Per the spec...", "Added during convergence", "Fixed per review feedback"). These are process artifacts, not documentation. Fix any found. This is not adversarial review — it's basic hygiene to prevent slop from compounding across phases.

**Test DRY check:** Before marking this phase complete, scan all tests written in this phase for repeated setup patterns. If 3+ tests share identical mock/fixture construction, extract a shared fixture. If tests differ only in input values and expected outputs, consolidate with `@pytest.mark.parametrize` (or language equivalent). This prevents test bloat from compounding across phases.

**Post-refactor traceability check:** Verify that every new abstraction, utility, or extracted function introduced during refactoring is exercised by an existing test. If refactoring introduced code paths that no test covers, **inline the abstraction** — it was premature. If the new code path genuinely needs a test, revert the refactor, return to Phase 3a to write the failing test for that behavior, and proceed through the micro-cycle. Do not write tests after implementation — that violates Red-Before-Green.

#### 3f: Mark Phase Complete

- Use `TaskUpdate` to mark this phase task as `completed`
- **Full test-plan reconciliation:** Verify every spec-listed test for this phase has a corresponding test case. Flag any gaps before marking complete.
- Ensure all items for this phase in `CHECKLIST.md` were checked off during 3b and 3d (per Phase 2c rules)
- **Git checkpoint:** Create a commit for this phase's work: `git add` the relevant files (implementation + tests + updated spec docs), then commit with message: `feat([feature-name]): phase N — [phase name]`. These per-phase commits can be squashed later if desired.
- If another implementation phase exists, use `TaskUpdate` to mark the **next** phase task as `in_progress` and move to it
- If this was the last implementation phase, all phase tasks should be `completed` — proceed to Phase 4

★ Insight ─────────────────────────────────────
As you implement, provide insights about:
- Interesting patterns being applied
- How this connects to existing code
- Any discoveries made during implementation
─────────────────────────────────────────────────

### Spec Feedback Loop

**Triggered when implementation reveals that SPEC.md is wrong or incomplete.**

This is expected — even airtight specs encounter reality. The protocol:

1. **Stop implementation** at the current substep
2. **Document the issue**: what the spec says vs. what reality requires
3. **Update spec documents**:
   - For **significant changes** (triggers notification): create a new version snapshot in `plans/<new-timestamp>/`, copy all docs, apply changes in the new version, update `PLAN.md` to point to the new version, and update CHECKPOINT.md's `Spec Version` to match. This preserves traceability and prevents version drift between PLAN.md and CHECKPOINT.md.
   - For **minor clarifications**: edit in place. Add an entry to the Iteration Log with date, change, and reason. Update the relevant spec section.
4. **Update CHECKLIST.md** if tasks changed. If the change adds or removes implementation phases, use `TaskCreate` to add tasks for new phases and `TaskUpdate` to mark removed-phase tasks as `completed` with description suffix "[phase removed by spec change]".
5. **Notify the developer and get explicit approval** via `AskUserQuestion` if the change is significant. Do not resume implementation until the developer approves the spec change — this is a hard gate, not just a notification. For minor clarifications, proceed and note in the log.

   **Notification triggers** (must notify):
   - Alters acceptance criteria or success conditions
   - Adds or removes implementation phases
   - Changes public API, data model, or schema
   - Affects security posture or non-functional requirements
   - Adds meaningful scope

   **Proceed without notifying** (log only):
   - Parameter naming, ordering, or internal renaming
   - Clarification of existing behavior (no new behavior)
   - Internal refactor that doesn't change interfaces

   **Default:** If a change does not clearly fit either list, treat it as significant and notify. Over-notifying is better than silently changing the spec.

6. **Circuit breaker:** If the spec feedback loop has been triggered more than 3 times within the same implementation phase, pause and present an `AskUserQuestion`: "This phase has required N spec revisions. Would you like to (a) continue implementation, (b) re-scope this phase, or (c) return to Phase 2 for a full spec revision?" This prevents infinite spec-implementation cycles.
   - If **(a) continue**: proceed to step 7 below.
   - If **(b) re-scope**: update SPEC.md for this phase only (narrowing scope or simplifying approach), then proceed to step 7.
   - If **(c) return to Phase 2**: update CHECKPOINT.md to Phase: 2, Substep: 2b, and jump to Phase 2b to rewrite the spec. This is equivalent to a Restart from Spec but retains exploration context.

7. **Resume TDD** at the correct substep based on the scope of the change:
   - If the spec change affects which tests are needed → resume at **3a** (Write Failing Tests)
   - If only implementation approach changed → resume at **3c** (Implement Minimum Code)
   - If the change is cosmetic/documentation only → resume where you left off (e.g., if you were in 3e Refactor, continue from 3e)

**Gate:** All implementation phase tasks completed. All tests pass. CHECKLIST.md fully checked off.

**Pre-Phase-4 gate:** If all implementation phases were resolved via the "behavior pre-existed" path (3b) and no net code changes were made by this workflow, skip Phase 4 entirely — adversarial diff review would review empty scope. Instead, proceed directly to Phase 5 with a "feature pre-existed" completion path, citing spec/test evidence.

---

## Phase 4: Adversarial Convergence

**Purpose:** Subject the implementation to adversarial review and iterate until quality converges.

### 4a: Initial Review

Update CHECKPOINT.md: Phase: 4, Substep: 4a. **On first entry to Phase 4** (not returning from a spec-triggered re-entry), set Convergence Iteration: 0. On **spec-triggered re-entry** from 4c, add a +1 penalty to the counter before running the review (this consumes one iteration as a spec-churn deterrent). The counter is then incremented again only in 4d after the re-review completes — so one spec-triggered cycle costs 2 iterations total. This is intentional: spec churn during convergence is expensive.

Run `/git-review --external` (thorough mode with external models).

This launches the full review pipeline:
- Codebase pattern exploration
- Multi-model review via external models
- Synthesis into `REVIEW_SUMMARY.md` with severity classifications
- Interactive fix application (Apply/Skip/Apply All/Skip All)

**Adversary focus areas** (in addition to standard code quality):
- **Test quality:** Flag tautological tests, over-mocked tests, tests asserting on implementation details rather than behavior, and tests that would pass even if the implementation were subtly wrong. This is distinct from checking whether tests *exist* — it's checking whether tests are *honest*.
- **Spec compliance:** For each functional requirement in SPEC.md, verify there is a traceable test-and-implementation pair. Any requirement without both is a CRITICAL finding.
- **Test DRY violations:** Flag test suites where 3+ tests share identical setup/mock construction but aren't using shared fixtures or parameterization. Flag tests that differ only in input values — these are candidates for `@pytest.mark.parametrize`.
- **Test necessity audit:** For each test, ask: "If this test were deleted, what production failure would go undetected?" Tests where the answer is "none" or "extremely unlikely" should be flagged as LOW-impact candidates for consolidation or removal. Prefer parameterized tests over many nearly-identical individual tests.
- **Documentation slop:** Flag docstrings that restate function names or obvious parameter types, comments that restate what code already says (e.g., `# increment counter` before `counter += 1`), and documentation overly specific to the current feature that will become stale. Docstrings are warranted for public APIs and non-obvious behavior — not for every function.
- **Development artifact comments:** Flag any comment or docstring that references the plan, spec, implementation phases, micro-cycles, convergence, or the development process. These are process artifacts that should have been caught in Phase 3e's anti-slop check — their presence here is a MINOR finding but should be fixed.

The review automatically discovers spec docs by reading `PLAN.md` in `.claude/docs/[feature-name]/` to locate the current versioned plan snapshot, then passes the discovered spec docs (SPEC.md, CHECKLIST.md, and KEY_DECISIONS.md if it exists) to reviewers for spec compliance checking.

### 4b: Triage Results

After the review completes (including interactive fix application), locate the review round directory. **Primary method (branch-scoped):** resolve the current branch, sanitize it (`/` → `--`), then list the contents of `.claude/reviews/<sanitized-branch>/` and select the most recent timestamp directory. Example: branch `feat/user-search` → `.claude/reviews/feat--user-search/` → pick the newest `<YYYYMMDD-HHMMSS-scope>/` subdirectory. **Secondary method** (if the branch-scoped directory is missing, empty, or contains no valid timestamp subdirectory): read `.claude/reviews/REVIEW.md`, find the most recent round's link in the Review Rounds table (first row), and resolve the full path as `.claude/reviews/` + the relative link directory — but **verify the link's branch segment matches your current branch** before using it. This prevents cross-branch contamination in concurrent workflows. Read `REVIEW_SUMMARY.md` from the resolved directory. Issues marked "Applied" are resolved. Issues marked "Skipped" are the remaining findings to triage.

- **Only MINOR, POTENTIAL, or deferred IMPORTANT findings remain → Converged.** Proceed to Phase 5. (Deferred = IMPORTANT findings the user explicitly skipped during interactive fix application. These are documented in the completion summary but do not block convergence. **CRITICAL findings cannot be deferred** — if a CRITICAL was "Skipped" during interactive fix, it remains unresolved and blocks convergence until addressed or the developer explicitly accepts it via the 4e escalation prompt.)
- **Any CRITICAL findings remain, or undeferred IMPORTANT findings remain** → proceed to 4c.

### 4c: Fix Remaining Issues

- Address all remaining CRITICAL findings
- Address IMPORTANT findings unless the developer explicitly defers them (IMPORTANT findings skipped during interactive prompts count as deferred — record them in CHECKPOINT.md's Deferred Issues field and document in the completion summary)
- **TDD applies to convergence fixes:** For any fix that changes observable behavior (new code paths, altered logic, changed API surface), write or adjust a failing regression test first, verify Red, then implement the fix and verify Green. For non-behavioral fixes (formatting, naming, documentation, dead code removal, config changes), apply directly. If uncertain whether a fix is behavioral, write the test — the cost is low.
- Run the **full test suite** after fixes to ensure no regressions
- If fixes require spec changes, trigger the Spec Feedback Loop:
  1. Create a new implementation phase task (treating the fix as an add-on phase to preserve prior completion status)
  2. Execute Phase 3 (3a-3f) for that new phase only
  3. Return to Phase 4a for a fresh full review
  - The convergence iteration counter increments on re-entering 4a (see 4a for counter rules)
  - A second spec issue during convergence escalates to the developer via `AskUserQuestion` regardless of iteration count

### 4d: Re-Review

Run `/git-review --external` (thorough mode) for re-review to ensure full severity-tagged `REVIEW_SUMMARY.md` output for triage. Do **not** use `--quick` for convergence iterations — quick mode produces no subagents, no synthesis round directory, and no `REVIEW_SUMMARY.md`, making the triage protocol in 4b unreachable.

Increment Convergence Iteration in CHECKPOINT.md after each re-review.

### 4e: Convergence Check

Repeat the triage (4b → 4c → 4d). **Default cap: 3 iterations** of the fix-and-review loop. When Convergence Iteration reaches **≥ 3** (not just exactly 3 — spec re-entries can cause the counter to skip values), the developer must explicitly approve any further iterations.

**If convergence is not reached after 3 iterations:**

```
AskUserQuestion:
  question: "After 3 review iterations, these CRITICAL/IMPORTANT issues remain: [list]. How would you like to proceed?"
  header: "Convergence"
  options:
    - label: "Fix and review again"
      description: "Continue the convergence loop for another iteration."
    - label: "Accept remaining issues"
      description: "Proceed with known issues documented. They'll be noted in the completion summary."
    - label: "I'll handle these manually"
      description: "Stop the review loop. I'll address these myself."
```

- If **"Fix and review again"**: return to 4c. The cap extends by 1 iteration each time this option is chosen.
- If **"Accept remaining issues"**: document deferred issues and proceed to Phase 5.
- If **"I'll handle these manually"**: update CHECKPOINT.md status to `completed`, add `Completion Mode: manual-handoff` and set Deferred Issues to the remaining items. Remove the CLAUDE.md breadcrumb, present the completion summary (5d) with "manual handoff" next steps, and **stop orchestration**. (This is not Abandon — the feature is substantially complete, just with review items remaining.)

**Gate:** Only MINOR/POTENTIAL/deferred-IMPORTANT findings remain, OR the developer explicitly accepts remaining issues.

---

## PR Handoff Gate (Multi-PR Only)

**Purpose:** Ensure the developer reviews and approves each PR before work begins on the next one. Prevents cascading branch changes when modifications to PR N require propagation to PR N+1.

**Triggered:** After Phase 4 converges (or the developer accepts remaining issues) for a PR that is **not the last PR** in `PR_STRATEGY.md`. If this is the last PR, skip this gate and proceed directly to Phase 5.

### Automated Cleanup

Run `/deslop-around:deslop-around apply` first (mechanical sweep: console.log, TODO, commented-out code, debug imports, etc.), then run `/polish` (semantic sweep: development artifact comments, low-value docstrings, test audit). Both operate on the current PR's branch diff and commit their changes independently. This two-pass approach produces clean, review-ready code before presenting the PR to the developer.

### Developer Review Gate

```
AskUserQuestion:
  question: "PR [N] of [M] ([branch-name]) is ready for your review. `/deslop-around:deslop-around` + `/polish` cleanup has been applied. Review the branch, then choose how to proceed."
  header: "PR Handoff"
  options:
    - label: "PR is good — continue to next PR"
      description: "Start PR [N+1] on the next branch."
    - label: "I made changes to this PR"
      description: "I've pushed changes to this branch. Incorporate them before continuing."
    - label: "Shelve remaining PRs"
      description: "Stop here. Remaining PRs will not be started."
```

### Option Handling

**"PR is good — continue to next PR":**
1. Update CHECKPOINT.md Notes to reflect moving to the next PR (e.g., "PR 2 of 3: feat/user-search--ui")
2. Determine the base for the next PR's branch from `PR_STRATEGY.md`:
   - If the next PR depends on the current PR → `git checkout -b <next-branch> <current-branch>` (stacked)
   - If the next PR is independent → `git checkout -b <next-branch> main` (or the project's default branch)
3. Return to Phase 3 for the next PR's implementation phases

**"I made changes to this PR":**
1. Fetch the latest state of the current branch: `git pull --rebase origin <current-branch>` (or detect local changes if not yet pushed)
2. If the next PR's branch already exists and was branched off the current PR, rebase it: `git checkout <next-branch> && git rebase <current-branch>`. If conflicts arise, present them to the developer
3. Run `/git-review --quick` on the current branch as a sanity check on the developer's changes. If CRITICAL findings appear, flag them but do not re-enter the full convergence loop — the developer owns this PR now
4. Re-prompt this gate (the developer may have more changes, or may now approve)

**"Shelve remaining PRs":**
1. Update CHECKPOINT.md: Status: `shelved`, Notes: "PR [N] of [M] completed. PRs [N+1]-[M] not started."
2. Replace the active CLAUDE.md breadcrumb with the shelved variant
3. Present a summary of what was completed and what remains
4. Stop orchestration

---

## Phase 5: Completion

**Purpose:** Final validation and handoff.

### 5a: Cleanup Pass

Run `/deslop-around:deslop-around apply` (mechanical sweep) followed by `/polish` (semantic sweep) on the current branch diff. This ensures the final code is clean before completion. In multi-PR mode, both already ran at each PR Handoff Gate — run them again here only if post-convergence changes were made (Phase 5d edits, final cleanups, etc.). If no changes were made since the last cleanup run, skip.

### 5b: Final Test Run

Run the complete test suite one last time. All tests must pass.

### 5c: Final Checklist

- [ ] All success criteria from SPEC.md checked
- [ ] All tests passing
- [ ] Adversarial convergence reached (Phase 4 gate satisfied), or Phase 4 was intentionally skipped via the pre-existing-feature gate
- [ ] SPEC.md iteration log reflects final state
- [ ] CHECKLIST.md fully checked off

### 5d: Quick Final Check (conditional)

If Phase 4 ran and any code changes were made after the last `/git-review` pass (e.g., minor cleanups, `/polish` changes, refactoring during 5a/5b), run `/git-review --quick` for a final sanity check. To detect: check if you made any commits or edits after the last Phase 4 review. If uncertain, run the quick check — the cost is low. If CRITICAL findings are discovered, run a full `/git-review --external` (thorough) and return to Phase 4a to resume the convergence loop (increment Convergence Iteration by 1 on re-entry from 5d). If no CRITICAL findings, proceed to 5e.

### 5e: Summary

Present to the developer:
- **What was built** — feature summary
- **Files created/modified** — with line counts
- **Test coverage** — number of tests added, types (unit/integration)
- **TDD compliance** — phases where Red→Green→Refactor was followed
- **Convergence status** — how many adversarial iterations, CRITICAL/IMPORTANT count per iteration, what was found and fixed
- **Deferred issues** — any IMPORTANT findings accepted in Phase 4
- **Spec changes** — entries from the Iteration Log (if any)
- **Next steps** — Per-phase commits already exist from 3f. Suggest: "Ready to merge or squash" if no deferred issues; "Ready to merge with N deferred issues (see above)" if issues were accepted; or "Manual handoff — address remaining issues before merging" if the developer chose to handle manually

**Cleanup:** Update CHECKPOINT.md status to `completed`. Remove only the `<!-- new-feature-vdd: [feature-name] -->` breadcrumb for the current feature from the project's CLAUDE.md (do not remove breadcrumbs for other shelved features). Use line-level insert/replace/delete for breadcrumb lines only; never overwrite CLAUDE.md wholesale.

---

## Exit Protocol (Restart / Shelve / Abandon)

**Available at any point during the workflow.** If the developer says "stop", "abort", "shelve", "start over", or otherwise indicates they want to exit the current workflow:

- **Phases 0-1** (before checkpoint exists): No state artifacts to update. Simply stop orchestration. If the developer wants to restart later, they begin fresh from Phase 0. Only offer **Abandon** (Restart from Spec and Shelve require a feature slug and checkpoint, which do not exist yet).
- **Phase 2a onward** (checkpoint + breadcrumb exist since 2a initialization): Follow the full exit protocol below. In Phase 2a, Restart from Spec loops back to 2a (no spec snapshot exists yet). In Phase 2b onward, Restart copies the current `plans/<timestamp>/` snapshot before returning to 2a.

Present:

```
AskUserQuestion:
  question: "How would you like to exit this feature workflow?"
  header: "Exit"
  options:
    - label: "Restart from spec"
      description: "Keep exploration findings, create a new spec version, and redesign the approach from Phase 2."
    - label: "Shelve (resume later)"
      description: "Pause the workflow. All state is preserved for future resumption."
    - label: "Abandon"
      description: "Stop entirely. Artifacts are preserved as a record. Changed files are left as-is."
```

### Restart from Spec

1. If `PLAN.md` points to a current version, create a new snapshot in `plans/<new-timestamp>/` by copying that version's docs. If no current version exists yet (early Phase 2a), skip snapshot copy and proceed directly to step 4
2. Add an Iteration Log entry: "Restarted from Phase [N] — [reason]"
3. Run `TaskList` to get all task IDs. Mark all incomplete tasks as `completed` via `TaskUpdate`, appending "[superseded by spec restart]" to each task's description so they are distinguishable from genuinely completed tasks
4. Update CHECKPOINT.md: Phase: 2, Substep: 2a, Status: active
5. Jump to Phase 2a (Architecture Design) — Phase 0 exploration findings are retained in SPEC.md's Codebase Context and Discovery Summary sections and do not need to be re-gathered

### Shelve

1. Update CHECKPOINT.md: set Status to `shelved`
2. Replace the active CLAUDE.md breadcrumb with the shelved variant. If the active breadcrumb is missing (e.g., interrupted initialization or manual edits), append the shelved variant instead:
   ```
   <!-- new-feature-vdd: [feature-name] (shelved) --> A shelved feature exists at .claude/docs/[feature-name]/. Read CHECKPOINT.md there to see its state before starting new work.
   ```
3. Present a brief summary: current phase/substep, what's done, what remains
4. **Stop orchestration.** The resume protocol in Phase 0 will detect the shelved breadcrumb in a future session.

### Abandon

1. Update CHECKPOINT.md: set Status to `abandoned`
2. Remove the CLAUDE.md breadcrumb entirely
3. Present a brief summary: what was built, what files were changed, what remains incomplete
4. **Stop orchestration.** Changed files are left as-is — the developer can manually commit, revert, or discard them.

---

## Usage

```
/new-feature-vdd [brief description]
```

**Examples:**
- `/new-feature-vdd user search preferences endpoint`
- `/new-feature-vdd add export to PDF functionality`
- `/new-feature-vdd refactor auth middleware to support OAuth`

---

## Subagent & Command Reference

| Phase | Tool / Agent | Purpose |
|-------|-------------|---------|
| 0 | `Explore` subagent (×2) | Breadth-first pattern and architecture discovery |
| 0 | `feature-dev:code-explorer` subagent (conditional) | Deep execution path tracing — complex features only |
| 2a | `feature-dev:code-architect` or `Plan` subagent | Architecture blueprint |
| 2d | `/plan-review` command (optional) | Multi-model spec review |
| 2d, 3, 4c | `TaskCreate` / `TaskUpdate` / `TaskList` | Create phase tasks at approval gate, track implementation, adjust during convergence |
| 4 | `/git-review --external` (thorough) | Adversarial code review + convergence re-reviews |
| PR Handoff | `/deslop-around:deslop-around apply` → `/polish` | Mechanical sweep then semantic sweep before developer reviews each PR (multi-PR only) |
| 5a | `/deslop-around:deslop-around apply` → `/polish` | Mechanical sweep then semantic sweep before completion (single-PR or final PR) |
| 5d | `/git-review --quick` (conditional) | Post-convergence sanity check only — never used for convergence evidence |

---

## Integration Notes

- `/git-review --external` automatically discovers spec docs by reading `PLAN.md` in `.claude/docs/[feature-name]/` to locate the current versioned plan snapshot, then passes them to reviewers. It uses CRITICAL/IMPORTANT/MINOR/POTENTIAL severity tags. **Branch naming:** Branch `feat/<slug>` matches `.claude/docs/<slug>/` — the directory name must equal the branch segment after `feat/`. Use the exact feature slug from Phase 2a (e.g., branch `feat/user-search-preferences-endpoint` matches `.claude/docs/user-search-preferences-endpoint/`). **Single-directory shortcut:** When only one `.claude/docs/` directory exists, `/git-review` uses it regardless of branch name — branch matching only applies when multiple directories exist. For review directory paths, `/git-review` sanitizes the branch name (replacing `/` with `--`, e.g., `feat--user-search-preferences-endpoint`).
- `/plan-review` uses CRITICAL/IMPORTANT/MINOR/GOOD severity tags (no POTENTIAL category). GOOD findings are informational and require no action. Findings are organized into Auto-apply, Needs your input, and Unique insights buckets. It creates new versioned plan snapshots automatically.

## Fallbacks

If tools are unavailable:
- **`Explore` or `feature-dev:code-explorer` unavailable** → Use a `general-purpose` subagent with a prompt describing the same objectives (pattern discovery, architecture context, execution path tracing). The exploration quality may be lower but the workflow continues.
- **`feature-dev:code-architect` unavailable** → Use a `Plan` subagent with the same inputs (exploration findings + requirements). `Plan` is lighter but sufficient for most features.
- **`/plan-review` unavailable** → Skip multi-model spec review. The user reviews the spec manually at the Phase 2d gate. Proceed on user approval.
- **`/polish` unavailable** → Perform the cleanup inline: scan for development artifact comments (plan references, micro-cycle mentions, process notes) and low-value docstrings, remove them, then categorize tests as HIGH/MEDIUM/LOW and remove LOW-value tests. This is a degraded version of `/polish` but covers the critical patterns. Commit the cleanup before presenting the PR Handoff Gate.
- **`/git-review` unavailable** → Launch a fresh `Explore` or `general-purpose` subagent with an adversarial review prompt: provide the diff and SPEC.md, instruct it to flag issues using the same severity-tagged format as REVIEW_SUMMARY.md (issue title, severity, file:line, current code, suggested fix). Resolve the current branch via `git rev-parse --abbrev-ref HEAD` and **sanitize the branch name** for the path (replace `/` with `--` and strip invalid filesystem characters, matching git-review's convention). Write the subagent's output to `.claude/reviews/<sanitized-branch>/fallback-<YYYYMMDD-HHMMSS>/REVIEW_SUMMARY.md` and update `.claude/reviews/REVIEW.md` to point to this fallback directory using the same table structure as `/git-review`: add a row to the Review Rounds table with columns `| Round | Date | Branch | Scope | Models | Failures | Summary |` and a relative link `[REVIEW_SUMMARY.md](<sanitized-branch>/fallback-<timestamp>/REVIEW_SUMMARY.md)`. If `REVIEW.md` doesn't exist, create it with the table header and this row. **After writing the fallback REVIEW_SUMMARY.md**, present each finding to the developer interactively (Apply/Skip) — matching the standard `/git-review` flow — and update each finding's status in the file to `Applied` or `Skipped`. This ensures 4b's triage can operate consistently regardless of whether `/git-review` or the fallback produced the review. Do NOT review in the main context — this would violate the fresh-context principle. The convergence loop still applies.
- **`agent` CLI unavailable** → `/git-review --external` requires the `agent` CLI. If it fails, rerun `/git-review` without `--external` (built-in Claude reviewers only). Note the downgrade in CHECKPOINT.md Notes field. The convergence loop still applies, just with single-model review instead of multi-model.
