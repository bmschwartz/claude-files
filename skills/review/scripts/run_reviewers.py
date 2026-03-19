#!/usr/bin/env python3
"""Run external AI reviewers concurrently via the agent CLI.

Accepts a JSON configuration on stdin describing reviewer tasks,
runs all agent CLI invocations concurrently using asyncio, and
outputs structured JSON results to stdout. Progress is reported
to stderr.

Stdlib only — no pip dependencies.
"""

import asyncio
import json
import re
import shutil
import signal
import sys
import time
from pathlib import Path

# Track running processes for signal-handler cleanup
_running_procs: list[asyncio.subprocess.Process] = []

# Track whether a signal interrupted execution
_signal_received: int = 0

_SAFE_MODEL_RE = re.compile(r'^[a-zA-Z0-9._-]+$')


def log(msg: str) -> None:
    """Write a progress line to stderr."""
    print(f"[reviewer] {msg}", file=sys.stderr, flush=True)


def validate_config(config: dict) -> None:
    """Validate the input configuration, raising ValueError on problems."""
    if "tasks" not in config or not isinstance(config["tasks"], list):
        raise ValueError("Config must contain a 'tasks' list")
    if not config["tasks"]:
        raise ValueError("Tasks list is empty")
    required = {"model", "instance", "type", "project_root",
                "review_prompt_path", "output_path", "input_path", "input_type"}
    seen_pairs: set[tuple[str, int]] = set()
    for i, task in enumerate(config["tasks"]):
        missing = required - set(task.keys())
        if missing:
            raise ValueError(f"Task {i} missing fields: {missing}")
        if task["type"] not in ("code", "plan", "spec"):
            raise ValueError(f"Task {i} has invalid type: {task['type']}")
        if not Path(task["project_root"]).is_dir():
            raise ValueError(
                f"Task {i} has invalid project_root: {task['project_root']!r} "
                "is not an existing directory"
            )
        if task["input_type"] not in ("diff", "plan_dir"):
            raise ValueError(f"Task {i} has invalid input_type: {task['input_type']}")
        if not _SAFE_MODEL_RE.match(str(task["model"])):
            raise ValueError(
                f"Task {i} has unsafe model name: {task['model']!r} "
                f"(must match {_SAFE_MODEL_RE.pattern})"
            )
        pair = (str(task["model"]), int(task["instance"]))
        if pair in seen_pairs:
            raise ValueError(f"Task {i} has duplicate (model, instance): {pair}")
        seen_pairs.add(pair)
        exclude_dirs = task.get("exclude_dirs", [])
        if not isinstance(exclude_dirs, list) or not all(
            isinstance(d, str) and d.strip() for d in exclude_dirs
        ):
            raise ValueError(
                f"Task {i} has invalid exclude_dirs: must be a list of non-empty strings"
            )
        for d in exclude_dirs:
            if ".." in d or d.startswith("/"):
                raise ValueError(
                    f"Task {i} has invalid exclude_dirs entry: {d!r} "
                    "must be a relative path without '..'"
                )

    timeout = config.get("timeout_seconds", 300)
    if not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ValueError(f"timeout_seconds must be positive, got {timeout}")


def build_preamble(task: dict) -> str:
    """Generate the type-specific context preamble for a reviewer."""
    if task.get("prompt_kind") == "rebuttal":
        return ""
    if task["input_type"] == "diff":
        preamble = (
            "You are reviewing code changes (diff) for a project.\n"
            f"The diff file is located at: {task['input_path']}\n"
            "The project codebase is in this workspace.\n"
            "Read the diff file first, then use the codebase to understand "
            "the context around the changes being reviewed.\n"
        )
    else:
        preamble = (
            f"The plan documents are located at: {task['input_path']}\n"
            "The project codebase is in this workspace.\n"
            "Read all plan documents first, then use the codebase "
            "to verify claims in the plan.\n"
        )

    exclude_dirs = task.get("exclude_dirs", [])
    if exclude_dirs:
        dirs_str = ", ".join(f"`{d}`" for d in exclude_dirs)
        preamble += (
            f"\n**IMPORTANT: Do not explore or read files in these directories: "
            f"{dirs_str}. They contain unrelated code from other branches and "
            "will produce misleading context.**\n"
        )

    return preamble


