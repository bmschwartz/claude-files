#!/usr/bin/env python3
"""
Execute multiple external reviewers in parallel using the `agent` CLI.

Replaces the per-model review-executor subagent spawning with a single
Python process that fans out to all requested models concurrently.

Usage:
    python run_reviewers.py \
        --type code \
        --models "gpt-5.4-high-fast,composer-1.5" \
        --review-prompt /path/to/_review-prompt.md \
        --diff /path/to/_diff.patch \
        --output-dir /path/to/round-dir \
        --workspace /path/to/project \
        [--count 1] \
        [--timeout 300]
"""

import argparse
import asyncio
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

ReviewType = Literal["code", "plan", "spec"]


# -- Data types ---------------------------------------------------------------


@dataclass
class ReviewJob:
    model: str
    instance: int
    review_type: ReviewType
    prompt_path: Path
    input_path: Path  # diff path (code) or plan dir (plan/spec)
    output_path: Path
    workspace: Path
    timeout: int


@dataclass
class ReviewResult:
    model: str
    instance: int
    output_path: Path
    success: bool
    duration_secs: float
    file_size: int = 0
    error: str = ""
    retried: bool = False


# -- Preambles ----------------------------------------------------------------


def preamble_for(review_type: ReviewType, input_path: Path) -> str:
    if review_type == "code":
        return (
            f"You are reviewing code changes (diff) for a project.\n"
            f"The diff file is located at: {input_path}\n"
            f"The project codebase is in this workspace.\n"
            f"Read the diff file first, then use the codebase to understand "
            f"the context around the changes being reviewed.\n"
        )
    return (
        f"The plan documents are located at: {input_path}\n"
        f"The project codebase is in this workspace.\n"
        f"Read all plan documents first, then use the codebase to verify "
        f"claims in the plan.\n"
    )


# -- CLI validation -----------------------------------------------------------


REQUIRED_FLAGS = ["--model", "--print", "--workspace", "--mode", "--force"]


def validate_agent_cli() -> None:
    agent_bin = shutil.which("agent")
    if agent_bin is None:
        sys.exit("error: `agent` CLI not found on PATH")


# -- Single review execution --------------------------------------------------


async def run_single_review(job: ReviewJob) -> ReviewResult:
    """Run a single agent CLI invocation with one retry on failure."""
    # Build combined prompt in a temp file
    review_prompt = job.prompt_path.read_text()
    preamble = preamble_for(job.review_type, job.input_path)
    combined = f"{preamble}\n{review_prompt}"

    combined_file = job.output_path.parent / f"_prompt-{job.model}-{job.instance}.md"
    combined_file.write_text(combined)

    async def attempt() -> tuple[int, float]:
        """Execute the agent CLI, return (exit_code, elapsed_secs)."""
        stdin_fh = combined_file.open("r")
        stdout_fh = job.output_path.open("w")

        start = asyncio.get_event_loop().time()
        proc = await asyncio.create_subprocess_exec(
            "agent",
            "--print",
            "--model", job.model,
            "--mode", "plan",
            "--force",
            "--workspace", str(job.workspace),
            stdin=stdin_fh,
            stdout=stdout_fh,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            await asyncio.wait_for(proc.wait(), timeout=job.timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            elapsed = asyncio.get_event_loop().time() - start
            stdout_fh.close()
            stdin_fh.close()
            return -1, elapsed

        elapsed = asyncio.get_event_loop().time() - start
        stdout_fh.close()
        stdin_fh.close()
        return proc.returncode, elapsed

    retried = False

    # First attempt
    exit_code, elapsed = await attempt()
    output_ok = job.output_path.exists() and job.output_path.stat().st_size > 0

    # Retry once on failure
    if exit_code != 0 or not output_ok:
        retried = True
        await asyncio.sleep(10)
        exit_code, elapsed = await attempt()
        output_ok = job.output_path.exists() and job.output_path.stat().st_size > 0

    # Cleanup temp prompt
    combined_file.unlink(missing_ok=True)

    if exit_code != 0 or not output_ok:
        error_detail = f"exit_code={exit_code}, output_exists={job.output_path.exists()}"
        if exit_code == -1:
            error_detail = f"timeout after {job.timeout}s"
        return ReviewResult(
            model=job.model,
            instance=job.instance,
            output_path=job.output_path,
            success=False,
            duration_secs=elapsed,
            error=error_detail,
            retried=retried,
        )

    return ReviewResult(
        model=job.model,
        instance=job.instance,
        output_path=job.output_path,
        success=True,
        duration_secs=elapsed,
        file_size=job.output_path.stat().st_size,
        retried=retried,
    )


# -- Parallel orchestration ---------------------------------------------------


async def run_all_reviews(jobs: list[ReviewJob]) -> list[ReviewResult]:
    """Fan out all review jobs concurrently and collect results."""
    tasks = [asyncio.create_task(run_single_review(job)) for job in jobs]
    return await asyncio.gather(*tasks)


# -- CLI entrypoint -----------------------------------------------------------


def build_jobs(args: argparse.Namespace) -> list[ReviewJob]:
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    jobs = []
    for model in models:
        for instance in range(1, args.count + 1):
            output_path = output_dir / f"review-{model}-{instance}.md"
            jobs.append(ReviewJob(
                model=model,
                instance=instance,
                review_type=args.type,
                prompt_path=Path(args.review_prompt),
                input_path=Path(args.diff if args.type == "code" else args.plan_dir),
                output_path=output_path,
                workspace=Path(args.workspace),
                timeout=args.timeout,
            ))
    return jobs


def print_report(results: list[ReviewResult]) -> None:
    succeeded = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)

    print(f"\n{'='*60}")
    print(f"Review execution complete: {succeeded} succeeded, {failed} failed")
    print(f"{'='*60}")

    for r in results:
        status = "OK" if r.success else "FAILED"
        retry_tag = " (retried)" if r.retried else ""
        size_tag = f" [{r.file_size} bytes]" if r.success else f" [{r.error}]"
        print(f"  {status} {r.model}-{r.instance}  {r.duration_secs:.1f}s{retry_tag}{size_tag}")
        print(f"        -> {r.output_path}")

    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run multiple external model reviews in parallel via the agent CLI."
    )
    parser.add_argument("--type", choices=["code", "plan", "spec"], required=True)
    parser.add_argument("--models", required=True, help="Comma-separated model names")
    parser.add_argument("--review-prompt", required=True, help="Path to _review-prompt.md")
    parser.add_argument("--diff", help="Path to _diff.patch (required for --type code)")
    parser.add_argument("--plan-dir", help="Path to plan directory (required for --type plan/spec)")
    parser.add_argument("--output-dir", required=True, help="Review round output directory")
    parser.add_argument("--workspace", required=True, help="Project root for agent --workspace")
    parser.add_argument("--count", type=int, default=1, help="Instances per model (default: 1)")
    parser.add_argument("--timeout", type=int, default=300, help="Per-review timeout in seconds")
    args = parser.parse_args()

    # Validate inputs
    if args.type == "code" and not args.diff:
        parser.error("--diff is required when --type is code")
    if args.type in ("plan", "spec") and not args.plan_dir:
        parser.error("--plan-dir is required when --type is plan or spec")

    validate_agent_cli()

    jobs = build_jobs(args)
    if not jobs:
        print("No review jobs to run.")
        return 0

    print(f"Launching {len(jobs)} review(s) across {args.models} ...")
    results = asyncio.run(run_all_reviews(jobs))
    print_report(results)

    # Exit non-zero if any review failed
    return 0 if all(r.success for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
