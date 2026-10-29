import unittest

from learnings_text import (
    new_learning_text,
    next_learning_id,
    parse_frontmatter,
    record_recurrence,
    render_index,
    set_frontmatter_field,
)
from tests.fixtures import LEARNING


class LearningsTextTest(unittest.TestCase):
    def test_next_learning_id(self):
        names = [f"L-{n:03d}.md" for n in range(1, 55)] + ["LEARNINGS.md", ".lock"]
        self.assertEqual(next_learning_id(names), "L-055")
        self.assertEqual(next_learning_id(["L-001.md", "L-007.md"]), "L-008")
        self.assertEqual(next_learning_id([]), "L-001")

    def test_record_recurrence(self):
        out = record_recurrence(
            LEARNING,
            "Seen again.",
            "2026-10-27",
            ".claude/reviews/x/1/",
            ["app/new/**/*.py", "app/credentialing/timecards/**/*.py"],
        )
        self.assertIn("occurrences: 3\n", out)
        self.assertIn('last_seen: "2026-10-27"\n', out)
        self.assertEqual(out.count('"app/credentialing/timecards/**/*.py"'), 1)
        self.assertIn('  - "app/new/**/*.py"\n', out)
        self.assertTrue(out.endswith("## Recurrence — 2026-10-27 (`.claude/reviews/x/1/`)\n\nSeen again.\n"))
        changed = {"occurrences", "last_seen"}
        before = [
            line
            for line in LEARNING.split("\n---", 1)[0].splitlines()
            if line.split(":")[0] not in changed
        ]
        after = out.split("\n---", 1)[0].splitlines()
        for line in before:
            self.assertIn(line, after)

    def test_record_recurrence_refuses_inactive(self):
        promoted = set_frontmatter_field(LEARNING, "status", "promoted")
        with self.assertRaises(ValueError):
            record_recurrence(promoted, "x", "2026-10-27", "r/", [])

    def test_record_recurrence_refuses_unparseable(self):
        with self.assertRaises(ValueError):
            record_recurrence(LEARNING.split("\n---\n", 1)[0] + "\n", "x", "2026-10-27", "r/", [])
        with self.assertRaises(ValueError):
            record_recurrence(LEARNING.replace("\n", "\r\n"), "x", "2026-10-27", "r/", [])

    def test_new_learning_text_overrides_owned_keys(self):
        draft = (
            '---\nid: L-999\ntitle: "T"\ncategory: correctness\nseverity: important\n'
            'scope:\n  - "app/**/*.py"\noccurrences: 7\nstatus: promoted\n---\n\n## Finding\n\nBody.\n'
        )
        out = new_learning_text(draft, "L-055", "2026-10-27")
        fields, body = parse_frontmatter(out)
        self.assertEqual(
            (fields["id"], fields["occurrences"], fields["status"], fields["first_seen"], fields["last_seen"], fields["_staleness_count"]),
            ("L-055", 1, "active", "2026-10-27", "2026-10-27", 0),
        )
        self.assertTrue(out.startswith("---\nid: L-055\n"))
        self.assertNotIn("L-999", out)
        self.assertIn("## Finding\n\nBody.\n", body)

    def test_render_index_orders_newest_first(self):
        rows = [
            {"id": "L-001", "title": "a", "category": "c", "severity": "important", "status": "active",
             "occurrences": 1, "first_seen": "2026-01-01", "last_seen": "2026-10-22"},
            {"id": "L-002", "title": "b", "category": "c", "severity": "critical", "status": "promoted",
             "occurrences": 4, "first_seen": "2026-02-01", "last_seen": "2026-10-22"},
            {"id": "L-003", "title": "c", "category": "c", "severity": "important", "status": "expired",
             "occurrences": 1, "first_seen": "2026-03-01", "last_seen": "2026-09-01"},
        ]
        lines = render_index(rows).splitlines()
        self.assertEqual(lines[0], "# Review Learnings")
        self.assertEqual(
            [line.split(" | ")[0] for line in lines if line.startswith("| L-")],
            ["| L-002", "| L-001", "| L-003"],
        )


if __name__ == "__main__":
    unittest.main()
