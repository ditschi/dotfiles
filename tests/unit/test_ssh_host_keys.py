from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from machine_loader import load_machine_module
from package_sets import REPO

MACHINE = REPO / "machine_cli/machine"
HOST = "unit-test-host"
ITEM = f"ssh/home/hosts/{HOST}"


def ssh_machine(tmp_path, monkeypatch, fake_bw, context="private", session=True):
    bw, store = fake_bw
    repo = tmp_path / "dotfiles"
    (repo / "home").mkdir(parents=True)
    (repo / ".git").mkdir()
    home = tmp_path / "home"
    (home / ".ssh").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("DOTFILES_REPO", str(repo))
    monkeypatch.setenv("PATH", f"{bw.parent}:{os.environ.get('PATH', '')}")
    if session:
        monkeypatch.setenv("BW_SESSION", "fake-session")
    monkeypatch.setenv(
        "MACHINE_APPLIED_HOST_FILE", str(home / ".config/machine/profile.yml")
    )
    monkeypatch.setenv(
        "MISE_LOCAL_CONFIG", str(home / ".config/mise/config.local.toml")
    )
    monkeypatch.setenv("MACHINE_STATE_DIR", str(home / ".local/share/machine"))
    cli = load_machine_module("machine_ssh", MACHINE)
    monkeypatch.setattr(cli.system, "in_docker", lambda: False)
    monkeypatch.setattr(cli.system, "is_tty", lambda: False)
    monkeypatch.setattr(cli.system, "hostname_short", lambda: HOST)
    machine = cli.Machine()
    machine.write_profile(context, "desktop", ["zsh-full", "ssh-host-key"], [])
    return cli, machine, home, repo, store


def make_key(path: Path) -> str:
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(path)],
        check=True,
        capture_output=True,
    )
    return Path(str(path) + ".pub").read_text().strip()


def fingerprint(public: str) -> str:
    out = subprocess.run(
        ["ssh-keygen", "-l", "-E", "sha256", "-f", "-"],
        input=public + "\n",
        text=True,
        capture_output=True,
        check=True,
    ).stdout
    return out.split()[1]


def items(store: Path, name: str = ITEM) -> list:
    data = json.loads(store.read_text())
    return [i for i in data.get("items", {}).values() if i.get("name") == name]


def trash(store: Path) -> list:
    return list(json.loads(store.read_text()).get("trash", {}).values())


def put_items(store: Path, *entries: dict) -> None:
    data = json.loads(store.read_text())
    data["items"] = {e["id"]: e for e in entries}
    store.write_text(json.dumps(data))


def ssh_item(public: str, private: str = "PRIVATE\n", item_id="old-ssh") -> dict:
    return {
        "id": item_id,
        "type": 5,
        "name": ITEM,
        "sshKey": {
            "privateKey": private,
            "publicKey": public,
            "keyFingerprint": fingerprint(public),
        },
    }


def note_item(public: str, private: str) -> dict:
    fields = [
        {"name": "public_key", "value": public, "type": 0},
        {"name": "private_key", "value": private, "type": 1},
    ]
    return {"id": "old-note", "type": 2, "name": ITEM, "fields": fields}


def no_prompts(cli, monkeypatch):
    monkeypatch.setattr(
        cli.system, "prompt_yes_no", lambda *_a, **_k: pytest.fail("must not prompt")
    )
    monkeypatch.setattr(
        cli.system, "choose", lambda *_a, **_k: pytest.fail("must not prompt")
    )


def test_setup_stores_whole_key_as_ssh_key_item(tmp_path, monkeypatch, fake_bw, capsys):
    cli, machine, home, repo, store = ssh_machine(tmp_path, monkeypatch, fake_bw)
    monkeypatch.setattr(cli.system, "is_tty", lambda: True)
    no_prompts(cli, monkeypatch)
    public = make_key(home / ".ssh/id_ed25519")
    assert machine.provision_host_ssh_key() == 0
    [item] = items(store)
    assert item["type"] == 5
    assert item["sshKey"]["privateKey"] == (home / ".ssh/id_ed25519").read_text()
    assert item["sshKey"]["publicKey"] == public
    assert item["sshKey"]["keyFingerprint"] == fingerprint(public)
    # home class: public key versioned for authorized_keys, written without a question
    assert (repo / f"machine/ssh_keys/{HOST}.pub").read_text() == public + "\n"
    assert "commit and push" in capsys.readouterr().out


def test_same_key_changes_nothing(tmp_path, monkeypatch, fake_bw):
    _, machine, home, _, store = ssh_machine(tmp_path, monkeypatch, fake_bw)
    public = make_key(home / ".ssh/id_ed25519")
    put_items(store, ssh_item(public))
    before = store.read_text()
    assert machine.provision_host_ssh_key() == 0
    assert store.read_text() == before
    assert not machine.ssh_key_attention.exists()


