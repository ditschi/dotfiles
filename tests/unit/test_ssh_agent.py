"""Which SSH agent a shell uses (spec ssh-agent): never one started by the dotfiles."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
ENVIRONMENT = REPO / "home/core/.shell/common/environment.sh"
ZPROFILE = REPO / "home/core/.zprofile"
SHELLS = ["bash", "zsh"]


@pytest.fixture
def setup(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    runtime = tmp_path / "run"
    runtime.mkdir(mode=0o700)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls = tmp_path / "ssh-agent.calls"
    agent = bin_dir / "ssh-agent"
    agent.write_text(f'#!/bin/sh\necho "$@" >>"{calls}"\n')
    agent.chmod(0o755)
    return home, runtime, bin_dir, calls


def _env(home, bin_dir, **extra):
    env = {"HOME": str(home), "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    env.update({k: v for k, v in extra.items() if v is not None})
    return env


def _agent_sock(shell, env):
    if not shutil.which(shell):
        pytest.skip(f"{shell} is not installed")
    return subprocess.run(
        [
            shell,
            "-c",
            '. "$1" >/dev/null; printf "%s" "${SSH_AUTH_SOCK-unset}"',
            "_",
            str(ENVIRONMENT),
        ],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )


def _listen(path: Path) -> socket.socket:
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(path))
    server.listen(1)
    return server


@pytest.mark.parametrize("shell", SHELLS)
def test_existing_socket_is_kept(setup, shell):
    home, runtime, bin_dir, calls = setup
    server = _listen(runtime / "openssh_agent")
    try:
        result = _agent_sock(
            shell,
            _env(
                home,
                bin_dir,
                XDG_RUNTIME_DIR=str(runtime),
                SSH_AUTH_SOCK="/forwarded/agent",
            ),
        )
    finally:
        server.close()
    assert result.stdout == "/forwarded/agent"
    assert not calls.exists()


@pytest.mark.parametrize("shell", SHELLS)
def test_system_socket_is_exported(setup, shell):
    home, runtime, bin_dir, calls = setup
    server = _listen(runtime / "openssh_agent")
    try:
        result = _agent_sock(shell, _env(home, bin_dir, XDG_RUNTIME_DIR=str(runtime)))
    finally:
        server.close()
    assert result.stdout == str(runtime / "openssh_agent")
    assert result.stderr == ""
    assert not calls.exists()


@pytest.mark.parametrize("shell", SHELLS)
@pytest.mark.parametrize("runtime_set", [True, False])
def test_nothing_without_system_socket(setup, shell, runtime_set):
    home, runtime, bin_dir, calls = setup
    (runtime / "openssh_agent").write_text("not a socket")
    env = _env(home, bin_dir, XDG_RUNTIME_DIR=str(runtime) if runtime_set else None)
    result = _agent_sock(shell, env)
    assert result.stdout == "unset"
    assert result.stderr == ""
    assert not calls.exists()


def test_zsh_login_profile_starts_no_agent(setup):
    if not shutil.which("zsh"):
        pytest.skip("zsh is not installed")
    home, runtime, bin_dir, calls = setup
    subprocess.run(
        [
            "zsh",
            "-c",
            '. "$1"; printf "%s" "${SSH_AUTH_SOCK-unset}"',
            "_",
            str(ZPROFILE),
        ],
        env=_env(home, bin_dir, XDG_RUNTIME_DIR=str(runtime)),
        capture_output=True,
        text=True,
        check=True,
    )
    assert not calls.exists()
