from __future__ import annotations

import subprocess
import shutil
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
def test_migrate_clears_old_root_symlinks(tmp_path: Path, docker_image):
    repo = tmp_path / "dotfiles"
    (repo / ".zsh/config").mkdir(parents=True)
    (repo / ".zshrc").write_text("legacy shell\n")
    (repo / ".zsh/config/custom.zsh").write_text("legacy alias\n")
    (repo / "install.py").write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "def create_links_for_directory():\n    pass\n"
        "assert sys.argv[1:] == ['--update', '--force']\n"
        "repo = Path(__file__).parent\n"
        "for name in ('.zshrc', '.zsh/config/custom.zsh'):\n"
        "    target = Path.home() / name\n"
        "    target.parent.mkdir(parents=True, exist_ok=True)\n"
        "    target.unlink(missing_ok=True)\n"
        "    target.symlink_to(repo / name)\n"
    )

    def git(*args):
        return subprocess.run(
            ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
        ).stdout.strip()

    git("init", "-q")
    git("config", "user.name", "Migration Test")
    git("config", "user.email", "migration@example.com")
    git("commit", "--allow-empty", "-qm", "initial")
    git("add", ".")
    git("commit", "-qm", "legacy layout")
    old_sha = git("rev-parse", "HEAD")
    git("rm", "-r", ".zsh", ".zshrc")
    for directory in ("home", "machine", "ansible"):
        shutil.copytree(
            REPO / directory,
            repo / directory,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    for filename in ("bootstrap", "install.py"):
        shutil.copy2(REPO / filename, repo / filename)
    git("add", ".")
    git("commit", "-qm", "machine layout")
    name = f"dotfiles-migrate-{uuid.uuid4().hex[:8]}"
    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            name,
            "-v",
            f"{repo}:/dotfiles:rw",
            "-e",
            "DOTFILES_REPO=/dotfiles",
            "-e",
            "DEBIAN_FRONTEND=noninteractive",
            "-e",
            "MACHINE_SKIP_BW=1",
            docker_image,
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
            [
                *exec_cmd,
                "git",
                "config",
                "--global",
                "--add",
                "safe.directory",
                "/dotfiles",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        # Old-style links into repo root (targets need not exist)
        subprocess.run(
            [
                *exec_cmd,
                "bash",
                "-lc",
                "ln -sfn /dotfiles/.zshrc $HOME/.zshrc && ln -sfn /dotfiles/.zsh $HOME/.zsh",
            ],
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
                "--features",
                "zsh-full",
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
            [
                *exec_cmd,
                "bash",
                "-lc",
                "test -x $HOME/.local/share/machine/rollback.sh",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        assert rollback.returncode == 0
        restored = subprocess.run(
            [
                *exec_cmd,
                "bash",
                "-lc",
                "$HOME/.local/share/machine/rollback.sh && "
                'test "$(readlink $HOME/.zshrc)" = /dotfiles/.zshrc && '
                'test "$(readlink $HOME/.zsh/config/custom.zsh)" = /dotfiles/.zsh/config/custom.zsh',
            ],
            capture_output=True,
            text=True,
        )
        assert restored.returncode == 0, restored.stdout + restored.stderr
        assert git("rev-parse", "HEAD") == old_sha
    finally:
        subprocess.run(
            ["docker", "rm", "-f", name],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
