#!/usr/bin/env python3
"""Prepare a /deep-review round in one call.

Computes workspace scoping, creates the round directory, captures the
diff, matches and injects project learnings (with the staleness check),
renders one review prompt per reviewer model from the shared template
sections and that model's profile (references/model-profiles/), and
writes the external reviewer config for run_reviewers.py. Prints a JSON
report to stdout.

Stdlib only — no pip dependencies.

Usage (code):
    prepare_round.py --type code --diff-args "master...HEAD" --scope-suffix vs-master \
        [--spec-file PATH ...] [--plan-file PATH ...] [--drop-section TEXT ...] \
        [--inline-tests] [--keep-tests GLOB ...] [--patterns-file PATH] [--context-stdin] \
        [--models a,b] [--count 1] [--no-external] [--dry-run]

Usage (plan/spec):
    prepare_round.py --type plan --plan-input PATH [--plan-root PATH] [...]
"""

import argparse
import json
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_MODELS = ["composer-2.5", "gpt-5.6-sol-high"]
DEFAULT_COUNT = 1
INTERNAL_MODEL = "opus"
PROFILES_DIR = SKILL_DIR / "references" / "model-profiles"
EFFORT_SUFFIX = re.compile(r"-(?:none|minimal|low|medium|high|xhigh|extra-high|max)$")
# Advisory exploration budget (file reads and searches beyond the input),
# by diff size. A profile's budget_scale multiplies it; "budget: none" drops it.
BUDGET_TIERS = [(600, 40), (1400, 30), (None, 20)]
PLAN_BUDGET = 40
DELIVERY = {
    "internal": "Write the complete review to the output path you were given.",
    "external": (
        "Everything you write outside tool calls is saved verbatim as the review file, so "
        "write only the review: no plan or narration of your steps, and no opening or "
        "closing remarks."
    ),
}
LEARNINGS_CAP = 10
STALENESS_LIMIT = 3
LARGE_DIFF_LINES = 3000
REVIEWER_SETTINGS = {
    "timeout_seconds": 900,
    "retry_count": 1,
    "retry_delay_seconds": 5,
    "quorum_fraction": 0.75,
    "quorum_grace_seconds": 90,
    "launch_stagger_seconds": 1.5,
    "min_output_bytes": 200,
}
DEPENDENCY_MANIFESTS = {
    "requirements.txt", "requirements-dev.txt", "pyproject.toml", "poetry.lock",
    "uv.lock", "Pipfile", "Pipfile.lock", "setup.py", "setup.cfg",
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "go.mod", "go.sum", "Cargo.toml", "Cargo.lock", "Gemfile", "Gemfile.lock",
}
SEVERITY_RANK = {"critical": 0, "important": 1}
TEST_GLOBS = [
    "**/*_test.py", "**/test_*.py", "**/tests/**", "**/test/**", "**/__tests__/**",
    "**/*.test.*", "**/*.spec.*",
]
FIXTURE_GLOBS = [
    "**/conftest.py", "**/factories/**", "**/factories.py", "**/factory.py", "**/fixtures/**",
    "**/__mocks__/**", "**/test-helpers*", "**/test-helpers/**", "**/testHelpers*", "**/setupTests.*",
]
TEST_DEFINITION = re.compile(
    r"^([+-])\s*(?:(?:async\s+)?(?:def|class)\s+((?:test_|Test)\w*)"
    r"|(?:describe|it|test)(?:\.(?:only|skip|each\(.*?\)))?\(\s*(['\"`])(.+?)\3)"
)
PLAN_KEEP_HEADINGS = ("global constraints", "review focus")
MARKDOWN_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
LEARNING_POINTER = (
    "Each entry names a pattern. When a change comes near one, open its file: the "
    "`## Finding` and `## Mitigation` sections say how it shows up and how to fix it."
)
LEARNINGS_INTRO = {
    "code": (
        "The following patterns have been identified in prior reviews of this codebase. "
        f"Pay special attention to whether the current changes exhibit these patterns. {LEARNING_POINTER}"
    ),
    "plan": (
        "The following patterns have been identified in prior reviews of this codebase. "
        f"Evaluate whether the proposed plan addresses or risks repeating these patterns. {LEARNING_POINTER}"
    ),
}
LEARNINGS_OUTRO = {
    "code": (
        "When evaluating changes, cross-reference against these known patterns. If a change "
        "matches a known learning, flag it explicitly and reference the learning ID. If a change "
        "deliberately avoids a previously-identified pattern, note that as a positive signal."
    ),
    "plan": (
        "When evaluating the plan, cross-reference against these known patterns. Plans that "
        "proactively address known learnings should be noted positively. Plans that risk "
        "repeating known issues should be flagged with the learning ID."
    ),
}


