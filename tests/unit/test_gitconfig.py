from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from package_sets import REPO

SHARED = REPO / "home/dot_gitconfig"
HOST_ONLY = (
    r"^(user\.(name|email|signingkey)|gpg\.|commit\.gpgsign|tag\.gpgsign"
    r"|safe\.|credential\.|https?\.|core\.sshcommand)"
)


def _git(
    *args: str, env: dict | None = None, cwd: Path | None = None
) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], env=env, cwd=cwd, capture_output=True, text=True
    )


def test_shared_gitconfig_has_no_host_only_settings():
    res = _git("config", "-f", str(SHARED), "--no-includes", "--get-regexp", HOST_ONLY)
    assert res.stdout == "", f"move to ~/.gitconfig.local:\n{res.stdout}"


def test_local_include_is_last_so_it_wins():
    res = _git("config", "-f", str(SHARED), "--no-includes", "--list")
    assert res.stdout.strip().splitlines()[-1] == "include.path=~/.gitconfig.local"


@pytest.mark.skipif(shutil.which("chezmoi") is None, reason="chezmoi not installed")
@pytest.mark.parametrize(
    "profile, email",
    [
        ("work-laptop", "dci2lr@bosch.com"),
        ("home-laptop", "chris@ditscher.me"),
        ("container", "chris@ditscher.me"),
    ],
)
def test_default_identity_per_profile(tmp_path: Path, profile: str, email: str):
    home = tmp_path / "home"
    home.mkdir()
    cfg = tmp_path / "chezmoi.yaml"
    cfg.write_text(
        f"sourceDir: {REPO / 'home'}\nmode: symlink\ndata:\n  profile: {profile}\n"
    )
    targets = [str(home / ".gitconfig"), str(home / ".gitconfig.local")]
    subprocess.run(
        [
            "chezmoi",
            "--config",
            str(cfg),
            "--persistent-state",
            str(tmp_path / "state.boltdb"),
            "-D",
            str(home),
            "apply",
            "--force",
            *targets,
        ],
        check=True,
    )
    assert (home / ".gitconfig").is_symlink()
    assert not (home / ".gitconfig.local").is_symlink()

    env = {**os.environ, "HOME": str(home), "XDG_CONFIG_HOME": str(home / ".config")}
    env.pop("GIT_CONFIG_GLOBAL", None)
    repo = tmp_path / "repo"
    _git("init", "-q", str(repo), env=env)
    assert _git("config", "user.email", env=env, cwd=repo).stdout.strip() == email
    assert (
        _git("commit", "-q", "--allow-empty", "-m", "t", env=env, cwd=repo).returncode
        == 0
    )

    # create_: later applies keep local edits
    local = home / ".gitconfig.local"
    local.write_text(local.read_text() + "# edited\n")
    subprocess.run(
        [
            "chezmoi",
            "--config",
            str(cfg),
            "--persistent-state",
            str(tmp_path / "state.boltdb"),
            "-D",
            str(home),
            "apply",
            "--force",
            *targets,
        ],
        check=True,
    )
    assert local.read_text().endswith("# edited\n")
