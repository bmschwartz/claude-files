# Model Profiles

A profile tunes how the shared review prompt is **delivered** to one model: section order, formatting style, text added around sections, and the exploration budget. It never changes the rubric. `dimensions`, `severities` and the per-finding fields in `output` are identical for every reviewer, because the synthesizer's agreement analysis compares reviewers that were asked the same question.

`prepare_round.py` renders one `_review-prompt-<key>.md` per profile key in the round directory and keeps it as the record of what each model received.

## Keys

The key is the model slug with the `-fast` tier and the effort suffix (`-none`, `-minimal`, `-low`, `-medium`, `-high`, `-xhigh`, `-extra-high`, `-max`) removed, so every effort level of a model shares one profile:

| Slug | Key |
|------|-----|
| `gpt-5.6-terra-high`, `gpt-5.6-terra-xhigh-fast` | `gpt-5.6-terra` |
| `gemini-3.8-flash-high` | `gemini-3.8-flash` |
| `grok-4.7-high` | `grok-4.7` |
| `composer-2.5`, `composer-2.5-fast` | `composer-2.5` |
| internal `deep-reviewer` (alias `opus`) | `opus` |

A version bump is a new key (`gemini-3.8-flash` → `gemini-3.9-flash`), so guidance written for one version is never silently reused for the next.

## Missing or invalid profile

The reviewer gets the shared baseline prompt in the default order, and `prepare_round.py` adds a warning to `profile_warnings`. The orchestrator shows these warnings at the top of the review output and in the `REVIEW_SUMMARY.md` header. The review is not blocked.

For the internal reviewer, `deep-reviewer` reports its exact model ID; when it differs from the `opus` profile's `verified_against`, the orchestrator raises the same kind of warning.

## Format

```markdown
---
key: gpt-5.6-terra                  # must match the file name
verified_against: gpt-5.6-terra-high  # exact model the guidance was checked for
checked: 2026-09-29
order: [task, context, dimensions, severities, output, exploration]  # optional; all six ids
style: markdown                     # optional; xml wraps each section in <id></id> tags
budget_scale: 0.75                  # optional multiplier on the read budget (default 1)
budget: none                        # optional; drops the read budget entirely
sources:
  - https://…                       # official vendor guidance only
---

## Rationale
Why each choice was made, citing the sources or measured data. Not sent to the model.

## before task
Text placed immediately before the `task` section.

## after output
Text placed immediately after the `output` section.
```

Section ids: `task`, `context`, `dimensions`, `severities`, `exploration`, `output` (the same ids in the code and plan templates). Only `## before <id>` and `## after <id>` headings are sent to the model; any other `##` heading is documentation. Insert text must not restate or redefine the rubric.

## Adding or bumping a model

1. Read the vendor's official prompting guidance for that exact version. Guidance from third-party blogs does not count.
2. Copy the closest profile to `<new key>.md` and update `verified_against`, `checked` and `sources`.
3. Keep only the choices the guidance, or measured data from `_external-results.json` telemetry, supports. When the vendor publishes nothing about prompt content, keep the baseline (no `order`, no inserts) and say so under Rationale.
4. Render a prompt to check it: `prepare_round.py --dry-run` reports `profile_warnings`; a real round writes `_review-prompt-<key>.md`.
