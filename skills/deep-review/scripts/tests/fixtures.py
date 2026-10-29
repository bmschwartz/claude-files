from pathlib import Path

from learnings_store import StorePaths

LEARNING = """---
id: L-044
title: "A high-impact test trim must keep one direct test per pricing formula"
category: test-gap
severity: important
scope:
  - "app/credentialing/timecards/**/*.py"
  - "app/pay_package/**/*.py"
tags: [high-impact-tests, trim, formula]
source:
  review_round: ".claude/reviews/weekly-summary--2/20261015-114651-vs-pr1/"
  agreement: strong
  reviewers: [claude-code-1, composer-2.5-1]
occurrences: 2
first_seen: "2026-10-15"
last_seen: "2026-10-20"
status: active
promoted_to: ""
_staleness_count: 0
---

## Finding

The trim left three rules green under a broken implementation.
"""


MAIN = StorePaths(
    main_root=Path("/m"),
    checkout_root=Path("/m"),
    learnings_dir=Path("/s"),
    main_claude_md=Path("/m/.claude/CLAUDE.md"),
    checkout_claude_md=Path("/m/.claude/CLAUDE.md"),
)
WORKTREE = StorePaths(
    main_root=Path("/m"),
    checkout_root=Path("/m/.claude/worktrees/w"),
    learnings_dir=Path("/s"),
    main_claude_md=Path("/m/.claude/CLAUDE.md"),
    checkout_claude_md=Path("/m/.claude/worktrees/w/.claude/CLAUDE.md"),
)
