"""Local verification (replaces tests/run.sh): `uvx nox` runs everything, `uvx nox -l` lists sessions.

Each session gets a uv-managed venv with the pinned test dependencies. Extra pytest
arguments are passed through: `uvx nox -s tests -- -k handoff`.
"""

import shutil
import subprocess

import nox

nox.options.default_venv_backend = "uv"
nox.options.sessions = ["compile", "tests", "ansible", "docker"]

PYTHON = "3.12"
PLAYBOOKS_LINT = [
    "ansible/workstation.yml",
    "ansible/homelab.yml",
    "ansible/site.yml",
    "ansible/dump_packages.yml",
    "ansible/dump_monitoring.yml",
]


@nox.session(python=PYTHON)
def compile(session: nox.Session) -> None:
    """Byte-compile the machine CLI and installer."""
    session.run(
        "python",
        "-m",
        "py_compile",
        "machine_cli/machine",
    )
    session.run("python", "-m", "compileall", "-q", "machine_cli")


@nox.session(python=PYTHON)
def tests(session: nox.Session) -> None:
    """Unit tests."""
    session.install("-r", "tests/requirements.txt")
    session.run("pytest", "tests/unit", "-q", *session.posargs)


@nox.session(name="code-health", python=False)
def code_health(session: nox.Session) -> None:
    """ai-health scan and score per component (docs/code-health.md); arguments go to the scan."""
    session.run("scripts/aihealth", "scan", *session.posargs, external=True)
    session.run("scripts/aihealth_components.py", external=True)


@nox.session(name="code-health-own", python=PYTHON)
def code_health_own(session: nox.Session) -> None:
    """The own checker, kept as a cross-check until the ai-health gate is green."""
    session.install("PyYAML>=6.0")
    session.run("python", "-m", "code_health", *session.posargs)


@nox.session(python=PYTHON)
def ansible(session: nox.Session) -> None:
    """Ansible syntax check and lint."""
    session.install("-r", "tests/requirements.txt")
    session.run(
        "ansible-playbook",
        "--syntax-check",
        "-i",
        "ansible/inventory/local.yml",
        "ansible/workstation.yml",
    )
    session.run("ansible-lint", *PLAYBOOKS_LINT)


@nox.session(python=PYTHON)
def docker(session: nox.Session) -> None:
    """Docker profile smoke tests (skipped when Docker is not available)."""
    if (
        shutil.which("docker") is None
        or subprocess.run(["docker", "info"], capture_output=True).returncode != 0
    ):
        session.skip("Docker not available; skipped tests/integration")
    session.install("-r", "tests/requirements.txt")
    session.run(
        "pytest",
        "tests/integration",
        "-q",
        "-m",
        "docker and not apt and not apt_gnome",
        "-n",
        "auto",
        *session.posargs,
    )
    session.log("Full apt profile: pytest tests/integration -m apt")
    session.log(
        "Host-YAML clean install: pytest tests/integration/test_host_yaml_install.py -q"
    )
    session.log("Interactive lab: docker compose -f tests/compose.yaml run --rm shell")
