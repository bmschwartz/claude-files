---
key: composer-2.5
verified_against: composer-2.5
checked: 2026-09-29
sources:
  - https://cursor.com/blog/composer-2-5
  - https://cursor.com/docs/models/cursor-composer-2-5
  - https://cursor.com/blog/agent-best-practices
---

## Rationale

Cursor publishes no prompt-content guidance for Composer 2.5. The launch post covers training, and the model page covers tool use. Cursor's general agent advice, which isn't specific to Composer, is to be specific, state verifiable success criteria up front, and prefer targeted instructions over long prompts. The shared baseline already does all of that, so this profile deliberately uses it in its default order.

Composer 2.5 finishes in a median of 165s (90th percentile 264s, 20 runs); its only timeouts were on diffs of 1,650–2,030 lines, which the shared budget's large-diff tier now covers.
