"""Set the terminal font of Ddterm and the VS Code terminal to the Nerd Font."""

from __future__ import annotations

import re
from pathlib import Path

from . import system
from .core import log

FONT_FAMILY = "FiraCode Nerd Font Mono"
VSCODE_KEY = "terminal.integrated.fontFamily"
_VSCODE_ENTRY = re.compile(
    r'("terminal\.integrated\.fontFamily"\s*:\s*)"(?:[^"\\]|\\.)*"'
)


def with_vscode_font(text: str, family: str = FONT_FAMILY) -> str:
    """`settings.json` text with only the terminal font key set; comments and other keys stay.

    The file is JSONC that VS Code also writes, so it is edited as text, not re-serialised.
    """
    entry = f'"{VSCODE_KEY}": "{family}"'
    if _VSCODE_ENTRY.search(text):
        return _VSCODE_ENTRY.sub(lambda m: f'{m.group(1)}"{family}"', text, count=1)
    if not text.strip():
        return "{\n    " + entry + "\n}\n"
    start = text.find("{")
    if start < 0:
        raise ValueError("settings.json is not a JSON object")
    head, rest = text[: start + 1], text[start + 1 :]  # noqa: E203
    empty = re.match(r"\s*\}", rest) is not None
    if empty:
        return f"{head}\n    {entry}\n{rest.lstrip()}"
    return f"{head}\n    {entry},{rest}"


def set_vscode_font(home: Path, family: str = FONT_FAMILY) -> bool:
    """Only when VS Code has a user directory; returns True when the file changed."""
    user_dir = home / ".config" / "Code" / "User"
    if not user_dir.is_dir():
        return False
    path = user_dir / "settings.json"
    old = path.read_text(encoding="utf-8") if path.is_file() else ""
    try:
        new = with_vscode_font(old, family)
    except ValueError as error:
        log(f"{path}: {error}; terminal font not set")
        return False
    if new == old:
        return False
    path.write_text(new, encoding="utf-8")
    log(f"set {VSCODE_KEY} in {path}")
    return True


DDTERM_SCHEMA = "org.gnome.shell.extensions.ddterm"
DDTERM_SCHEMA_DIR = Path(
    ".local/share/gnome-shell/extensions/ddterm@amezin.github.com/schemas"
)


def ddterm_font(current: str, family: str = FONT_FAMILY) -> str:
    """`'Monospace Regular 12'` -> `'<family> 12'`; the size is kept."""
    size = re.search(r"\s(\d+(?:\.\d+)?)\s*'?$", current.strip())
    return f"{family} {size.group(1) if size else 10}"


def set_ddterm_font(home: Path, family: str = FONT_FAMILY) -> bool:
    """Only when the Ddterm extension (with its own schema) is installed; returns True on a change.

    The schema lives in the extension directory, so gsettings needs `--schemadir`.
    """
    schemas = home / DDTERM_SCHEMA_DIR
    if not schemas.is_dir() or not system.have("gsettings"):
        return False
    base = ["gsettings", "--schemadir", str(schemas)]
    got = system.run(
        [*base, "get", DDTERM_SCHEMA, "custom-font"], check=False, capture=True
    )
    if got.returncode != 0:
        log("could not read the Ddterm font; not set")
        return False
    wanted = ddterm_font(got.stdout or "", family)
    system_font = system.run(
        [*base, "get", DDTERM_SCHEMA, "use-system-font"], check=False, capture=True
    )
    changed = False
    if (got.stdout or "").strip().strip("'") != wanted:
        system.run(
            [*base, "set", DDTERM_SCHEMA, "custom-font", wanted],
            check=False,
            capture=True,
        )
        changed = True
    if (system_font.stdout or "").strip() != "false":
        system.run(
            [*base, "set", DDTERM_SCHEMA, "use-system-font", "false"],
            check=False,
            capture=True,
        )
        changed = True
    if changed:
        log(f"set the Ddterm font to {wanted}")
    return changed
