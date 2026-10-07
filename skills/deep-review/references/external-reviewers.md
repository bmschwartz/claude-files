# External Reviewers — Dual Backend

External reviewers add **cross-model diversity** beyond internal Explore reviewers. The orchestrator must produce `review-<MODEL>-<N>.md` files in the round directory regardless of backend.

## When to use which backend

| Host | Default backend | Fallback |
|------|-----------------|----------|
| **Cursor** | Task subagents (`generalPurpose`, readonly) | `run_reviewers.py` when `--agent-cli` or Task launch fails |
| **Claude Code** | `run_reviewers.py` + `agent` CLI | none (Task tool unavailable) |

Detect host: Cursor when `CURSOR_CONVERSATION_ID` is set or the Task tool is available. Claude Code otherwise.

**Flags:**
- `--external` (default for code type): enable external reviewers
- `--no-external`: internal Explore reviewers only
- `--agent-cli`: force agent CLI backend even on Cursor
- `--models <m1,m2,...>`: override default model list
- `--count <N>`: instances per model (default 1)

**Default models** (valid for both Task `model` and `agent --model`):
`composer-2.5`, `gpt-5.6-sol-high`

`gpt-5.6-terra-high` was replaced by `gpt-5.6-sol-high` on 2026-10-02. Its profile stays, so pass it with `--models` when wanted.

`grok-4.7-high` was dropped from the defaults on 2026-09-30 after timing out in all 4 of its runs, as `cursor-grok-4.6-high` was before it. `gemini-3.8-flash-high` was dropped the same day after repeated timeouts and a provider connection error. Pass either with `--models` when wanted.

Each model's prompt is rendered from its profile in [model-profiles/](model-profiles/README.md). A model without a profile runs on the shared baseline prompt, and `prepare_round.py` reports a `profile_warnings` entry for it.

---

## Shared configuration

`prepare_round.py` builds these entries (one per `(model, instance)`) into `_reviewers-config.json` and lists the output paths in its `external_outputs`:

| Field | Value |
|-------|-------|
| `model` | slug from `--models` or defaults |
| `instance` | 1..N |
| `output_path` | `<ROUND_DIR>/review-<MODEL>-<instance>.md` |
| `profile` | profile key: the slug without `-fast` and its effort suffix |
| `review_prompt_path` | `<ROUND_DIR>/_review-prompt-<profile>.md`, the complete prompt for this model (input path and excluded directories included) |
| `input_path` | `_diff.patch` (code) or plan version directory (plan/spec); informational |
| `input_type` | `diff` or `plan_dir`; informational |
| `project_root` | `PROJECT_ROOT` (not `GIT_ROOT`) |
| `exclude_dirs` | `EXCLUDE_DIRS` |

`<MODEL>` in filenames has `/` and spaces replaced with `-` (models already match `[a-zA-Z0-9._-]+`).

---

## Cursor: Task subagents (preferred)

Same parallel pattern as `/multi-model-review`, but with each model's **`_review-prompt-<profile>.md`** and **file outputs** for the synthesizer.

### Launch rules

1. Fire **all** reviewer Task calls in **one assistant turn** — internal Explore + external generalPurpose together. Never sequential.
2. Set `run_in_background: true` on every Task call.
3. Each external reviewer:
   - `subagent_type`: `generalPurpose`
   - `readonly`: `true`
   - `model`: the task's model slug
4. **Parallelism is mandatory** — do not wait for one external reviewer before starting the next.

### Subagent prompt template

The task's `review_prompt_path` already holds the complete, model-specific prompt, so the Task prompt only points at it:

```markdown
Read {review_prompt_path} and carry out the review it describes, working read-only in {PROJECT_ROOT}. Return the complete review as your final message.
```

### Capture output

When each Task subagent completes, the **orchestrator** writes its full response to `output_path` unchanged. Track status per reviewer:

| Status | Condition |
|--------|-----------|
| `success` | Non-empty output written |
| `failed` | Task error, empty output, or timeout |

If a Task launch fails (invalid model slug), retry once with the closest valid slug from Task tool feedback, then mark failed.

### Advantages over agent CLI on Cursor

- No subprocess / workspace-trust prompts
- Same model slugs as parent Agent
- Native parallel Task batching with internal Explore reviewers
- No `run_reviewers.py` dependency for the happy path

---

## Claude Code / fallback: agent CLI

Use when host is Claude Code, or Cursor with `--agent-cli`, or after Task backend exhausts retries.

`prepare_round.py` writes the config to `<ROUND_DIR>/_reviewers-config.json`:

