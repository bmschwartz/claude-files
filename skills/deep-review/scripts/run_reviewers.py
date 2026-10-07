#!/usr/bin/env python3
"""Run external AI reviewers concurrently via the agent CLI.

Accepts a JSON configuration on stdin describing reviewer tasks,
runs all agent CLI invocations concurrently using asyncio, and
outputs structured JSON results to stdout. Progress is reported
to stderr.

Each task's review_prompt_path is sent to the agent verbatim; it is
already the complete prompt for that model (prepare_round.py renders it).
The agent runs with --output-format stream-json. The review is the text the
model wrote after its last tool call (narration between tool calls is
dropped; see review_text), and each reviewer's tool calls are kept as a
compact log (_log-<output stem>.jsonl) and summarised in its result, so a
timed-out or cut-off reviewer still shows how far it got.

Launches are staggered to avoid the agent CLI's config-file rename
race. Timeouts are not retried; only fast failures are. With
quorum_fraction below 1 (the default is 1: wait for every task),
once that fraction of the tasks have succeeded, stragglers get
quorum_grace_seconds to finish and are then cut off.

Stdlib only — no pip dependencies.
"""

import asyncio
import json
import math
import os
import re
import shutil
import signal
import sys
import tempfile
import time
from pathlib import Path

# Track running processes for signal-handler cleanup
_running_procs: list[asyncio.subprocess.Process] = []

# Track whether a signal interrupted execution
_signal_received: int = 0

_SAFE_MODEL_RE = re.compile(r'^[a-zA-Z0-9._-]+$')

DEFAULT_TIMEOUT_SECONDS = 900
DEFAULT_RETRY_COUNT = 1
DEFAULT_RETRY_DELAY_SECONDS = 5
DEFAULT_QUORUM_FRACTION = 1.0
DEFAULT_QUORUM_GRACE_SECONDS = 90
DEFAULT_LAUNCH_STAGGER_SECONDS = 1.5
DEFAULT_MIN_OUTPUT_BYTES = 200
TARGET_ARG_KEYS = ("path", "pattern", "query", "command", "globPattern", "targetDirectory", "url")


def log(msg: str) -> None:
    """Write a progress line to stderr."""
    print(f"[reviewer] {msg}", file=sys.stderr, flush=True)


def validate_config(config: dict) -> None:
    """Validate the input configuration, raising ValueError on problems."""
    if "tasks" not in config or not isinstance(config["tasks"], list):
        raise ValueError("Config must contain a 'tasks' list")
    if not config["tasks"]:
        raise ValueError("Tasks list is empty")
    required = {"model", "instance", "project_root", "review_prompt_path", "output_path"}
    seen_outputs: set[str] = set()
    for i, task in enumerate(config["tasks"]):
        missing = required - set(task.keys())
        if missing:
            raise ValueError(f"Task {i} missing fields: {missing}")
        if task.get("type", "code") not in ("code", "plan", "spec"):
            raise ValueError(f"Task {i} has invalid type: {task['type']}")
        if not Path(task["review_prompt_path"]).is_file():
            raise ValueError(
                f"Task {i} review_prompt_path does not exist: {task['review_prompt_path']!r}"
            )
        if not Path(task["project_root"]).is_dir():
            raise ValueError(
                f"Task {i} has invalid project_root: {task['project_root']!r} "
                "is not an existing directory"
            )
        if not _SAFE_MODEL_RE.match(str(task["model"])):
            raise ValueError(
                f"Task {i} has unsafe model name: {task['model']!r} "
                f"(must match {_SAFE_MODEL_RE.pattern})"
            )
        output_path = str(Path(task["output_path"]).resolve())
        if output_path in seen_outputs:
            raise ValueError(f"Task {i} has duplicate output_path: {output_path}")
        seen_outputs.add(output_path)
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

    timeout = config.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)
    if not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ValueError(f"timeout_seconds must be positive, got {timeout}")
    quorum = config.get("quorum_fraction", DEFAULT_QUORUM_FRACTION)
    if not isinstance(quorum, (int, float)) or not 0 < quorum <= 1:
        raise ValueError(f"quorum_fraction must be in (0, 1], got {quorum}")
    for key in ("quorum_grace_seconds", "launch_stagger_seconds",
                "min_output_bytes", "retry_count", "retry_delay_seconds"):
        value = config.get(key, 0)
        if not isinstance(value, (int, float)) or value < 0:
            raise ValueError(f"{key} must be a non-negative number, got {value}")


