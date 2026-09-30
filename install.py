#!/usr/bin/env python3
"""Backward-compatible wrapper. Prefer ./bootstrap or `machine setup`."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def _in_docker() -> bool:
    return Path("/.dockerenv").is_file()


def _ensure_uv() -> None:
    """executable_machine's shebang needs uv; ./bootstrap installs it, this
    legacy wrapper does the same for anyone still calling install.py directly."""
    if shutil.which("uv"):
        return
    local_bin = Path.home() / ".local/bin"
    local_bin.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "UV_INSTALL_DIR": str(local_bin)}
    try:
        script = subprocess.run(
            ["curl", "-LsSf", "https://astral.sh/uv/install.sh"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        subprocess.run(["sh"], input=script, text=True, check=True, env=env)
    except (OSError, subprocess.CalledProcessError):
        print("install.py: could not install uv", file=sys.stderr)
        return
    os.environ["PATH"] = f"{local_bin}:{os.environ.get('PATH', '')}"


def main() -> int:
    repo = Path(__file__).resolve().parent
    machine = repo / "home" / "dot_local" / "bin" / "executable_machine"
    if not machine.exists():
        print(f"machine helper not found at {machine}", file=sys.stderr)
        return 1

    args = sys.argv[1:]
    if "--help" in args or "-h" in args:
        print(
            "install.py is a wrapper. Use ./bootstrap or: machine setup|update|migrate"
        )
        print(
            "Mapped flags: --update -> machine update, --new-host/--ui -> machine setup"
        )
        return 0

    if "--dry-run" in args:
        print(
            "install.py --dry-run is no longer supported; use ansible-playbook --check",
            file=sys.stderr,
        )
        return 2

    if "--update" in args:
        mapped = ["update"]
        if "--force" in args:
            mapped.append("--force")
    elif _in_docker():
        mapped = ["setup", "--profile", "container", "--yes", "--no-become"]
    else:
        mapped = ["setup"]
        if "--non-interactive" in args:
            mapped.append("--yes")
        profile = os.environ.get("MACHINE_PROFILE_NAME")
        if profile:
            mapped.extend(["--profile", profile])

    _ensure_uv()
    os.execv(str(machine), [str(machine), *mapped])
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
