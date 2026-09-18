---
name: consult
description: >
  Use when you're mid-discussion on an architectural or design decision, on the fence between
  options, and want an independent second opinion from an external non-Claude model. Triggers:
  "get a second opinion", "consult", "ask another model", "what would X think", "outside
  perspective", "sanity-check this decision". NOT for reviewing a code diff (use /deep-review) or
  delegating implementation work.
disable-model-invocation: true
argument-hint: "[question] [--new] [--challenge] [--list] [--switch <hash>] [--model <name>] [--agent-cli]"
allowed-tools: Read, Write, Edit, Bash(cursor-agent*, uuidgen*, python3*, git rev-parse*, git config*, git check-ignore*, mkdir*, date*)
---

# Consult

## Overview

Get a **independent second opinion** on a decision from a single external model. On **Cursor**,
the default backend is a readonly `generalPurpose` Task subagent (same family as `/deep-review`
external reviewers). On **Claude Code**, or with `--agent-cli` on Cursor, use the `cursor-agent`
CLI.

The consultant runs inside your repo with read access — **you supply the *decision*, not the
codebase**. Point it at relevant files and let it read them itself.

**Core principle:** a second opinion is only worth something if it's independent of yours. The
default bundle never reveals which way *you* lean.

**Not for:** reviewing a concrete diff → `/deep-review`. Delegating implementation → read-only
consultation only.

## Host compatibility

`CONSULT_SKILL_DIR="${CLAUDE_SKILL_DIR:-$HOME/.claude/skills/consult}"`

| Host | Default backend | Fallback |
|------|-----------------|----------|
| **Cursor** | Task subagent (`generalPurpose`, `readonly`) | `cursor-agent` CLI with `--agent-cli` |
| **Claude Code** | `cursor-agent` CLI | none |

Detect Cursor: `CURSOR_CONVERSATION_ID` is set or the Task tool is available.

Full Task protocol: [references/task-consult.md](${CONSULT_SKILL_DIR}/references/task-consult.md)

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
steer, not the whole input. Write these six parts to `bundle.md`. Blind-neutral unless
`--challenge`:

1. **Role:** senior engineer giving an independent second opinion; read-only.
2. **The decision**, stated neutrally, and why it matters.
3. **The options, each steel-manned** with honest tradeoffs — no hint which is preferred.
4. **Constraints:** perf, team, deadline, existing patterns.
5. **Repo pointers:** "Relevant code: `path:line`. Workspace is this repo — read these to ground
   your answer." Never paste code it can read itself.
6. **The ask:** which would you choose, why, and what am I missing?

For `--challenge`, replace 3 & 6 with the lean + "argue the strongest case against."

## Threads & flags

An **active thread** is the `CHAT` id in the session marker. It's set by starting a thread
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
| `--agent-cli` | Force `cursor-agent` CLI (Cursor fallback; default on Claude Code) |

**One model per thread.** A thread keeps the model it was created with. If `--model` is passed on
a *continue*, do **not** switch — print: "a thread stays on its original model; use
`--new --model <name>` for another model's independent take." (`--new --model` is the blessed way
to compare models — it hands the fresh model the decision with no prior answer to anchor on.)

## Identity: the hash

Each thread's id is the **first 8 hex characters of its `CHAT` uuid** (e.g. `cac439e0-2fa0-…` →
`cac439e0`). Stable forever, unique within a repo. `--list` shows it, `--switch` takes it (match
by prefix).

## State — three stores

- **Session marker** — `${TMPDIR:-/tmp}/consult-$SESSION_ID/current-consult`, a simple
  `CHAT=<uuid>` / `MODEL=<id>` file **read line-by-line, never `source`d**, and re-validated on
  read. `SESSION_ID` is `CLAUDE_CODE_SESSION_ID` (Claude Code) or `CURSOR_CONVERSATION_ID`
  (Cursor). Written on create or `--switch`. Display titles live in the history index, never here.
- **Thread directory** — `<repo>/.claude/consult/threads/<CHAT>/` with `bundle.md` (new threads)
  and `transcript.md` (all turns). Powers **continue** on Cursor without remote chat resume. Outside
  a git repo: `$MARKER_DIR/threads/<CHAT>/` only (no cross-session persistence).
- **Durable index** (git repos only) — `<repo>/.claude/consult/history.jsonl`, one line per
  thread: `{chatId, title, description, model, created_at, last_used_at}`. Gitignore
  `.claude/consult/` on first use. Powers `--list` / `--switch` across sessions.

`title` (short label) and `description` (one sentence) are written by you when a thread is created.

## `--list` and `--switch`

- **`--list`** (repo only): read `history.jsonl`, sort by `last_used_at` newest-first, print one
  line per thread — `<hash>  <title> — <description>` — and mark the active thread with `→`.
  Changes nothing, sends nothing. Empty index → "No saved consult threads yet."
- **`--switch <hash>`**: match `<hash>` as a prefix against the index; **validate** model against
  `[a-zA-Z0-9._-]+`; write `CHAT=<chatId>` / `MODEL=<model>` to the session marker; print
  `switched → <hash>: <title>`. Send nothing — the next `/consult <q>` continues it. No match →
  print the list and stop.

## Execution paths

### Setup (both backends)