def test_other_key_is_kept_and_reported(tmp_path, monkeypatch, fake_bw):
    cli, machine, home, _, store = ssh_machine(tmp_path, monkeypatch, fake_bw)
    monkeypatch.setattr(cli.system, "is_tty", lambda: True)
    no_prompts(cli, monkeypatch)
    key = home / ".ssh/id_ed25519"
    local = make_key(key)
    original = key.read_bytes()
    other = make_key(tmp_path / "other")
    put_items(store, ssh_item(other))
    assert machine.provision_host_ssh_key() == 0
    assert items(store)[0]["sshKey"]["publicKey"] == other
    assert key.read_bytes() == original
    reason = machine.ssh_key_attention.read_text()
    assert fingerprint(local) in reason and fingerprint(other) in reason
    assert "ssh-key" in [i.kind for i in machine.attention_items()]


def test_secure_note_with_the_same_name_is_ignored(tmp_path, monkeypatch, fake_bw):
    _, machine, home, _, store = ssh_machine(tmp_path, monkeypatch, fake_bw)
    note_key = make_key(tmp_path / "noted")
    note = note_item(note_key, (tmp_path / "noted").read_text())
    put_items(store, note)
    public = make_key(home / ".ssh/id_ed25519")
    assert machine.provision_host_ssh_key() == 0
    by_type = {i["type"]: i for i in items(store)}
    assert by_type[2] == note
    assert by_type[5]["sshKey"]["publicKey"] == public
    assert not machine.ssh_key_attention.exists()


def test_work_key_is_not_written_to_the_repo(tmp_path, monkeypatch, fake_bw):
    _, machine, home, repo, store = ssh_machine(
        tmp_path, monkeypatch, fake_bw, context="work"
    )
    make_key(home / ".ssh/id_ed25519")
    assert machine.provision_host_ssh_key() == 0
    assert items(store, f"ssh/work/hosts/{HOST}")
    assert not (repo / "machine/ssh_keys").exists()


