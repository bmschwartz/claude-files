#!/usr/bin/env python3
"""The only writer of a project's learnings store.

Every checkout of a project (the main checkout and each worktree) shares one
store at ~/.claude/projects/<main-checkout slug>/learnings/. Each command
re-links the checkout's .claude/learnings to it, takes the store lock for its
whole read-modify-write, writes files atomically and rebuilds LEARNINGS.md.

Exit codes: 0 success, 2 refused (nothing written), 3 store lock timed out.
Stdlib only — no pip dependencies.

Usage:
    learnings.py [--home DIR] [--lock-timeout SECONDS] paths
    learnings.py list [--status S] --json
    learnings.py new --draft FILE
    learnings.py recur ID --draft FILE [--round-dir R] [--scope GLOB ...]
    learnings.py index
    learnings.py promote ID --claude-md FILE --expect-sha SHA --heading TEXT [--round-dir R]
    learnings.py apply-promotions --dry-run | --expect-sha SHA   (main checkout only)
    learnings.py migrate   (main checkout only, once: moves .claude/learnings into the store)
"""

import argparse
import difflib
import json
import os
import shutil
import sys
import time
from datetime import date
from pathlib import Path

from learnings_store import (
    LockTimeout,
    StorePaths,
    awaiting_migration,
    create_exclusive,
    directory_files,
    link_checkout_copy,
    store_lock,
    store_paths,
    write_atomic,
)
from learnings_promotions import Pending, Plan, apply_fingerprint, merge3, plan_apply, plan_promotion
from learnings_text import new_learning_text, next_learning_id, parse_frontmatter, record_recurrence, render_index

WRITE_COMMANDS = {"new", "recur", "index", "promote", "apply-promotions"}


class Refusal(Exception):
    pass


def read_learning(path: Path) -> str:
    return path.read_bytes().decode()


def read_learnings(learnings_dir: Path) -> list[tuple[Path, dict, str]]:
    learnings = []
    for path in sorted(learnings_dir.glob("L-*.md")):
        parsed = parse_frontmatter(read_learning(path))
        if parsed is None:
            print(f"warning: {path.name}: unparseable frontmatter, skipped", file=sys.stderr)
            continue
        learnings.append((path, parsed[0], parsed[1]))
    return learnings


def rebuild_index(learnings_dir: Path) -> Path:
    index = learnings_dir / "LEARNINGS.md"
    write_atomic(index, render_index([fields for _, fields, _ in read_learnings(learnings_dir)]))
    return index


def round_dir_label(round_dir: Path, paths: StorePaths) -> str:
    try:
        return round_dir.relative_to(paths.checkout_root).as_posix() + "/"
    except ValueError:
        return str(round_dir) + "/"


def command_paths(paths: StorePaths, args) -> str:
    return json.dumps({
        "main_root": str(paths.main_root),
        "checkout_root": str(paths.checkout_root),
        "learnings_dir": str(paths.learnings_dir),
        "main_claude_md": str(paths.main_claude_md),
        "checkout_claude_md": str(paths.checkout_claude_md),
        "in_worktree": paths.in_worktree,
        "awaiting_migration": awaiting_migration(paths),
    }, indent=2)


def command_list(paths: StorePaths, args) -> str:
    if awaiting_migration(paths):
        return "[]"
    return json.dumps([
        {"id": fields.get("id", path.stem), "path": str(path), "fields": fields, "body": body}
        for path, fields, body in read_learnings(paths.learnings_dir)
        if args.status is None or fields.get("status", "active") == args.status
    ], indent=2, default=str)


def command_new(paths: StorePaths, args) -> str:
    draft = Path(args.draft).read_text()
    today = date.today().isoformat()
    store = paths.learnings_dir
    try:
        new_learning_text(draft, "L-000", today)
    except ValueError as error:
        raise Refusal(f"{args.draft}: {error}")
    with store_lock(store, args.lock_timeout):
        learning_id = next_learning_id([path.name for path in store.iterdir()])
        while not create_exclusive(store / f"{learning_id}.md", new_learning_text(draft, learning_id, today)):
            learning_id = f"L-{int(learning_id[2:]) + 1:03d}"
        rebuild_index(store)
    return learning_id


