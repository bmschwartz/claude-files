---
name: consult
description: >
  Use when you're mid-discussion on an architectural or design decision, on the fence between
  options, and want an independent second opinion from an external non-Claude model. Triggers:
  "get a second opinion", "consult", "ask another model", "what would X think", "outside
  perspective", "sanity-check this decision". NOT for reviewing a code diff (use /review) or
  delegating implementation work.
disable-model-invocation: true
argument-hint: "[question] [--new] [--list] [--challenge] [--model <name>]"
allowed-tools: Read, Write, Edit, Bash(cursor-agent*, git rev-parse*, git config*, git check-ignore*, mkdir*, date*)
---

# Consult

## Overview

Get a one-shot **independent second opinion** on a decision from a single external model via the
`cursor-agent` (Cursor) CLI. It runs inside your repo with read access, so **you supply the
*decision*, not the codebase** — point it at the relevant files and let it read them itself.

**Core principle:** a second opinion is only worth something if it's independent of yours. The
default bundle never reveals which way *you* lean.

**When NOT to use:** reviewing a concrete diff → `/review`. Delegating implementation → this is
read-only (`--mode ask`), it only answers.

## The framing contract (the one judgment call)

Two modes, and **only `--challenge` discloses your lean**:

- **Default (blind-neutral):** your own preference does **not** appear in the bundle. You present
  each option's case as evenhandedly as you can and ask the model to choose. This is what makes
  the answer independent.
- **`--challenge`:** the bundle opens with "I'm leaning toward X because …" and asks the model to
  make the strongest possible case *against* it. Use when you want your lean stress-tested, not a
  fresh vote.

## Bundle recipe (what you write and send)

Write these six parts to a temp file and pipe it in. Blind-neutral unless `--challenge`:

1. **Role:** senior engineer giving an independent second opinion; read-only.
2. **The decision**, stated neutrally, and why it matters.
3. **The options, each steel-manned** with honest tradeoffs — no hint which is preferred.
4. **Constraints:** perf, team, deadline, existing patterns.
5. **Repo pointers:** "Relevant code: `path:line`. Workspace is this repo — read these to ground
   your answer." Never paste code it can read itself.
6. **The ask:** which would you choose, why, and what am I missing?

For `--challenge`, replace 3 & 6 with the lean + "argue the strongest case against."

## Behavior & flags

| Invocation | Behavior |
|---|---|
| *(no flag)*, session marker **present** | **Continue** the active chat — send the question as a follow-up (no re-bundle) |
| *(no flag)*, marker **absent**, repo **has** history | **Picker** — numbered list, user replies with a number or `new` |
| *(no flag)*, marker **absent**, **no** history | **New** consult (skip an empty picker) |
| `--new` | Fresh chat + full bundle; re-points the marker |
| `--list` | Picker (even mid-session) |
| `--challenge` | Framing modifier for a **new** consult's bundle |
| `--model <name>` | Override default `gpt-5.6-sol-xhigh` |

## State — two stores, each to its strength

- **Session marker** — `<session-scratchpad>/current-consult.json` = `{chatId, topic, model}`.
  Written to your per-session scratchpad dir, so it's **absent at the start of every new
  session** → first consult of a session goes to the picker. Its presence = "already consulting
  this session" → continue.
- **Repo history** — `<repo>/.claude/consult/history.jsonl`, one line per new consult:
  `{chatId, topic, model, created_at, last_used_at}`. Durable, powers the picker. On first use,
  ensure `.claude/consult/` is gitignored (it's personal decision history).

`topic` is a one-line descriptor you write from the decision (e.g. "primary datastore for events
service") — the label the picker shows.

## Commands (exact — the mechanical part agents can't guess)

```bash
REPO=$(git rev-parse --show-toplevel)

# NEW consult:
CHAT=$(cursor-agent create-chat)
cursor-agent -p --resume "$CHAT" --model gpt-5.6-sol-xhigh \
  --mode ask --force --workspace "$REPO" < bundle.md

# CONTINUE / follow-up (reuse the consult's stored model unless --model given):
cursor-agent -p --resume "$CHAT" --model <stored-model> \
  --mode ask --force --workspace "$REPO" "your follow-up question"
```

> **Bash timeout: pass `timeout: 600000`.** The default model `gpt-5.6-sol-xhigh` runs 420–540s;
> Bash's 120s default will kill it mid-answer. (For a faster turnaround use
> `--model gpt-5.6-sol-xhigh-fast`, which completes in ~190–380s.)

## After the response

1. Present the external model's answer to the user.
2. **Add your own reaction** — where you agree, where you'd push back. The user asked for two
   views; give them the juxtaposition (this costs no extra external call).
3. New consult → append `history.jsonl` and write the marker. Continue → update `last_used_at`.

## Edge cases

- **Dead chatId on resume** (Cursor pruned it): tell the user, offer a fresh consult on the same
  topic.
- **Picker with empty history** (`--list`, nothing stored): "No past consults — starting new."
- **`--new` mid-session** re-points the marker, so later no-flag calls continue the *new* thread.
