---
key: grok-4.7
verified_against: grok-4.7-high
checked: 2026-09-29
sources:
  - https://docs.x.ai/developers/grok-4-7
  - https://docs.x.ai/developers/model-capabilities/text/reasoning
  - https://x.ai/news/grok-4-7
---

## Rationale

xAI publishes no prompt-content guidance for Grok 4.7: its model and reasoning pages cover only API settings such as reasoning effort and caching. So this profile deliberately uses the shared baseline in its default order.

The launch post says the model checks its own work more carefully and works longer on hard tasks. Its predecessor, `cursor-grok-4.6-high`, was dropped for timeouts, and the only Grok 4.7 runs so far (`grok-4.7-high-fast`, twice) both timed out. Watch its tool-call counts in `_external-results.json` and `_log-review-grok-4.7-high-*.jsonl` before adding a `budget_scale`.
