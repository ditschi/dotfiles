"""Glob patterns with `**` for any number of directories, matched against repository paths."""

from __future__ import annotations

import re
from functools import lru_cache


def matches(path: str, patterns: list[str]) -> bool:
    return any(_glob_regex(pattern).fullmatch(path) for pattern in patterns)


@lru_cache(maxsize=None)
def _glob_regex(pattern: str) -> re.Pattern:
    regex = ""
    for token in re.split(r"(\*\*/|\*\*|\*|\?)", pattern):
        regex += {"**/": "(?:.*/)?", "**": ".*", "*": "[^/]*", "?": "[^/]"}.get(
            token, re.escape(token)
        )
    return re.compile(regex)
