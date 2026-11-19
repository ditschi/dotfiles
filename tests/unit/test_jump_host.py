"""Feature jump-host: the tunnel list from the written host list reaches Ansible."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from test_homelab_node import homelab_machine

LIST = """\
Host oracle
  HostName jump.example
  HostKeyAlias privatecloud

Host homeserver
  HostKeyAlias homeserver
  ProxyCommand ~/.local/bin/ssh-route %k lan=192.168.1.4:22 jump=oracle:2223
"""


def record_vars(cli, monkeypatch, machine):
    seen: list[dict] = []
    monkeypatch.setattr(machine, "record_ansible_applied", lambda: None)
    monkeypatch.setattr(cli.system, "is_root", lambda: False)
    monkeypatch.setattr(
        machine, "local_ansible_prefix", lambda _i: ["ansible-playbook"]
    )
    real_run = cli.system.run

    def fake_run(cmd, **kw):
        if cmd and cmd[0] == "ansible-playbook":
            for i, arg in enumerate(cmd):
                if arg == "--extra-vars" and cmd[i + 1].startswith("@"):
                    path = Path(cmd[i + 1][1:])
                    if path.name.startswith("machine-jump-host-"):
                        seen.append(json.loads(path.read_text()))
            return subprocess.CompletedProcess(cmd, 0)
        return real_run(cmd, **kw)

    monkeypatch.setattr(cli.system, "run", fake_run)
    return seen


def test_tunnels_reach_ansible(tmp_path, monkeypatch, fake_bw):
    cli, machine, home, _store = homelab_machine(
        tmp_path, monkeypatch, fake_bw, features=("jump-host",)
    )
    (home / ".ssh/config.d").mkdir(parents=True)
    (home / ".ssh/config.d/20-home").write_text(LIST)
    keys = machine.repo / "machine/ssh_keys"
    keys.mkdir(parents=True)
    (keys / "homeserver.pub").write_text("ssh-ed25519 AAAAhome ditschi@homeserver\n")
    seen = record_vars(cli, monkeypatch, machine)

    machine.run_ansible("workstation", ask_become=False)

    assert seen == [
        {
            "jump_host_tunnels": [
                {"alias": "homeserver", "port": 2223, "key": "ssh-ed25519 AAAAhome"}
            ],
            "jump_host_missing_keys": [],
        }
    ]


def test_without_host_list_the_role_keeps_the_keys(tmp_path, monkeypatch, fake_bw):
    cli, machine, _home, _store = homelab_machine(
        tmp_path, monkeypatch, fake_bw, features=("jump-host",)
    )
    seen = record_vars(cli, monkeypatch, machine)

    machine.run_ansible("workstation", ask_become=False)

    assert seen[0]["jump_host_tunnels"] is None


def test_other_hosts_get_no_tunnel_vars(tmp_path, monkeypatch, fake_bw):
    cli, machine, _home, _store = homelab_machine(
        tmp_path, monkeypatch, fake_bw, features=("ssh-tunnel",)
    )
    seen = record_vars(cli, monkeypatch, machine)

    machine.run_ansible("workstation", ask_become=False)

    assert seen == []
