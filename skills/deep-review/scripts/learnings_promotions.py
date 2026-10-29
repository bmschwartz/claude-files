"""Promotion planning: which files a promotion or an apply-promotions run writes, decided without touching disk."""

import hashlib
import json
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from learnings_store import StorePaths
from learnings_text import parse_frontmatter, remove_frontmatter_field, set_frontmatter_field

Merge3 = Callable[[str, str, str], str | None]


@dataclass
class Plan:
    writes: dict[Path, str] = field(default_factory=dict)
    moves: list[tuple[Path, Path]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class Pending:
    name: str
    learning_id: str
    heading: str
    base: str
    revised: str


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def apply_fingerprint(main_text: str, pending: list[Pending]) -> str:
    parts = [main_text]
    for promotion in sorted(pending, key=lambda item: item.name):
        parts.extend([promotion.name, promotion.base, promotion.revised])
    return sha256_text("\0".join(parts))


def quoted(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def promoted_learning(text: str, heading: str) -> str:
    text = set_frontmatter_field(text, "status", "promoted")
    text = set_frontmatter_field(text, "promoted_to", quoted(f".claude/CLAUDE.md — {heading}"))
    return remove_frontmatter_field(text, "promotion_pending")


def plan_promotion(
    paths: StorePaths,
    learning_id: str,
    learning_text: str,
    main_text: str,
    checkout_text: str | None,
    expect_sha: str,
    revised: str,
    heading: str,
    today: str,
    stamp: str,
    round_dir: str,
) -> Plan:
    if sha256_text(main_text) != expect_sha:
        return Plan(error=f"{paths.main_claude_md} changed since it was read; re-read it and redo the edit")
    parsed = parse_frontmatter(learning_text)
    if parsed is None:
        return Plan(error=f"{learning_id}: frontmatter does not parse")
    fields = parsed[0]
    if fields.get("status", "active") != "active":
        return Plan(error=f"{learning_id} is {fields.get('status')}, not active")
    if "promotion_pending" in fields:
        return Plan(error=f"{learning_id} already has a pending promotion: {fields['promotion_pending']}")
    learning_path = paths.learnings_dir / f"{learning_id}.md"
    try:
        learning = set_frontmatter_field(learning_text, "occurrences", str(int(fields.get("occurrences", 1) or 1) + 1))
        learning = set_frontmatter_field(learning, "last_seen", quoted(today))
        if not paths.in_worktree:
            return Plan(writes={paths.main_claude_md: revised, learning_path: promoted_learning(learning, heading)})
        name = f"{learning_id}-{stamp}"
        learning = set_frontmatter_field(learning, "promotion_pending", quoted(name))
    except ValueError as error:
        return Plan(error=f"{learning_id}: {error}")
    queued = paths.learnings_dir / "promotions" / name
    meta = {"learning_id": learning_id, "heading": heading, "base_sha": expect_sha, "round_dir": round_dir}
    plan = Plan(writes={
        queued / "base.md": main_text,
        queued / "revised.md": revised,
        queued / "meta.json": json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
        learning_path: learning,
    })
    if checkout_text == main_text:
        plan.writes[paths.checkout_claude_md] = revised
    else:
        plan.warnings.append(
            f"{paths.checkout_claude_md} differs from the main checkout's, so it was left alone; "
            f"this worktree's sessions won't load the rule until apply-promotions runs and a new worktree is made"
        )
    return plan


def plan_apply(paths: StorePaths, main_text: str, pending: list[Pending], learning_texts: dict[str, str], merge3: Merge3) -> Plan:
    plan = Plan()
    current = main_text
    promotions = paths.learnings_dir / "promotions"
    for promotion in sorted(pending, key=lambda item: item.name):
        learning_text = learning_texts.get(promotion.learning_id)
        if learning_text is None:
            plan.warnings.append(f"{promotion.name}: learning {promotion.learning_id} not found; left pending")
            continue
        result = promotion.revised if current == promotion.base else merge3(current, promotion.base, promotion.revised)
        if result is None:
            plan.warnings.append(
                f"{promotion.name}: CLAUDE.md changed in the same lines since it was queued; left pending — "
                f"redo the promotion from the main checkout"
            )
            continue
        current = result
        plan.writes[paths.learnings_dir / f"{promotion.learning_id}.md"] = promoted_learning(learning_text, promotion.heading)
        plan.moves.append((promotions / promotion.name, promotions / "applied" / promotion.name))
    if current != main_text:
        plan.writes[paths.main_claude_md] = current
    return plan


def merge3(current: str, base: str, revised: str) -> str | None:
    with tempfile.TemporaryDirectory() as directory:
        names = {"current.md": current, "base.md": base, "revised.md": revised}
        for name, text in names.items():
            Path(directory, name).write_text(text)
        result = subprocess.run(
            ["git", "merge-file", "-p", "current.md", "base.md", "revised.md"],
            cwd=directory,
            capture_output=True,
            text=True,
        )
    if result.returncode == 0:
        return result.stdout
    if 0 < result.returncode < 128:
        return None
    raise RuntimeError(f"git merge-file failed: {result.stderr.strip()}")
