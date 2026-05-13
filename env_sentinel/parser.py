"""
.env file parser — handles comments, quoted values, multiline, export prefix.
"""

import re
from dataclasses import dataclass, field


@dataclass
class EnvEntry:
    key: str
    value: str
    raw_line: str
    line_number: int
    has_value: bool          # False for placeholder keys (KEY= with no value)
    is_comment: bool = False


@dataclass
class ParsedEnv:
    path: str
    entries: list[EnvEntry] = field(default_factory=list)

    @property
    def keys(self) -> set[str]:
        return {e.key for e in self.entries if not e.is_comment}

    @property
    def mapping(self) -> dict[str, str]:
        return {e.key: e.value for e in self.entries if not e.is_comment}

    def get(self, key: str) -> str | None:
        return self.mapping.get(key)


# Regex for a valid KEY= line (with optional `export ` prefix)
_KEY_RE = re.compile(
    r"^(?:export\s+)?"           # optional "export "
    r"([A-Za-z_][A-Za-z0-9_]*)" # KEY
    r"\s*=\s*(.*)?$"             # = VALUE (optional)
)


def _strip_inline_comment(value: str) -> str:
    """Remove trailing # comment from unquoted value."""
    # Only strip if not inside quotes
    if value.startswith(("'", '"')):
        return value
    idx = value.find(" #")
    if idx == -1:
        idx = value.find("\t#")
    if idx != -1:
        return value[:idx].rstrip()
    return value


def _unquote(value: str) -> str:
    """Strip surrounding single or double quotes."""
    if len(value) >= 2:
        if (value[0] == '"' and value[-1] == '"') or \
           (value[0] == "'" and value[-1] == "'"):
            return value[1:-1]
    return value


def parse(path: str) -> ParsedEnv:
    """Parse a .env file and return a ParsedEnv."""
    result = ParsedEnv(path=path)
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return result

    i = 0
    while i < len(lines):
        line = lines[i]
        raw = line.rstrip("\n")
        stripped = raw.strip()

        # Skip blank lines and comments
        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        m = _KEY_RE.match(stripped)
        if not m:
            i += 1
            continue

        key = m.group(1)
        raw_value = (m.group(2) or "").strip()

        # Handle multiline double-quoted values
        if raw_value.startswith('"') and not raw_value.endswith('"'):
            collected = [raw_value]
            i += 1
            while i < len(lines):
                extra = lines[i].rstrip("\n")
                collected.append(extra)
                if extra.rstrip().endswith('"'):
                    break
                i += 1
            raw_value = "\n".join(collected)

        raw_value = _strip_inline_comment(raw_value)
        value = _unquote(raw_value)
        has_value = bool(value)

        result.entries.append(EnvEntry(
            key=key,
            value=value,
            raw_line=raw,
            line_number=i + 1,
            has_value=has_value,
        ))
        i += 1

    return result


def parse_string(content: str, path: str = "<string>") -> ParsedEnv:
    """Parse .env content from a string."""
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
        f.write(content)
        tmp = f.name
    try:
        result = parse(tmp)
        result.path = path
        return result
    finally:
        os.unlink(tmp)