def test_cli_offers_sync_and_rotate_only():
    result = subprocess.run(
        ["python3", str(MACHINE), "ssh", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "sync" in result.stdout and "rotate" in result.stdout
    for gone in ("publish", "restore", "--private"):
        assert gone not in result.stdout


def test_setup_restores_the_key_of_a_reinstalled_host(tmp_path, monkeypatch, fake_bw):
    cli, machine, home, _, store = ssh_machine(tmp_path, monkeypatch, fake_bw)
    no_prompts(cli, monkeypatch)
    public = make_key(tmp_path / "saved")
    private = (tmp_path / "saved").read_text()
    put_items(store, ssh_item(public, private))
    assert machine.provision_host_ssh_key() == 0
    restored, restored_pub = machine.host_key_paths()
    assert restored.read_text() == private
    assert restored_pub.read_text().strip() == public
    assert machine.saved_ssh_key() == restored
    assert len(items(store)) == 1


def test_setup_uploads_an_existing_key_unchanged(tmp_path, monkeypatch, fake_bw):
    _, machine, home, _, store = ssh_machine(tmp_path, monkeypatch, fake_bw)
    key = home / ".ssh/id_ed25519"
    public = make_key(key)
    original = key.read_bytes()
    assert machine.provision_host_ssh_key() == 0
    assert key.read_bytes() == original
    assert not machine.host_key_paths()[0].exists()
    assert items(store)[0]["sshKey"]["publicKey"] == public


def test_setup_generates_a_key_for_a_new_host(tmp_path, monkeypatch, fake_bw, capsys):
    _, machine, home, _, store = ssh_machine(tmp_path, monkeypatch, fake_bw)
    assert machine.provision_host_ssh_key() == 0
    private, public = machine.host_key_paths()
    assert private.is_file() and public.read_text().startswith("ssh-ed25519 ")
    # no passphrase: the public key derives without a prompt
    subprocess.run(
        ["ssh-keygen", "-y", "-P", "", "-f", str(private)],
        check=True,
        capture_output=True,
    )
    assert items(store)[0]["sshKey"]["publicKey"] == public.read_text().strip()
    assert "gh ssh-key add" in capsys.readouterr().out


def test_setup_without_bitwarden_creates_nothing(
    tmp_path, monkeypatch, fake_bw, capsys
):
    cli, machine, home, _, store = ssh_machine(
        tmp_path, monkeypatch, fake_bw, session=False
    )
    monkeypatch.setattr(cli.system, "is_tty", lambda: True)
    monkeypatch.setattr(
        machine, "unlock_bitwarden", lambda **_k: pytest.fail("no extra unlock prompt")
    )
    assert machine.provision_host_ssh_key() == 1
    assert not machine.host_key_paths()[0].exists()
    assert not items(store)
    assert "machine setup" in capsys.readouterr().out


def selected_machine(tmp_path, monkeypatch, fake_bw, session=True):
    cli, machine, home, repo, store = ssh_machine(
        tmp_path, monkeypatch, fake_bw, session=session
    )
    key = home / ".ssh/id_ed25519"
    public = make_key(key)
    machine.remember_ssh_key(key)
    return cli, machine, key, store, public


def test_update_backs_up_a_missing_item(tmp_path, monkeypatch, fake_bw):
    cli, machine, _, store, public = selected_machine(tmp_path, monkeypatch, fake_bw)
    no_prompts(cli, monkeypatch)
    machine.check_ssh_key_backup()
    assert items(store)[0]["sshKey"]["publicKey"] == public
    assert not machine.ssh_key_attention.exists()


def test_update_reports_a_different_key(tmp_path, monkeypatch, fake_bw):
    cli, machine, _, store, public = selected_machine(tmp_path, monkeypatch, fake_bw)
    no_prompts(cli, monkeypatch)
    other = make_key(tmp_path / "other")
    put_items(store, ssh_item(other))
    machine.check_ssh_key_backup()
    assert "another key" in machine.ssh_key_attention.read_text()
    assert items(store)[0]["sshKey"]["publicKey"] == other
    put_items(store, ssh_item(public))
    machine.check_ssh_key_backup()
    assert not machine.ssh_key_attention.exists()


def test_update_without_session_warns_how_to_log_in(
    tmp_path, monkeypatch, fake_bw, capsys
):
    cli, machine, _, store, _ = selected_machine(
        tmp_path, monkeypatch, fake_bw, session=False
    )
    no_prompts(cli, monkeypatch)
    machine.check_ssh_key_backup()
    out = capsys.readouterr()
    assert "machine env pull" in out.out + out.err
    assert not items(store) and not machine.ssh_key_attention.exists()


def test_background_update_does_not_use_bitwarden(tmp_path, monkeypatch, fake_bw):
    cli, machine, _, _, _ = selected_machine(tmp_path, monkeypatch, fake_bw)
    real_run = cli.system.run
    calls = []

    def run(args, **kwargs):
        calls.append(list(args))
        return real_run(args, **kwargs)

    monkeypatch.setattr(cli.system, "run", run)
    monkeypatch.setattr(machine, "run_local_resolvers", lambda *_a, **_k: None)
    monkeypatch.setattr(
        machine,
        "update_plan",
        lambda **_k: {"state": "up-to-date", "steps": [], "blockers": []},
    )
    assert machine._update_auto_locked() == 0
    assert not [c for c in calls if c and c[0] == "bw"]


def different_keys(tmp_path, monkeypatch, fake_bw, answer=None):
    cli, machine, key, store, local = selected_machine(tmp_path, monkeypatch, fake_bw)
    other = make_key(tmp_path / "other")
    put_items(store, ssh_item(other, (tmp_path / "other").read_text()))
    machine.check_ssh_key_backup()
    if answer:
        monkeypatch.setattr(cli.system, "is_tty", lambda: True)
        monkeypatch.setattr(cli.system, "choose", lambda *_a: answer)
    return machine, key, store, local, other


def test_sync_local_wins(tmp_path, monkeypatch, fake_bw):
    machine, key, store, local, _ = different_keys(
        tmp_path, monkeypatch, fake_bw, "local"
    )
    assert machine.resolve_ssh_key_difference() == 0
    assert items(store)[0]["sshKey"]["publicKey"] == local
    assert not machine.ssh_key_attention.exists()


def test_sync_bitwarden_wins_keeps_the_old_key(tmp_path, monkeypatch, fake_bw):
    machine, key, store, local, other = different_keys(
        tmp_path, monkeypatch, fake_bw, "bitwarden"
    )
    old_private = key.read_text()
    assert machine.resolve_ssh_key_difference() == 0
    assert key.read_text() == (tmp_path / "other").read_text()
    assert Path(f"{key}.pub").read_text().strip() == other
    [old] = key.parent.glob("id_ed25519.old-*")
    assert old.read_text() == old_private
    [old_pub] = key.parent.glob("id_ed25519.pub.old-*")
    assert old_pub.read_text().strip() == local
    assert not machine.ssh_key_attention.exists()


def test_sync_later_changes_nothing(tmp_path, monkeypatch, fake_bw):
    machine, key, store, local, other = different_keys(
        tmp_path, monkeypatch, fake_bw, "later"
    )
    before = key.read_bytes()
    assert machine.resolve_ssh_key_difference() == 0
    assert key.read_bytes() == before
    assert items(store)[0]["sshKey"]["publicKey"] == other
    assert machine.ssh_key_attention.exists()


def test_sync_without_terminal_changes_nothing(tmp_path, monkeypatch, fake_bw):
    machine, key, store, _, other = different_keys(tmp_path, monkeypatch, fake_bw)
    before = key.read_bytes()
    assert machine.resolve_ssh_key_difference() == 1
    assert key.read_bytes() == before
    assert items(store)[0]["sshKey"]["publicKey"] == other


def test_rotate_replaces_key_and_item(tmp_path, monkeypatch, fake_bw):
    cli, machine, home, repo, store = ssh_machine(tmp_path, monkeypatch, fake_bw)
    private, public = machine.host_key_paths()
    old = make_key(private)
    put_items(store, ssh_item(old))
    assert machine.rotate_ssh_key() == 0
    new = public.read_text().strip()
    assert new != old
    assert machine.saved_ssh_key() == private
    assert [p.read_text().strip() for p in home.glob(".ssh/*.pub.old-*")] == [old]
    [item] = items(store)
    assert item["sshKey"]["publicKey"] == new
    assert (repo / f"machine/ssh_keys/{HOST}.pub").read_text().strip() == new