class PrepareError(Exception):
    pass


def git(args: list[str], cwd: Path, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True
    )
    if check and result.returncode != 0:
        raise PrepareError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def sanitize_branch(name: str) -> str:
    name = name.replace("/", "--")
    name = re.sub(r"[^A-Za-z0-9._-]", "", name)
    return name[:100] or "unknown"


def current_branch(cwd: Path) -> str:
    branch = git(["symbolic-ref", "--short", "HEAD"], cwd, check=False).strip()
    if branch:
        return branch
    sha = git(["rev-parse", "--short", "HEAD"], cwd, check=False).strip()
    return f"detached-{sha or 'unknown'}"


def workspace_scoping(project_root: Path) -> dict:
    git_root = Path(git(["rev-parse", "--show-toplevel"], project_root).strip())
    git_prefix = git(["rev-parse", "--show-prefix"], project_root).strip()
    inside_worktree = ".claude/worktrees/" in f"{git_root.as_posix()}/"
    exclude_dirs = [] if git_prefix or inside_worktree else [".claude/worktrees"]
    return {
        "git_root": git_root,
        "git_prefix": git_prefix,
        "exclude_dirs": exclude_dirs,
    }


def glob_regex(pattern: str) -> re.Pattern:
    out = ""
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out += "(?:.*/)?"
            i += 3
        elif pattern.startswith("**", i):
            out += ".*"
            i += 2
        elif pattern[i] == "*":
            out += "[^/]*"
            i += 1
        elif pattern[i] == "?":
            out += "[^/]"
            i += 1
        elif pattern[i] == "[" and "]" in pattern[i + 1:]:
            end = pattern.index("]", i + 1)
            out += "[" + pattern[i + 1:end].replace("\\", "\\\\") + "]"
            i = end + 1
        else:
            out += re.escape(pattern[i])
            i += 1
    return re.compile(out + r"\Z")


def parse_scalar(raw: str):
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        return [parse_scalar(part) for part in raw[1:-1].split(",") if part.strip()]
    if len(raw) >= 2 and raw[0] == raw[-1] == '"':
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw[1:-1]
    if len(raw) >= 2 and raw[0] == raw[-1] == "'":
        return raw[1:-1]
    if re.fullmatch(r"-?\d+", raw):
        return int(raw)
    if re.fullmatch(r"-?\d+\.\d+", raw):
        return float(raw)
    return raw


def parse_frontmatter(text: str) -> tuple[dict, str] | None:
    match = re.match(r"---\n(.*?)\n---\n?(.*)", text, re.S)
    if not match:
        return None
    fields: dict = {}
    current_list_key: str | None = None
    for line in match.group(1).splitlines():
        if not line.strip():
            continue
        list_item = re.match(r"\s+-\s+(.*)", line)
        if list_item and current_list_key:
            fields[current_list_key].append(parse_scalar(list_item.group(1)))
            continue
        top_level = re.match(r"([A-Za-z_][\w]*):\s*(.*)", line)
        if top_level:
            key, value = top_level.groups()
            if value.strip() == "":
                fields[key] = []
                current_list_key = key
            else:
                fields[key] = parse_scalar(value)
                current_list_key = None
        else:
            current_list_key = None
    return fields, match.group(2)


def path_label(path: Path, project_root: Path) -> str:
    try:
        return path.relative_to(project_root).as_posix()
    except ValueError:
        return str(path)


def update_staleness(path: Path, text: str, count: int, expire: bool) -> None:
    head, sep, rest = text.partition("\n---")
    if re.search(r"^_staleness_count:.*$", head, re.M):
        head = re.sub(r"^_staleness_count:.*$", f"_staleness_count: {count}", head, flags=re.M)
    else:
        head = f"{head}\n_staleness_count: {count}"
    if expire:
        head = re.sub(r"^status:.*$", "status: expired", head, flags=re.M)
    path.write_text(head + sep + rest)


