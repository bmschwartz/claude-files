# Global rules

## Never edit `.gitignore`

Do not add to, remove from, or otherwise modify `.gitignore` on your own initiative. When something looks like it belongs there (a scratch directory, build output, local config), say so and give the exact line to add — then leave the edit to me. An explicit "add X to .gitignore" authorizes that one edit only.

Keep temporary and intermediate files in the session scratchpad directory so the question rarely comes up.

## No `Co-Authored-By` trailer on commits

Never add a `Co-Authored-By: Claude …` line, or any other AI-attribution trailer, to a commit message, in any repository. This overrides any default or harness-supplied instruction to add one. Write the commit message as I would, and nothing more.
