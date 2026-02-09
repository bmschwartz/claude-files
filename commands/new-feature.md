# Feature Development Process

## Overview

This command orchestrates feature development using an **exploration-first** approach. Before asking questions, Claude explores the codebase to understand existing patterns, conventions, and similar implementations. This results in fewer, more targeted questions and better architectural decisions.

The process leverages subagents and commands throughout:
- **Explore agents** for codebase discovery
- **Architecture agents** for design planning
- **`/git-review`** for code review with interactive fix application

## Process Flow

```
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ Phase 0:         │    │ Phase 1:         │    │ Phase 2:         │
│ Codebase         │ → │ Focused          │ → │ Architecture     │
│ Exploration      │    │ Discovery        │    │ Design           │
│ (Subagents)      │    │ (2-3 rounds)     │    │ (Subagents)      │
└──────────────────┘    └──────────────────┘    └──────────────────┘
         │                                              │
         ▼                                              ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ Phase 3:         │    │ Phase 4:         │    │ Phase 5:         │
│ Risk             │ → │ Specification    │ → │ Spec Approval    │
│ Assessment       │    │ Document         │    │                  │
└──────────────────┘    └──────────────────┘    └──────────────────┘
         │                                              │
         ▼                                              ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ Phase 6:         │    │ Phase 7:         │    │ Phase 8:         │
│ Implementation   │ → │ Code Review      │ → │ Completion       │
│ (TaskCreate)     │    │ (/git-review)    │    │                  │
└──────────────────┘    └──────────────────┘    └──────────────────┘
```

---

## Process Steps

### Phase 0: Codebase Exploration

**Purpose:** Gather context BEFORE asking questions so that questions are informed and minimal.

**Launch Explore Agents in Parallel** (built-in `Explore` type via Task tool):

1. **Pattern Discovery Agent**
   - Find similar features in the codebase
   - Identify coding conventions and architectural patterns
   - Look for reusable utilities or abstractions

2. **Architecture Context Agent** (for broad-scope features)
   - Map relevant dependencies and integration points
   - Identify testing patterns used
   - Find configuration patterns

**For Complex Features:** Consider launching a `feature-dev:code-explorer` agent (built-in type via Task tool) for deep architecture tracing and execution path analysis. This is slower but provides detailed execution path mapping and dependency analysis that `Explore` does not.

**Codebase Context Report:**

After exploration, provide a report:

```
## Codebase Context Report

### Similar Features Found
- `path/to/feature/` - [How it's relevant, what patterns it uses]
- `path/to/another/` - [Relevance and reusable patterns]

### Patterns to Follow
- [Pattern name] from `path/to/example`
- [Convention] used throughout the codebase

### Architectural Constraints
- [Constraint from existing architecture]
- [Integration requirement discovered]

### Recommended Approach
Based on exploration, the recommended approach is [summary].
```

★ Insight ─────────────────────────────────────
Provide insights about what was discovered:
- Why certain patterns exist in the codebase
- Trade-offs observed in similar implementations
- Conventions that should be followed
─────────────────────────────────────────────────

---

### Phase 1: Focused Discovery

Since codebase exploration already revealed feature type, similar implementations, integration points, and testing patterns, questions now focus on **what the codebase can't tell us**.

#### Round 1: Core Requirements (1-2 questions)

Focus on business requirements and success criteria:
- "What specific behavior or outcome are you trying to achieve?"
- "What does success look like for this feature?"

*After receiving answers, assess complexity and determine if Round 2 is needed.*

#### Round 2: Design Preferences (1-2 questions)

Based on Round 1 and exploration findings, ask about preferences:
- Edge case priorities (what matters most?)
- Trade-off preferences (performance vs. simplicity, flexibility vs. speed-to-ship)
- User experience expectations

*Skip to Phase 2 if requirements are clear, otherwise proceed to Round 3.*

#### Round 3: Final Clarifications (Optional, 1 question)

Only if ambiguity remains after Rounds 1-2:
- Resolve remaining uncertainties
- Confirm understanding of critical requirements

---

### Phase 2: Architecture Design

**Launch Design Subagents:**

Use `feature-dev:code-architect` agent (deep codebase-aware blueprints) or `Plan` agent (lighter-weight strategy without deep code analysis) to design the implementation:

**Input to Agent:**
- Discovery findings from Phase 0
- Requirements from Phase 1
- Risk considerations

**Expected Output - Implementation Blueprint:**

```
## Implementation Blueprint

### Files to Create
- `path/to/new/file.py` - [Purpose and structure]
- `path/to/new/test.py` - [Test coverage]

### Files to Modify
- `path/to/existing.py:123` - [Specific changes]
- `path/to/config.py` - [Configuration updates]

### Component Design
- [Component boundaries]
- [Data flow between components]
- [Interface definitions]

### Build Sequence
1. [First thing to implement]
2. [Second thing - depends on first]
3. [Continue in dependency order]

### Testing Strategy
- Unit tests: [Coverage areas]
- Integration tests: [Scenarios]
```

★ Insight ─────────────────────────────────────
Explain the architectural decisions:
- Why this structure was chosen
- How it aligns with existing patterns
- Trade-offs made and alternatives considered
─────────────────────────────────────────────────

---

### Phase 3: Risk Assessment

Evaluate risks with codebase-aware context:

**Codebase-Aware Risks:**

| Risk Type | Level | Details | Mitigation |
|-----------|-------|---------|------------|
| Pattern Deviation | High/Med/Low | Does this break existing conventions? | [Strategy] |
| Dependency Impact | High/Med/Low | Impact on dependent systems | [Strategy] |
| Testing Coverage | High/Med/Low | Gaps based on existing test patterns | [Strategy] |

**Standard Risk Categories:**

| Risk Type | Level | Details | Mitigation |
|-----------|-------|---------|------------|
| Technical Complexity | High/Med/Low | Implementation difficulty | [Strategy] |
| Integration | High/Med/Low | Systems that need modification | [Strategy] |
| Data | High/Med/Low | Migration or consistency concerns | [Strategy] |
| Performance | High/Med/Low | System performance impact | [Strategy] |
| Security | High/Med/Low | Security implications | [Strategy] |

**Feasibility Check:**
- Are there immediate blockers?
- Do we need additional resources or permissions?
- Should we consider a phased approach?

---

### Phase 4: Specification Document

Create a `.claude/docs/[feature-name]/` directory with versioned plan snapshots.

**Directory structure:**

```
.claude/docs/[feature-name]/
├── PLAN.md                          # Root index linking to current version
├── plans/
│   └── <YYYYMMDD-HHMMSS>/          # Versioned snapshot (initial version)
│       ├── SPEC.md                  # Full specification
│       ├── README.md                # Navigation guide
│       ├── KEY_DECISIONS.md         # Quick reference for design choices
│       ├── CHECKLIST.md             # Implementation tasks extracted from spec
│       ├── PR_STRATEGY.md           # PR breakdown and dependencies
│       └── FIXTURES.md             # Test data definitions
└── reviews/                         # Created later by /plan-review
```

Generate a timestamp (format: `YYYYMMDD-HHMMSS`) and create the plan directories and documents:

```bash
mkdir -p .claude/docs/[feature-name]/plans/<timestamp>/
```

**Create `PLAN.md` at the root** with links to the versioned files:

```markdown
# [Feature Name] Plan

Current version: `plans/<timestamp>/`

## Documents

- [SPEC.md](plans/<timestamp>/SPEC.md) — Full specification
- [README.md](plans/<timestamp>/README.md) — Navigation guide
- [KEY_DECISIONS.md](plans/<timestamp>/KEY_DECISIONS.md) — Design choices
- [CHECKLIST.md](plans/<timestamp>/CHECKLIST.md) — Implementation tasks
- [PR_STRATEGY.md](plans/<timestamp>/PR_STRATEGY.md) — PR breakdown
- [FIXTURES.md](plans/<timestamp>/FIXTURES.md) — Test data

_(Only list documents that were actually created)_
```

**Document purposes:**

| Document | Purpose | Key content |
|----------|---------|-------------|
| `SPEC.md` | Full specification | Requirements, implementation phases, iteration log |
| `README.md` | Navigation guide | Document index, quick start |
| `KEY_DECISIONS.md` | Quick reference | Design decisions, trade-offs, rationale |
| `CHECKLIST.md` | Progress tracking | Extracted tasks organized by phase |
| `PR_STRATEGY.md` | PR planning | Dependency graph, PR sequence, branch names |
| `FIXTURES.md` | Test ground truth | Pytest fixtures, sample data, assertions |

