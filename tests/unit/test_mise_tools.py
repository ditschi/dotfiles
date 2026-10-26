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
    monkeypatch.setenv("MACHINE_APPLIED_HOST_FILE", str(tmp_path / "profile.yml"))
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
    context = "work" if "azure-cli" in features else "private"
    host.applied_host_path.write_text(
        f"context: {context}\ndevice: desktop\nfeatures:\n"
        + "".join(f"  - {f}\n" for f in features)
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


def _gnome(host, monkeypatch, tmp_path):
    _profile(host, ["gnome"])
    monkeypatch.setattr(
        mise_tools.system, "have", lambda name: name in ("mise", "gnome-shell", "dconf")
    )
    settings = tmp_path / "home/gnome/.config/machine/dconf"
    settings.mkdir(parents=True)
    (settings / "gtile.ini").write_text("[/]\ngrid-sizes='3x3'\n")


def test_gnome_extensions_install_missing_ones_and_load_settings_once(
    machine, monkeypatch, tmp_path
):
    host, commands = machine
    _gnome(host, monkeypatch, tmp_path)
    present = tmp_path / ".local/share/gnome-shell/extensions/gTile@vibou"
    present.mkdir(parents=True)

    host.run_tools_install()

    gext = [c for c in commands if c[:4] == ["mise", "exec", "--", "gext"]]
    installed = [c[-1] for c in gext if "install" in c]
    assert "ddterm@amezin.github.com" in installed
    assert "gTile@vibou" not in installed  # already there
    assert "tiling-assistant@ubuntu.com" not in installed  # system extension
    assert ["dconf", "load", "/org/gnome/shell/extensions/gtile/"] in commands

    commands.clear()
    host.run_tools_install()
    assert not any(c[0] == "dconf" for c in commands)  # settings load only once


@pytest.mark.parametrize("already_installed", [False, True])
@pytest.mark.parametrize("mode", [0o640, 0o750])
def test_ddterm_launcher_is_executable_before_enable(
    machine, monkeypatch, tmp_path, already_installed, mode
):
    host, commands = machine
    _gnome(host, monkeypatch, tmp_path)
    uuid = "ddterm@amezin.github.com"
    launcher = (
        tmp_path
        / ".local/share/gnome-shell/extensions"
        / uuid
        / "bin"
        / "com.github.amezin.ddterm"
    )

    def install_launcher():
        launcher.parent.mkdir(parents=True)
        launcher.write_text("#!/usr/bin/gjs\n")
        launcher.chmod(mode)

    if already_installed:
        install_launcher()

    def run(args, **_kw):
        commands.append(list(args))
        if args[-2:] == ["install", uuid]:
            install_launcher()
        if args[-2:] == ["enable", uuid]:
            assert launcher.stat().st_mode & 0o100
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(mise_tools.system, "run", run)

    host.run_tools_install()
    host.run_tools_install()

    assert launcher.stat().st_mode & 0o777 == mode | 0o100
    installs = [args for args in commands if args[-2:] == ["install", uuid]]
    assert len(installs) == (0 if already_installed else 1)


def test_gnome_extension_failure_does_not_fail_the_run_or_mark_settings(
    machine, monkeypatch, tmp_path
):
    host, commands = machine
    _gnome(host, monkeypatch, tmp_path)

    def run(args, **_kw):
        commands.append(list(args))
        code = 1 if "install" in args and args[-1] != "mise" else 0
        return subprocess.CompletedProcess(args, code, stdout="", stderr="")

    monkeypatch.setattr(mise_tools.system, "run", run)

    host.run_tools_install()

    assert not any(c[0] == "dconf" for c in commands)


def test_gnome_extension_failure_names_the_reason(machine, monkeypatch, tmp_path):
    host, commands = machine
    _gnome(host, monkeypatch, tmp_path)
    messages = []
    monkeypatch.setattr(mise_tools, "log", messages.append)

    def run(args, **_kw):
        commands.append(list(args))
        failed = "install" in args and args[-1] != "mise"
        return subprocess.CompletedProcess(
            args,
            1 if failed else 0,
            stdout="",
            stderr="gext: not found\n" if failed else "",
        )

    monkeypatch.setattr(mise_tools.system, "run", run)

    host.run_tools_install()

    assert any(
        m.startswith("could not install ") and ": gext: not found;" in m
        for m in messages
    )


def test_no_gnome_extensions_without_gnome_shell(machine):
    host, commands = machine
    _profile(host, ["gnome"])

    host.run_tools_install()

    assert not any("gext" in c for c in commands)