def tool_entry(tool_call: dict, project_root: str) -> tuple[str, str]:
    """(tool name, target) for a stream-json tool_call payload."""
    name = next((k for k in tool_call if k.endswith("ToolCall")), "unknown")
    args = tool_call.get(name, {}).get("args", {}) if isinstance(tool_call.get(name), dict) else {}
    target = next((str(args[k]) for k in TARGET_ARG_KEYS if args.get(k)), "")
    if target.startswith(project_root.rstrip("/") + "/"):
        target = target[len(project_root.rstrip("/")) + 1:]
    return name.removesuffix("ToolCall"), target[:200]


def summarize_events(raw_path: Path, log_path: Path, task: dict,
                     started_ms: int) -> tuple[dict, dict | None, list[str]]:
    """Turn the raw stream-json output into a compact tool log and a summary.

    Returns (telemetry, result_event, text_segments), where text_segments are
    the model's text blocks split at each tool call. Tolerates a truncated
    last line, which is what a killed process leaves behind.
    """
    started: dict[str, tuple[int, str, str]] = {}
    entries: list[dict] = []
    tools: dict[str, int] = {}
    segments: list[str] = [""]
    result_event = None
    reported_model = None
    try:
        lines = raw_path.read_text(errors="replace").splitlines()
    except FileNotFoundError:
        lines = []
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind, subtype = event.get("type"), event.get("subtype")
        if kind == "system" and subtype == "init":
            reported_model = event.get("model")
        elif kind == "assistant":
            content = event.get("message", {}).get("content", [])
            segments[-1] += "".join(c.get("text", "") for c in content if isinstance(c, dict))
        elif kind == "tool_call" and subtype == "started":
            if segments[-1].strip():
                segments.append("")
            name, target = tool_entry(event.get("tool_call", {}), task["project_root"])
            started[event.get("call_id", "")] = (event.get("timestamp_ms", started_ms), name, target)
            tools[name] = tools.get(name, 0) + 1
        elif kind == "tool_call" and subtype == "completed":
            begin, name, target = started.pop(
                event.get("call_id", ""), (event.get("timestamp_ms", started_ms), "unknown", ""))
            entries.append({
                "t": round((begin - started_ms) / 1000, 1),
                "secs": round((event.get("timestamp_ms", begin) - begin) / 1000, 1),
                "tool": name,
                "target": target,
            })
        elif kind == "result":
            result_event = event
    for begin, name, target in started.values():  # still running when the process stopped
        entries.append({"t": round((begin - started_ms) / 1000, 1), "secs": None,
                        "tool": name, "target": target})
    entries.sort(key=lambda e: e["t"])
    log_path.write_text("".join(json.dumps(e) + "\n" for e in entries))
    telemetry = {
        "reported_model": reported_model,
        "tool_calls": sum(tools.values()),
        "tools": tools,
        "last_tool": f"{entries[-1]['tool']} {entries[-1]['target']}".strip() if entries else None,
        "log_path": str(log_path),
    }
    if result_event:
        telemetry["api_duration_seconds"] = round(result_event.get("duration_api_ms", 0) / 1000, 1)
        telemetry["usage"] = result_event.get("usage")
    return telemetry, result_event, [seg.strip() for seg in segments if seg.strip()]


def review_text(result_event: dict, segments: list[str], min_bytes: int) -> str:
    """The review: the text after the last tool call.

    Some models narrate between tool calls despite the prompt, and the result
    event joins every text block together. Prefer the final block, then the
    longest, then the joined result, taking the first that is long enough.
    """
    joined = str(result_event.get("result", "")).strip()
    for candidate in (segments[-1:], [max(segments, key=len)] if segments else []):
        if candidate and len(candidate[0].encode()) >= min_bytes:
            return candidate[0]
    return joined


def task_label(task: dict) -> str:
    """Short label for log messages: the output file stem."""
    return Path(task["output_path"]).stem


def kill_process_group(proc: asyncio.subprocess.Process) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        try:
            proc.kill()
        except ProcessLookupError:
            pass


def failure_result(task: dict, status: str, error: str, telemetry: dict | None = None) -> dict:
    result = {
        "model": task["model"],
        "instance": task["instance"],
        "output_path": str(Path(task["output_path"])),
        "status": status,
        "file_size": 0,
        "duration_seconds": 0,
        "error": error,
    }
    if telemetry:
        result["telemetry"] = telemetry
    return result