def command_recur(paths: StorePaths, args) -> str:
    draft_body = Path(args.draft).read_text()
    round_dir = Path(args.round_dir) if args.round_dir else Path(args.draft).resolve().parent
    path = paths.learnings_dir / f"{args.id}.md"
    with store_lock(paths.learnings_dir, args.lock_timeout):
        if not path.is_file():
            raise Refusal(f"no learning {args.id} in {paths.learnings_dir}")
        try:
            updated = record_recurrence(
                read_learning(path), draft_body, date.today().isoformat(), round_dir_label(round_dir, paths), args.scope
            )
        except ValueError as error:
            raise Refusal(f"{args.id}: {error}")
        write_atomic(path, updated)
        rebuild_index(paths.learnings_dir)
    return args.id


def command_index(paths: StorePaths, args) -> str:
    with store_lock(paths.learnings_dir, args.lock_timeout):
        return str(rebuild_index(paths.learnings_dir))


def read_text_or_empty(path: Path) -> str:
    return path.read_text() if path.is_file() else ""


def carry_out(plan: Plan) -> None:
    if plan.error:
        raise Refusal(plan.error)
    for path, text in plan.writes.items():
        write_atomic(path, text)
    for source, destination in plan.moves:
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.replace(source, destination)
    for warning in plan.warnings:
        print(f"warning: {warning}", file=sys.stderr)


def command_promote(paths: StorePaths, args) -> str:
    revised = Path(args.claude_md).read_text()
    round_dir = Path(args.round_dir) if args.round_dir else Path(args.claude_md).resolve().parent
    path = paths.learnings_dir / f"{args.id}.md"
    with store_lock(paths.learnings_dir, args.lock_timeout):
        if not path.is_file():
            raise Refusal(f"no learning {args.id} in {paths.learnings_dir}")
        checkout_text = read_text_or_empty(paths.checkout_claude_md) if paths.in_worktree else None
        carry_out(plan_promotion(
            paths,
            args.id,
            read_learning(path),
            read_text_or_empty(paths.main_claude_md),
            checkout_text,
            args.expect_sha,
            revised,
            args.heading,
            date.today().isoformat(),
            time.strftime("%Y%m%d-%H%M%S"),
            round_dir_label(round_dir, paths),
        ))
        rebuild_index(paths.learnings_dir)
    if paths.in_worktree:
        return f"{args.id}: queued; run apply-promotions from {paths.main_root} to add it to {paths.main_claude_md}"
    return f"{args.id}: promoted into {paths.main_claude_md}"


def pending_promotions(learnings_dir: Path) -> list[Pending]:
    promotions = learnings_dir / "promotions"
    if not promotions.is_dir():
        return []
    pending = []
    for directory in sorted(promotions.iterdir()):
        if directory.name == "applied" or not directory.is_dir():
            continue
        meta = json.loads((directory / "meta.json").read_text())
        pending.append(Pending(
            name=directory.name,
            learning_id=meta["learning_id"],
            heading=meta["heading"],
            base=(directory / "base.md").read_text(),
            revised=(directory / "revised.md").read_text(),
        ))
    return pending


def command_apply_promotions(paths: StorePaths, args) -> str:
    if paths.in_worktree:
        raise Refusal(f"apply-promotions writes {paths.main_claude_md}; run it from a session in {paths.main_root}")
    with store_lock(paths.learnings_dir, args.lock_timeout):
        main_text = read_text_or_empty(paths.main_claude_md)
        pending = pending_promotions(paths.learnings_dir)
        texts = {path.stem: read_learning(path) for path in paths.learnings_dir.glob("L-*.md")}
        plan = plan_apply(paths, main_text, pending, texts, merge3)
        new_main = plan.writes.get(paths.main_claude_md, main_text)
        if args.dry_run:
            for warning in plan.warnings:
                print(f"warning: {warning}", file=sys.stderr)
            diff = difflib.unified_diff(
                main_text.splitlines(keepends=True),
                new_main.splitlines(keepends=True),
                fromfile=str(paths.main_claude_md),
                tofile=f"{paths.main_claude_md} (after apply-promotions)",
            )
            return f"expect-sha: {apply_fingerprint(main_text, pending)}\n" + "".join(diff)
        if args.expect_sha != apply_fingerprint(main_text, pending):
            raise Refusal(
                f"{paths.main_claude_md} or the pending promotions differ from what --dry-run showed; "
                f"run --dry-run again, show it, and pass its expect-sha"
            )
        carry_out(plan)
        rebuild_index(paths.learnings_dir)
    applied = [destination.name for _, destination in plan.moves]
    return f"applied {len(applied)} of {len(pending)} pending promotion(s): {', '.join(applied) or 'none'}"


