"""Where a project's learnings store lives, and the locked, atomic file operations every writer uses."""

import fcntl
import os
import re
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

GitRunner = Callable[[list[str], Path], str]
MIGRATE_WARNING = (
    "main checkout still has a real .claude/learnings; run learnings.py migrate from a main-checkout session"
)


@dataclass(frozen=True)
class StorePaths:
    main_root: Path
    checkout_root: Path
    learnings_dir: Path
    main_claude_md: Path
    checkout_claude_md: Path

    @property
    def in_worktree(self) -> bool:
        return self.checkout_root != self.main_root


class SwapAction(Enum):
    NONE = "none"
    REPLACE = "replace"
    DIVERT = "divert"


class LockTimeout(Exception):
    pass


def run_git(args: list[str], cwd: Path) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def project_slug(path: Path) -> str:
    return re.sub(r"[^A-Za-z0-9-]", "-", str(path))


def store_paths(cwd: Path, home: Path | None = None, git: GitRunner = run_git) -> StorePaths:
    main_root = Path(git(["rev-parse", "--path-format=absolute", "--git-common-dir"], cwd).strip()).parent
    checkout_root = Path(git(["rev-parse", "--show-toplevel"], cwd).strip())
    home = home or Path.home()
    return StorePaths(
        main_root=main_root,
        checkout_root=checkout_root,
        learnings_dir=home / ".claude" / "projects" / project_slug(main_root) / "learnings",
        main_claude_md=main_root / ".claude" / "CLAUDE.md",
        checkout_claude_md=checkout_root / ".claude" / "CLAUDE.md",
    )


def swap_action(copy_is_link_to_store: bool, copy_files: dict[str, bytes], store_files: dict[str, bytes]) -> SwapAction:
    if copy_is_link_to_store:
        return SwapAction.NONE
    if all(store_files.get(name) == content for name, content in copy_files.items() if name != "LEARNINGS.md"):
        return SwapAction.REPLACE
    return SwapAction.DIVERT


@contextmanager
def store_lock(learnings_dir: Path, timeout_seconds: float = 30.0) -> Iterator[None]:
    learnings_dir.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout_seconds
    with open(learnings_dir / ".lock", "a") as handle:
        while True:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise LockTimeout(f"timed out after {timeout_seconds}s waiting for {learnings_dir / '.lock'}")
                time.sleep(0.05)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def write_temporary(directory: Path, name: str, text: str, mode: int = 0o644) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=directory, prefix=f".{name}.", suffix=".tmp")
    os.fchmod(descriptor, mode)
    with os.fdopen(descriptor, "w") as handle:
        handle.write(text)
    return Path(temporary)


def write_atomic(path: Path, text: str) -> None:
    target = path.resolve() if path.is_symlink() else path
    mode = target.stat().st_mode & 0o777 if target.exists() else 0o644
    os.replace(write_temporary(target.parent, target.name, text, mode), target)


def create_exclusive(path: Path, text: str) -> bool:
    temporary = write_temporary(path.parent, path.name, text)
    try:
        os.link(temporary, path)
        return True
    except FileExistsError:
        return False
    finally:
        temporary.unlink()


def directory_files(root: Path) -> dict[str, bytes]:
    if not root.is_dir():
        return {}
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.name.startswith(".")
    }


def awaiting_migration(paths: StorePaths) -> bool:
    main_copy = paths.main_root / ".claude" / "learnings"
    return main_copy.is_dir() and not main_copy.is_symlink()


def link_checkout_copy(paths: StorePaths, stamp: str, timeout_seconds: float = 30.0) -> list[str]:
    if awaiting_migration(paths):
        return [MIGRATE_WARNING]
    claude_dir = paths.checkout_root / ".claude"
    copy = claude_dir / "learnings"
    if not claude_dir.is_dir():
        return []
    with store_lock(paths.learnings_dir, timeout_seconds):
        if copy.is_symlink() and copy.resolve() == paths.learnings_dir.resolve():
            return []
        if not copy.exists() and not copy.is_symlink():
            copy.symlink_to(paths.learnings_dir, target_is_directory=True)
            return []
        copy_files = directory_files(copy)
        store_files = directory_files(paths.learnings_dir)
        action = swap_action(False, copy_files, store_files)
        warnings = []
        if action is SwapAction.REPLACE and not copy.is_symlink():
            shutil.rmtree(copy)
        else:
            diverted = claude_dir / f"learnings.diverged-{stamp}"
            copy.rename(diverted)
            differing = sorted(name for name, content in copy_files.items() if store_files.get(name) != content)
            warnings.append(
                f"moved {copy} to {diverted}: it differs from the learnings store in "
                f"{', '.join(differing) or 'its link target'}; review it and delete it by hand"
            )
        copy.symlink_to(paths.learnings_dir, target_is_directory=True)
        return warnings
