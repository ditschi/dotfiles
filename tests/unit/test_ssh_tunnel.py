"""ssh-tunnel: own jump route from the host list, ssh options, systemd unit."""

from __future__ import annotations

import configparser
import importlib.machinery
import importlib.util

import pytest

from package_sets import REPO

GROUP = REPO / "home/ssh-tunnel"
SCRIPT = GROUP / ".local/bin/ssh-tunnel"
UNIT = GROUP / ".config/systemd/user/ssh-tunnel.service"
LIST = """\
Host oracle
  HostName jump.example
  User ubuntu
  HostKeyAlias privatecloud

Host homeserver m720q
  User ditschi
  HostKeyAlias homeserver
  ProxyCommand ~/.local/bin/ssh-route %k lan=192.168.1.4:22 jump=oracle:2223

Host netmaster
  ProxyCommand ~/.local/bin/ssh-route %k lan=192.168.1.5:22 jump=oracle:2224

Host nas
  HostName 192.168.1.222
"""


def load():
    loader = importlib.machinery.SourceFileLoader("ssh_tunnel", str(SCRIPT))
    spec = importlib.util.spec_from_loader("ssh_tunnel", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


@pytest.fixture
def tunnel(tmp_path, monkeypatch):
    module = load()
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("MACHINE_STATE_DIR", str(tmp_path / "state"))
    (tmp_path / ".ssh/config.d").mkdir(parents=True)
    (tmp_path / ".ssh/config.d/20-home").write_text(LIST)
    calls = []
    monkeypatch.setattr(module.os, "execvp", lambda f, args: calls.append(args))
    return module, tmp_path, calls


def test_own_jump_by_host_key_alias_or_name(tunnel):
    module, *_ = tunnel
    assert module.own_jump(LIST, "homeserver") == ("oracle", 2223)
    assert module.own_jump(LIST, "netmaster") == ("oracle", 2224)
    assert module.own_jump(LIST, "nas") is None
    assert module.own_jump(LIST, "m720q") is None  # only the HostKeyAlias counts


def test_runs_ssh_with_the_tunnel_options(tunnel, monkeypatch):
    module, home, calls = tunnel
    monkeypatch.setattr(module.socket, "gethostname", lambda: "homeserver.lan")
    key = home / ".ssh/id_ed25519_homeserver"
    key.write_text("private")
    (home / "state").mkdir()
    (home / "state/ssh-key-path").write_text(f"{key}\n")

    assert module.main() == 0

    [cmd] = calls
    assert cmd[:2] == ["ssh", "-N"]
    options = {cmd[i + 1] for i, arg in enumerate(cmd) if arg == "-o"}
    for option in (
        "ControlMaster=no",
        "ControlPath=none",
        "ExitOnForwardFailure=yes",
        "ServerAliveInterval=30",
        "BatchMode=yes",
    ):
        assert option in options
    assert cmd[cmd.index("-i") + 1] == str(key)
    assert cmd[-3:] == ["-R", "127.0.0.1:2223:localhost:22", "tunnel@oracle"]


def test_without_a_jump_route_exits_78(tunnel, monkeypatch, capsys):
    module, _home, calls = tunnel
    monkeypatch.setattr(module.socket, "gethostname", lambda: "nas")

    assert module.main() == 78

    assert calls == []
    err = capsys.readouterr().err
    assert "machine ssh add" in err and "machine ssh edit" in err


def test_without_a_selected_key_ssh_picks_its_default(tunnel, monkeypatch):
    module, _home, calls = tunnel
    monkeypatch.setattr(module.socket, "gethostname", lambda: "netmaster")

    assert module.main() == 0

    assert "-i" not in calls[0]


def test_unit_restarts_always_but_not_on_a_missing_route():
    unit = configparser.ConfigParser(strict=False, interpolation=None)
    unit.optionxform = str
    unit.read_string(UNIT.read_text())
    service = unit["Service"]
    assert service["ExecStart"] == "%h/.local/bin/ssh-tunnel"
    assert service["Restart"] == "always"
    assert service["RestartSec"] == "30"
    assert service["RestartPreventExitStatus"] == "78"
    assert unit["Unit"]["StartLimitIntervalSec"] == "0"
    assert unit["Install"]["WantedBy"] == "default.target"