def command_migrate(paths: StorePaths, args) -> str:
    source = paths.main_root / ".claude" / "learnings"
    if paths.in_worktree:
        raise Refusal(f"migrate changes {source}; run it from a session in {paths.main_root}")
    if source.is_symlink():
        raise Refusal(f"{source} is already a symlink; nothing to migrate")
    if not source.is_dir():
        raise Refusal(f"{source} does not exist; nothing to migrate")
    store = paths.learnings_dir
    if any(store.glob("L-*.md")):
        raise Refusal(f"{store} already holds learnings; refusing to mix them with {source}")
    backup = source.with_name(f"learnings.pre-shared-{date.today().strftime('%Y%m%d')}")
    if backup.exists():
        raise Refusal(f"{backup} already exists")
    with store_lock(store, args.lock_timeout):
        originals = directory_files(source)
        for name in originals:
            destination = store / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / name, destination)
        copied = directory_files(store)
        mismatched = sorted(name for name, content in originals.items() if copied.get(name) != content)
        if mismatched:
            raise Refusal(f"copies differ from the originals: {', '.join(mismatched)}; {source} left in place")
        source.rename(backup)
        source.symlink_to(store, target_is_directory=True)
    return f"migrated {len(originals)} file(s) into {store}; originals kept at {backup} — delete it once the index check passes"


COMMANDS = {
    "migrate": command_migrate,
    "paths": command_paths,
    "list": command_list,
    "new": command_new,
    "recur": command_recur,
    "index": command_index,
    "promote": command_promote,
    "apply-promotions": command_apply_promotions,
}


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read and write the shared learnings store.")
    parser.add_argument("--home", help="home directory holding .claude/projects (default: the user's home)")
    parser.add_argument("--lock-timeout", type=float, default=30.0)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("paths")
    listing = commands.add_parser("list")
    listing.add_argument("--status")
    listing.add_argument("--json", action="store_true")
    new = commands.add_parser("new")
    new.add_argument("--draft", required=True)
    recur = commands.add_parser("recur")
    recur.add_argument("id")
    recur.add_argument("--draft", required=True)
    recur.add_argument("--round-dir")
    recur.add_argument("--scope", action="append", default=[])
    commands.add_parser("index")
    commands.add_parser("migrate")
    promote = commands.add_parser("promote")
    promote.add_argument("id")
    promote.add_argument("--claude-md", required=True, help="the complete revised .claude/CLAUDE.md")
    promote.add_argument("--expect-sha", required=True, help="sha256 of the main checkout's CLAUDE.md as read")
    promote.add_argument("--heading", required=True, help="CLAUDE.md section heading the rule lives under")
    promote.add_argument("--round-dir")
    apply = commands.add_parser("apply-promotions")
    apply.add_argument("--dry-run", action="store_true")
    apply.add_argument("--expect-sha")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        paths = store_paths(Path.cwd(), home=Path(args.home) if args.home else None)
        if args.command != "migrate":
            for warning in link_checkout_copy(paths, time.strftime("%Y%m%d-%H%M%S"), args.lock_timeout):
                print(f"warning: {warning}", file=sys.stderr)
        if args.command in WRITE_COMMANDS and awaiting_migration(paths):
            raise Refusal("the store is not in use until the main checkout is migrated")
        print(COMMANDS[args.command](paths, args))
        return 0
    except Refusal as refusal:
        print(f"refused: {refusal}", file=sys.stderr)
        return 2
    except LockTimeout as timeout:
        print(f"error: {timeout}", file=sys.stderr)
        return 3
    except (OSError, RuntimeError) as error:
        print(f"refused: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
