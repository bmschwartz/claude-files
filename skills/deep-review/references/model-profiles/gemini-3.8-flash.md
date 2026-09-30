---
key: gemini-3.8-flash
verified_against: gemini-3.8-flash-high
checked: 2026-09-29
order: [severities, output, context, dimensions, exploration, task]
sources:
  - https://ai.google.dev/gemini-api/docs/prompting-strategies
  - https://ai.google.dev/gemini-api/docs/gemini-3
  - https://ai.google.dev/gemini-api/docs/latest-model
---

## Rationale

- Google's layout: critical constraints at the start of the prompt, long context in the middle, and the specific task at the end, introduced by an anchor phrase. Here the constraints are the severity scheme and the output contract.
- Gemini 3.x gives direct, brief answers by default, so depth has to be asked for explicitly.
- Google recommends including examples with consistent formatting. One illustrative finding shows the expected shape.
- At `-high` thinking, 3.8 Flash makes more tool calls on long tasks. Google's prompt-side mitigation is an action budget, which the shared exploration section already provides at the default scale. There is no 3.8 timing data yet; check `_external-results.json` telemetry before tightening it.

## after output

One finding in the expected shape (the content is illustrative only):

### IMPORTANT: Retry loop hides the final timeout
**Location:** `src/jobs/sync.py:88`
**Current code:**
```python
for attempt in range(3):
    try:
        return sync()
    except TimeoutError:
        continue
```
**Suggested fix:**
```python
for attempt in range(3):
    try:
        return sync()
    except TimeoutError:
        if attempt == 2:
            raise
```
**Why:** after the third timeout the loop ends and the function returns `None`, so callers treat a failed sync as a success.

## before task

Based on the review criteria and project context above, here is your task.

## after task

Report every finding with the full detail the output section asks for, even when that makes the review long.
