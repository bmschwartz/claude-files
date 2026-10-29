import unittest

from learnings_promotions import Pending, apply_fingerprint, merge3, plan_apply, plan_promotion, sha256_text
from learnings_text import set_frontmatter_field
from tests.fixtures import LEARNING, MAIN, WORKTREE

RULES = "rules\n"
REVISED = "rules\nnew\n"


class PromotionsTest(unittest.TestCase):
    def test_promote_wrong_sha_writes_nothing(self):
        plan = plan_promotion(MAIN, "L-044", LEARNING, RULES, RULES, "bad", REVISED, "Money", "2026-10-27", "s", "r/")
        self.assertIsNotNone(plan.error)
        self.assertEqual(plan.writes, {})

    def test_promote_in_main_checkout(self):
        plan = plan_promotion(MAIN, "L-044", LEARNING, RULES, None, sha256_text(RULES), REVISED, "Money", "2026-10-27", "s", "r/")
        self.assertIsNone(plan.error)
        self.assertEqual(plan.writes[MAIN.main_claude_md], REVISED)
        learning = plan.writes[MAIN.learnings_dir / "L-044.md"]
        self.assertIn("status: promoted\n", learning)
        self.assertIn('promoted_to: ".claude/CLAUDE.md — Money"\n', learning)
        self.assertIn("occurrences: 3\n", learning)

    def test_promote_in_worktree_queues(self):
        plan = plan_promotion(WORKTREE, "L-044", LEARNING, RULES, RULES, sha256_text(RULES), REVISED, "Money", "2026-10-27", "s", "r/")
        queued = WORKTREE.learnings_dir / "promotions/L-044-s"
        self.assertEqual(plan.writes[queued / "base.md"], RULES)
        self.assertEqual(plan.writes[queued / "revised.md"], REVISED)
        self.assertNotIn(WORKTREE.main_claude_md, plan.writes)
        self.assertEqual(plan.writes[WORKTREE.checkout_claude_md], REVISED)
        learning = plan.writes[WORKTREE.learnings_dir / "L-044.md"]
        self.assertIn("status: active\n", learning)
        self.assertIn('promotion_pending: "L-044-s"\n', learning)
        diverged = plan_promotion(
            WORKTREE, "L-044", LEARNING, RULES, "rules\nbreadcrumb\n", sha256_text(RULES), REVISED, "Money", "2026-10-27", "s", "r/"
        )
        self.assertNotIn(WORKTREE.checkout_claude_md, diverged.writes)
        self.assertTrue(diverged.warnings)

    def test_promote_refuses_when_already_pending(self):
        pending = set_frontmatter_field(LEARNING, "promotion_pending", '"L-044-old"')
        plan = plan_promotion(WORKTREE, "L-044", pending, RULES, RULES, sha256_text(RULES), "x\n", "Money", "2026-10-27", "s", "r/")
        self.assertIsNotNone(plan.error)
        self.assertEqual(plan.writes, {})

    def test_apply_promotions(self):
        queued = Pending("L-044-s", "L-044", "Money", base="a\nb\n", revised="a\nb\nnew\n")
        texts = {"L-044": set_frontmatter_field(LEARNING, "promotion_pending", '"L-044-s"')}
        unchanged = plan_apply(MAIN, "a\nb\n", [queued], texts, merge3=lambda *texts: self.fail("no merge needed"))
        self.assertEqual(unchanged.writes[MAIN.main_claude_md], "a\nb\nnew\n")
        applied_learning = unchanged.writes[MAIN.learnings_dir / "L-044.md"]
        self.assertNotIn("promotion_pending", applied_learning)
        self.assertIn("status: promoted\n", applied_learning)
        self.assertEqual(unchanged.moves, [(MAIN.learnings_dir / "promotions/L-044-s", MAIN.learnings_dir / "promotions/applied/L-044-s")])
        merged = plan_apply(MAIN, "z\na\nb\n", [queued], texts, merge3=lambda current, base, revised: "z\na\nb\nnew\n")
        self.assertEqual(merged.writes[MAIN.main_claude_md], "z\na\nb\nnew\n")
        conflict = plan_apply(MAIN, "a\nB\n", [queued], texts, merge3=lambda *texts: None)
        self.assertEqual(conflict.writes, {})
        self.assertEqual(conflict.moves, [])
        self.assertTrue(conflict.warnings)

    def test_apply_fingerprint_covers_the_pending_set(self):
        queued = Pending("L-044-s", "L-044", "Money", base="a\n", revised="a\nnew\n")
        later = Pending("L-045-t", "L-045", "Other", base="a\n", revised="a\nother\n")
        shown = apply_fingerprint("a\n", [queued])
        self.assertEqual(shown, apply_fingerprint("a\n", [queued]))
        self.assertNotEqual(shown, apply_fingerprint("a\n", [queued, later]))
        self.assertNotEqual(shown, apply_fingerprint("a\nb\n", [queued]))
        self.assertNotEqual(shown, apply_fingerprint("a\n", [Pending("L-044-s", "L-044", "Money", base="a\n", revised="a\nedited\n")]))

    def test_merge3_with_git(self):
        base = "# A\nx\n\n# B\ny\n"
        self.assertEqual(merge3("# A\nX\n\n# B\ny\n", base, "# A\nx\n\n# B\ny\nnew\n"), "# A\nX\n\n# B\ny\nnew\n")
        self.assertIsNone(merge3("# A\nX\n\n# B\ny\n", base, "# A\nQ\n\n# B\ny\n"))


if __name__ == "__main__":
    unittest.main()