def repository_files(git_root: Path) -> list[str]:
    output = git(["ls-files", "--cached", "--others", "--exclude-standard"], git_root)
    return [line for line in output.splitlines() if line]


def match_learnings(
    learnings_dir: Path,
    target_paths: list[str],
    all_files: list[str],
    project_root: Path,
    write: bool,
) -> dict:
    report = {"matched": [], "omitted": 0, "expired": [], "warnings": [], "entries": []}
    if not learnings_dir.is_dir():
        return report
    matched = []
    for path in sorted(learnings_dir.glob("L-*.md")):
        text = path.read_text()
        parsed = parse_frontmatter(text)
        if parsed is None:
            report["warnings"].append(f"{path.name}: unparseable frontmatter, skipped")
            continue
        fields, body = parsed
        if fields.get("status", "active") != "active":
            continue
        scope = fields.get("scope") or []
        if isinstance(scope, str):
            scope = [scope]
        patterns = [glob_regex(glob) for glob in scope]
        matches_repo = any(p.match(f) for p in patterns for f in all_files)
        previous = int(fields.get("_staleness_count", 0) or 0)
        staleness = 0 if matches_repo else previous + 1
        expire = staleness >= STALENESS_LIMIT
        if write and staleness != previous:
            update_staleness(path, text, staleness, expire)
        if expire:
            report["expired"].append(fields.get("id", path.stem))
            continue
        if any(p.match(t) for p in patterns for t in target_paths):
            matched.append((fields, path))
    matched.sort(key=lambda item: (
        SEVERITY_RANK.get(str(item[0].get("severity", "")).lower(), 9),
        -int(item[0].get("occurrences", 0) or 0),
        [-ord(c) for c in str(item[0].get("last_seen", ""))],
    ))
    report["omitted"] = max(0, len(matched) - LEARNINGS_CAP)
    for fields, path in matched[:LEARNINGS_CAP]:
        learning_id = fields.get("id", path.stem)
        report["matched"].append(learning_id)
        report["entries"].append(
            f"**[{learning_id}] {fields.get('title', '')}** "
            f"({fields.get('category', '?')}, {fields.get('severity', '?')}, "
            f"seen {fields.get('occurrences', 1)}x): `{path_label(path, project_root)}`"
        )
    return report


def learnings_section(kind: str, entries: list[str]) -> str:
    if not entries:
        return ""
    numbered = "\n".join(f"{i}. {entry}" for i, entry in enumerate(entries, 1))
    return (
        f"## Known Project Learnings\n\n{LEARNINGS_INTRO[kind]}\n\n{numbered}\n\n"
        f"{LEARNINGS_OUTRO[kind]}"
    )


def project_convention_files(project_root: Path, git_root: Path) -> list[Path]:
    for root in dict.fromkeys([project_root, git_root]):
        found = [root / name for name in ("CLAUDE.md", ".claude/CLAUDE.md") if (root / name).is_file()]
        if not found and (root / "AGENTS.md").is_file():
            found = [root / "AGENTS.md"]
        if found:
            return found
    return []


def load_sections(name: str) -> dict[str, str]:
    """Read the ```section <id>``` blocks of a prompt template, in file order."""
    text = (SKILL_DIR / "references" / name).read_text()
    sections = {
        m.group(1): m.group(2).strip()
        for m in re.finditer(r"^```section ([a-z_]+)\n(.*?)\n```\s*$", text, re.S | re.M)
    }
    if not sections:
        raise PrepareError(f"No ```section blocks in references/{name}")
    return sections


def profile_key(model: str) -> str:
    """Profile key for a model slug: drop the -fast tier and the effort suffix."""
    return EFFORT_SUFFIX.sub("", re.sub(r"-fast$", "", model))


