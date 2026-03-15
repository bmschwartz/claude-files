# Review Execution Protocol

> Read this when: executing Step 2f (launching reviewers in thorough mode).

## Internal-only Mode (default, no --external)

Launch `<COUNT>` (default 1) `feature-dev:code-reviewer` agents (`model: "opus"`, `run_in_background: true`). Each receives:

- The full diff content
- Codebase patterns discovered in Phase 0
- Project-specific rules from CLAUDE.md
- Feature spec docs (if available) — SPEC.md, KEY_DECISIONS.md, CHECKLIST.md, FIXTURES.md
- PR metadata (if `--pr` mode)
- **Confidence threshold:** "Only report issues with HIGH confidence. Pattern violations carry extra weight. Tag uncertain issues as 'Potential Issue'."
- **Output instruction:** "Return your complete review as your final message in markdown format. Do NOT attempt to write files — you do not have Write tool access."

**IMPORTANT — File writing:** `feature-dev:code-reviewer` does NOT have the Write tool. After each agent completes, the **parent orchestrator** must capture the returned output and write it to `${ROUND_DIR}/review-claude-code-<N>.md`.

These reviewers have native Claude Code codebase access — they can read files, explore the project, and use all built-in tools beyond the diff.

## External Mode (with --external)

In addition to Claude code-reviewers, launch `<COUNT>` `code-review-executor` agents per external model (`run_in_background: true`). Each receives:

```
Run a code review using the Cursor `agent` CLI:
- Model: <MODEL>
- Instance: <N>
- Review prompt: ${ROUND_DIR}/_review-prompt.md
- Diff: ${ROUND_DIR}/_diff.patch
- Project root: <PROJECT_ROOT> (workspace for codebase access)
- Output: ${ROUND_DIR}/review-<MODEL>-<N>.md

If CLI fails, retry once. If it fails again, write error report to output file.
```

## Progress Tracking

As each reviewer completes, report: "Review complete: `<reviewer>` instance `<N>` (`M` of `TOTAL` remaining)".

## Error Recovery

After all reviewers finish:
1. Write internal review files from agent outputs
2. Verify each expected review file exists and is non-empty
3. For missing/errored files: note failure, continue with successful reviews
4. **Zero-success guard:** If ALL reviews failed, stop. At least one is required for synthesis.
