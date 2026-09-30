---
key: gpt-5.6-terra
verified_against: gpt-5.6-terra-high
checked: 2026-09-29
order: [task, context, dimensions, severities, output, exploration]
budget_scale: 0.75
sources:
  - https://developers.openai.com/api/docs/guides/prompt-guidance-gpt-5p6
  - https://developers.openai.com/api/docs/models/gpt-5.6-terra
---

## Rationale

- OpenAI's GPT-5.6 guide is family-level; it has nothing specific to Terra. It orders a prompt as goal and success criteria, then constraints and output, then stop rules last. It also says to state each rule once and keep absolutes for true invariants.
- 5.6 is terser than 5.5, and the `verbosity` parameter can't be set through Cursor's CLI. The guide's prompt-side answer is to say what must be kept and what to cut first. Past `gpt-5.6-terra-high` reviews had a median length of about 4k characters, against about 11k for Opus.
- `budget_scale: 0.75`: its slow runs finished at a 90th percentile of 456s against the 480s timeout (9 runs, September 2026). The guide's retrieval rule, to search again only for a missing fact, is the stop rule added after `exploration`.

## after output

Past reviews from this model have been much shorter than other reviewers'. Short is right only when there is little to find: keep every issue you find, with its evidence and fix, and when you need to save space, cut the prose around findings, never a finding.

## after exploration

After your first pass over the diff or plan, search again only when a fact the review needs is missing, a finding is not yet supported by code you have read, or a specific file has to be read; a finding that is already supported needs no more searching. If a search comes back empty, try one or two other queries before concluding the code isn't there.
