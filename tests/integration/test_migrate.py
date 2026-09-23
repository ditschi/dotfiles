from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
IMAGE = "dotfiles-preset-test:local"


def docker_available() -> bool:
    try:
        subprocess.run(
            ["docker", "info"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


@pytest.mark.docker
def test_migrate_clears_old_root_symlinks(tmp_path: Path):
    if not docker_available():
        pytest.skip("Docker is not available")
    subprocess.run(
        ["docker", "build", "-t", IMAGE, str(REPO / "tests/docker")],
        check=True,
    )
    name = f"dotfiles-migrate-{uuid.uuid4().hex[:8]}"
    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            name,
            "-v",
            f"{REPO}:/dotfiles:ro",
            "-e",
            "DOTFILES_REPO=/dotfiles",
            "-e",
            "DEBIAN_FRONTEND=noninteractive",
            "-e",
            "MACHINE_SKIP_BW=1",
            IMAGE,
            "sleep",
            "infinity",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    try:
        exec_cmd = ["docker", "exec", "-u", "tester", "-w", "/dotfiles", name]
        subprocess.run(
            [*exec_cmd, "git", "config", "--global", "--add", "safe.directory", "/dotfiles"],
            check=False,
            capture_output=True,
            text=True,
        )
        # Old-style links into repo root (targets need not exist)
        subprocess.run(
            [*exec_cmd, "bash", "-lc", "ln -sfn /dotfiles/.zshrc $HOME/.zshrc && ln -sfn /dotfiles/.zsh $HOME/.zsh"],
            check=True,
            capture_output=True,
            text=True,
        )
        result = subprocess.run(
            [
                *exec_cmd,
                "./bootstrap",
                "--profile",
                "home-laptop",
                "--yes",
                "--skip-ansible",
                "--no-become",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise AssertionError(
                f"migrate/setup failed\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )
        # Chezmoi should have replaced links to home/dot_*
        link = subprocess.run(
            [*exec_cmd, "bash", "-lc", "readlink $HOME/.zshrc"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert "home/dot_zshrc" in link or "home/dot_zshrc" in link.replace("\\", "/")
        rollback = subprocess.run(
            [*exec_cmd, "bash", "-lc", "test -x $HOME/.local/share/machine/rollback.sh"],
            check=False,
            capture_output=True,
            text=True,
        )
        assert rollback.returncode == 0
    finally:
        subprocess.run(
            ["docker", "rm", "-f", name],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
