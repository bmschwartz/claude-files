---
key: opus
verified_against: claude-opus-5-5
checked: 2026-10-02
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
- **Parallel tool calls (added 2026-10-02).** Measured on round 1 of the nomad-flask timecard weekly summary plan review (`.claude/reviews/master/20261002-120334-plan/`):
  - Opus made 97 tool calls in 88 turns, 81 of them single-call. It took 1,232 s, about 1,070 s of it generating between calls.
  - gpt-5.6-sol-high made 108 calls in 23 batches of up to 8 and took 285 s.
  - The one-clause "run independent reads and searches in parallel" in the shared template and in the agent file didn't change that.

  Anthropic's best-practices page ("Optimize parallel tool calling") gives a `<use_parallel_tool_calls>` prompt as the way to raise parallel calling to about 100%. The `after exploration` insert adapts it, with a review-shaped example.
- **Dedicated tools, no filesystem-wide search (added 2026-10-02).** In the same run, 89 of the 97 calls went through Bash (`grep`, `sed`, `find`), and one `find /` looking for `nomad_openapi`'s source took 121 s by itself; the package was in the workspace's `.venv`. The insert points searches and reads at Grep, Glob and Read and keeps Bash for git. The agent file still lists `rg` among Bash's read-only commands, which allows it but no longer makes it the default.
- **Not changed: effort or time pressure.** The Opus 5.5 guide says effort is the main control on thinking time, reliably more than prompt instructions, and to reserve `xhigh` and `max` for measured quality gains. The skill runs this reviewer at the session's effort on purpose, so lowering it is a separate, untested decision. The guide's time-signal sentence ("Time matters here…") is also left out, because the guide notes that under time pressure the model may search and verify a little less, and verification is this reviewer's value.
- Re-measure after the next few rounds: turns per tool call and wall time against round 1's 88 turns and 1,232 s, and whether findings per review hold up.

## after exploration

<use_parallel_tool_calls>
When you intend to make several tool calls and none of them needs another's result, make them all in the same turn rather than one per turn. For example, read the input together with every spec and convention file the context names in a single turn, and when you check several functions, paths or fields the input cites, run all of those searches at once. Make calls one after another only when a call needs a value that an earlier call returns, and never guess a missing parameter to make a call parallel.
</use_parallel_tool_calls>

<tool_choice>
Use the Grep, Glob and Read tools to search and read files, and keep Bash for what they can't do, such as `git log`, `git show` and `git blame`. Search inside the workspace root only, never the whole filesystem (`find /`, or `rg` from `/`). If you need an installed package's source, look for it in a virtualenv inside the workspace (for example `.venv/lib/python*/site-packages/`). If it isn't there, say what you couldn't confirm rather than searching further.
</tool_choice>