def write_failure_note(task: dict, heading: str, error: str, telemetry: dict | None = None) -> None:
    note = f"# {heading}\n\n{error}\n"
    if telemetry and telemetry.get("tool_calls"):
        note += (
            f"\nTool calls before it stopped: {telemetry['tool_calls']} "
            f"(last: {telemetry['last_tool']}). Full log: {telemetry['log_path']}\n"
        )
    try:
        Path(task["output_path"]).write_text(note)
    except OSError:
        pass


async def run_single_reviewer(
    task: dict,
    timeout: int,
    min_output_bytes: int,
    telemetry: dict,
) -> dict:
    """Run the agent CLI for a single reviewer task.

    Fills `telemetry` in place (also on timeout or cancellation) and returns a
    result dict with status, duration and file_size.
    """
    output_path = Path(task["output_path"])
    log_path = output_path.with_name(f"_log-{output_path.stem}.jsonl")
    # The raw stream stays outside the workspace: other reviewers must not read it.
    fd, raw_name = tempfile.mkstemp(prefix=f"deep-review-{output_path.stem}-", suffix=".jsonl")
    os.close(fd)
    raw_path = Path(raw_name)
    start = time.monotonic()
    started_ms = int(time.time() * 1000)

    try:
        with open(task["review_prompt_path"], "r") as fin, open(raw_path, "w") as fout:
            proc = await asyncio.create_subprocess_exec(
                "agent", "--print",
                "--output-format", "stream-json",
                "--model", task["model"],
                "--mode", "ask",
                "--force",
                "--trust",
                "--workspace", task["project_root"],
                stdin=fin,
                stdout=fout,
                stderr=asyncio.subprocess.PIPE,
                start_new_session=True,
            )
            _running_procs.append(proc)
            try:
                _, stderr_data = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except (asyncio.TimeoutError, asyncio.CancelledError):
                kill_process_group(proc)
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    pass
                raise
            finally:
                if proc in _running_procs:
                    _running_procs.remove(proc)
    finally:
        summary, result_event, segments = summarize_events(raw_path, log_path, task, started_ms)
        telemetry.clear()
        telemetry.update(summary)
        raw_path.unlink(missing_ok=True)

    duration = time.monotonic() - start
    if proc.returncode != 0:
        raise RuntimeError(
            f"agent exited with code {proc.returncode}: "
            f"{stderr_data.decode(errors='replace').strip()}"
        )
    if result_event is None:
        raise RuntimeError("agent exited without a result event")
    if result_event.get("is_error") or result_event.get("subtype") != "success":
        raise RuntimeError(f"agent result was {result_event.get('subtype')!r}")
    review = review_text(result_event, segments, min_output_bytes)
    if not review:
        raise RuntimeError("agent finished without writing a review")
    dropped = len(str(result_event.get("result", "")).strip()) - len(review)
    if dropped > 0:
        telemetry["narration_dropped_chars"] = dropped
    output_path.write_text(review + "\n")
    file_size = output_path.stat().st_size

    return {
        "model": task["model"],
        "instance": task["instance"],
        "output_path": str(output_path),
        "status": "success",
        "file_size": file_size,
        "duration_seconds": round(duration, 1),
        "telemetry": dict(telemetry),
    }


async def run_with_retry(
    task: dict,
    settings: dict,
    launch_delay: float,
) -> dict:
    """Run a reviewer, retrying fast failures but never timeouts.

    Cancellation (quorum cut-off) is converted into a cut_off result.
    """
    label = task_label(task)
    telemetry: dict = {}
    timeout = settings["timeout_seconds"]
    retry_count = settings["retry_count"]

    try:
        if launch_delay:
            await asyncio.sleep(launch_delay)
        log(f"Starting {label}...")
        last_error = "Unknown error"

        for attempt in range(1 + retry_count):
            try:
                result = await run_single_reviewer(
                    task, timeout, settings["min_output_bytes"], telemetry,
                )
                if attempt > 0:
                    result["status"] = "retry_success"
                    result["retry_reason"] = last_error
                log(
                    f"{label} {'completed' if attempt == 0 else 'retry succeeded'} "
                    f"({result['file_size']} bytes, {result['duration_seconds']}s, "
                    f"{telemetry.get('tool_calls', 0)} tool calls)"
                )
                return result

            except asyncio.TimeoutError:
                last_error = f"Timeout after {timeout}s"
                log(
                    f"{label} timed out ({timeout}s) after {telemetry.get('tool_calls', 0)} "
                    f"tool calls, last: {telemetry.get('last_tool')} - FAILED (timeouts are not retried)"
                )
                break

            except RuntimeError as e:
                last_error = str(e)
                if attempt < retry_count:
                    log(f"{label} failed ({last_error}), retrying...")
                    await asyncio.sleep(settings["retry_delay_seconds"])
                else:
                    log(f"{label} failed - {last_error}")

        write_failure_note(task, "Review failed", last_error, telemetry)
        return failure_result(task, "failed", last_error, telemetry)

    except asyncio.CancelledError:
        error = (
            f"Cut off {settings['quorum_grace_seconds']}s after external "
            "quorum was reached"
        )
        log(
            f"{label} cut off - quorum reached and grace period expired "
            f"({telemetry.get('tool_calls', 0)} tool calls, last: {telemetry.get('last_tool')})"
        )
        write_failure_note(task, "Review cut off", error, telemetry)
        return failure_result(task, "cut_off", error, telemetry)


