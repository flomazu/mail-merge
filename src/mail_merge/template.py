"""Load the body template and fill placeholders like {Company}.

A placeholder is a column name in curly braces. `{greeting}` is reserved: it is
filled with the greeting built from the config pattern (see build_greeting).
"""

from __future__ import annotations

import re
from pathlib import Path

from docx import Document

from mail_merge.config import ConfigError

GREETING = "greeting"
_PLACEHOLDER = re.compile(r"\{([^{}\r\n]+)\}")


def load_template(path: Path) -> str:
    """Return the template text. From .docx only the plain text is used."""
    if not path.is_file():
        raise ConfigError(f"Template file not found: {path}")
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return path.read_text(encoding="utf-8-sig")
    if suffix == ".docx":
        return "\n".join(p.text for p in Document(str(path)).paragraphs)
    raise ConfigError(f"Unsupported template type '{suffix}'. Use .txt or .docx.")


def placeholders(text: str) -> set[str]:
    """Names of all placeholders used in a text."""
    return {match.strip() for match in _PLACEHOLDER.findall(text)}


def fill(text: str, values: dict[str, str]) -> str:
    """Replace every placeholder with its value. All names must be in `values`."""
    return _PLACEHOLDER.sub(lambda m: values[m.group(1).strip()], text)


def build_greeting(pattern: str, fallback: str, values: dict[str, str]) -> str:
    """Fill the greeting pattern, or use the fallback if a value is missing."""
    names = placeholders(pattern)
    if not pattern or any(not values.get(name) for name in names):
        return fallback
    return fill(pattern, values)