def load_profile(key: str, section_ids: list[str]) -> tuple[dict | None, str | None]:
    """Load references/model-profiles/<key>.md. Returns (profile, warning)."""
    path = PROFILES_DIR / f"{key}.md"
    if not path.is_file():
        return None, (
            f"NO PROMPT PROFILE for `{key}`: its reviewers got the shared baseline prompt. "
            f"Add references/model-profiles/{key}.md (see the README there)."
        )
    parsed = parse_frontmatter(path.read_text())
    if parsed is None:
        return None, f"PROMPT PROFILE `{key}` has no frontmatter: using the shared baseline prompt."
    fields, body = parsed
    order = fields.get("order") or section_ids
    if isinstance(order, str):
        order = [order]
    if sorted(order) != sorted(section_ids):
        return None, (
            f"PROMPT PROFILE `{key}` has an invalid order {order} (sections are "
            f"{section_ids}): using the shared baseline prompt."
        )
    inserts: dict[tuple[str, str], str] = {}
    headings = list(re.finditer(r"^## (.+?)\s*$", body, re.M))
    for i, heading in enumerate(headings):
        match = re.fullmatch(r"(before|after) ([a-z_]+)", heading.group(1))
        if not match:
            continue  # any other heading is documentation, not prompt text
        if match.group(2) not in section_ids:
            return None, (
                f"PROMPT PROFILE `{key}` inserts {heading.group(1)!r}, but there is no "
                f"`{match.group(2)}` section: using the shared baseline prompt."
            )
        end = headings[i + 1].start() if i + 1 < len(headings) else len(body)
        inserts[(match.group(1), match.group(2))] = body[heading.end():end].strip()
    budget = fields.get("budget")
    try:
        scale = float(fields.get("budget_scale", 1))
    except (TypeError, ValueError):
        return None, (
            f"PROMPT PROFILE `{key}` has a non-numeric budget_scale: using the shared "
            "baseline prompt."
        )
    return {
        "key": key,
        "path": str(path),
        "verified_against": fields.get("verified_against"),
        "order": order,
        "style": fields.get("style", "markdown"),
        "budget_scale": None if budget == "none" else scale,
        "inserts": inserts,
    }, None


def read_budget(diff_lines: int | None, scale: float | None) -> str:
    if scale is None:
        return ""
    if diff_lines is None:
        base = PLAN_BUDGET
    else:
        base = next(n for limit, n in BUDGET_TIERS if limit is None or diff_lines <= limit)
    return (
        f"For this input, plan on roughly {max(5, round(base * scale))} file reads and "
        f"searches beyond the input itself. Reviews that run past "
        f"{REVIEWER_SETTINGS['timeout_seconds'] // 60} minutes are discarded, so if you reach "
        "that number, write the review with what you have and report anything you could not "
        "confirm as POTENTIAL."
    )


def render_prompt(sections: dict[str, str], profile: dict | None, values: dict[str, str]) -> str:
    order = profile["order"] if profile else list(sections)
    inserts = profile["inserts"] if profile else {}
    style = profile["style"] if profile else "markdown"
    parts: list[str] = []
    for section_id in order:
        body = sections[section_id]
        for name, value in values.items():
            body = body.replace("{{" + name + "}}", value)
        body = body.strip()
        if inserts.get(("before", section_id)):
            parts.append(inserts[("before", section_id)])
        if body:
            parts.append(f"<{section_id}>\n{body}\n</{section_id}>" if style == "xml" else body)
        if inserts.get(("after", section_id)):
            parts.append(inserts[("after", section_id)])
    prompt = "\n\n".join(parts)
    return re.sub(r"\n{3,}", "\n\n", prompt).strip() + "\n"


def plan_referenced_paths(plan_input: Path) -> list[str]:
    documents = sorted(plan_input.rglob("*.md")) if plan_input.is_dir() else [plan_input]
    paths: set[str] = set()
    for document in documents:
        for token in re.findall(r"[\w.-]+(?:/[\w.*-]+)+(?:\.\w+)?", document.read_text()):
            paths.add(token.strip("./").rstrip(".,:;"))
    return sorted(paths)


