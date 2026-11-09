"""Feature homelab-node: settings, host age key handed only to Ansible, attention."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from machine_loader import load_machine_module
from package_sets import REPO

from machine_cli import homelab_node  # noqa: E402

MACHINE = REPO / "machine_cli/machine"
AGE_KEY = "AGE-SECRET-KEY-1TESTTESTTESTTESTTESTTESTTESTTESTTESTTESTTESTTESTTESTTEST"


# --- settings -----------------------------------------------------------------


def test_oracle_settings_from_the_block():
    settings = homelab_node.resolve_settings(
        {"host": "oracle"}, "privatecloud", "ubuntu"
    )
    assert settings["host"] == "oracle"
    assert settings["user"] == "ubuntu"
    assert settings["clone"] == "/opt/homelab"
    assert settings["managed_clone"] is True
    assert settings["ci_restrict"] is False
    assert settings["problems"] == []


def test_machine_as_root_defaults_to_ditschi():
    settings = homelab_node.resolve_settings({}, "contabo", "root")
    assert settings["host"] == "contabo"
    assert settings["user"] == "ditschi"
    assert settings["problems"] == []


def test_homeserver_existing_checkout_is_not_managed():
    settings = homelab_node.resolve_settings(
        {"clone": "/mnt/data-internal/homelab/"}, "homeserver", "ditschi"
    )
    assert settings["clone"] == "/mnt/data-internal/homelab"
    assert settings["managed_clone"] is False


def test_root_as_deploy_user_is_refused():
    settings = homelab_node.resolve_settings({"user": "root"}, "contabo", "root")
    assert any("root" in p for p in settings["problems"])


@pytest.mark.parametrize("host", ["key", "Bad Host", "../x"])
def test_invalid_host_names_are_refused(host):
    settings = homelab_node.resolve_settings({"host": host}, "h", "ditschi")
    assert settings["problems"]


def test_ci_restrict_only_when_true():
    assert (
        homelab_node.resolve_settings({"ci_restrict": "yes"}, "h", "u")["ci_restrict"]
        is False
    )
    assert (
        homelab_node.resolve_settings({"ci_restrict": True}, "h", "u")["ci_restrict"]
        is True
    )


def test_age_private_key_reads_only_the_hidden_field():
    item = {
        "notes": AGE_KEY,
        "fields": [
            {"name": "public_key", "value": "age1abc", "type": 0},
            {"name": "private_key", "value": f" {AGE_KEY}\n", "type": 1},
        ],
    }
    assert homelab_node.age_private_key(item) == AGE_KEY
    assert homelab_node.age_private_key({"notes": AGE_KEY}) == ""
    assert (
        homelab_node.age_private_key(
            {"fields": [{"name": "private_key", "value": "not a key"}]}
        )
        == ""
    )


# --- Bitwarden handover -------------------------------------------------------


def homelab_machine(
    tmp_path, monkeypatch, fake_bw, features=("homelab-node",), block=""
):
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
    applied = home / ".config/machine/profile.yml"
    monkeypatch.setenv("MACHINE_APPLIED_HOST_FILE", str(applied))
    monkeypatch.setenv(
        "MISE_LOCAL_CONFIG", str(home / ".config/mise/config.local.toml")
    )
    monkeypatch.setenv("MACHINE_STATE_DIR", str(home / ".local/share/machine"))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    cli = load_machine_module("machine_homelab", MACHINE)
    monkeypatch.setattr(cli.system, "in_docker", lambda: False)
    monkeypatch.setattr(cli.system, "is_tty", lambda: False)
    monkeypatch.setattr(cli.system, "hostname_short", lambda: "privatecloud")
    machine = cli.Machine()
    applied.parent.mkdir(parents=True, exist_ok=True)
    applied.write_text(
        "---\ncontext: private\ndevice: server\nfeatures:\n"
        + "".join(f"  - {f}\n" for f in features)
        + "ssh_allow_from: []\n"
        + block,
        encoding="utf-8",
    )
    return cli, machine, home, store


def put_item(store: Path, name: str, item: dict) -> None:
    data = json.loads(store.read_text() or "{}")
    data.setdefault("items", {})[name] = {"name": name, **item}
    store.write_text(json.dumps(data))


def record_ansible(cli, monkeypatch, machine):
    seen: list[dict] = []
    real_run = cli.system.run
    monkeypatch.setattr(machine, "record_ansible_applied", lambda: None)
    monkeypatch.setattr(cli.system, "is_root", lambda: False)
    monkeypatch.setattr(
        machine, "local_ansible_prefix", lambda _i: ["ansible-playbook"]
    )
    from machine_cli import tools

    monkeypatch.setattr(tools, "_login_user", lambda: "ubuntu")

    def fake_run(cmd, **kw):
        if cmd and cmd[0] == "ansible-playbook":
            files = [
                Path(cmd[i + 1][1:])
                for i, arg in enumerate(cmd)
                if arg == "--extra-vars" and cmd[i + 1].startswith("@")
            ]
            homelab = [p for p in files if p.name.startswith("machine-homelab-")]
            seen.append(
                {
                    "cmd": list(cmd),
                    "homelab": [
                        (p, json.loads(p.read_text()), oct(p.stat().st_mode & 0o777))
                        for p in homelab
                    ],
                }
            )
            return subprocess.CompletedProcess(cmd, 0)
        return real_run(cmd, **kw)

    monkeypatch.setattr(cli.system, "run", fake_run)
    return seen


ORACLE_ITEM = {
    "type": 2,
    "notes": "host key of oracle",
    "fields": [
        {"name": "private_key", "value": AGE_KEY, "type": 1},
        {"name": "public_key", "value": "age1oracle", "type": 0},
    ],
}


def test_age_key_reaches_only_ansible(tmp_path, monkeypatch, fake_bw, capsys):
    cli, machine, home, store = homelab_machine(
        tmp_path, monkeypatch, fake_bw, block="homelab:\n  host: oracle\n"
    )
    put_item(store, "homelab-age-oracle", ORACLE_ITEM)
    put_item(
        store,
        "homelab-age-key",
        {"fields": [{"name": "private_key", "value": "AGE-SECRET-KEY-PERSONAL"}]},
    )
    seen = record_ansible(cli, monkeypatch, machine)

    machine.run_ansible("workstation", ask_become=False)

    [(path, values, mode)] = seen[-1]["homelab"]
    assert values["homelab_age_private_key"] == AGE_KEY
    assert values["homelab_node"]["host"] == "oracle"
    assert values["homelab_node"]["user"] == "ubuntu"
    assert mode == "0o600"
    assert not path.exists()
    assert not list(home.glob(".env*"))
    out = capsys.readouterr()
    assert AGE_KEY not in out.out + out.err
    assert "PERSONAL" not in json.dumps(values)


def test_host_without_the_feature_reads_no_item(tmp_path, monkeypatch, fake_bw):
    cli, machine, _home, store = homelab_machine(
        tmp_path, monkeypatch, fake_bw, features=("zsh-full",)
    )
    monkeypatch.setattr(
        machine, "homelab_age_key", lambda _s: pytest.fail("item must not be read")
    )
    seen = record_ansible(cli, monkeypatch, machine)

    machine.run_ansible("workstation", ask_become=False)

    assert seen[-1]["homelab"] == []


@pytest.mark.parametrize(
    "item",
    [None, {"fields": [{"name": "public_key", "value": "age1x"}]}],
    ids=["missing-item", "missing-field"],
)
def test_missing_item_or_field_runs_ansible_without_the_key(
    tmp_path, monkeypatch, fake_bw, capsys, item
):
    cli, machine, _home, store = homelab_machine(
        tmp_path, monkeypatch, fake_bw, block="homelab:\n  host: oracle\n"
    )
    if item is not None:
        put_item(store, "homelab-age-oracle", item)
    seen = record_ansible(cli, monkeypatch, machine)

    machine.run_ansible("workstation", ask_become=False)

    [(_path, values, _mode)] = seen[-1]["homelab"]
    assert "homelab_age_private_key" not in values
    assert "homelab-age-oracle" in capsys.readouterr().out


def test_invalid_host_reads_no_item(tmp_path, monkeypatch, fake_bw):
    cli, machine, _home, _store = homelab_machine(
        tmp_path, monkeypatch, fake_bw, block="homelab:\n  host: key\n"
    )
    monkeypatch.setattr(
        machine, "bw_get_item_raw", lambda _n: pytest.fail("item must not be read")
    )
    seen = record_ansible(cli, monkeypatch, machine)

    machine.run_ansible("workstation", ask_become=False)

    [(_path, values, _mode)] = seen[-1]["homelab"]
    assert values["homelab_node"]["problems"]
    assert "homelab_age_private_key" not in values


def test_remote_run_resolves_the_target_host(tmp_path, monkeypatch, fake_bw):
    cli, machine, _home, store = homelab_machine(
        tmp_path,
        monkeypatch,
        fake_bw,
        block="homelab:\n  clone: /mnt/data-internal/homelab\n",
    )
    target = tmp_path / "contabo.yml"
    target.write_text(
        "---\ncontext: private\ndevice: server\nfeatures:\n  - homelab-node\n",
        encoding="utf-8",
    )
    put_item(store, "homelab-age-contabo", ORACLE_ITEM)
    put_item(store, "homelab-age-privatecloud", {"fields": []})
    seen = record_ansible(cli, monkeypatch, machine)

    machine.run_ansible(
        "workstation", limit="contabo", ask_become=False, extra_vars_file=target
    )

    [(_path, values, _mode)] = seen[-1]["homelab"]
    settings = values["homelab_node"]
    assert settings["host"] == "contabo"
    assert settings["user"] == ""  # the role resolves it on the target
    assert settings["clone"] == "/opt/homelab"
    assert values["homelab_age_private_key"] == AGE_KEY


def test_only_the_exact_item_counts(tmp_path, monkeypatch, fake_bw):
    """`bw get item` also searches; a short host must not get homelab-age-key."""
    _cli, machine, _home, _store = homelab_machine(tmp_path, monkeypatch, fake_bw)
    personal = {
        "name": "homelab-age-key",
        "fields": [{"name": "private_key", "value": AGE_KEY}],
    }
    monkeypatch.setattr(machine, "bw_get_item_raw", lambda _name: personal)
    values = machine.homelab_ansible_vars({"host": "ke"}, "h", "ditschi")
    assert "homelab_age_private_key" not in values


def test_no_secret_file_is_left_when_sudo_fails(tmp_path, monkeypatch, fake_bw):
    cli, machine, _home, store = homelab_machine(
        tmp_path, monkeypatch, fake_bw, block="homelab:\n  host: oracle\n"
    )
    put_item(store, "homelab-age-oracle", ORACLE_ITEM)
    record_ansible(cli, monkeypatch, machine)

    def sudo_fails(_interactive):
        raise subprocess.CalledProcessError(1, ["sudo", "-v"])

    monkeypatch.setattr(machine, "local_ansible_prefix", sudo_fails)
    with pytest.raises(subprocess.CalledProcessError):
        machine.run_ansible("workstation", ask_become=False)
    assert not list(tmp_path.glob("machine-homelab-*"))


def test_hostname_with_capitals_is_lowered():
    settings = homelab_node.resolve_settings({}, "NAS-Ditscher", "ditschi")
    assert settings["host"] == "nas-ditscher"
    assert settings["problems"] == []


# --- attention ----------------------------------------------------------------

OK_STATUS = {
    "problems": [],
    "user": "ditschi",
    "host": "contabo",
    "clone": "/opt/homelab",
    "clone_state": "ok",
    "age_key": "ok",
    "sops_path": "/usr/local/bin/sops",
    "sops_version": "sops 3.13.3 (latest)",
    "docker": True,
    "compose": True,
    "missing_key_files": [],
    "ci_key_unrestricted": False,
}


def test_healthy_status_needs_no_attention():
    assert homelab_node.status_problems(OK_STATUS) == []


def test_items_name_the_time_of_the_last_apply():
    status = {**OK_STATUS, "docker": False, "run_at": "2026-11-09T20:49:21.9"}
    [text] = homelab_node.status_problems(status)
    assert text.endswith("(last apply 2026-11-09 20:49)")


@pytest.mark.parametrize(
    "change, expected",
    [
        ({"age_key": "missing"}, "homelab-age-contabo"),
        ({"age_key": "differs"}, "kept as it is"),
        ({"clone_state": "not-a-repo"}, "not a git checkout"),
        (
            {"clone_state": "clone-failed", "clone_error": "destination path exists"},
            "destination path exists",
        ),
        (
            {
                "clone_state": "waiting-for-deploy-key",
                "deploy_public_key": "ssh-ed25519 AAAA homelab-deploy@contabo",
            },
            "ssh-ed25519 AAAA homelab-deploy@contabo",
        ),
        (
            {
                "sops_path": "/home/ditschi/.local/share/mise/shims/sops",
                "sops_version": "",
            },
            "mise/shims/sops",
        ),
        ({"docker": False}, "docker CLI"),
        ({"compose": False}, "Compose plugin"),
        ({"missing_key_files": ["homelab-ci.pub"]}, "homelab-ci.pub"),
        ({"ci_key_unrestricted": True}, "ci_restrict"),
    ],
)
def test_status_problems(change, expected):
    texts = homelab_node.status_problems({**OK_STATUS, **change})
    assert len(texts) == 1 and expected in texts[0]


def test_unrestricted_ci_key_is_quiet_before_the_clone_exists():
    status = {
        **OK_STATUS,
        "ci_key_unrestricted": True,
        "clone_state": "waiting-for-deploy-key",
    }
    assert not any("ci_restrict" in t for t in homelab_node.status_problems(status))


def test_refused_setup_reports_only_the_reason():
    status = {**OK_STATUS, "problems": ["homelab.user is root"], "docker": False}
    assert homelab_node.status_problems(status) == ["homelab.user is root"]


def test_attention_reads_the_status_file(tmp_path, monkeypatch, fake_bw):
    _cli, machine, _home, _store = homelab_machine(tmp_path, monkeypatch, fake_bw)
    status = tmp_path / "homelab-node.json"
    monkeypatch.setattr(machine, "homelab_status_file", status)
    assert machine.homelab_problems() == []
    status.write_text(json.dumps({**OK_STATUS, "docker": False}), encoding="utf-8")
    kinds = [item.kind for item in machine.attention_items() if item.kind == "homelab"]
    assert kinds == ["homelab"]


def test_attention_ignores_the_status_file_without_the_feature(
    tmp_path, monkeypatch, fake_bw
):
    _cli, machine, _home, _store = homelab_machine(
        tmp_path, monkeypatch, fake_bw, features=("zsh-full",)
    )
    status = tmp_path / "homelab-node.json"
    status.write_text(json.dumps({**OK_STATUS, "docker": False}), encoding="utf-8")
    monkeypatch.setattr(machine, "homelab_status_file", status)
    assert machine.homelab_problems() == []
