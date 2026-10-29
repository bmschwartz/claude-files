import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import learnings
from learnings_store import store_lock, store_paths, write_atomic
from learnings_text import new_learning_text
from prepare_round import checkout_link_warnings

SCRIPTS = Path(__file__).resolve().parent.parent
LEARNINGS_PY = SCRIPTS / "learnings.py"
DRAFT = (
    '---\ntitle: "Draft learning"\ncategory: correctness\nseverity: important\n'
    'scope:\n  - "app/**/*.py"\n---\n\n## Finding\n\nSomething broke.\n'
)
WORKER = """
import os, sys
sys.path.insert(0, sys.argv[1])
import learnings
home, repo, draft, recurrence_draft = sys.argv[2:]
os.chdir(repo)
for _ in range(20):
    if learnings.main(["--home", home, "new", "--draft", draft]) != 0:
        sys.exit(1)
    if learnings.main(["--home", home, "recur", "L-001", "--draft", recurrence_draft]) != 0:
        sys.exit(1)
"""


def git(args: list[str], cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def make_checkout(path: Path) -> Path:
    path.mkdir(parents=True)
    git(["init", "-q"], path)
    git(["-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "--allow-empty", "-m", "init"], path)
    return path.resolve()


class LearningsCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name).resolve()
        self.root = root
        self.home = root / "home"
        self.repo = make_checkout(root / "repo")
        self.store = store_paths(self.repo, home=self.home).learnings_dir
        self.draft = root / "draft.md"
        self.draft.write_text(DRAFT)
        self.recurrence_draft = root / "recurrence.md"
        self.recurrence_draft.write_text("Seen again.\n")

    def run_cli(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(LEARNINGS_PY), "--home", str(self.home), *args],
            cwd=cwd or self.repo,
            capture_output=True,
            text=True,
        )

    def test_concurrent_writers(self):
        self.assertEqual(self.run_cli("new", "--draft", str(self.draft)).returncode, 0)
        workers = [
            subprocess.Popen(
                [sys.executable, "-c", WORKER, str(SCRIPTS), str(self.home), str(self.repo),
                 str(self.draft), str(self.recurrence_draft)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            for _ in range(2)
        ]
        for worker in workers:
            _, stderr = worker.communicate(timeout=120)
            self.assertEqual(worker.returncode, 0, stderr)
        ids = sorted(path.name for path in self.store.glob("L-*.md"))
        self.assertEqual(len(ids), 41)
        self.assertEqual(ids[-1], "L-041.md")
        self.assertIn("occurrences: 41\n", (self.store / "L-001.md").read_text())
        index = (self.store / "LEARNINGS.md").read_text()
        self.assertEqual(sum(1 for line in index.splitlines() if line.startswith("| L-")), 41)

    def test_new_skips_an_id_taken_outside_the_lock(self):
        self.assertEqual(self.run_cli("new", "--draft", str(self.draft)).returncode, 0)
        original = (self.store / "L-001.md").read_bytes()
        previous = os.getcwd()
        os.chdir(self.repo)
        try:
            with mock.patch.object(learnings, "next_learning_id", return_value="L-001"):
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    status = learnings.main(["--home", str(self.home), "new", "--draft", str(self.draft)])
        finally:
            os.chdir(previous)
        self.assertEqual(status, 0)
        self.assertEqual(out.getvalue().strip(), "L-002")
        self.assertEqual((self.store / "L-001.md").read_bytes(), original)

    def test_write_atomic_keeps_mode(self):
        existing = self.root / "CLAUDE.md"
        existing.write_text("rules\n")
        existing.chmod(0o640)
        write_atomic(existing, "rules\nnew\n")
        self.assertEqual((existing.stat().st_mode & 0o777, existing.read_text()), (0o640, "rules\nnew\n"))
        fresh = self.root / "fresh.md"
        write_atomic(fresh, "x\n")
        self.assertEqual(fresh.stat().st_mode & 0o777, 0o644)

    def test_lock_timeout_exits_3(self):
        with store_lock(self.store):
            result = self.run_cli("--lock-timeout", "0.2", "index")
        self.assertEqual(result.returncode, 3)

    def test_paths_reports_store_and_claude_md(self):
        result = self.run_cli("paths")
        self.assertEqual(result.returncode, 0, result.stderr)
        reported = json.loads(result.stdout)
        self.assertEqual(reported["learnings_dir"], str(self.store))
        self.assertEqual(reported["main_claude_md"], str(self.repo / ".claude/CLAUDE.md"))
        self.assertEqual((reported["in_worktree"], reported["awaiting_migration"]), (False, False))

    def test_worktree_links_to_fresh_store(self):
        repo = make_checkout(self.root / "main")
        (repo / ".claude/learnings").mkdir(parents=True)
        (repo / ".claude/learnings/L-001.md").write_text(new_learning_text(DRAFT, "L-001", "2026-10-27"))
        worktree = repo / ".claude/worktrees/w"
        git(["worktree", "add", "-q", str(worktree)], repo)
        shutil.copytree(repo / ".claude/learnings", worktree / ".claude/learnings")
        store = store_paths(repo, home=self.home).learnings_dir
        before = self.run_cli("index", cwd=worktree)
        self.assertEqual(before.returncode, 2)
        self.assertIn("run learnings.py migrate", before.stderr)
        self.assertFalse((worktree / ".claude/learnings").is_symlink())
        self.assertFalse(list(worktree.glob(".claude/learnings.diverged-*")))
        self.assertEqual(self.run_cli("migrate", cwd=worktree).returncode, 2)
        migrated = self.run_cli("migrate", cwd=repo)
        self.assertEqual(migrated.returncode, 0, migrated.stderr)
        self.assertTrue((repo / ".claude/learnings").is_symlink())
        self.assertEqual(self.run_cli("index", cwd=worktree).returncode, 0)
        self.assertEqual((worktree / ".claude/learnings").resolve(), store.resolve())
        self.assertEqual(self.run_cli("new", "--draft", str(self.draft), cwd=worktree).stdout.strip(), "L-002")
        self.assertTrue((store / "L-002.md").exists())
        fresh = self.run_cli("list", "--json", cwd=make_checkout(self.root / "fresh"))
        self.assertEqual((fresh.returncode, json.loads(fresh.stdout)), (0, []))

    def test_recur_refuses_crlf_learning_untouched(self):
        self.assertEqual(self.run_cli("new", "--draft", str(self.draft)).returncode, 0)
        learning = self.store / "L-001.md"
        crlf = learning.read_bytes().replace(b"\n", b"\r\n")
        learning.write_bytes(crlf)
        result = self.run_cli("recur", "L-001", "--draft", str(self.recurrence_draft))
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(learning.read_bytes(), crlf)

    def test_broken_checkout_or_cwd_exits_2(self):
        (self.repo / ".claude").mkdir()
        (self.repo / ".claude/learnings").write_text("not a directory\n")
        broken = self.run_cli("list", "--json")
        self.assertEqual(broken.returncode, 2, broken.stderr)
        self.assertNotIn("Traceback", broken.stderr)
        outside = self.root / "not-a-repo"
        outside.mkdir()
        self.assertEqual(self.run_cli("paths", cwd=outside).returncode, 2)

    def test_prepare_round_link_failure_is_a_warning(self):
        (self.repo / ".claude").mkdir()
        (self.repo / ".claude/learnings").write_text("not a directory\n")
        warnings = checkout_link_warnings(store_paths(self.repo, home=self.home), "20261028-000000", dry_run=False)
        self.assertTrue(any("learnings symlink not checked" in warning for warning in warnings), warnings)

    def test_recur_unknown_id_exits_2(self):
        result = self.run_cli("recur", "L-404", "--draft", str(self.recurrence_draft))
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
