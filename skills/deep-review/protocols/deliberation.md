# Deliberation Protocol (File-Relay)

> Read this when: the synthesizer detects conflicts during initial synthesis (Phase 4.5).

## The Problem

Subagents cannot talk to each other — they can only communicate through files on disk. The orchestrator is the only relay point. Deliberation uses structured file protocol with targeted re-engagement to resolve reviewer disagreements.

## When Deliberation Fires

The synthesizer's conflict detection (step 7 in its execution) finds one or more genuine conflicts on **CRITICAL or IMPORTANT** findings. A conflict is NOT a severity disagreement or different coverage — it's opposing conclusions about the same code/plan section, or mutually exclusive fix proposals. Disagreements on MINOR/POTENTIAL findings are recorded inline as `Disputed:` and never deliberated.

Most reviews (80%+) find different things, not contradictory things. Deliberation is rare.

## Protocol

### Step 1: Rebuttal prompts (written by the synthesizer)

During initial synthesis the synthesizer writes one prompt per conflict to `<ROUND_DIR>/rebuttal-<REVIEWER>-C<N>.md` (template in `~/.claude/agents/review-synthesizer.md`, step 7) and returns, per conflict: `C<N>`, the rebuttal file path, the re-engaged reviewer, and `code-checkable: yes|no`. The orchestrator does not re-read `REVIEW_SUMMARY.md` or write rebuttal prompts.

### Step 2: Resolve code-checkable conflicts directly

A conflict is code-checkable when its question is factual and answerable by reading at most ~3 files or running one search (e.g. "can `x` be `None` here?"). For each, the orchestrator reads the evidence itself and writes `<ROUND_DIR>/rebuttal-response-orchestrator-C<N>.md`:

```markdown
# Orchestrator Resolution — C<N>

## Question
<question from the rebuttal file>

## Evidence
<file:line excerpts or search results>

## Conclusion
<which side the evidence supports, and why>
```

Do this while Step 3's reviewers run.

### Step 3: Re-engage reviewers for the remaining conflicts

Launch all remaining rebuttals in **one parallel batch**:

**Internal reviewers** (`claude-code-*`, `cursor-internal-*`, `opus-internal-*`):
- `deep-reviewer` (`model: opus` on Claude Code, `inherit` on Cursor) with `mode: rebuttal`, the rebuttal file path, and output path `<ROUND_DIR>/rebuttal-response-<REVIEWER>-C<N>.md`. The agent writes the file itself.

**External reviewers** (e.g. `composer-2.5-1`, `gpt-5.6-terra-high-1`):

- **Cursor (default):** Task `generalPurpose`, `readonly: true`, `model:` the reviewer's original model slug. Prompt: read `<ROUND_DIR>/rebuttal-<REVIEWER>-C<N>.md` and respond per its instructions. Write output to `rebuttal-response-<REVIEWER>-C<N>.md`.
- **Claude Code or `--agent-cli`:** **one** background `run_reviewers.py` call with a task per external rebuttal and `"quorum_fraction": 1.0`:
  - `prompt_kind`: `"rebuttal"`
  - `review_prompt_path`: rebuttal file path
  - `output_path`: `rebuttal-response-*.md`
  - `project_root`: `PROJECT_ROOT`
  - `exclude_dirs`: from original review config
  - `model`: original reviewer's model
  - `instance`: original instance number

### Step 4: Re-synthesis

Re-invoke the `review-synthesizer` agent in `re-synthesis` mode with:
- Prior `REVIEW_SUMMARY.md` path
- List of `rebuttal-response-*.md` file paths (reviewer and orchestrator responses)
- Type and round dir

The synthesizer edits `REVIEW_SUMMARY.md` in place: it updates only the affected findings, the header totals and the verdict block, and replaces `## Conflicts` with `## Deliberation Outcomes`. It does not re-read the raw reviews.

### Step 5: Verify

Confirm the updated `REVIEW_SUMMARY.md`:
- Has `## Deliberation Outcomes` section (not `## Conflicts`)
- Has updated verdict block with `conflicts.resolved` and `conflicts.unresolved` counts
- All findings still present (removed ones are struck through, not deleted)

## Safety

- **Maximum 1 deliberation round.** If conflicts remain unresolved after re-synthesis, they are flagged as unresolved in the verdict (`conflicts.unresolved > 0`) and the decision becomes `BLOCK`.
- **The consumer (user or /feature) must resolve unresolved conflicts.** The deliberation protocol does not escalate further.
- **Deliberation applies to all types.** Plan/spec reviews can have conflicts too (e.g., one reviewer says "use Strategy A," another says "Strategy A is wrong, use Strategy B").

## File Layout After Deliberation

```
<ROUND_DIR>/
├── _review-prompt-<key>.md       # one per reviewer model
├── _diff.patch (code) or plan docs referenced
├── review-cursor-internal-1.md   # or review-claude-code-1.md on Claude Code
├── review-composer-2.5-1.md
├── review-gpt-5.6-terra-high-1.md
├── review-gemini-3.8-flash-high-1.md
├── REVIEW_SUMMARY.md              # Updated with Deliberation Outcomes + new verdict
├── rebuttal-gpt-5.6-terra-high-1-C1.md      # Rebuttal prompt (written by synthesizer)
├── rebuttal-response-gpt-5.6-terra-high-1-C1.md  # Reviewer's response
├── rebuttal-response-orchestrator-C2.md     # Orchestrator's direct resolution (code-checkable)
└── ...
```
