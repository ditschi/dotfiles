from __future__ import annotations

import fcntl
import os
import subprocess
import uuid
from contextlib import contextmanager
from pathlib import Path

import pytest
import testinfra
from insecure_tls import insecure_tls

REPO = Path(__file__).resolve().parents[2]
# Ubuntu releases the container tests run on, default first; pick another with
# UBUNTU_VERSION=<version>.
UBUNTU_VERSIONS = ("26.04", "24.04")
UBUNTU_VERSION = os.environ.get("UBUNTU_VERSION", UBUNTU_VERSIONS[0])
# Test-only escape hatch for hosts that intercept TLS; containers are thrown away.
# On by default on work machines; DOTFILES_TEST_INSECURE_TLS=0|1 overrides.
INSECURE_TLS = insecure_tls()
INSECURE_TLS_ENV = (
    "PYTHONHTTPSVERIFY=0",
    "GIT_SSL_NO_VERIFY=1",
    "ANSIBLE_GALAXY_IGNORE_CERTS=1",
    "UV_NATIVE_TLS=0",
    "UV_INSECURE_HOST=*",
)
IMAGE = (
    "dotfiles-preset-test:local"
    if UBUNTU_VERSION == UBUNTU_VERSIONS[0]
    else f"dotfiles-preset-test:ubuntu-{UBUNTU_VERSION}"
)
# Local runs send the apt traffic of the APT tests through one caching proxy container
# (apt-cacher-ng), kept running between runs. Off in CI, where the cache starts empty.
# DOTFILES_TEST_APT_CACHE=0|1 overrides; remove it with `docker rm -f dotfiles-test-apt-cache`.
APT_CACHE = os.environ.get(
    "DOTFILES_TEST_APT_CACHE", "0" if os.environ.get("CI") else "1"
) not in ("0", "")
APT_CACHE_NAME = "dotfiles-test-apt-cache"
APT_CACHE_NETWORK = "dotfiles-test"


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


