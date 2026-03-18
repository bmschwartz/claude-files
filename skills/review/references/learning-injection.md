# Learning Injection

> Read this when: injecting learnings into review prompts, feature exploration, or retrospectives.

## Overview

Learnings from `.claude/learnings/` are injected into review prompts and feature exploration to prime reviewers and planners with historical context. This document defines how learnings are matched against targets, ranked, and formatted for injection.

## Scope Matching Algorithm

1. **Collect target file paths** from the current context:
   - **Code review (Phase 2):** File paths from the diff (`git diff --name-only`)
   - **Plan/spec review (Phase 2):** File paths referenced in plan documents
   - **Feature Explore:** File paths inferred from feature description + architecture context

2. **Load active learnings:** Read all `L-*.md` files from `.claude/learnings/`. Skip files where `status` is `promoted` or `expired`.

3. **Match:** For each active learning, expand its `scope` globs against the repository root. A learning **matches** if any of its scope globs matches any target file path. Multiple scope entries are OR'd.

4. **Staleness check (lazy):** For each active learning evaluated (whether or not it matches the targets):
   - Expand scope globs against the **entire repository** (not just the diff/targets).
   - If **zero files** in the repo match any scope glob: increment `_staleness_count` in the learning file.
   - If **any file** matches: reset `_staleness_count` to 0.
   - If `_staleness_count >= 3`: set `status: expired`. Log: "Learning L-NNN expired (scope no longer matches any files)."

5. **Collect** all matched, still-active learnings.

## Ranking and Cap

Sort matched learnings by:
1. Severity descending (`critical` before `important`)
2. Occurrences descending (more recurrent = higher priority)
3. `last_seen` descending (more recent = higher priority)

**Cap at 10.** If more than 10 learnings match, include only the top 10. Log how many were omitted.

## Injection Format

Insert the following section into the review prompt or exploration context. Only include this section if at least one learning matches.

```markdown
## Known Project Learnings

The following patterns have been identified in prior reviews of this codebase.
Pay special attention to whether the current changes exhibit or address these patterns.

1. **[L-003] Auth middleware ordering dependency** (architecture, critical, seen 3x)
   This service has an implicit ordering dependency between the auth middleware
   and the rate limiter. If auth runs after rate limiting, unauthenticated
   requests consume rate limit quota.

2. **[L-002] Missing transaction wrapping in API handlers** (pattern-violation, important, seen 1x)
   Database mutations in src/api/ handlers must be wrapped in transactions.
   Several handlers were found performing multi-table writes without
   transaction boundaries.
```

Each entry shows:
- **Header:** `[ID] Title` (category, severity, seen Nx)
- **Body:** The `## Finding` section content from the learning file (not Context or Mitigation — keep prompt size manageable)

## Injection Points

| Point | When | What to match against | Reference |
|-------|------|-----------------------|-----------|
| Review prompt (Phase 2) | After writing `_review-prompt.md` | Diff file paths | `SKILL.md` Phase 2 |
| Feature Explore | Pattern Discovery agent | Inferred feature file paths | `feature/phases/explore.md` |
| Feature Complete | Retrospective generation | Feature's review round learnings | `feature/phases/complete.md` |

## Notes

- **Promoted learnings are skipped** — they are already in CLAUDE.md and will be seen by reviewers through that channel.
- **The staleness check runs on every injection attempt**, even if the learning doesn't match the current targets. This ensures learnings whose scope no longer exists in the repo are eventually expired regardless of what files are being reviewed.
- **Do not modify learning files during injection** except for the `_staleness_count` update (and `status: expired` when threshold hit). Content changes happen only during extraction (Phase 4.7).
