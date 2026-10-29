"""Pure text functions for learning files. Edits are line-level: lines not being changed stay byte-identical."""

import json
import re

OWNED_KEYS: tuple[str, ...] = (
    "id",
    "occurrences",
    "first_seen",
    "last_seen",
    "status",
    "promoted_to",
    "_staleness_count",
    "promotion_pending",
)
LEARNING_FILE = re.compile(r"L-(\d{3,})\.md")
TOP_LEVEL_KEY = re.compile(r"([A-Za-z_][\w]*):")
INDEX_HEADER = (
    "# Review Learnings\n"
    "\n"
    "> Auto-generated index. Do not edit manually — updated by `/deep-review` Phase 4.7.\n"
    "\n"
    "| ID | Title | Category | Severity | Status | Occurrences | Last Seen |\n"
    "|----|-------|----------|----------|--------|-------------|-----------|\n"
)


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


def split_frontmatter(text: str) -> tuple[list[str], str]:
    if "\r" in text or not text.startswith("---\n"):
        raise ValueError("learning frontmatter must open with '---' and use LF line endings")
    end = text.find("\n---\n", 3)
    if end == -1:
        if not text.endswith("\n---"):
            raise ValueError("learning frontmatter has no closing '---'")
        end = len(text) - 4
    return text[4:end].split("\n"), text[end + 5:]


def join_frontmatter(lines: list[str], body: str) -> str:
    return "---\n" + "\n".join(lines) + "\n---\n" + body


def key_span(lines: list[str], key: str) -> tuple[int, int] | None:
    for start, line in enumerate(lines):
        match = TOP_LEVEL_KEY.match(line)
        if match and match.group(1) == key:
            stop = start + 1
            while stop < len(lines) and lines[stop][:1] in (" ", "\t"):
                stop += 1
            return start, stop
    return None


def set_frontmatter_field(text: str, key: str, value: str) -> str:
    lines, body = split_frontmatter(text)
    span = key_span(lines, key)
    if span:
        lines[span[0]:span[1]] = [f"{key}: {value}"]
    else:
        lines.append(f"{key}: {value}")
    return join_frontmatter(lines, body)


def remove_frontmatter_field(text: str, key: str) -> str:
    lines, body = split_frontmatter(text)
    span = key_span(lines, key)
    if span:
        del lines[span[0]:span[1]]
    return join_frontmatter(lines, body)


def merge_scope(text: str, globs: list[str]) -> str:
    parsed = parse_frontmatter(text)
    if parsed is None:
        raise ValueError("learning frontmatter does not parse")
    existing = parsed[0].get("scope") or []
    if isinstance(existing, str):
        existing = [existing]
    additions = []
    for glob in globs:
        if glob not in existing and glob not in additions:
            additions.append(glob)
    if not additions:
        return text
    lines, body = split_frontmatter(text)
    new_items = [f"  - {json.dumps(glob, ensure_ascii=False)}" for glob in additions]
    span = key_span(lines, "scope")
    if span is None:
        lines.extend(["scope:", *new_items])
    elif lines[span[0]].strip() != "scope:":
        raise ValueError("scope must be a block list to merge globs into it")
    else:
        lines[span[1]:span[1]] = new_items
    return join_frontmatter(lines, body)


def record_recurrence(text: str, draft_body: str, today: str, round_dir: str, scope: list[str]) -> str:
    split_frontmatter(text)
    parsed = parse_frontmatter(text)
    if parsed is None:
        raise ValueError("learning frontmatter does not parse")
    fields = parsed[0]
    if fields.get("status", "active") != "active":
        raise ValueError(f"{fields.get('id', 'learning')} is {fields.get('status')}, not active")
    occurrences = int(fields.get("occurrences", 1) or 1) + 1
    text = set_frontmatter_field(text, "occurrences", str(occurrences))
    text = set_frontmatter_field(text, "last_seen", json.dumps(today, ensure_ascii=False))
    text = merge_scope(text, scope)
    if not text.endswith("\n"):
        text += "\n"
    return text + f"\n## Recurrence — {today} (`{round_dir}`)\n\n{draft_body.strip()}\n"


def new_learning_text(draft: str, learning_id: str, today: str) -> str:
    lines, body = split_frontmatter(draft)
    for key in OWNED_KEYS:
        span = key_span(lines, key)
        while span:
            del lines[span[0]:span[1]]
            span = key_span(lines, key)
    lines = [
        f"id: {learning_id}",
        *lines,
        "occurrences: 1",
        f"first_seen: {json.dumps(today, ensure_ascii=False)}",
        f"last_seen: {json.dumps(today, ensure_ascii=False)}",
        "status: active",
        'promoted_to: ""',
        "_staleness_count: 0",
    ]
    return join_frontmatter(lines, body)


def next_learning_id(names: list[str]) -> str:
    numbers = [int(match.group(1)) for name in names if (match := LEARNING_FILE.fullmatch(name))]
    return f"L-{max(numbers, default=0) + 1:03d}"


def bump_staleness(text: str, count: int, expire: bool) -> str:
    text = set_frontmatter_field(text, "_staleness_count", str(count))
    if expire:
        text = set_frontmatter_field(text, "status", "expired")
    return text


def render_index(learnings: list[dict]) -> str:
    def cell(value) -> str:
        return str(value if value is not None else "").replace("|", "\\|")

    ordered = sorted(
        learnings,
        key=lambda fields: (str(fields.get("last_seen", "")), str(fields.get("first_seen", "")), str(fields.get("id", ""))),
        reverse=True,
    )
    rows = [
        "| " + " | ".join(cell(fields.get(column)) for column in
                          ("id", "title", "category", "severity", "status", "occurrences", "last_seen")) + " |"
        for fields in ordered
    ]
    return INDEX_HEADER + "".join(f"{row}\n" for row in rows)