**SPEC.md structure:**

```markdown
# Feature Specification: [Feature Name]

## Feature Overview
[Concise description of the feature and its purpose]

## Codebase Context

### Similar Implementations
- `path/to/similar/feature.py` - [How it's relevant]
- `path/to/pattern/example.py` - [What we're reusing]

### Patterns to Follow
- [Pattern name] from `path/to/example`

### Constraints Discovered
- [Constraint from existing architecture]

## Discovery Summary

### Discovery: Codebase Exploration
*Key findings from exploration:*
- [Finding 1]
- [Finding 2]

### Discovery: Requirements
Q: [Question asked]
A: [Answer provided]
*Requirement: [What we learned]*

## Key Insights

★ [Insight about architectural decision]
★ [Insight about trade-offs made]
★ [Insight about codebase patterns]

## Risk Assessment

| Risk Type | Level | Details | Mitigation |
|-----------|-------|---------|------------|
| [Type] | [Level] | [Details] | [Strategy] |

## Requirements

### Functional Requirements
- [ ] Requirement 1 (Priority: High/Med/Low)
- [ ] Requirement 2 (Priority: High/Med/Low)

### Non-Functional Requirements
- [ ] Performance: [Specific metrics]
- [ ] Security: [Specific requirements]
- [ ] Scalability: [Expected load]

## Implementation Plan

### Phase 1: [Core Functionality]
**Complexity:** Low/Medium/High
**Dependencies:** [What must be completed first]

1. `path/to/file.py`
   - [ ] Add function X
   - [ ] Update method Y
2. `path/to/newfile.py`
   - [ ] Implement class Z

### Phase 2: [Enhancements/Edge Cases]
**Complexity:** Low/Medium/High
**Dependencies:** [Phase 1 completion]
...

## Testing Strategy

### Unit Tests
- [ ] Test case 1: [Description]
- [ ] Test case 2: [Description]

### Integration Tests
- [ ] Test scenario 1: [Description]
- [ ] Test scenario 2: [Description]

### Manual Testing Checklist
- [ ] User workflow 1
- [ ] Edge case handling

## Success Criteria
- [ ] All functional requirements implemented
- [ ] All tests passing
- [ ] Performance metrics met: [Specific metrics]
- [ ] No regression in existing functionality
- [ ] Code review complete

## Rollback Plan
1. Revert commits: [Will be listed during implementation]
2. Database changes: [If applicable]
3. Configuration rollback: [If applicable]

## Iteration Log
*Track changes to the spec during implementation:*

| Date | Change | Reason |
|------|--------|--------|
| [Date] | Initial spec | - |
```

---

### Phase 5: Spec Approval

After creating the specification:

1. **Notify user** that spec has been created at `.claude/docs/[feature-name]/plans/<timestamp>/` with `PLAN.md` at the root linking to the current version.
2. **Summarize** what documents were created and why:
   - "Created SPEC.md, README.md, KEY_DECISIONS.md, and CHECKLIST.md in `plans/<timestamp>/`"
   - "Skipped PR_STRATEGY.md (single PR) and FIXTURES.md (no new models)"
   - "Created PLAN.md at root with links to current version"
3. **Remind user** they can run `/plan-review <project_root> .claude/docs/[feature-name]` to get a multi-model review of the plan before proceeding.
4. **User reviews** the specification, starting with `PLAN.md` or `README.md`
5. **User can:**
   - Approve and proceed to implementation
   - Request changes to the specification
   - Add missing details or requirements
   - Adjust phasing or implementation approach
   - Request additional supporting documents
   - Run `/plan-review` for multi-model analysis
6. **Once approved**, proceed to implementation

---

### Phase 6: Implementation

**Task Tracking:**

Before starting implementation, create tasks from `CHECKLIST.md`:
1. Use `TaskCreate` to create a task for each phase/item
2. Use `TaskUpdate` to mark `in_progress` as you work on each
3. Use `TaskUpdate` to mark `completed` immediately upon finishing
4. Update `CHECKLIST.md` to reflect actual progress

