from __future__ import annotations

import os
import subprocess
import uuid
from contextlib import contextmanager
from pathlib import Path

import pytest
import testinfra

REPO = Path(__file__).resolve().parents[2]
# Ubuntu releases the container tests run on, default first; pick another with
# UBUNTU_VERSION=<version>.
UBUNTU_VERSIONS = ("26.04", "24.04")
UBUNTU_VERSION = os.environ.get("UBUNTU_VERSION", UBUNTU_VERSIONS[0])
IMAGE = (
    "dotfiles-preset-test:local"
    if UBUNTU_VERSION == UBUNTU_VERSIONS[0]
    else f"dotfiles-preset-test:ubuntu-{UBUNTU_VERSION}"
)


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


@pytest.fixture(scope="session")
def docker_image():
    if not docker_available():
        pytest.skip("Docker is not available")
    if UBUNTU_VERSION not in UBUNTU_VERSIONS:
        pytest.fail(f"UBUNTU_VERSION={UBUNTU_VERSION} not in {UBUNTU_VERSIONS}")
    subprocess.run(
        [
            "docker",
            "build",
            "--build-arg",
            f"UBUNTU_VERSION={UBUNTU_VERSION}",
            "-t",
            IMAGE,
            str(REPO / "tests/docker"),
        ],
        check=True,
    )
    return IMAGE


MACHINE_CLI = ["uv", "run", "--script", "home/dot_local/bin/executable_machine"]


def wants_apt(request) -> bool:
    """True for tests marked apt / apt_gnome: they run the real ansible apply."""
    return any(request.node.get_closest_marker(m) for m in ("apt", "apt_gnome"))


@contextmanager
def running_container(
    image: str,
    prefix: str,
    *,
    repo: Path = REPO,
    repo_mode: str = "ro",
    hostname: str = "",
    user: str = "tester",
    env: tuple[str, ...] = (),
    exec_env: tuple[str, ...] = (),
):
    """Start a throwaway container with the repo at /dotfiles.

    Yields (container name, `docker exec` prefix running as `user` in /dotfiles).
    `env` is set on the container, `exec_env` only for commands run through the prefix.
    """
    name = f"dotfiles-{prefix}-{uuid.uuid4().hex[:8]}"
    cmd = ["docker", "run", "-d", "--name", name]
    if hostname:
        cmd += ["--hostname", hostname]
    cmd += ["-v", f"{repo}:/dotfiles:{repo_mode}"]
    for item in ("DOTFILES_REPO=/dotfiles", "DEBIAN_FRONTEND=noninteractive", *env):
        cmd += ["-e", item]
    subprocess.run(
        [*cmd, image, "sleep", "infinity"], check=True, capture_output=True, text=True
    )
    try:
        exec_cmd = ["docker", "exec", "-u", user, "-e", f"HOME=/home/{user}"]
        for item in exec_env:
            exec_cmd += ["-e", item]
        exec_cmd += ["-w", "/dotfiles", name]
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
        yield name, exec_cmd
    finally:
        subprocess.run(
            ["docker", "rm", "-f", name],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def run_checked(exec_cmd: list[str], cmd: list[str], what: str) -> None:
    """Run a command in the container; fail the test with its output on error."""
    result = subprocess.run(
        [*exec_cmd, *cmd], check=False, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise AssertionError(
            f"{what} failed\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )


@pytest.fixture
def profile_env(docker_image, request):
    profile = request.param
    setup_cmd = ["./bootstrap", "--profile", profile, "--yes"]
    if not wants_apt(request):
        setup_cmd.extend(["--skip-ansible", "--no-become"])
    with running_container(docker_image, profile) as (name, exec_cmd):
        run_checked(exec_cmd, setup_cmd, f"bootstrap for {profile}")
        yield testinfra.get_host(f"docker://{name}"), profile
