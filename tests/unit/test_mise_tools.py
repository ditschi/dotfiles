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


def test_dotfile_apply_never_prompts(machine, monkeypatch):
    host, commands = machine
    _profile(host, [])
    host.mise_local_config.parent.mkdir(parents=True, exist_ok=True)
    host.mise_local_config.write_text('[bootstrap]\ndotfile_groups = ["core"]\n')
    from machine_cli import dotfiles

    monkeypatch.setattr(dotfiles.system, "run", mise_tools.system.run)
    monkeypatch.setattr(dotfiles.system, "have", mise_tools.system.have)
    monkeypatch.setattr(host, "ensure_machine_link", lambda: None)

    host.run_dotfiles_apply()

    assert ["mise", "dot", "apply", "--prune", "--yes"] in commands


class _FakeResponse:
    def __init__(self, data: bytes):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self.data


def _xpi_target(host):
    # DOTFILES_REPO in the fixture is no checkout, so pin the repo explicitly.
    name = mise_tools.TB_EXTENSION_URL.rsplit("/", 1)[1]
    return host.repo / "downloads" / name


def test_thunderbird_extension_is_downloaded_and_verified(machine, monkeypatch):
    host, _ = machine
    host.repo = host.home
    _profile(host, ["thunderbird"])
    data = b"xpi"
    monkeypatch.setattr(mise_tools, "TB_EXTENSION_SHA256", mise_tools._sha256(data))
    calls = []
    monkeypatch.setattr(
        mise_tools.urllib.request,
        "urlopen",
        lambda url, timeout: calls.append(url) or _FakeResponse(data),
    )

    host.run_tools_install()
    host.run_tools_install()  # present and valid: no second download

    assert _xpi_target(host).read_bytes() == data
    assert calls == [mise_tools.TB_EXTENSION_URL]


def test_thunderbird_extension_with_wrong_checksum_is_not_saved(machine, monkeypatch):
    host, _ = machine
    host.repo = host.home
    _profile(host, ["thunderbird"])
    monkeypatch.setattr(
        mise_tools.urllib.request, "urlopen", lambda url, timeout: _FakeResponse(b"bad")
    )

    host.run_tools_install()

    assert not _xpi_target(host).exists()


def test_no_extension_download_without_the_feature(machine, monkeypatch):
    host, _ = machine
    host.repo = host.home
    _profile(host, [])
    monkeypatch.setattr(
        mise_tools.urllib.request,
        "urlopen",
        lambda *a, **k: pytest.fail("must not download"),
    )

    host.run_tools_install()