def markdown_sections(text: str) -> list[tuple[int, str, str]]:
    """Split markdown into (level, heading, block) parts, ignoring headings inside code fences.

    Level 0 is the text before the first heading; each block starts with its heading line.
    """
    parts: list[tuple[int, str, list[str]]] = [(0, "", [])]
    fence = None
    for line in text.splitlines():
        stripped = line.lstrip()
        if fence:
            if stripped.startswith(fence):
                fence = None
        elif stripped.startswith(("```", "~~~")):
            fence = stripped[:3]
        else:
            heading = MARKDOWN_HEADING.match(line)
            if heading:
                parts.append((len(heading.group(1)), heading.group(2), []))
        parts[-1][2].append(line)
    return [(level, heading, "\n".join(lines)) for level, heading, lines in parts]


def trim_document(text: str, keep: tuple[str, ...] | None, drop: list[str]) -> tuple[str, list[str], list[str]]:
    """Keep a document's sections by heading. Returns (text, kept headings, dropped headings).

    A section carries its subsections. A heading containing a `drop` substring removes its
    section, and wins over `keep`. With `keep` set, only the title (level 1), the text before
    it and sections whose heading contains a `keep` substring stay; with `keep` None,
    everything not dropped stays.
    """
    drop_lowered = [d.lower() for d in drop]
    stack: list[tuple[int, str | None]] = []
    blocks, kept, dropped = [], [], []
    for level, heading, block in markdown_sections(text):
        decision = None
        if level:
            while stack and stack[-1][0] >= level:
                stack.pop()
            inherited = stack[-1][1] if stack else None
            lowered = heading.lower()
            if inherited == "drop" or any(d in lowered for d in drop_lowered):
                decision = "drop"
                if inherited != "drop":
                    dropped.append(heading)
            elif keep is not None and any(k in lowered for k in keep):
                decision = "keep"
                if inherited != "keep":
                    kept.append(heading)
            else:
                decision = inherited
            stack.append((level, decision))
        if decision == "keep" or (decision is None and (keep is None or level <= 1)):
            blocks.append(block)
    return "\n".join(blocks).strip(), kept, dropped


def diff_file_chunks(diff_text: str) -> list[tuple[str, str]]:
    """Split a git diff into (path, chunk) per file; the path is the new one, or the old for deletions."""
    chunks = []
    for chunk in re.split(r"(?m)^(?=diff --git )", diff_text):
        if not chunk.startswith("diff --git "):
            continue
        new = re.search(r"(?m)^\+\+\+ b/(.+)$", chunk)
        old = re.search(r"(?m)^--- a/(.+)$", chunk)
        header = re.match(r"diff --git a/(.+) b/(.+)$", chunk, re.M)
        if new or old:
            path = (new or old).group(1)
        else:
            path = header.group(2) if header else ""
        chunks.append((path, chunk))
    return chunks


def test_index_entry(path: str, chunk: str, first_line: int, last_line: int) -> str:
    added = removed = 0
    new_names: list[str] = []
    removed_names: list[str] = []
    for line in chunk.splitlines():
        if line.startswith(("+++ ", "--- ")):
            continue
        if line.startswith("+"):
            added += 1
        elif line.startswith("-"):
            removed += 1
        definition = TEST_DEFINITION.match(line)
        if definition:
            name = definition.group(2) or f'"{definition.group(4)}"'
            (new_names if definition.group(1) == "+" else removed_names).append(name)
    changed = [n for n in new_names if n in removed_names]
    entry = f"- `{path}` (+{added}/-{removed}): lines {first_line}-{last_line}"
    for label, names in (
        ("new", [n for n in new_names if n not in changed]),
        ("edited", changed),
        ("removed", [n for n in removed_names if n not in changed]),
    ):
        if names:
            entry += f"; {label}: " + ", ".join(dict.fromkeys(names))
    return entry


def split_tests(diff_text: str, keep_globs: list[str]) -> tuple[str, str, list[str], list[str]]:
    """Move test files' hunks out of the diff. Returns (diff, tests patch, test paths, index entries).

    Fixtures, factories, conftest.py and `keep_globs` stay in the diff. Nothing moves when the
    diff holds only tests or no tests.
    """
    stay_patterns = [glob_regex(g) for g in [*FIXTURE_GLOBS, *keep_globs]]
    test_patterns = [glob_regex(g) for g in TEST_GLOBS]
    production, tests = [], []
    for path, chunk in diff_file_chunks(diff_text):
        is_test = any(p.match(path) for p in test_patterns) and not any(p.match(path) for p in stay_patterns)
        (tests if is_test else production).append((path, chunk))
    if not production or not tests:
        return diff_text, "", [], []
    entries, line = [], 1
    for path, chunk in tests:
        length = chunk.count("\n")
        entries.append(test_index_entry(path, chunk, line, line + length - 1))
        line += length
    return (
        "".join(chunk for _, chunk in production),
        "".join(chunk for _, chunk in tests),
        [path for path, _ in tests],
        entries,
    )


