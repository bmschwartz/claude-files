# [Feature Name] PR Strategy

## Dependency Graph

```
Phase 1 ──► Phase 2 ──► Phase 3
                │
                ▼
            Phase 4
```

## Recommended PR Sequence

| PR | Phases | Scope | Can Merge When |
|----|--------|-------|----------------|
| PR 1 | 1, 2 | [Scope] | Tests pass |
| PR 2 | 3 | [Scope] | PR 1 merged |

---

## PR 1: [Name]

**Branch:** `feat/[slug]--[slice]`

**Files:**
```
path/to/files
```

**Checklist:**
- [ ] Items from CHECKLIST.md

**Review focus:** [What reviewers should look for]
