---
name: consult
description: >
  Use when you're mid-discussion on an architectural or design decision, on the fence between
  options, and want an independent second opinion from an external non-Claude model. Triggers:
  "get a second opinion", "consult", "ask another model", "what would X think", "outside
  perspective", "sanity-check this decision". NOT for reviewing a code diff (use /review) or
  delegating implementation work.
disable-model-invocation: true
argument-hint: "[question] [--new] [--challenge] [--list] [--switch <hash>] [--model <name>]"
allowed-tools: Read, Write, Edit, Bash(cursor-agent*, git rev-parse*, git config*, git check-ignore*, mkdir*, date*)
---

# Consult

## Overview

Get a one-shot **independent second opinion** on a decision from a single external model via the
`cursor-agent` (Cursor) CLI. It runs inside your repo with read access, so **you supply the
*decision*, not the codebase** — point it at the relevant files and let it read them itself.

**Core principle:** a second opinion is only worth something if it's independent of yours. The
default bundle never reveals which way *you* lean.

**Not for:** reviewing a concrete diff → `/review`. Delegating implementation → this is read-only
(`--mode ask`), it only answers.

## The framing contract (the one judgment call)

Two modes, and **only `--challenge` discloses your lean**:

- **Default (blind-neutral):** your own preference does **not** appear in the bundle. You present
  each option's case as evenhandedly as you can and ask the model to choose. This independence is
  the whole point.
- **`--challenge`:** the bundle opens with "I'm leaning toward X because …" and asks the model to
  make the strongest possible case *against* it. Implies a new thread (you can only frame a bundle
  when creating one).

## Bundle recipe (what you write and send)

The decision comes from the **current conversation**; any `<question>` the user typed is their
steer, not the whole input. Write these six parts to a temp file and pipe it in. Blind-neutral
unless `--challenge`:

1. **Role:** senior engineer giving an independent second opinion; read-only.
2. **The decision**, stated neutrally, and why it matters.
3. **The options, each steel-manned** with honest tradeoffs — no hint which is preferred.
4. **Constraints:** perf, team, deadline, existing patterns.
5. **Repo pointers:** "Relevant code: `path:line`. Workspace is this repo — read these to ground
   your answer." Never paste code it can read itself.
6. **The ask:** which would you choose, why, and what am I missing?

For `--challenge`, replace 3 & 6 with the lean + "argue the strongest case against."

## Threads & flags

An **active thread** is the chatId in the session marker. It's set by starting a thread
(default-new / `--new` / `--challenge`) or by `--switch`, and it's **absent at the start of every
session** (the marker lives in per-session scratchpad) — so the first `/consult` of a session
always starts fresh.

| Invocation | Behavior |
|---|---|
| `/consult <q>` — active thread **set** | Continue it: send `<q>` as a follow-up (no re-bundle) |
| `/consult <q>` — **no** active thread | New thread: build the bundle, send it |
| `--new [<q>]` | Force a new thread; becomes active |
| `--challenge [<q>]` | New thread with the lean **disclosed** (implies `--new`) |
| `--list` | Print saved threads; **no state change, nothing sent** |
| `--switch <hash>` | Set the active thread to `<hash>`; **nothing sent** |
| `--model <name>` | Pick the model — **honored only when creating a thread** |

**One model per thread.** A thread keeps the model it was created with. If `--model` is passed on
a *continue*, do **not** switch — print: "a thread stays on its original model; use
`--new --model <name>` for another model's independent take." (`--new --model` is the blessed way
to compare models — it hands the fresh model the decision with no prior answer to anchor on.)

## Identity: the hash

Each thread's id is the **first 8 hex characters of its chatId** (e.g. chatId
`cac439e0-2fa0-…` → `cac439e0`). Stable forever, unique within a repo. `--list` shows it,
`--switch` takes it (match by prefix).

## State — two stores

- **Session marker** — `${TMPDIR:-/tmp}/consult-$CLAUDE_CODE_SESSION_ID/current-consult`,
  **shell-sourceable** (`CHAT=…`, `MODEL=…`; add `TITLE=…` for the display label) so a continue
  can `source` it directly. Keyed on the session id, so it's **absent at the start of every new
  session**; its presence = the active thread. Written when you create or `--switch` to a thread.
- **Durable index** (git repos only) — `<repo>/.claude/consult/history.jsonl`, one line per
  thread: `{chatId, title, description, model, created_at, last_used_at}`. Gitignore
  `.claude/consult/` on first use. Powers `--list` / `--switch` across sessions.

