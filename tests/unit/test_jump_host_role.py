"""jump_host role: tunnel key lines, the sshd block and the feature wiring."""

from __future__ import annotations

import jinja2
import yaml

from package_sets import ANSIBLE

ROLE = ANSIBLE / "roles/jump_host"


def _defaults():
    return yaml.safe_load((ROLE / "defaults/main.yml").read_text())


def _render(name: str, **values) -> str:
    template = jinja2.Template((ROLE / "templates" / name).read_text())
    return template.render(**{**_defaults(), **values})


def test_one_restricted_line_per_tunnel_sorted_by_port():
    text = _render(
        "authorized_keys.j2",
        jump_host_tunnels=[
            {"alias": "netmaster", "port": 2224, "key": "ssh-ed25519 AAAAnet"},
            {"alias": "homeserver", "port": 2223, "key": "ssh-ed25519 AAAAhome"},
        ],
    )
    lines = [line for line in text.splitlines() if line and not line.startswith("#")]
    assert lines == [
        'restrict,port-forwarding,permitlisten="127.0.0.1:2223" '
        "ssh-ed25519 AAAAhome homeserver",
        'restrict,port-forwarding,permitlisten="127.0.0.1:2224" '
        "ssh-ed25519 AAAAnet netmaster",
    ]


def test_no_tunnels_gives_an_empty_key_file():
    text = _render("authorized_keys.j2", jump_host_tunnels=[])
    assert [line for line in text.splitlines() if not line.startswith("#")] == []


def test_sshd_block_allows_remote_forwarding_only():
    text = _render("50-jump-host.conf.j2")
    lines = [line.split() for line in text.splitlines() if line and line[0] != "#"]
    assert lines[0] == ["Match", "User", "tunnel"]
    options = {words[0]: " ".join(words[1:]) for words in lines[1:]}
    assert options == {
        "AllowTcpForwarding": "remote",
        "GatewayPorts": "no",
        "PermitTTY": "no",
        "X11Forwarding": "no",
        "AllowAgentForwarding": "no",
        "AllowStreamLocalForwarding": "no",
        "PermitTunnel": "no",
        "ClientAliveInterval": "30",
        "ClientAliveCountMax": "3",
        "ForceCommand": "/usr/sbin/nologin",
    }


def _all_tasks():
    tasks = yaml.safe_load((ROLE / "tasks/main.yml").read_text())
    for task in tasks:
        yield task
        for key in ("block", "rescue", "always"):
            yield from task.get(key, [])


def test_user_has_no_shell_and_keys_belong_to_root():
    tasks = list(_all_tasks())
    user = next(t for t in tasks if "ansible.builtin.user" in t)["ansible.builtin.user"]
    assert user["shell"] == "/usr/sbin/nologin"
    assert user["system"] is True
    keys = next(
        t["ansible.builtin.template"]
        for t in tasks
        if t.get("ansible.builtin.template", {}).get("src") == "authorized_keys.j2"
    )
    assert keys["owner"] == "root" and keys["mode"] == "0644"


def test_keys_are_kept_without_a_host_list():
    tasks = list(_all_tasks())
    keys = next(
        t
        for t in tasks
        if t.get("ansible.builtin.template", {}).get("src") == "authorized_keys.j2"
    )
    assert keys["when"] == "jump_host_tunnels is not none"


def test_role_opens_no_firewall_port():
    text = (ROLE / "tasks/main.yml").read_text()
    for word in ("ufw", "iptables", "firewalld", "nftables"):
        assert word not in text


def test_feature_wiring():
    plays = yaml.safe_load((ANSIBLE / "workstation.yml").read_text())
    roles = [role for play in plays for role in play.get("roles", [])]
    wired = [r for r in roles if r.get("role") == "jump_host"]
    assert wired == [{"role": "jump_host", "when": "'jump-host' in machine_features"}]
