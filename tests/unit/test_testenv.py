from __future__ import annotations

import os
import pwd
import socket
import sys


from package_sets import REPO

sys.path.insert(0, str(REPO))

from machine_cli import testenv  # noqa: E402

ME = pwd.getpwuid(os.getuid())


def _opt(args: list[str], flag: str) -> list[str]:
    return [args[i + 1] for i, a in enumerate(args) if a == flag]


def _entry_args(args: list[str]) -> list[str]:
    """Positional arguments after `sh -c ENTRY testenv`."""
    start = args.index("testenv") + 1
    return args[start:]


def test_parse_args_strips_separator_and_keeps_command_options():
    args = testenv.parse_args(["--", "machine", "update", "--check"])
    assert args.command == ["machine", "update", "--check"]


def test_shell_command_default_is_login_shell(monkeypatch):
    monkeypatch.setenv("SHELL", "/usr/bin/zsh")
    assert testenv.shell_command([]) == ["/usr/bin/zsh", "-l"]


def test_shell_command_single_argument_is_a_script(monkeypatch):
    monkeypatch.setenv("SHELL", "/bin/bash")
    script = "machine update && machine"
    assert testenv.shell_command([script]) == ["/bin/bash", "-lc", script]


def test_shell_command_several_arguments_are_quoted(monkeypatch):
    monkeypatch.setenv("SHELL", "/bin/bash")
    cmd = testenv.shell_command(["git", "commit", "-m", "a b"])
    assert cmd == ["/bin/bash", "-lc", "git commit -m 'a b'"]


def test_shell_command_falls_back_to_bash_for_other_shells(monkeypatch):
    monkeypatch.setenv("SHELL", "/usr/bin/fish")
    assert testenv.shell_command([])[0] == "/bin/bash"


def test_home_is_mounted_read_only_and_writes_go_to_a_volume():
    args = testenv.build_run_args("img", ["true"], rootless=True)
    assert f"{ME.pw_dir}:{testenv.LOWER}:ro" in _opt(args, "-v")
    assert _opt(args, "--mount") == [f"type=volume,dst={testenv.RW}"]
    assert "--rm" in args
    assert _opt(args, "--hostname") == [socket.gethostname()]


def test_rootless_runs_as_container_root_rootful_as_host_user():
    rootless = _entry_args(testenv.build_run_args("img", [], rootless=True))
    rootful = _entry_args(testenv.build_run_args("img", [], rootless=False))
    assert rootless[:3] == [ME.pw_dir, "0", "0"]
    assert rootful[:3] == [ME.pw_dir, str(ME.pw_uid), str(ME.pw_gid)]


def test_command_reaches_the_entry_script():
    args = testenv.build_run_args("img", ["bash", "-lc", "machine"], rootless=True)
    assert _entry_args(args) == [ME.pw_dir, "0", "0", "bash", "-lc", "machine"]


def test_context_and_device_overrides_are_passed():
    args = testenv.build_run_args(
        "img", [], rootless=True, context="private", device="desktop"
    )
    assert "MACHINE_CONTEXT_OVERRIDE=private" in _opt(args, "-e")
    assert "MACHINE_DEVICE_OVERRIDE=desktop" in _opt(args, "-e")
    assert "MACHINE_TESTENV=1" in _opt(args, "-e")


def test_host_values_prefer_the_applied_host_config(tmp_path, monkeypatch):
    monkeypatch.delenv("MACHINE_STATE_DIR", raising=False)
    applied = tmp_path / ".local/share/machine/applied-host.yml"
    applied.parent.mkdir(parents=True)
    applied.write_text("---\ncontext: work\ndevice: desktop\nfeatures: []\n")
    legacy = tmp_path / ".config/machine/profile.yml"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("profile: home-server\n")
    hosts = tmp_path / "dotfiles/machine/hosts"
    hosts.mkdir(parents=True)
    (hosts / f"{socket.gethostname()}.yml").write_text(
        "context: private\ndevice: desktop\n"
    )
    assert testenv.host_values(tmp_path) == ("work", "desktop")
    applied.unlink()
    assert testenv.host_values(tmp_path) == ("private", "server")
    legacy.unlink()
    assert testenv.host_values(tmp_path) == ("private", "desktop")
    (hosts / f"{socket.gethostname()}.yml").unlink()
    assert testenv.host_values(tmp_path) == ("", "")


def test_image_matches_host_os_and_changes_with_mode(monkeypatch):
    monkeypatch.setattr(testenv, "os_release", lambda: ("ubuntu", "26.04"))
    tag_rootless, dockerfile = testenv.image_spec(rootless=True)
    tag_rootful, _ = testenv.image_spec(rootless=False)
    assert dockerfile.startswith("FROM ubuntu:26.04\n")
    assert f"1i {ME.pw_name}:x:0:0:" in dockerfile
    assert tag_rootless.startswith("machine-testenv:ubuntu-26.04-")
    assert tag_rootless != tag_rootful
