# Consult — Task Subagent Backend (Cursor)

On **Cursor**, `/consult` uses readonly `generalPurpose` Task subagents instead of the `cursor-agent` CLI. Pass `--agent-cli` to force the legacy CLI path.

## When to use which backend

| Host | Default | Fallback |
|------|---------|----------|
| **Cursor** | Task subagent (`generalPurpose`, `readonly`) | `cursor-agent` CLI when `--agent-cli` or Task fails |
| **Claude Code** | `cursor-agent` CLI | none (no Task tool) |

Detect Cursor: `CURSOR_CONVERSATION_ID` is set or the Task tool is available.

## Thread storage (replaces cursor-agent chat resume)

Each thread is a directory under the repo (or session scratchpad outside a git repo):

```
.claude/consult/
  history.jsonl
  threads/<CHAT>/
    bundle.md       # six-part bundle (new threads only)
    transcript.md   # appended external responses + follow-ups
```

- **`CHAT`**: UUID generated locally (`uuidgen` or `python3 -c 'import uuid; print(uuid.uuid4())'`), not from `cursor-agent create-chat`.
- **Hash** (for `--list` / `--switch`): first 8 hex chars of `CHAT`, unchanged.
- **Continue**: Task reads `bundle.md` + `transcript.md` + new follow-up — no remote chat resume.

Outside a git repo, use `$MARKER_DIR/threads/<CHAT>/` instead of `.claude/consult/threads/`.

## New thread — Task launch

After writing `bundle.md`:

```
Task(
  subagent_type: "generalPurpose",
  readonly: true,
  model: "<MODEL>",
  run_in_background: false,   # consult is interactive — wait for answer
  prompt: <see template below>
)
```

### New-thread prompt template

```markdown
You are an independent second-opinion consultant (senior engineer). Read-only — analyze and advise, do not edit files.

## Workspace
Repository root: {REPO}
Read the consult bundle: {THREAD_DIR}/bundle.md

## Instructions
1. Read the bundle completely.
2. Read any repo files the bundle points to — do not ask for pasted code.
3. Give your full independent opinion in markdown.

## Output
Respond with your analysis only. No preamble about being an AI.
```

`THREAD_DIR` = `.claude/consult/threads/<CHAT>` (repo) or `$MARKER_DIR/threads/<CHAT>` (no repo).

After Task completes:
1. Write response to `{THREAD_DIR}/transcript.md` as `## External — Turn 1\n\n{response}`
2. Update marker, append `history.jsonl`

## Continue thread — Task launch

Append to transcript before launch:

```markdown
## Follow-up — Turn {N}
{user follow-up question}
```

```
Task(
  subagent_type: "generalPurpose",
  readonly: true,
  model: "<MODEL from marker>",
  run_in_background: false,
  prompt: <continue template>
)
```

### Continue prompt template

```markdown
You are continuing an independent consult thread. Read-only.

## Workspace
Repository root: {REPO}
Initial bundle: {THREAD_DIR}/bundle.md
Prior conversation: {THREAD_DIR}/transcript.md

## Instructions
1. Read bundle and transcript.
2. Read any repo files needed for context.
3. Answer ONLY the latest follow-up in transcript (## Follow-up — Turn {N}).

## Output
Your follow-up answer in markdown. Do not repeat the full prior opinion.
```

After Task completes, append `## External — Turn {N}\n\n{response}` to `transcript.md`.

## Legacy threads (cursor-agent chatId only)

If `threads/<CHAT>/` is missing but marker/history has a `CHAT` from before this migration:
- On continue: warn and offer `--new` with same title, or use `--agent-cli` to resume via `cursor-agent --resume`.

## Model and timing

- Default model: `gpt-5.6-sol-high` (Task `model` slug)
- Faster option: `--model gpt-5.6-terra-high`
- Task subagents typically finish in 2–6 minutes; no Bash timeout needed (unlike `cursor-agent` CLI — use `timeout: 600000` only on `--agent-cli` path).

## `--agent-cli` path (fallback)

Same as the legacy bash block in SKILL.md: `cursor-agent create-chat` / `--resume` with `--mode ask --force --trust`.
