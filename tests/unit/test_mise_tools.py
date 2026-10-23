"""Tool install: mise install plus the Azure CLI as a uv tool."""

from __future__ import annotations

import subprocess

import sys

import pytest
from package_sets import REPO

sys.path.insert(0, str(REPO))

from machine_cli import mise_tools  # noqa: E402
from machine_cli.machine import Machine  # noqa: E402


@pytest.fixture
def machine(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("DOTFILES_REPO", str(tmp_path))
    monkeypatch.setenv("MACHINE_PROFILE_FILE", str(tmp_path / "profile.yml"))
    host = Machine()
    commands: list[list[str]] = []

    def run(args, **_kw):
        commands.append(list(args))
        out = "azure-cli v2.0\n" if host.have_az else ""
        return subprocess.CompletedProcess(args, 0, stdout=out, stderr="")

    host.have_az = False
    monkeypatch.setattr(mise_tools.system, "run", run)
    monkeypatch.setattr(mise_tools.system, "have", lambda name: name == "mise")
    return host, commands


def _profile(host, features):
    host.profile_path.write_text(
        "profile: work-machine\nfeatures:\n" + "".join(f"  - {f}\n" for f in features)
    )


def test_installs_missing_tools_and_azure_cli_when_the_feature_is_on(machine):
    host, commands = machine
    _profile(host, ["azure-cli"])

    host.run_tools_install()

    assert ["mise", "install"] in commands
    assert [
        "mise", "exec", "--", "uv", "tool", "install", "azure-cli",
        "--python-preference", "only-managed",
    ] in commands  # fmt: skip


def test_upgrades_azure_cli_when_present(machine):
    host, commands = machine
    host.have_az = True
    _profile(host, ["azure-cli"])

    host.run_tools_install()

    assert ["mise", "exec", "--", "uv", "tool", "upgrade", "azure-cli"] in commands
    assert not any("install" in c and "azure-cli" in c for c in commands)


def test_no_azure_cli_without_the_feature(machine):
    host, commands = machine
    _profile(host, [])

    host.run_tools_install()

    assert not any("azure-cli" in c for c in commands)


def test_font_is_linked_for_the_fonts_feature_and_removed_without(
    machine, tmp_path, monkeypatch
):
    host, _ = machine
    installed = tmp_path / ".local/share/mise/installs/nerd-fonts/3.5.1"
    installed.mkdir(parents=True)
    monkeypatch.setattr(
        mise_tools.system,
        "run",
        lambda args, **_kw: subprocess.CompletedProcess(
            args, 0, stdout=f"{installed}\n", stderr=""
        ),
    )
    link = tmp_path / ".local/share/fonts/FiraCodeNerdFont"

    host.link_fonts({}, True)
    assert link.resolve() == installed.resolve()
    host.link_fonts({}, True)  # idempotent
    host.link_fonts({}, False)
    assert not link.is_symlink()