`title` (short label) and `description` (one sentence) are written by you when a thread is
created.

## `--list` and `--switch`

- **`--list`** (repo only): read `history.jsonl`, sort by `last_used_at` newest-first, print one
  line per thread — `<hash>  <title> — <description>` — and mark the active thread with `→`.
  Changes nothing, sends nothing. Empty index → "No saved consult threads yet."
- **`--switch <hash>`**: match `<hash>` as a prefix against the index; write that thread's
  `{chatId, title, model}` to the session marker; print `switched → <hash>: <title>`. Send
  nothing — the next `/consult <q>` continues it. No match → print the list and stop.

## Commands (exact — the mechanical part agents can't guess)

```bash
REPO=$(git rev-parse --show-toplevel)   # if this fails, see "Outside a git repo"

# Per-session marker (shell-sourceable), keyed on the Claude Code session id so it is
# stable within a session and absent in a fresh one. No ambient $SCRATCH is needed.
MARKER_DIR="${TMPDIR:-/tmp}/consult-${CLAUDE_CODE_SESSION_ID:-shared}"; mkdir -p "$MARKER_DIR"
MARKER="$MARKER_DIR/current-consult"

# Decide the path — FLAGS WIN over marker state:
#   --list / --switch <hash>  → handled in "--list and --switch" (no send); never reach here.
#   --new / --challenge       → force a NEW thread even if a marker already exists.
#   otherwise                 → CONTINUE the active thread if the marker exists, else NEW.
case " $ARGUMENTS " in
  *" --new "*|*" --challenge "*) MODE=new ;;
  *) [ -f "$MARKER" ] && MODE=continue || MODE=new ;;
esac

if [ "$MODE" = new ]; then
  # Parse the model (default unless --model was passed). Parameter expansion, not
  # word-splitting, so it works under zsh, bash, and sh; MODEL is always a real id.
  MODEL=gpt-5.6-sol-xhigh
  case " $ARGUMENTS " in *" --model "*) rest="${ARGUMENTS#*--model }"; MODEL="${rest%% *}";; esac
  CHAT=$(cursor-agent create-chat)
  # write the six-part bundle (see Bundle recipe) to "$MARKER_DIR/bundle.md" first, then:
  cursor-agent -p --resume "$CHAT" --model "$MODEL" \
    --mode ask --force --trust --workspace "$REPO" < "$MARKER_DIR/bundle.md"
  printf 'CHAT=%s\nMODEL=%s\n' "$CHAT" "$MODEL" > "$MARKER"   # persist active thread (shell-sourceable)
  # also append one line to $REPO/.claude/consult/history.jsonl (see State)
else
  source "$MARKER"      # CONTINUE: sets CHAT and MODEL from the active thread; never switch model mid-thread
  cursor-agent -p --resume "$CHAT" --model "$MODEL" \
    --mode ask --force --trust --workspace "$REPO" "your follow-up question"
fi
```

> **Bash timeout: pass `timeout: 600000`.** The default model `gpt-5.6-sol-xhigh` runs 420–540s;
> Bash's 120s default will kill it mid-answer. (For a faster turnaround use
> `--model gpt-5.6-sol-xhigh-fast`, ~190–380s.)

> **Keep `--trust` (headless-only).** It trusts the workspace without prompting; `--force` only
> auto-approves commands. Without `--trust`, a first-use consult in a repo Cursor hasn't trusted
> yet can block on an interactive trust prompt and never return — defeating the non-interactive
> path. `--mode ask` keeps it read-only regardless.

## Outside a git repo

If `git rev-parse --show-toplevel` fails: use **cwd** as the workspace and keep **no durable
index** — write nothing to `.claude/consult/`. `/consult <q>` and in-session continue still work
via the session marker. `--list` / `--switch` reply: "saved threads need a git repo." Nothing
persists past the session.

## After the response

1. Present the external model's answer to the user.
2. **Add your own reaction** — where you agree, where you'd push back. The user wanted two views;
   give the juxtaposition (no extra external call). This is also where you may disclose your own
   lean to the *user* — blind-neutral applies only to the external bundle.
3. Write the session marker. In a repo: new thread → append `history.jsonl`; continue → update
   `last_used_at`.

## Edge cases

- **Dead chatId on continue** (Cursor pruned it — rare; chats persist for months): tell the user,
  offer a fresh thread on the same title. `--list` does not pre-probe liveness.
- **`--switch <hash>` no match:** print the list, change nothing.
- **`--new` / `--challenge` mid-session** re-points the marker, so later no-flag calls continue
  the *new* thread.
