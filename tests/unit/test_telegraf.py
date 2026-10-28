"""Telegraf: Influx credentials from Bitwarden, handed only to Ansible."""

from __future__ import annotations

import json
import os
import subprocess
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

from package_sets import REPO

MACHINE = REPO / "machine_cli/machine"
ITEM = "influxdb-telegraf-write"


def telegraf_machine(tmp_path, monkeypatch, fake_bw, features=("monitoring",)):
    bw, store = fake_bw
    repo = tmp_path / "dotfiles"
    (repo / "home").mkdir(parents=True)
    (repo / ".git").mkdir()
    (repo / "ansible").mkdir()
    (repo / "ansible/workstation.yml").write_text("---\n", encoding="utf-8")
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("DOTFILES_REPO", str(repo))
    monkeypatch.setenv("PATH", f"{bw.parent}:{os.environ.get('PATH', '')}")
    monkeypatch.setenv("BW_SESSION", "fake-session")
    monkeypatch.setenv(
        "MACHINE_APPLIED_HOST_FILE", str(home / ".config/machine/profile.yml")
    )
    monkeypatch.setenv(
        "MISE_LOCAL_CONFIG", str(home / ".config/mise/config.local.toml")
    )
    monkeypatch.setenv("MACHINE_STATE_DIR", str(home / ".local/share/machine"))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    cli = SourceFileLoader("machine_telegraf", str(MACHINE)).load_module()
    monkeypatch.setattr(cli.system, "in_docker", lambda: False)
    monkeypatch.setattr(cli.system, "is_tty", lambda: False)
    machine = cli.Machine()
    machine.write_profile("private", "desktop", list(features), [])
    return cli, machine, home, store


def put_item(store: Path, item: dict) -> None:
    data = json.loads(store.read_text() or "{}")
    data.setdefault("items", {})[ITEM] = {"name": ITEM, **item}
    store.write_text(json.dumps(data))


LOGIN_ITEM = {
    "type": 1,
    "login": {
        "password": "tok-login",  # pragma: allowlist secret
        "uris": [{"uri": "https://influx.uri"}],
    },
    "fields": [
        {"name": "INFLUX_URL", "value": "https://influx.field", "type": 0},
        {"name": "INFLUX_ORG", "value": "home", "type": 0},
        {"name": "INFLUX_BUCKET", "value": "telegraf", "type": 0},
        {"name": "UNRELATED", "value": "x", "type": 0},
    ],
}


def test_login_item_password_is_the_token_and_fields_win(
    tmp_path, monkeypatch, fake_bw
):
    _cli, machine, _home, store = telegraf_machine(tmp_path, monkeypatch, fake_bw)
    put_item(store, LOGIN_ITEM)
    assert machine.influx_credentials() == {
        "INFLUX_TOKEN": "tok-login",
        "INFLUX_URL": "https://influx.field",
        "INFLUX_ORG": "home",
        "INFLUX_BUCKET": "telegraf",
    }


def test_login_uri_fills_the_url_and_token_field_wins(tmp_path, monkeypatch, fake_bw):
    _cli, machine, _home, store = telegraf_machine(tmp_path, monkeypatch, fake_bw)
    item = json.loads(json.dumps(LOGIN_ITEM))
    item["fields"] = [{"name": "INFLUX_TOKEN", "value": "tok-field", "type": 1}]
    put_item(store, item)
    assert machine.influx_credentials() == {
        "INFLUX_TOKEN": "tok-field",
        "INFLUX_URL": "https://influx.uri",
    }


def test_field_only_item(tmp_path, monkeypatch, fake_bw):
    _cli, machine, _home, store = telegraf_machine(tmp_path, monkeypatch, fake_bw)
    put_item(
        store,
        {
            "type": 2,
            "fields": [
                {"name": "INFLUX_URL", "value": "https://i", "type": 0},
                {"name": "INFLUX_TOKEN", "value": "t", "type": 1},
            ],
        },
    )
    assert machine.influx_credentials() == {
        "INFLUX_URL": "https://i",
        "INFLUX_TOKEN": "t",
    }


def test_missing_item_logs_and_returns_nothing(tmp_path, monkeypatch, fake_bw, capsys):
    _cli, machine, _home, _store = telegraf_machine(tmp_path, monkeypatch, fake_bw)
    assert machine.influx_credentials() == {}
    assert f"Bitwarden item '{ITEM}' not found" in capsys.readouterr().out