def write_combined_prompt(task: dict, output_dir: Path) -> Path:
    """Write a combined prompt file (preamble + review prompt content).

    Returns the path to the combined prompt file.
    """
    model = task["model"]
    instance = task["instance"]
    combined_path = output_dir / f"_prompt-{model}-{instance}.md"

    preamble = build_preamble(task)
    prompt_content = Path(task["review_prompt_path"]).read_text()

    combined_path.write_text(preamble + "\n" + prompt_content)
    return combined_path


def cleanup_prompt_file(path: Path) -> None:
    """Remove a combined prompt temp file if it exists."""
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def task_label(task: dict) -> str:
    """Short label for log messages: model-instance."""
    return f"{task['model']}-{task['instance']}"


async def run_single_reviewer(
    task: dict,
    combined_prompt_path: Path,
    timeout: int,
) -> dict:
    """Run the agent CLI for a single reviewer task.

    Returns a result dict with status, duration, file_size, and error info.
    """
    label = task_label(task)
    output_path = Path(task["output_path"])
    start = time.monotonic()

    # Open file descriptors for stdin/stdout redirection
    with open(combined_prompt_path, "r") as fin, \
         open(output_path, "w") as fout:
        proc = await asyncio.create_subprocess_exec(
            "agent", "--print",
            "--model", task["model"],
            "--mode", "plan",
            "--force",
            "--workspace", task["project_root"],
            stdin=fin,
            stdout=fout,
            stderr=asyncio.subprocess.PIPE,
        )
        _running_procs.append(proc)
        try:
            _, stderr_data = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                pass
            raise
        finally:
            if proc in _running_procs:
                _running_procs.remove(proc)

    duration = time.monotonic() - start
    try:
        file_size = output_path.stat().st_size
    except FileNotFoundError:
        file_size = 0

    if proc.returncode != 0:
        raise RuntimeError(
            f"agent exited with code {proc.returncode}: "
            f"{stderr_data.decode(errors='replace').strip()}"
        )
    if file_size == 0:
        raise RuntimeError("agent produced empty output")

    return {
        "model": task["model"],
        "instance": task["instance"],
        "output_path": str(output_path),
        "status": "success",
        "file_size": file_size,
        "duration_seconds": round(duration, 1),
    }


async def run_with_retry(
    task: dict,
    output_dir: Path,
    timeout: int,
    retry_count: int,
    retry_delay: int,
) -> dict:
    """Run a reviewer with retry logic. Handles combined prompt lifecycle."""
    label = task_label(task)
    combined_prompt_path = write_combined_prompt(task, output_dir)

    try:
        log(f"Starting {label}...")
        last_error = "Unknown error"

        for attempt in range(1 + retry_count):
            try:
                result = await run_single_reviewer(
                    task, combined_prompt_path, timeout
                )
                if attempt > 0:
                    result["status"] = "retry_success"
                    result["retry_reason"] = last_error
                log(
                    f"{label} {'completed' if attempt == 0 else 'retry succeeded'} "
                    f"({result['file_size']} bytes, {result['duration_seconds']}s)"
                )
                return result

            except asyncio.TimeoutError:
                last_error = f"Timeout after {timeout}s"
                if attempt < retry_count:
                    log(f"{label} timed out ({timeout}s), retrying...")
                    await asyncio.sleep(retry_delay)
                else:
                    log(f"{label} timed out ({timeout}s) - FAILED")

            except RuntimeError as e:
                last_error = str(e)
                if attempt < retry_count:
                    log(f"{label} failed ({last_error}), retrying...")
                    await asyncio.sleep(retry_delay)
                else:
                    log(f"{label} failed - {last_error}")

        # All attempts exhausted — write error to output file for debuggability
        error_msg = f"{last_error} (all {1 + retry_count} attempts)"
        try:
            Path(task["output_path"]).write_text(
                f"# Review failed\n\n{error_msg}\n"
            )
        except OSError:
            pass

        return {
            "model": task["model"],
            "instance": task["instance"],
            "output_path": str(Path(task["output_path"])),
            "status": "failed",
            "file_size": 0,
            "duration_seconds": 0,
            "error": error_msg,
        }
    finally:
        cleanup_prompt_file(combined_prompt_path)