@contextmanager
def shared_lock(tmp_path_factory, name: str):
    """Lock shared by all pytest-xdist workers of a run (one builds, the others wait)."""
    with open(tmp_path_factory.getbasetemp().parent / f"{name}.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


@pytest.fixture(scope="session")
def docker_image(tmp_path_factory):
    if not docker_available():
        pytest.skip("Docker is not available")
    if UBUNTU_VERSION not in UBUNTU_VERSIONS:
        pytest.fail(f"UBUNTU_VERSION={UBUNTU_VERSION} not in {UBUNTU_VERSIONS}")
    with shared_lock(tmp_path_factory, "docker-build"):
        subprocess.run(
            [
                "docker",
                "build",
                "--build-arg",
                f"UBUNTU_VERSION={UBUNTU_VERSION}",
                "--build-arg",
                f"INSECURE_TLS={int(INSECURE_TLS)}",
                "-t",
                IMAGE,
                str(REPO / "tests/docker"),
            ],
            check=True,
        )
    return IMAGE


def docker_ok(*args: str) -> bool:
    return subprocess.run(["docker", *args], capture_output=True).returncode == 0


@pytest.fixture(scope="session")
def apt_proxy(docker_image, tmp_path_factory) -> str:
    """URL of the caching apt proxy, started when missing; "" when APT_CACHE is off."""
    if not APT_CACHE:
        return ""
    image = f"{APT_CACHE_NAME}:local"
    with shared_lock(tmp_path_factory, "apt-cache"):
        subprocess.run(
            [
                "docker",
                "build",
                "-q",
                "-t",
                image,
                str(REPO / "tests/docker/apt-cache"),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        if not docker_ok("network", "inspect", APT_CACHE_NETWORK):
            subprocess.run(
                ["docker", "network", "create", APT_CACHE_NETWORK],
                check=True,
                stdout=subprocess.DEVNULL,
            )
        if not docker_ok("start", APT_CACHE_NAME):
            subprocess.run(
                [
                    "docker",
                    "run",
                    "-d",
                    "--name",
                    APT_CACHE_NAME,
                    "--network",
                    APT_CACHE_NETWORK,
                    "-v",
                    f"{APT_CACHE_NAME}:/var/cache/apt-cacher-ng",
                    image,
                ],
                check=True,
                stdout=subprocess.DEVNULL,
            )
    return f"http://{APT_CACHE_NAME}:3142"


MACHINE_CLI = ["uv", "run", "--script", "machine_cli/machine"]


def wants_apt(request) -> bool:
    """True for tests marked apt / apt_gnome: they run the real ansible apply."""
    return any(request.node.get_closest_marker(m) for m in ("apt", "apt_gnome"))


def apt_proxy_for(request) -> str:
    """The apt proxy for an APT test, else "" (other tests do not touch apt)."""
    return request.getfixturevalue("apt_proxy") if wants_apt(request) else ""


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
    apt_proxy: str = "",
):
    """Start a throwaway container with the repo at /dotfiles.

    Yields (container name, `docker exec` prefix running as `user` in /dotfiles).
    `env` is set on the container, `exec_env` only for commands run through the prefix.
    With `apt_proxy`, apt in the container downloads through that proxy.
    """
    name = f"dotfiles-{prefix}-{uuid.uuid4().hex[:8]}"
    cmd = ["docker", "run", "-d", "--name", name]
    if hostname:
        cmd += ["--hostname", hostname]
    if apt_proxy:
        cmd += ["--network", APT_CACHE_NETWORK]
    cmd += ["-v", f"{repo}:/dotfiles:{repo_mode}"]
    for item in (
        "DOTFILES_REPO=/dotfiles",
        "DEBIAN_FRONTEND=noninteractive",
        *env,
        *(INSECURE_TLS_ENV if INSECURE_TLS else ()),
    ):
        cmd += ["-e", item]
    subprocess.run(
        [*cmd, image, "sleep", "infinity"], check=True, capture_output=True, text=True
    )
    try:
        if apt_proxy:
            subprocess.run(
                [
                    "docker",
                    "exec",
                    "-u",
                    "root",
                    name,
                    "sh",
                    "-c",
                    # retries: the proxy passes on a dropped upstream download as 503
                    f'echo \'Acquire::http::Proxy "{apt_proxy}"; Acquire::Retries "5";\''
                    " >/etc/apt/apt.conf.d/01-test-proxy",
                ],
                check=True,
                capture_output=True,
            )
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


# Test hosts: name -> (context, device, hardware Ansible would detect).
TEST_HOSTS = {
    "private-desktop": ("private", "desktop", ""),
    "work-desktop": ("work", "desktop", ""),
    "private-server": ("private", "server", ""),
    "container": ("", "container", ""),
}


def host_env(context: str, device: str, hardware: str = "") -> tuple[str, ...]:
    """Docker means the container device without context unless overridden."""
    env = [f"MACHINE_DEVICE_OVERRIDE={device}", f"MACHINE_CONTEXT_OVERRIDE={context}"]
    if hardware:
        env.append(f"MACHINE_HARDWARE={hardware}")
    return tuple(env)


@pytest.fixture
def profile_env(docker_image, request):
    name = request.param
    context, device, hardware = TEST_HOSTS[name]
    # Dotfiles only; the APT runs are in test_host_yaml_install.py
    setup_cmd = [
        "./bootstrap",
        "--device",
        device,
        "--yes",
        "--skip-ansible",
        "--no-become",
    ]
    if context:
        setup_cmd.extend(["--context", context])
    with running_container(
        docker_image,
        name,
        env=("MACHINE_SKIP_TOOLS=1", *host_env(context, device, hardware)),
    ) as (container, exec_cmd):
        run_checked(exec_cmd, setup_cmd, f"bootstrap for {name}")
        yield testinfra.get_host(f"docker://{container}"), name