def test_locked_bitwarden_does_not_prompt(tmp_path, monkeypatch, fake_bw, capsys):
    cli, machine, _home, store = telegraf_machine(tmp_path, monkeypatch, fake_bw)
    put_item(store, LOGIN_ITEM)
    monkeypatch.delenv("BW_SESSION")
    monkeypatch.setattr(
        cli.system, "prompt_yes_no", lambda *_a, **_k: pytest.fail("prompted")
    )
    assert machine.influx_credentials() == {}
    assert "Bitwarden not unlocked" in capsys.readouterr().out


def test_credentials_are_read_once_per_command(tmp_path, monkeypatch, fake_bw):
    _cli, machine, _home, store = telegraf_machine(tmp_path, monkeypatch, fake_bw)
    put_item(store, LOGIN_ITEM)
    first = machine.influx_credentials()
    store.write_text("{}")
    assert machine.influx_credentials() == first


def _record_ansible(cli, monkeypatch, machine):
    seen: list[dict] = []
    real_run = cli.system.run
    monkeypatch.setattr(machine, "record_ansible_applied", lambda: None)

    def fake_run(cmd, **kw):
        if cmd and cmd[0] == "ansible-playbook":
            files = [
                Path(cmd[i + 1][1:])
                for i, arg in enumerate(cmd)
                if arg == "--extra-vars" and cmd[i + 1].startswith("@")
            ]
            influx = [p for p in files if p.name.startswith("machine-influx-")]
            seen.append(
                {
                    "cmd": list(cmd),
                    "influx": [
                        (p, json.loads(p.read_text()), oct(p.stat().st_mode & 0o777))
                        for p in influx
                    ],
                }
            )
            return subprocess.CompletedProcess(cmd, 0)
        return real_run(cmd, **kw)

    monkeypatch.setattr(cli.system, "run", fake_run)
    return seen


def test_monitoring_host_hands_influx_vars_to_ansible_only(
    tmp_path, monkeypatch, fake_bw
):
    cli, machine, home, store = telegraf_machine(tmp_path, monkeypatch, fake_bw)
    put_item(store, LOGIN_ITEM)
    seen = _record_ansible(cli, monkeypatch, machine)

    machine.run_ansible("workstation", ask_become=False)

    [(path, values, mode)] = seen[-1]["influx"]
    assert values == {
        "influx_token": "tok-login",
        "influx_url": "https://influx.field",
        "influx_org": "home",
        "influx_bucket": "telegraf",
    }
    assert mode == "0o600"
    assert not path.exists()
    assert not list(home.glob(".env*"))


def test_host_without_monitoring_does_not_read_the_item(tmp_path, monkeypatch, fake_bw):
    cli, machine, _home, store = telegraf_machine(
        tmp_path, monkeypatch, fake_bw, features=("zsh-full",)
    )
    put_item(store, LOGIN_ITEM)
    monkeypatch.setattr(
        machine, "influx_credentials", lambda: pytest.fail("item must not be read")
    )
    seen = _record_ansible(cli, monkeypatch, machine)

    machine.run_ansible("workstation", ask_become=False)

    assert seen[-1]["influx"] == []


def test_missing_item_runs_ansible_without_influx_vars(tmp_path, monkeypatch, fake_bw):
    cli, machine, _home, _store = telegraf_machine(tmp_path, monkeypatch, fake_bw)
    seen = _record_ansible(cli, monkeypatch, machine)

    machine.run_ansible("workstation", ask_become=False)

    assert seen[-1]["influx"] == []


def telegraf_state(
    cli,
    monkeypatch,
    machine,
    tmp_path,
    *,
    installed=True,
    active="inactive",
    enabled="disabled",
    output=False,
):
    """Fake binary, unit state and output files; records the commands run."""
    conf = tmp_path / "telegraf.d"
    conf.mkdir(exist_ok=True)
    if output:
        (conf / "99_output_influx2.conf").write_text("[[outputs.influxdb_v2]]\n")
    machine.telegraf_conf_dir = conf
    monkeypatch.setattr(
        cli.system,
        "have",
        lambda name: name == "systemctl" or (installed and name == "telegraf"),
    )
    commands: list[list[str]] = []

    def fake_run(cmd, **_kw):
        commands.append(list(cmd))
        out = {"is-active": active, "is-enabled": enabled}.get(cmd[1], "")
        return subprocess.CompletedProcess(cmd, 0, out + "\n", "")

    monkeypatch.setattr(cli.system, "run", fake_run)
    return commands


