---
key: opus
verified_against: claude-opus-5-5
checked: 2026-09-29
order: [context, task, dimensions, severities, exploration, output]
style: xml
budget: none
sources:
  - https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
  - https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5
  - https://code.claude.com/docs/en/sub-agents
---

## Rationale

- Long context first and instructions last, which Anthropic reports improves results on long inputs. XML tags keep the project context, the rubric and the output spec apart.
- No read budget: the internal reviewer has no timeout, so a budget would only cost findings.
- The shared rubric asks for every finding tagged with its confidence. Opus 5.x follows "only report high-severity issues" literally and drops real findings, so the filtering is left to the synthesizer.
- Role, grounding, scope, the completion condition and the one-line status reply live in the system prompt, `agents/deep-reviewer.md`, which only this model reads. It reports its model ID so the orchestrator can warn when the `opus` alias moves past `verified_against`.