def tests_section(tests_path: Path, tests_patch: str, entries: list[str]) -> str:
    return (
        "## Test Changes (not in the diff)\n"
        f"The changed test files' hunks are in `{tests_path}` ({tests_patch.count(chr(10))} lines), "
        "not in the diff; fixtures, factories and `conftest.py` stay in the diff. When you check "
        "whether a production change is covered, read the hunks of the test files that cover it "
        "from that patch, using the line ranges below: always when the change writes or computes "
        "a stored or derived value, and whenever a finding depends on what a test does. Report "
        "test-coverage gaps as usual.\n\n" + "\n".join(entries)
    )


def spec_context(args) -> tuple[str, dict]:
    """Inline --spec-file in full and --plan-file trimmed to PLAN_KEEP_HEADINGS, minus --drop-section."""
    drop = args.drop_section or []
    documents, report = [], {"spec_files": args.spec_file or [], "plan_files": args.plan_file or [],
                             "kept_plan_sections": [], "dropped_sections": [], "source_bytes": 0}
    for path, keep in [(p, None) for p in args.spec_file or []] + [(p, PLAN_KEEP_HEADINGS) for p in args.plan_file or []]:
        source = Path(path).read_text()
        report["source_bytes"] += len(source.encode())
        text, kept, dropped = trim_document(source, keep, drop)
        report["kept_plan_sections"] += kept
        report["dropped_sections"] += dropped
        if text:
            documents.append(text)
    context = "\n\n".join(documents)
    report["inlined_bytes"] = len(context.encode())
    return context, report


def external_models(args) -> list[str]:
    if args.no_external:
        return []
    return [m.strip() for m in args.models.split(",") if m.strip()] if args.models else DEFAULT_MODELS


def reviewer_tasks(args, round_dir: Path, prompt_paths: dict[str, Path], input_path: Path,
                   project_root: Path, exclude_dirs: list[str]) -> list[dict]:
    return [
        {
            "model": model,
            "instance": instance,
            "type": args.type,
            "profile": profile_key(model),
            "project_root": str(project_root),
            "review_prompt_path": str(prompt_paths[profile_key(model)]),
            "output_path": str(round_dir / f"review-{re.sub(r'[/ ]', '-', model)}-{instance}.md"),
            "input_path": str(input_path),
            "input_type": "diff" if args.type == "code" else "plan_dir",
            "exclude_dirs": exclude_dirs,
        }
        for model in external_models(args)
        for instance in range(1, args.count + 1)
    ]