@pytest.mark.parametrize(
    ("state", "problem"),
    [
        ({"installed": False}, "not-installed"),
        ({}, "no-output"),
        ({"output": True}, "not-active"),
        ({"enabled": "enabled"}, "not-active"),  # remote configs: unit enabled
        ({"active": "active"}, None),
        ({"active": "activating", "output": True}, None),
    ],
)
def test_telegraf_problem(tmp_path, monkeypatch, fake_bw, state, problem):
    cli, machine, _home, _store = telegraf_machine(tmp_path, monkeypatch, fake_bw)
    telegraf_state(cli, monkeypatch, machine, tmp_path, **state)
    assert machine.telegraf_problem() == problem


def test_no_telegraf_check_without_monitoring(tmp_path, monkeypatch, fake_bw):
    cli, machine, _home, _store = telegraf_machine(
        tmp_path, monkeypatch, fake_bw, features=("zsh-full",)
    )
    commands = telegraf_state(cli, monkeypatch, machine, tmp_path, installed=False)
    assert machine.telegraf_problem() is None
    assert machine.monitoring_item() is None
    assert commands == []


def test_health_check_warns_but_keeps_the_apply(tmp_path, monkeypatch, fake_bw, capsys):
    cli, machine, _home, _store = telegraf_machine(tmp_path, monkeypatch, fake_bw)
    telegraf_state(cli, monkeypatch, machine, tmp_path, output=True)
    monkeypatch.setattr(machine, "zsh_health_failure", lambda: "")
    monkeypatch.setattr(machine, "dotfiles_health_failure", lambda: "")
    assert machine.health_check_after_apply() is True
    assert "health check: telegraf is not running (warn)" in capsys.readouterr().out


def test_attention_lists_monitoring_without_prompting(
    tmp_path, monkeypatch, fake_bw, capsys
):
    cli, machine, _home, _store = telegraf_machine(tmp_path, monkeypatch, fake_bw)
    telegraf_state(cli, monkeypatch, machine, tmp_path)
    for name in (
        "update_item",
        "pending_system_paths",
        "local_changes",
        "local_resolvers",
    ):
        monkeypatch.setattr(
            machine,
            name,
            (lambda *_a: None) if name == "update_item" else (lambda *_a: []),
        )
    monkeypatch.setattr(machine, "stash_items", lambda: [])
    monkeypatch.setattr(
        cli.system, "prompt_yes_no", lambda *_a, **_k: pytest.fail("prompted")
    )
    assert machine.cmd_attention() == 0
    out = capsys.readouterr().out
    assert "[monitoring] telegraf has no output" in out
    assert ITEM in out


@pytest.mark.parametrize("state", [{"installed": False}, {}])
def test_monitoring_item_offers_apply(tmp_path, monkeypatch, fake_bw, state):
    cli, machine, _home, _store = telegraf_machine(tmp_path, monkeypatch, fake_bw)
    telegraf_state(cli, monkeypatch, machine, tmp_path, **state)
    applied = []
    monkeypatch.setattr(machine, "cmd_apply", lambda args: applied.append(args) or 0)
    item = machine.monitoring_item()
    assert item.question == "Run `machine apply` now?"
    item.resolve()
    assert applied[0].playbook == "workstation"


def test_inactive_telegraf_shows_journal_and_restarts(tmp_path, monkeypatch, fake_bw):
    cli, machine, _home, _store = telegraf_machine(tmp_path, monkeypatch, fake_bw)
    commands = telegraf_state(cli, monkeypatch, machine, tmp_path, output=True)
    monkeypatch.setattr(cli.system, "prompt_yes_no", lambda *_a, **_k: True)
    item = machine.monitoring_item()
    assert item.text == "telegraf is not running"
    assert item.question is None
    item.resolve()
    assert ["journalctl", "-u", "telegraf", "-n", "20", "--no-pager"] in commands
    assert commands[-1] == ["sudo", "systemctl", "restart", "telegraf"]