**Implementation Approach:**

1. **Start with KEY_DECISIONS.md open** - Quick reference for design choices
2. Follow the build sequence from `PR_STRATEGY.md` (if created)
3. Reference similar implementations discovered in Phase 0
4. Apply patterns identified during exploration
5. Copy test fixtures from `FIXTURES.md` into actual test files
6. Update SPEC.md iteration log with any spec changes

**Continuous Validation:**
- After each phase, verify against success criteria
- Run tests as you implement
- Check off items in `CHECKLIST.md`
- Document any deviations in SPEC.md iteration log
- Adjust remaining phases if needed

★ Insight ─────────────────────────────────────
As you implement, provide insights about:
- Interesting patterns being applied
- How this connects to existing code
- Any discoveries made during implementation
─────────────────────────────────────────────────

---

### Phase 7: Code Review

After implementation, run `/git-review` to perform a comprehensive code review.

**What `/git-review` Does:**
1. **Explores codebase patterns** - Launches Explore agent to understand conventions
2. **Deep code analysis** - Uses `feature-dev:code-reviewer` agent
3. **Spec compliance check** - Validates against the feature spec created in Phase 4
4. **Categorizes issues** - Critical, Important, and Suggestions
5. **Interactive fix application** - Prompts to apply each fix (Apply/Skip)

**The review will automatically:**
- Check for bugs, logic errors, and security vulnerabilities
- Verify adherence to project conventions discovered in Phase 0
- Validate implementation against `.claude/docs/[feature-name]/` (reads `PLAN.md` to find the current plan version, then reads SPEC.md, KEY_DECISIONS.md, CHECKLIST.md from that version directory)
- Verify test coverage using FIXTURES.md as reference
- Offer to apply fixes interactively

**After the review:**
- Address any critical or important issues (via interactive prompts or manually)
- Consider suggestions for code quality
- Update SPEC.md iteration log if requirements changed
- Check off completed items in CHECKLIST.md

★ Insight ─────────────────────────────────────
The `/git-review` command provides insights throughout:
- What patterns were detected in the codebase
- Why certain issues were flagged
- How fixes align with project conventions
─────────────────────────────────────────────────

---

### Phase 8: Completion

**Final Checklist:**
- [ ] All success criteria checked
- [ ] All tests passing
- [ ] `/git-review` complete and issues addressed
- [ ] Spec iteration log reflects final state
- [ ] Documentation updated if needed
- [ ] Ready for commit

**If additional changes were made after Phase 7:** Run `/git-review --quick` for a fast final check before committing.

---

## Usage Instructions

To use this process:

1. Start with: `/new-feature [brief description]`
   - Example: `/new-feature user search preferences endpoint`
   - Example: `/new-feature add export to PDF functionality`

2. Wait for codebase exploration to complete (Phase 0)

3. Answer focused questions (typically 3-5 total, not 10)

4. Review architecture design and risk assessment

5. Approve specification

6. Implementation proceeds with progress tracking

7. Code review and completion

Alternative triggers:
- "I want to implement [feature]. Let's use the feature process."
- "New feature: [description]"

---

## Benefits of This Approach

- **Exploration-First**: Questions are informed by actual codebase context
- **Fewer Questions**: 3-5 focused questions instead of 7-10 generic ones
- **Pattern-Aware**: Automatically finds and follows existing conventions
- **Risk-Aware**: Identifies codebase-specific risks early
- **Subagent-Powered**: Leverages specialized agents for exploration, design, and review
- **Progress-Tracked**: TaskCreate/TaskUpdate integration ensures nothing is forgotten
- **Educational**: ★ Insight blocks explain architectural decisions throughout
- **Quality-Assured**: `/git-review` integration with interactive fix application

---

## Subagent & Command Reference

All agents below are **built-in Claude Code agent types** launched via the Task tool's `subagent_type` parameter. They do not require custom agent files in `.claude/agents/`.

