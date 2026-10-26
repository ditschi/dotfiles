from __future__ import annotations

import os
import subprocess
from pathlib import Path

from package_sets import REPO

COPY = REPO / "home/core/.local/bin/copy-selection"
CONFIG = REPO / "home/core/.config/zellij/config.kdl"


def _fake(bin_dir: Path, name: str, log: Path) -> None:
    script = bin_dir / name
    script.write_text(f'#!/bin/sh\necho "{name} $*" >> {log}\ncat >> {log}\n')
    script.chmod(0o755)


def _copy(env: dict, text: str = "sudo apt autoremove") -> None:
    subprocess.run(["sh", str(COPY)], input=text, text=True, env=env, check=True)


def _env(bin_dir: Path, **extra: str) -> dict:
    env = {
        k: v for k, v in os.environ.items() if k not in ("WAYLAND_DISPLAY", "DISPLAY")
    }
    env["PATH"] = f"{bin_dir}:/usr/bin:/bin"
    env.update(extra)
    return env


def test_config_uses_the_copy_script():
    assert 'copy_command "copy-selection"' in CONFIG.read_text()
    assert os.access(COPY, os.X_OK)


def test_wayland_copies_to_primary(tmp_path):
    log = tmp_path / "log"
    _fake(tmp_path, "wl-copy", log)
    _copy(_env(tmp_path, WAYLAND_DISPLAY="wayland-0"))
    assert log.read_text() == "wl-copy --primary\nsudo apt autoremove"


def test_x11_copies_to_primary(tmp_path):
    log = tmp_path / "log"
    _fake(tmp_path, "xclip", log)
    _copy(_env(tmp_path, DISPLAY=":0"))
    assert log.read_text() == "xclip -selection primary -in\nsudo apt autoremove"


def test_without_graphical_session_drops_the_text(tmp_path):
    log = tmp_path / "log"
    _fake(tmp_path, "wl-copy", log)
    _copy(_env(tmp_path))
    assert not log.exists()
