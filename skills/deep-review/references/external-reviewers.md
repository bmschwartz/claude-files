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
- `--count <N>`: instances per model (default 2)

**Default models** (valid for both Task `model` and `agent --model`):
`composer-2.5`, `gpt-5.6-terra-high`, `gemini-3.7-flash-high`

`cursor-grok-4.6-high` is no longer a default (no unique CRITICAL/IMPORTANT findings in the review history; frequent straggler). Add it with `--models` if wanted.

---

## Shared configuration

`prepare_round.py` builds these entries (one per `(model, instance)`) into `_reviewers-config.json` and lists the output paths in its `external_outputs`:

| Field | Value |
|-------|-------|
| `model` | slug from `--models` or defaults |
| `instance` | 1..N |
| `output_path` | `<ROUND_DIR>/review-<MODEL>-<instance>.md` |
| `review_prompt_path` | `<ROUND_DIR>/_review-prompt.md` |
| `input_path` | `_diff.patch` (code) or plan version directory (plan/spec) |
| `input_type` | `diff` or `plan_dir` |
| `project_root` | `PROJECT_ROOT` (not `GIT_ROOT`) |
| `exclude_dirs` | `EXCLUDE_DIRS` |

`<MODEL>` in filenames has `/` and spaces replaced with `-` (models already match `[a-zA-Z0-9._-]+`).

---

## Cursor: Task subagents (preferred)

Same parallel pattern as `/multi-model-review`, but with **`_review-prompt.md`** and **file outputs** for the synthesizer.

### Launch rules

1. Fire **all** reviewer Task calls in **one assistant turn** — internal Explore + external generalPurpose together. Never sequential.
2. Set `run_in_background: true` on every Task call.
3. Each external reviewer:
   - `subagent_type`: `generalPurpose`
   - `readonly`: `true`
   - `model`: the task's model slug
4. **Parallelism is mandatory** — do not wait for one external reviewer before starting the next.

### Subagent prompt template

Include in every external reviewer Task prompt:

```markdown
You are an external code/plan reviewer for a multi-model review pipeline.

## Workspace
- Root: {PROJECT_ROOT}
- Read and follow: {review_prompt_path}
<If input_type is diff>
- Diff file: {input_path} — read this first
</If>
<If input_type is plan_dir>
- Plan documents directory: {input_path}
</If>
<If EXCLUDE_DIRS non-empty>
- Do NOT explore: {EXCLUDE_DIRS joined}
</If>

## Rules
- Read the full prompt file at {review_prompt_path} and follow its severity rubric and output format.
- Use Read/Grep/Glob to inspect the codebase under {PROJECT_ROOT} for context.
- Do NOT write files. Return your complete review as your final message.
- Reviewer identity for synthesis: {model} instance {instance}
```

For **plan/spec** type, add: "Read all markdown files in the plan directory."

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
  "timeout_seconds": 480,
  "retry_count": 1,
  "retry_delay_seconds": 5,
  "quorum_fraction": 0.75,
  "quorum_grace_seconds": 90,
  "launch_stagger_seconds": 1.5,
  "min_output_bytes": 200,
  "tasks": [ { "...": "one object per (model, instance)" } ]
}
```

| Setting | Behaviour |
|---------|-----------|
| `timeout_seconds` | Per-attempt limit. **Timeouts are never retried** — a hung model would otherwise cost 2× the timeout. |
| `retry_count` | Retries for fast failures only (non-zero exit, output under `min_output_bytes`). |
| `quorum_fraction` / `quorum_grace_seconds` | Once this fraction of tasks has succeeded, stragglers get the grace period and are then killed (`status: cut_off`). Use `1.0` to wait for everything. |
| `launch_stagger_seconds` | Delay between launches; concurrent `agent` starts race on `~/.cursor/cli-config.json.tmp`. |
| `min_output_bytes` | Smaller outputs (e.g. a lone newline) count as failures. |

Run in the background with the Bash tool's `run_in_background: true`:

```bash
python3 "${CLAUDE_SKILL_DIR:-$HOME/.claude/skills/deep-review}/scripts/run_reviewers.py" < "<ROUND_DIR>/_reviewers-config.json" > "<ROUND_DIR>/_external-results.json" 2> "<ROUND_DIR>/_external-progress.log"
```

`_external-results.json` holds `{status, total, succeeded, failed, results}`. Each result: `status` (`success` | `retry_success` | `failed` | `cut_off`), `output_path`, `file_size`, `duration_seconds`, optional `error`. Failed and cut-off reviewers get a short `# Review failed` / `# Review cut off` note in their output file. Tasks are identified by `output_path`, which must be unique; `(model, instance)` may repeat (e.g. one reviewer answering two rebuttals).

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