def prepare(args) -> dict:
    project_root = Path.cwd().resolve()
    scoping = workspace_scoping(project_root)
    git_root = scoping["git_root"]
    git_prefix = scoping["git_prefix"]
    exclude_dirs = scoping["exclude_dirs"]
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    branch = args.branch_name or current_branch(project_root)
    report: dict = {
        "status": "ok",
        "dry_run": args.dry_run,
        "type": args.type,
        "project_root": str(project_root),
        "git_root": str(git_root),
        "git_prefix": git_prefix,
        "exclude_dirs": exclude_dirs,
        "branch": branch,
        "warnings": [],
    }

    sections: list[str] = []
    if git_prefix:
        sections.append(
            "## Workspace Scope\nThis review is scoped to a subdirectory of a larger repository. "
            "All paths are relative to this workspace root. Focus your analysis on the code "
            "within this workspace."
        )
    if exclude_dirs:
        joined = ", ".join(f"`{d}`" for d in exclude_dirs)
        sections.append(
            f"## Excluded Directories\nStay out of {joined}: those directories hold code from "
            "other branches and would give you misleading context."
        )
    scope_sections = len(sections)
    tests_path, tests_patch, test_entries = None, "", []
    if args.context_stdin:
        context = sys.stdin.read().strip()
        if context:
            if not context.startswith("## "):
                context = f"## Change Context\n{context}"
            sections.append(context)

    if args.type == "code":
        diff_args = shlex.split(args.diff_args)
        relative = ["--relative"] if git_prefix else []
        diff_command = ["diff", *relative, *diff_args]
        diff_text = git(diff_command, project_root)
        if not diff_text.strip():
            raise PrepareError(f"Empty diff for: git {' '.join(diff_command)}")
        changed = [
            line for line in git(["diff", "--name-only", *diff_args], project_root).splitlines()
            if line
        ]
        full_diff_lines = diff_text.count("\n")
        round_dir = (
            project_root / ".claude" / "reviews" / sanitize_branch(branch)
            / f"{timestamp}-{args.scope_suffix}"
        )
        input_path = round_dir / "_diff.patch"
        test_paths: list[str] = []
        if not args.inline_tests:
            diff_text, tests_patch, test_paths, test_entries = split_tests(diff_text, args.keep_tests or [])
        if tests_patch:
            tests_path = round_dir / "_tests.patch"
        diff_lines: int | None = diff_text.count("\n")
        report.update({
            "git_diff_command": "git " + " ".join(diff_command),
            "diff_stat": git(["diff", "--stat", *relative, *diff_args], project_root).rstrip(),
            "diff_lines": diff_lines,
            "full_diff_lines": full_diff_lines,
            "large_diff": diff_lines > LARGE_DIFF_LINES,
            "tests_path": str(tests_path) if tests_path else None,
            "test_files": test_paths,
            "test_patch_lines": tests_patch.count("\n"),
            "changed_files": len(changed),
            "manifest_changes": [f for f in changed if Path(f).name in DEPENDENCY_MANIFESTS],
        })
        convention_files = project_convention_files(project_root, git_root)
        for path in convention_files:
            sections.append(
                f"## Project Conventions (from {path.relative_to(git_root)})\n{path.read_text().strip()}"
            )
        report["convention_files"] = [str(p) for p in convention_files]
        if args.patterns_file:
            sections.append(
                "## Codebase Patterns (from automated analysis)\n"
                + Path(args.patterns_file).read_text().strip()
            )
        spec_text, report["spec"] = spec_context(args)
        if spec_text:
            sections.append(f"## Feature Specification Context\n{spec_text}")
        target_paths = changed
        template = load_sections("code-review-prompt.md")
        learnings_kind = "code"
        internal_source = args.internal_source or "claude-code"
    else:
        if not args.plan_input:
            raise PrepareError("--plan-input is required for plan/spec reviews")
        input_path = Path(args.plan_input).resolve()
        if not input_path.exists():
            raise PrepareError(f"Plan input does not exist: {input_path}")
        if args.plan_root:
            round_dir = Path(args.plan_root).resolve() / "reviews" / timestamp
        else:
            round_dir = (
                project_root / ".claude" / "reviews" / sanitize_branch(branch)
                / f"{timestamp}-{args.type}"
            )
        target_paths = plan_referenced_paths(input_path)
        diff_lines = None
        template = load_sections("plan-review-prompt.md")
        learnings_kind = "plan"
        internal_source = args.internal_source or "opus-internal"

    reviews_root = round_dir.parent if args.type != "code" and args.plan_root else round_dir.parent.parent
    try:
        reviews_label = reviews_root.relative_to(project_root).as_posix()
    except ValueError:
        reviews_label = str(reviews_root)
    sections.insert(scope_sections, (
        f"## Other Reviews\nApart from the input files named in this prompt, stay out of `{reviews_label}`: "
        "it holds this and earlier review rounds, including other reviewers' output. Your review "
        "has to be independent of theirs for the cross-model comparison to mean anything."
    ))
    if tests_path:
        sections.insert(scope_sections + 1, tests_section(tests_path, tests_patch, test_entries))

    all_files = repository_files(git_root)
    learnings = match_learnings(
        git_root / ".claude" / "learnings", target_paths, all_files, project_root, write=not args.dry_run
    )
    report["warnings"].extend(learnings.pop("warnings"))
    section = learnings_section(learnings_kind, learnings.pop("entries"))
    if section:
        sections.append(section)
    report["learnings"] = learnings

    section_ids = list(template)
    context = "\n\n".join(sections)
    reviewer_keys = {INTERNAL_MODEL: "internal"}
    for model in external_models(args):
        reviewer_keys.setdefault(profile_key(model), "external")
    prompts: dict[str, str] = {}
    prompt_paths: dict[str, Path] = {}
    profile_warnings: list[str] = []
    internal_profile = None
    for key, kind in reviewer_keys.items():
        profile, warning = load_profile(key, section_ids)
        if warning:
            profile_warnings.append(warning)
        if kind == "internal":
            internal_profile = {
                "key": key,
                "verified_against": profile["verified_against"] if profile else None,
            }
        prompts[key] = render_prompt(template, profile, {
            "INPUT_PATH": str(input_path),
            "CONTEXT_SECTIONS": context,
            "READ_BUDGET": read_budget(diff_lines, profile["budget_scale"] if profile else 1.0),
            "DELIVERY": DELIVERY[kind],
        })
        prompt_paths[key] = round_dir / f"_review-prompt-{key}.md"
    tasks = reviewer_tasks(args, round_dir, prompt_paths, input_path, project_root, exclude_dirs)
    config_path = round_dir / "_reviewers-config.json"

    report.update({
        "round_dir": str(round_dir),
        "input_path": str(input_path),
        "internal_prompt_path": str(prompt_paths[INTERNAL_MODEL]),
        "internal_profile": internal_profile,
        "prompt_paths": {key: str(path) for key, path in prompt_paths.items()},
        "prompt_bytes": {key: len(text.encode()) for key, text in prompts.items()},
        "profile_warnings": profile_warnings,
        "internal_outputs": [
            str(round_dir / f"review-{internal_source}-{i}.md") for i in range(1, args.count + 1)
        ],
        "external_outputs": [t["output_path"] for t in tasks],
        "reviewers_config_path": str(config_path) if tasks else None,
    })

    if not args.dry_run:
        round_dir.mkdir(parents=True, exist_ok=False)
        if args.type == "code":
            input_path.write_text(diff_text)
        if tests_path:
            tests_path.write_text(tests_patch)
        for key, text in prompts.items():
            prompt_paths[key].write_text(text)
        if tasks:
            config_path.write_text(json.dumps({**REVIEWER_SETTINGS, "tasks": tasks}, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--type", choices=["code", "plan", "spec"], default="code")
    parser.add_argument("--diff-args", default="--cached",
                        help="Arguments passed to git diff (default: --cached)")
    parser.add_argument("--scope-suffix", default="staged")
    parser.add_argument("--branch-name", help="Override branch name (PR mode: head branch)")
    parser.add_argument("--plan-input", help="Plan version directory or plan/spec file")
    parser.add_argument("--plan-root", help="Plan root; round goes under <plan-root>/reviews/")
    parser.add_argument("--spec-file", action="append", help="Spec doc to inline in full (repeatable)")
    parser.add_argument("--plan-file", action="append",
                        help="Implementation plan or code reference: only its title, Global "
                             "Constraints and Review Focus sections are inlined (repeatable)")
    parser.add_argument("--drop-section", action="append",
                        help="Leave out spec/plan sections whose heading contains this text, "
                             "with their subsections (repeatable)")
    parser.add_argument("--inline-tests", action="store_true",
                        help="Keep test files' hunks in _diff.patch instead of _tests.patch")
    parser.add_argument("--keep-tests", action="append",
                        help="Glob of test files to keep in _diff.patch (repeatable)")
    parser.add_argument("--patterns-file", help="Phase 1 --deep-explore output to inline")
    parser.add_argument("--context-stdin", action="store_true",
                        help="Read a Change Context section from stdin")
    parser.add_argument("--models", help="Comma-separated external models")
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--no-external", action="store_true")
    parser.add_argument("--internal-source",
                        help="Internal reviewer file label (default: claude-code / opus-internal)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        report = prepare(args)
    except (PrepareError, OSError) as e:
        print(json.dumps({"status": "error", "error": str(e)}))
        sys.exit(1)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