def read_settings(config: dict) -> dict:
    return {
        "timeout_seconds": config.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS),
        "retry_count": int(config.get("retry_count", DEFAULT_RETRY_COUNT)),
        "retry_delay_seconds": config.get(
            "retry_delay_seconds", DEFAULT_RETRY_DELAY_SECONDS),
        "quorum_fraction": config.get("quorum_fraction", DEFAULT_QUORUM_FRACTION),
        "quorum_grace_seconds": config.get(
            "quorum_grace_seconds", DEFAULT_QUORUM_GRACE_SECONDS),
        "launch_stagger_seconds": config.get(
            "launch_stagger_seconds", DEFAULT_LAUNCH_STAGGER_SECONDS),
        "min_output_bytes": int(config.get(
            "min_output_bytes", DEFAULT_MIN_OUTPUT_BYTES)),
    }


async def run_all(config: dict) -> dict:
    """Run all reviewer tasks concurrently and collect results.

    Once quorum_fraction of tasks have succeeded, remaining tasks get
    quorum_grace_seconds to finish before they are cancelled.
    """
    tasks = config["tasks"]
    settings = read_settings(config)

    output_dirs = {Path(t["output_path"]).parent for t in tasks}
    for d in output_dirs:
        d.mkdir(parents=True, exist_ok=True)

    running = {
        asyncio.ensure_future(run_with_retry(
            task, settings, index * settings["launch_stagger_seconds"],
        )): index
        for index, task in enumerate(tasks)
    }
    quorum_count = math.ceil(settings["quorum_fraction"] * len(tasks))
    results: dict[int, dict] = {}
    pending = set(running)
    cutoff_at: float | None = None
    loop = asyncio.get_running_loop()

    while pending:
        wait_timeout = None if cutoff_at is None else max(0.0, cutoff_at - loop.time())
        done, pending = await asyncio.wait(
            pending, timeout=wait_timeout, return_when=asyncio.FIRST_COMPLETED
        )
        for future in done:
            index = running[future]
            try:
                results[index] = future.result()
            except Exception as e:
                results[index] = failure_result(tasks[index], "failed", str(e))
        succeeded_so_far = sum(
            1 for r in results.values() if r["status"] in ("success", "retry_success")
        )
        if cutoff_at is None and pending and succeeded_so_far >= quorum_count:
            cutoff_at = loop.time() + settings["quorum_grace_seconds"]
            log(
                f"Quorum reached ({succeeded_so_far}/{len(tasks)} succeeded); "
                f"giving {len(pending)} straggler(s) "
                f"{settings['quorum_grace_seconds']}s to finish"
            )
        if cutoff_at is not None and pending and loop.time() >= cutoff_at:
            for future in pending:
                future.cancel()
            for future in pending:
                index = running[future]
                try:
                    results[index] = await future
                except asyncio.CancelledError:
                    results[index] = failure_result(
                        tasks[index], "cut_off", "Cut off after quorum grace period")
            pending = set()

    final_results = [results[i] for i in range(len(tasks))]
    succeeded = sum(
        1 for r in final_results if r["status"] in ("success", "retry_success")
    )
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
    blocks execute (cleaning up raw event files and file descriptors).
    """
    global _signal_received

    def handle_signal(sig: int) -> None:
        global _signal_received
        _signal_received = sig
        log(f"Received signal {sig}, killing {len(_running_procs)} running processes...")
        for proc in list(_running_procs):
            kill_process_group(proc)
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
