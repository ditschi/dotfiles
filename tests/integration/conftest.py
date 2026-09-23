from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

import pytest
import testinfra

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


@pytest.fixture(scope="session")
def docker_image():
    if not docker_available():
        pytest.skip("Docker is not available")
    subprocess.run(
        ["docker", "build", "-t", IMAGE, str(REPO / "tests/docker")],
        check=True,
    )
    return IMAGE


@pytest.fixture
def profile_env(docker_image, request):
    profile = request.param
    name = f"dotfiles-{profile}-{uuid.uuid4().hex[:8]}"
    run_apt = (
        request.node.get_closest_marker("apt") is not None
        or request.node.get_closest_marker("apt_gnome") is not None
    )
    setup_cmd = ["./bootstrap", "--profile", profile, "--yes"]
    if not run_apt:
        setup_cmd.extend(["--skip-ansible", "--no-become"])
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
            [*exec_cmd, "git", "config", "--global", "--add", "safe.directory", "/dotfiles"],
            check=False,
            capture_output=True,
            text=True,
        )
        result = subprocess.run(
            [*exec_cmd, *setup_cmd],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise AssertionError(
                f"bootstrap failed for {profile}\n"
                f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )
        yield testinfra.get_host(f"docker://{name}"), profile
    finally:
        subprocess.run(
            ["docker", "rm", "-f", name],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