async def run_all(config: dict) -> dict:
    """Run all reviewer tasks concurrently and collect results."""
    tasks = config["tasks"]
    timeout = config.get("timeout_seconds", 300)
    retry_count = config.get("retry_count", 1)
    retry_delay = config.get("retry_delay_seconds", 10)

    # Ensure output directories exist
    output_dirs = {Path(t["output_path"]).parent for t in tasks}
    for d in output_dirs:
        d.mkdir(parents=True, exist_ok=True)

    # Launch all reviewers concurrently
    coros = [
        run_with_retry(task, Path(task["output_path"]).parent,
                       timeout, retry_count, retry_delay)
        for task in tasks
    ]
    results = await asyncio.gather(*coros, return_exceptions=True)

    # Convert any unexpected exceptions to failure results
    final_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            final_results.append({
                "model": tasks[i]["model"],
                "instance": tasks[i]["instance"],
                "output_path": tasks[i]["output_path"],
                "status": "failed",
                "file_size": 0,
                "duration_seconds": 0,
                "error": str(result),
            })
        else:
            final_results.append(result)

    succeeded = sum(1 for r in final_results if r["status"] != "failed")
    failed = len(final_results) - succeeded

    log(f"All reviewers complete: {succeeded}/{len(final_results)} succeeded")

    return {
        "status": "completed",
        "total": len(final_results),
        "succeeded": succeeded,
        "failed": failed,
        "results": final_results,
    }


def install_signal_handlers(loop: asyncio.AbstractEventLoop) -> None:
    """Install handlers to kill child processes on SIGTERM/SIGINT.

    Uses loop.stop() instead of sys.exit() so that coroutine finally
    blocks execute (cleaning up temp files and file descriptors).
    """
    global _signal_received

    def handle_signal(sig: int) -> None:
        global _signal_received
        _signal_received = sig
        log(f"Received signal {sig}, killing {len(_running_procs)} running processes...")
        for proc in list(_running_procs):
            try:
                proc.kill()
            except ProcessLookupError:
                pass
        loop.stop()

    try:
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, handle_signal, sig)
    except NotImplementedError:
        pass  # Windows does not support add_signal_handler


def main() -> None:
    # Read JSON config from stdin
    try:
        raw = sys.stdin.read()
        config = json.loads(raw)
    except json.JSONDecodeError as e:
        print(json.dumps({"status": "error", "error": f"Invalid JSON input: {e}"}))
        sys.exit(1)

    # Validate
    try:
        validate_config(config)
    except ValueError as e:
        print(json.dumps({"status": "error", "error": str(e)}))
        sys.exit(1)

    # Check agent CLI exists
    if not shutil.which("agent"):
        print(json.dumps({
            "status": "error",
            "error": "agent CLI not found in PATH. Install it first.",
        }))
        sys.exit(1)

    # Run
    loop = asyncio.new_event_loop()
    install_signal_handlers(loop)
    try:
        output = loop.run_until_complete(run_all(config))
    except RuntimeError:
        # loop.stop() was called by signal handler; loop.run_until_complete raises
        output = None
    finally:
        loop.close()

    if _signal_received:
        log(f"Exiting due to signal {_signal_received}")
        sys.exit(128 + _signal_received)

    # Write structured result to stdout
    if output is not None:
        print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