```json
{
  "timeout_seconds": 900,
  "retry_count": 1,
  "retry_delay_seconds": 5,
  "quorum_fraction": 1.0,
  "quorum_grace_seconds": 90,
  "launch_stagger_seconds": 1.5,
  "min_output_bytes": 200,
  "tasks": [ { "...": "one object per (model, instance)" } ]
}
```

| Setting | Behaviour |
|---------|-----------|
| `timeout_seconds` | Per-attempt limit. **Timeouts are never retried** — a hung model would otherwise cost 2× the timeout. |
| `retry_count` | Retries for fast failures only (non-zero exit, an error result, or no review text at all). |
| `quorum_fraction` / `quorum_grace_seconds` | Below `1.0`, once this fraction of tasks has succeeded, stragglers get the grace period and are then killed (`status: cut_off`). The default `1.0` waits for everything: synthesis waits for the internal reviewers anyway, so a cut-off rarely saves time and discards the straggler's tokens. |
| `launch_stagger_seconds` | Delay between launches; concurrent `agent` starts race on `~/.cursor/cli-config.json.tmp`. |
| `min_output_bytes` | How long the model's last text block must be to count as the review on its own (see below). A shorter review, such as a one-line "no defects found", is kept as a success rather than retried; only empty output fails. Until 2026-10-07 anything under 200 bytes failed and was re-run in full. On 2026-09-30 gpt-5.6-terra wrote 106 bytes, was re-run, and wrote 98 bytes after 62 tool calls; both were discarded and the round lost that reviewer. On 2026-10-07 gpt-5.6-sol wrote 70 bytes and its re-run was cut off. |

Run in the background with the Bash tool's `run_in_background: true`:

```bash
python3 "${CLAUDE_SKILL_DIR:-$HOME/.claude/skills/deep-review}/scripts/run_reviewers.py" < "<ROUND_DIR>/_reviewers-config.json" > "<ROUND_DIR>/_external-results.json" 2> "<ROUND_DIR>/_external-progress.log"
```

`run_reviewers.py` sends `review_prompt_path` to `agent --print --output-format stream-json` as-is; it adds no preamble. The review file gets the text the model wrote after its last tool call. Some models (Grok 4.7 in testing) narrate between tool calls despite the prompt, and the `result` event joins all of it together; if that last block is shorter than `min_output_bytes`, the runner uses the longest block, then the joined `result`. Each reviewer's tool calls go to `<ROUND_DIR>/_log-<output stem>.jsonl`, one line per call: `t` (seconds from launch), `secs` (duration; `null` if still running when stopped), `tool`, `target` (path, pattern or command). The raw event stream is written to a temp file outside the workspace, so other reviewers can't read it, and deleted afterwards, since each file read carries the file's full contents.

`_external-results.json` holds `{status, total, succeeded, failed, results}`. Each result: `status` (`success` | `retry_success` | `failed` | `cut_off`), `output_path`, `file_size`, `duration_seconds`, optional `error`, and `telemetry`: `reported_model` (the CLI's display name), `tool_calls`, `tools` (count per tool), `last_tool`, `log_path`, and on completion `api_duration_seconds`, `usage` (tokens) and, when narration was dropped, `narration_dropped_chars`. Failed and cut-off reviewers get a short `# Review failed` / `# Review cut off` note in their output file, including their tool-call count and last tool call. Tasks are identified by `output_path`, which must be unique; `(model, instance)` may repeat (e.g. one reviewer answering two rebuttals).

Requires `agent` on PATH (`which agent`). Every agent process runs in its own process group, which is killed on timeout, cut-off or SIGTERM/SIGINT.

---

## Deliberation re-engagement (Phase 4.5)

| Backend | Action |
|---------|--------|
| **Cursor** | Task(`generalPurpose`, `readonly: true`, `model: <original model>`) with rebuttal file content; write response to `rebuttal-response-<REVIEWER>-C<N>.md` |
| **Claude Code / `--agent-cli`** | **One** background `run_reviewers.py` call whose `tasks` contain every external rebuttal: `prompt_kind: "rebuttal"`, `review_prompt_path` = rebuttal file, `output_path` = response file, original `model` / `instance`. Set `"quorum_fraction": 1.0` at the top level. |

Internal reviewers: `deep-reviewer` with `mode: rebuttal`, which writes `rebuttal-response-*.md` itself.

Launch all rebuttals for a deliberation round in **one parallel batch**.

---

## Zero-success guard

If **every** reviewer (internal + external) fails, stop before synthesis. List each failure with model/instance and reason.
