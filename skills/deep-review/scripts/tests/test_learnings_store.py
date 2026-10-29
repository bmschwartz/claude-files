import unittest
from pathlib import Path

from learnings_store import SwapAction, store_paths, swap_action


class LearningsStoreTest(unittest.TestCase):
    def test_store_paths_from_worktree(self):
        main = Path("/Users/bmschwartz/Development/nomad/nomad-flask")
        worktree = main / ".claude/worktrees/x"
        answers = {"--git-common-dir": f"{main}/.git\n", "--show-toplevel": f"{worktree}\n"}
        paths = store_paths(worktree, home=Path("/h"), git=lambda args, cwd: answers[args[-1]])
        self.assertEqual(paths.main_root, main)
        self.assertEqual(paths.checkout_root, worktree)
        self.assertTrue(paths.in_worktree)
        self.assertEqual(
            paths.learnings_dir,
            Path("/h/.claude/projects/-Users-bmschwartz-Development-nomad-nomad-flask/learnings"),
        )
        self.assertEqual(paths.main_claude_md, main / ".claude/CLAUDE.md")
        self.assertEqual(paths.checkout_claude_md, worktree / ".claude/CLAUDE.md")

    def test_swap_action(self):
        store = {"L-050.md": b"new", "L-055.md": b"x", "LEARNINGS.md": b"i"}
        self.assertIs(swap_action(True, {}, store), SwapAction.NONE)
        self.assertIs(swap_action(False, {"L-050.md": b"new", "LEARNINGS.md": b"i"}, store), SwapAction.REPLACE)
        self.assertIs(swap_action(False, {"L-050.md": b"new", "L-056.md": b"y"}, store), SwapAction.DIVERT)
        self.assertIs(swap_action(False, {"L-050.md": b"old"}, store), SwapAction.DIVERT)

    def test_swap_action_ignores_the_derived_index(self):
        store = {"L-050.md": b"new", "LEARNINGS.md": b"rebuilt after a later write"}
        self.assertIs(swap_action(False, {"L-050.md": b"new", "LEARNINGS.md": b"snapshot"}, store), SwapAction.REPLACE)


if __name__ == "__main__":
    unittest.main()
