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

The launch post says the model checks its own work more carefully and works longer on hard tasks. Its predecessor, `cursor-grok-4.6-high`, was dropped for timeouts, and Grok 4.7 timed out in all 4 of its runs: twice as `grok-4.7-high-fast`, then as `grok-4.7-high` on 2026-09-29, at 480s after 77 tool calls and at 720s after 106. The prompt told it to plan on about 30 reads, and it never began writing. It was dropped from the defaults on 2026-09-30. If it's passed with `--models` again, a `budget_scale` alone is unlikely to help, because it ignored the read budget.