| Phase | `subagent_type` | Purpose |
|-------|-----------------|---------|
| 0 | `Explore` | Quick pattern and file discovery |
| 0 | `feature-dev:code-explorer` | Deep architecture tracing (complex features) |
| 2 | `Plan` | Lighter-weight implementation strategy (no deep code analysis) |
| 2 | `feature-dev:code-architect` | Detailed architecture blueprints |
| 7 | `/git-review` command | Comprehensive code review with interactive fixes |

---

## Integration with `/git-review`

Phase 7 directly invokes `/git-review`, which provides:

- **Codebase exploration** via Explore agent
- **Deep analysis** via `feature-dev:code-reviewer` agent
- **Spec compliance checking** against `.claude/docs/[feature-name]/` directory (reads `PLAN.md` to resolve the current plan version, with legacy flat-layout fallback):
  - `SPEC.md` for requirements and implementation phases
  - `KEY_DECISIONS.md` for design choices to verify
  - `CHECKLIST.md` for task completion status
  - `FIXTURES.md` for test data validation
- **Interactive fix application** with Apply/Skip prompts
- **Educational insights** throughout the review

This creates a seamless workflow where the feature documentation created in Phase 4 is automatically validated during code review in Phase 7.

---

## Supporting Document Templates

### README.md Template

```markdown
# [Feature Name] Documentation

[One-line description of the feature]

## Documents

| File | Purpose | When to use |
|------|---------|-------------|
| `SPEC.md` | Full feature specification | Deep dives, understanding rationale |
| `KEY_DECISIONS.md` | Quick reference for design choices | During implementation, code review |
| `CHECKLIST.md` | Implementation task list | Tracking progress, PR scope |
| `PR_STRATEGY.md` | PR breakdown and dependencies | Planning work, ordering PRs |
| `FIXTURES.md` | Test data definitions | Writing tests, validating models |

## Quick Start

1. Read `KEY_DECISIONS.md` first (5 min)
2. Use `CHECKLIST.md` to track your phase
3. Reference `SPEC.md` for implementation details
4. Follow `PR_STRATEGY.md` for PR sequencing
```

### KEY_DECISIONS.md Template

```markdown
# [Feature Name] Key Decisions

> Quick reference for critical design decisions.
> For full context, see `SPEC.md`.

## [Category 1]

| Decision | Choice | Rationale |
|----------|--------|-----------|
| [Decision] | [Choice made] | [Why] |

## [Category 2]

| Decision | Choice | Rationale |
|----------|--------|-----------|
| [Decision] | [Choice made] | [Why] |

```

### CHECKLIST.md Template

```markdown
# [Feature Name] Implementation Checklist

> Extracted from `SPEC.md`
> Reference the spec for details on each item.

## Phase 1: [Phase Name]

**File:** `path/to/file.py`

- [ ] Task 1
- [ ] Task 2

**File:** `path/to/test.py`

- [ ] Test task 1

---

## Phase 2: [Phase Name]

...

---

## Final Validation

- [ ] All tests passing
- [ ] Code review complete
- [ ] [Other success criteria]
```

### PR_STRATEGY.md Template

```markdown
# [Feature Name] PR Strategy

## Dependency Graph

\`\`\`
Phase 1 ──► Phase 2 ──► Phase 3
                │
                ▼
            Phase 4
\`\`\`

## Recommended PR Sequence

| PR | Phases | Scope | Can Merge When |
|----|--------|-------|----------------|
| PR 1 | 1, 2 | [Scope] | Tests pass |
| PR 2 | 3 | [Scope] | PR 1 merged |

---

## PR 1: [Name]

**Branch:** `feature/[name]-[part]`

**Files:**
\`\`\`
path/to/files
\`\`\`

**Checklist:**
- [ ] Items from CHECKLIST.md

**Review focus:** [What reviewers should look for]
```

### FIXTURES.md Template

```markdown
# [Feature Name] Test Fixtures

> Ground truth for tests. Copy these into actual test files.

## Location

Test fixtures should live in:
\`\`\`
path/to/fixtures.py
\`\`\`

## Imports

\`\`\`python
import pytest
from path.to.models import Model
\`\`\`

---

## [Model/Context Name]

\`\`\`python
@pytest.fixture
def sample_[name]() -> [Type]:
    """Sample [name] for testing."""
    return [Type](
        field1=value1,
        field2=value2,
    )
```

