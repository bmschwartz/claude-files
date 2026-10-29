# Learning Schema

> Read this when: drafting a learning for `scripts/learnings.py`, or validating learning files in the store.

## File Location & Naming

Learning files live in the project's shared store, `~/.claude/projects/<main-checkout slug>/learnings/` (`scripts/learnings.py paths` prints it). Every checkout's `.claude/learnings` is a symlink to it. Only `scripts/learnings.py` writes there.

- **Naming:** `L-<NNN>.md` where NNN is zero-padded to 3 digits (e.g., `L-001.md`, `L-042.md`)
- **ID assignment:** `learnings.py new` assigns the next ID under the store lock and creates the file exclusively. Never pick an ID by hand: two sessions scanning the directory at once would mint the same one.
- **Index:** `LEARNINGS.md` in the store — table of all learnings, newest first, rebuilt by every `learnings.py` write.

## Frontmatter Schema

```yaml
---
id: L-<NNN>
title: "<short descriptive title>"
category: pattern-violation | architecture | security | correctness | test-gap | performance
severity: critical | important
scope:                                # file path globs where this learning applies
  - "src/api/**/*.ts"                 # globs are relative to repo root, OR'd
  - "src/middleware/*.ts"
tags: [auth, validation, error-handling]  # searchable keywords
source:
  review_round: ".claude/reviews/<branch>/<timestamp>/"
  agreement: strong | moderate        # agreement level of the original finding
  reviewers: [claude-code, gpt-5.6-terra-high]   # models that flagged it
  feature: "<feature-slug>"           # if extracted during /feature workflow
occurrences: 1                        # incremented on recurrence detection
first_seen: "YYYY-MM-DD"
last_seen: "YYYY-MM-DD"
status: active | promoted | expired
promoted_to: ""                       # CLAUDE.md reference when promoted
_staleness_count: 0                   # internal: consecutive zero-match injection attempts
---
```

### Field Notes

| Field | Required | Notes |
|-------|----------|-------|
| `id` | Yes | Must match filename |
| `title` | Yes | Short, descriptive, unique enough to distinguish from similar learnings |
| `category` | Yes | One of the 6 enumerated values |
| `severity` | Yes | Inherited from the finding that spawned the learning |
| `scope` | Yes | At least one glob. Should be as specific as possible — avoid `**/*` |
| `tags` | No | Freeform keywords for search. Lowercase, hyphenated. |
| `source` | Yes | Provenance of the original finding |
| `source.feature` | No | Only present when extracted during `/feature` workflow |
| `occurrences` | Yes | Starts at 1, incremented when same pattern detected in a new review |
| `first_seen` | Yes | Date of initial extraction |
| `last_seen` | Yes | Updated on each recurrence |
| `status` | Yes | Governs lifecycle behavior |
| `promoted_to` | No | Only populated when `status: promoted` |
| `_staleness_count` | Yes | Internal tracking, default 0. Not shown in LEARNINGS.md index. |
| `promotion_pending` | No | Set while a promotion made in a worktree waits in `<store>/promotions/<name>/` for `learnings.py apply-promotions` in the main checkout; `status` stays `active` until then, and `apply-promotions` removes it. |

## Body Sections

```markdown
## Finding

What was found and why it matters. This is the core lesson — the content that gets
injected into future review prompts.

## Context

When and where this pattern typically manifests. Helps future matching and helps
reviewers understand what to look for.

## Mitigation

What to do about it — specific actions, patterns to follow, or checks to perform.
```

## Status Transitions

```
  ┌──────────┐
  │  active   │──── occurrences >= 3 + user approves ────→ promoted
  └──────────┘                                              (promoted_to set,
       │                                                     stops separate injection)
       │
       └──── _staleness_count >= 3 ────→ expired
              (scope matches zero files                      (skipped at injection,
               on 3 consecutive attempts)                    retained for audit)
```

- **active** — Default for new learnings. Injected into matching reviews, plans, and feature exploration.
- **promoted** — Graduated to a CLAUDE.md rule. A promotion made in a worktree first waits with `promotion_pending` set (still `active`) until `learnings.py apply-promotions` adds the rule to the main checkout's `CLAUDE.md`. The learning file is updated with `promoted_to` referencing the CLAUDE.md entry. No longer injected separately (CLAUDE.md handles it).
- **expired** — Scope no longer matches any files in the repo. Retained on disk for audit but skipped during injection and matching.

## LEARNINGS.md Index Format

```markdown
# Review Learnings

> Auto-generated index. Do not edit manually — updated by `/deep-review` Phase 4.7.

| ID | Title | Category | Severity | Status | Occurrences | Last Seen |
|----|-------|----------|----------|--------|-------------|-----------|
| L-003 | Auth middleware ordering dependency | architecture | critical | active | 3 | 2026-03-16 |
| L-002 | Missing transaction wrapping in API handlers | pattern-violation | important | active | 1 | 2026-03-14 |
| L-001 | XSS in user-generated content rendering | security | critical | promoted | 4 | 2026-03-10 |
```

Newest entries first (by `last_seen`, then `first_seen`). All statuses included.
