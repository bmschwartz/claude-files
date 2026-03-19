# Deliberation Protocol (File-Relay)

> Read this when: the synthesizer detects conflicts during initial synthesis (Phase 4.5).

## The Problem

Subagents cannot talk to each other — they can only communicate through files on disk. The orchestrator is the only relay point. Deliberation uses structured file protocol with targeted re-engagement to resolve reviewer disagreements.

## When Deliberation Fires

The synthesizer's conflict detection (step 7 in its execution) finds one or more genuine conflicts. A conflict is NOT a severity disagreement or different coverage — it's opposing conclusions about the same code/plan section, or mutually exclusive fix proposals.

Most reviews (80%+) find different things, not contradictory things. Deliberation is rare.

## Protocol

### Step 1: Read Conflicts

Read the `## Conflicts` section from `REVIEW_SUMMARY.md`. Each conflict contains:
- Location (file:line or document section)
- Side A: reviewer name, confidence, position, rationale
- Side B: reviewer name, confidence, position, rationale
- Re-engage target: which reviewer to re-engage
- Question: specific question to resolve the disagreement

### Step 2: Write Rebuttal Prompts

For each conflict `C<N>`, write a rebuttal prompt file:

```
<ROUND_DIR>/rebuttal-<REVIEWER>-C<N>.md
```

Content:
```markdown
# Rebuttal Request

## Context
Another reviewer disagrees with your finding. Please respond to the specific question below.

## Your Original Position
<Side from the re-engaged reviewer — their exact finding and rationale>

## Opposing Position
<The other side's finding and rationale>

## Question
<The specific question from the conflict record>

## Instructions
- Respond to this specific question ONLY
- Do NOT perform a full re-review
- Reference specific code/plan evidence to support your response
- If you concede the point, say so clearly
- If you maintain your position, explain what the opposing reviewer missed
```

### Step 3: Re-engage Targeted Reviewers

For each rebuttal prompt:

**Internal reviewers (opus-internal, claude-code):** Launch an `Explore` agent with the rebuttal prompt file. Capture output and write to:
```
<ROUND_DIR>/rebuttal-response-<REVIEWER>-C<N>.md
```

**External reviewers:** Build a single-task JSON config for `run_reviewers.py` with the rebuttal prompt file as `review_prompt_path` and the rebuttal-response path as `output_path`. Use `PROJECT_ROOT` (not `GIT_ROOT`) for `project_root` and include `exclude_dirs` from the original review config. Run via `python3 "${CLAUDE_SKILL_DIR}/scripts/run_reviewers.py"`. Parse the JSON result to confirm success.

### Step 4: Re-synthesis

Re-invoke the `review-synthesizer` agent in `re-synthesis` mode with:
- Prior `REVIEW_SUMMARY.md` path
- List of `rebuttal-response-*.md` file paths
- All original inputs (type, round dir, review files, diff/plan path)

The synthesizer reads rebuttals, resolves conflicts, updates affected findings, replaces `## Conflicts` with `## Deliberation Outcomes`, and regenerates the verdict block.

### Step 5: Verify

Confirm the updated `REVIEW_SUMMARY.md`:
- Has `## Deliberation Outcomes` section (not `## Conflicts`)
- Has updated verdict block with `conflicts.resolved` and `conflicts.unresolved` counts
- All findings still present (no dropped findings)

## Safety

- **Maximum 1 deliberation round.** If conflicts remain unresolved after re-synthesis, they are flagged as unresolved in the verdict (`conflicts.unresolved > 0`) and the decision becomes `BLOCK`.
- **The consumer (user or /feature) must resolve unresolved conflicts.** The deliberation protocol does not escalate further.
- **Deliberation applies to all types.** Plan/spec reviews can have conflicts too (e.g., one reviewer says "use Strategy A," another says "Strategy A is wrong, use Strategy B").

## File Layout After Deliberation

```
<ROUND_DIR>/
├── _review-prompt.md
├── _diff.patch (code) or plan docs referenced
├── review-claude-code-1.md
├── review-opus-4.6-1.md
├── review-gpt-5.4-1.md
├── REVIEW_SUMMARY.md              # Updated with Deliberation Outcomes + new verdict
├── rebuttal-opus-4.6-1-C1.md      # Rebuttal prompt sent to reviewer
├── rebuttal-response-opus-4.6-1-C1.md  # Reviewer's response
└── ...
```