```bash
REPO=$(git rev-parse --show-toplevel 2>/dev/null) || REPO="$PWD"

SESSION_ID="${CLAUDE_CODE_SESSION_ID:-${CURSOR_CONVERSATION_ID:-}}"
: "${SESSION_ID:?consult: no session id (CLAUDE_CODE_SESSION_ID or CURSOR_CONVERSATION_ID)}"
MARKER_DIR="${TMPDIR:-/tmp}/consult-$SESSION_ID"; mkdir -p "$MARKER_DIR"
MARKER="$MARKER_DIR/current-consult"

MODEL_ARG=""
case " $ARGUMENTS " in *" --model "*) rest="${ARGUMENTS#*--model }"; MODEL_ARG="${rest%% *}" ;; esac
case "$MODEL_ARG" in *[!a-zA-Z0-9._-]*)
  echo "consult: invalid --model '$MODEL_ARG'"; exit 1 ;; esac

USE_AGENT_CLI=false
case " $ARGUMENTS " in *" --agent-cli "*) USE_AGENT_CLI=true ;; esac

# Cursor default: Task unless --agent-cli
ON_CURSOR=false
[ -n "${CURSOR_CONVERSATION_ID:-}" ] && ON_CURSOR=true

case " $ARGUMENTS " in
  *" --new "*|*" --challenge "*) MODE=new ;;
  *) [ -f "$MARKER" ] && MODE=continue || MODE=new ;;
esac

if [ "$MODE" = continue ] && [ -n "$MODEL_ARG" ]; then
  echo "consult: this thread stays on its original model; run --new --model $MODEL_ARG for another model's independent take."
  exit 0
fi
```

### Cursor path — Task subagent (default)

When `ON_CURSOR=true` and `USE_AGENT_CLI=false`:

1. **New thread**
   - `CHAT=$(uuidgen | tr '[:upper:]' '[:lower:]')` (or `python3 -c 'import uuid; print(uuid.uuid4())'`)
   - `MODEL="${MODEL_ARG:-gpt-5.6-sol-high}"`
   - `THREAD_DIR="$REPO/.claude/consult/threads/$CHAT"` (or `$MARKER_DIR/threads/$CHAT` if no git repo)
   - `mkdir -p "$THREAD_DIR"`; write six-part bundle to `$THREAD_DIR/bundle.md`
   - Launch **one** Task: `subagent_type: generalPurpose`, `readonly: true`, `model: MODEL`, `run_in_background: false`
   - Prompt per [references/task-consult.md](${CONSULT_SKILL_DIR}/references/task-consult.md)
   - Write response to `$THREAD_DIR/transcript.md` as `## External — Turn 1`
   - `printf 'CHAT=%s\nMODEL=%s\n' "$CHAT" "$MODEL" > "$MARKER"`; append `history.jsonl` in repo

2. **Continue**
   - Read marker (`CHAT`, `MODEL`) line-by-line with validation
   - Resolve `THREAD_DIR` (repo or marker scratchpad)
   - If `THREAD_DIR` missing → legacy cursor-agent thread; warn and offer `--new` or `--agent-cli`
   - Append `## Follow-up — Turn N` to `transcript.md`
   - Launch Task with continue prompt from task-consult.md
   - Append `## External — Turn N` with response; update `last_used_at` in index

Task subagents typically finish in 2–6 minutes. No Bash timeout needed.

### Claude Code / `--agent-cli` path — cursor-agent CLI

When `USE_AGENT_CLI=true` or not on Cursor:

```bash
if [ "$MODE" = new ]; then
  MODEL="${MODEL_ARG:-gpt-5.6-sol-high}"
  CHAT=$(cursor-agent create-chat)
  # write bundle to "$MARKER_DIR/bundle.md" first, then:
  cursor-agent -p --resume "$CHAT" --model "$MODEL" \
    --mode ask --force --trust --workspace "$REPO" < "$MARKER_DIR/bundle.md" || exit 1
  printf 'CHAT=%s\nMODEL=%s\n' "$CHAT" "$MODEL" > "$MARKER"
else
  CHAT=""; MODEL=""
  while IFS='=' read -r k v; do case "$k" in CHAT) CHAT="$v" ;; MODEL) MODEL="$v" ;; esac; done < "$MARKER"
  case "$MODEL" in ""|*[!a-zA-Z0-9._-]*) echo "consult: invalid model; run --new"; exit 1 ;; esac
  case "$CHAT"  in ""|*[!a-zA-Z0-9.-]*)  echo "consult: invalid chat id; run --new"; exit 1 ;; esac
  cursor-agent -p --resume "$CHAT" --model "$MODEL" \
    --mode ask --force --trust --workspace "$REPO" "your follow-up question"
fi
```

> **Bash timeout: pass `timeout: 600000`** on cursor-agent calls. Default model `gpt-5.6-sol-high`
> runs 420–540s. Faster: `--model gpt-5.6-terra-high`.

> **Keep `--trust` (headless-only).** `--mode ask` keeps it read-only.

## Outside a git repo

If `git rev-parse --show-toplevel` fails: use **cwd** as workspace, **no** `history.jsonl`.
`/consult` and in-session continue work via session marker + `$MARKER_DIR/threads/`. `--list` /
`--switch` reply: "saved threads need a git repo."

## After the response

1. Present the external model's answer to the user.
2. **Add your own reaction** — where you agree, where you'd push back. Blind-neutral applies
   only to the external bundle, not your reply to the user.
3. Persist marker and index as described above.

## Edge cases

- **Legacy thread** (marker chatId but no `threads/<CHAT>/`): offer `--new` or `--agent-cli` continue.
- **`--switch <hash>` no match:** print the list, change nothing.
- **`--new` / `--challenge` mid-session** re-points the marker; later no-flag calls continue the new thread.
