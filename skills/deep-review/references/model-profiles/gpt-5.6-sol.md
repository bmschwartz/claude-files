---
key: gpt-5.6-sol
verified_against: gpt-5.6-sol-high
checked: 2026-10-02
order: [task, context, dimensions, severities, output, exploration]
sources:
  - https://developers.openai.com/api/docs/guides/prompt-guidance-gpt-5p6
  - https://developers.openai.com/api/docs/models/gpt-5.6-sol
---

## Rationale

- Copied from `gpt-5.6-terra`. OpenAI's GPT-5.6 prompting guide is family-level, and the Sol model page has no prompting guidance of its own: it says only that Sol is the unsuffixed GPT-5 tier and that the `gpt-5.6` alias routes to it. So the guide's ordering applies unchanged: goal and success criteria, then constraints and output, then stop rules last. State each rule once and keep absolutes for true invariants.
- The output-length insert: Sol is as terse as Terra. Its 17 usable reviews in this repo (July–October 2026, mostly `xhigh-fast`) had a median length of about 3.4k characters, against about 11k for Opus. The guide's prompt-side answer, since `verbosity` can't be set through Cursor's CLI, is to say what must be kept and what to cut first.
- No `budget_scale`: Terra's 0.75 came from Terra's own runs finishing close to the timeout. Sol has one timed run on the current harness, `gpt-5.6-sol-high` at 195s on the 2026-10-02 plan review, so there is no evidence to shrink its budget. Ben allows Sol up to 15 minutes, which is the global `timeout_seconds: 900` default since 2026-10-02.
- The retrieval stop rule after `exploration` is the guide's: search again only for a missing fact.

## after output

Past reviews from this model have been much shorter than other reviewers'. Short is right only when there is little to find: keep every issue you find, with its evidence and fix, and when you need to save space, cut the prose around findings, never a finding.

## after exploration

After your first pass over the diff or plan, search again only when a fact the review needs is missing, a finding is not yet supported by code you have read, or a specific file has to be read; a finding that is already supported needs no more searching. If a search comes back empty, try one or two other queries before concluding the code isn't there.
