"""Key Vault -> Bitwarden sync of the technical users (spec techuser-password-sync)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from test_ssh_client import client

USER_A, USER_B = "ci-user-a", "ci-user-b"
MAPPING = (
    f"{USER_A}=vault-a/technical-user-password {USER_B}=vault-b/technical-user-password"
)
NEW = "new-pw-from-vault"  # pragma: allowlist secret
ID_A, ID_B = f"id-{USER_A}-1", f"id-{USER_B}-1"


@pytest.fixture
def az(tmp_path, monkeypatch):
    path = tmp_path / "azbin"
    path.mkdir()
    script = path / "az"
    script.write_text(
        "#!/bin/sh\n"
        'echo "$@" >>"$FAKE_AZ_LOG"\n'
        '[ -z "$FAKE_AZ_ERROR" ] || { echo "$FAKE_AZ_ERROR" >&2; exit 1; }\n'
        'case "$5" in *vault-a*) echo "$FAKE_AZ_A" ;; *vault-b*) echo "$FAKE_AZ_B" ;; esac\n'
    )
    script.chmod(0o755)
    log = tmp_path / "az.log"
    monkeypatch.setenv("PATH", f"{path}:{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_AZ_LOG", str(log))
    monkeypatch.setenv("FAKE_AZ_A", NEW)
    monkeypatch.setenv("FAKE_AZ_B", NEW)
    monkeypatch.delenv("FAKE_AZ_ERROR", raising=False)
    return log


def work_client(tmp_path, monkeypatch, fake_bw, mapping=MAPPING):
    cli, machine, home, _repo, store = client(tmp_path, monkeypatch, fake_bw, "work")
    if mapping:
        (home / ".env").write_text(f'AZKV_TECHUSERS="{mapping}"\n')
    return machine, home, store


def put_login(store: Path, user: str, password: str, kind: int = 1) -> None:
    data = json.loads(store.read_text())
    data.setdefault("items", {})[f"id-{user}-{kind}"] = {
        "id": f"id-{user}-{kind}",
        "type": kind,
        "name": user,
        "login": {"username": user, "password": password},
    }
    store.write_text(json.dumps(data))


def passwords(store: Path) -> dict:
    items = json.loads(store.read_text()).get("items", {})
    return {i["id"]: i.get("login", {}).get("password") for i in items.values()}


def test_outdated_item_follows_key_vault(tmp_path, monkeypatch, fake_bw, az, capsys):
    machine, _home, store = work_client(tmp_path, monkeypatch, fake_bw)
    put_login(store, USER_A, "old")
    put_login(store, USER_B, NEW)
    assert machine.sync_techuser_passwords() == 0
    assert passwords(store) == {ID_A: NEW, ID_B: NEW}
    shown = capsys.readouterr()
    assert f"{USER_A}: Bitwarden password updated" in shown.out + shown.err
    assert USER_B not in shown.out + shown.err
    assert NEW not in shown.out + shown.err


def test_equal_passwords_write_nothing(tmp_path, monkeypatch, fake_bw, az, capsys):
    machine, _home, store = work_client(tmp_path, monkeypatch, fake_bw)
    put_login(store, USER_A, NEW)
    put_login(store, USER_B, NEW)
    before = store.read_text()
    machine.sync_techuser_passwords()
    assert store.read_text() == before
    shown = capsys.readouterr()
    assert (
        "technical user passwords: 0 updated, 2 already equal" in shown.out + shown.err
    )


def test_missing_item_is_reported_not_created(
    tmp_path, monkeypatch, fake_bw, az, capsys
):
    machine, _home, store = work_client(tmp_path, monkeypatch, fake_bw)
    put_login(store, USER_A, "old")
    machine.sync_techuser_passwords()
    assert passwords(store) == {ID_A: NEW}
    shown = capsys.readouterr()
    assert f"no Bitwarden login item named {USER_B}" in shown.out + shown.err


def test_duplicate_items_are_left_alone(tmp_path, monkeypatch, fake_bw, az):
    machine, _home, store = work_client(tmp_path, monkeypatch, fake_bw)
    put_login(store, USER_A, "old")
    data = json.loads(store.read_text())
    data["items"]["id-dup"] = {
        "id": "id-dup",
        "type": 1,
        "name": USER_A,
        "login": {"password": "other"},  # pragma: allowlist secret
    }
    store.write_text(json.dumps(data))
    machine.sync_techuser_passwords()
    assert passwords(store)[ID_A] == "old"
    assert passwords(store)["id-dup"] == "other"


def test_secure_note_with_the_name_is_ignored(tmp_path, monkeypatch, fake_bw, az):
    machine, _home, store = work_client(tmp_path, monkeypatch, fake_bw)
    put_login(store, USER_A, "old", kind=2)
    machine.sync_techuser_passwords()
    assert passwords(store) == {f"id-{USER_A}-2": "old"}


def test_az_login_missing_records_attention_and_clears(
    tmp_path, monkeypatch, fake_bw, az
):
    machine, _home, store = work_client(tmp_path, monkeypatch, fake_bw)
    put_login(store, USER_A, "old")
    monkeypatch.setenv("FAKE_AZ_ERROR", "Please run 'az login' to setup account.")
    assert machine.sync_techuser_passwords() == 0
    assert passwords(store) == {ID_A: "old"}
    assert [i.kind for i in machine.attention_items()] == ["azure"]
    monkeypatch.delenv("FAKE_AZ_ERROR")
    machine.sync_techuser_passwords()
    assert [i.kind for i in machine.attention_items()] == []


def test_unknown_secret_does_not_ask_for_a_login(tmp_path, monkeypatch, fake_bw, az):
    machine, _home, store = work_client(tmp_path, monkeypatch, fake_bw)
    put_login(store, USER_A, "old")
    monkeypatch.setenv("FAKE_AZ_ERROR", "(SecretNotFound) A secret with name ...")
    machine.sync_techuser_passwords()
    assert not machine.azure_notice_path.exists()


@pytest.mark.parametrize(
    "error",
    [
        "(Forbidden) Client address is not authorized. ForbiddenByFirewall",
        "(Forbidden) Public network access is disabled. ForbiddenByConnection",
    ],
)
def test_firewalled_vault_needs_attention(tmp_path, monkeypatch, fake_bw, az, error):
    machine, _home, store = work_client(tmp_path, monkeypatch, fake_bw)
    put_login(store, USER_A, "old")
    monkeypatch.setenv("FAKE_AZ_ERROR", error)
    machine.sync_techuser_passwords()
    assert machine.azure_notice_path.exists()


def test_forbidden_secret_does_not_ask_for_a_login(tmp_path, monkeypatch, fake_bw, az):
    machine, _home, store = work_client(tmp_path, monkeypatch, fake_bw)
    put_login(store, USER_A, "old")
    monkeypatch.setenv("FAKE_AZ_ERROR", "(Forbidden) The user is not allowed ...")
    machine.sync_techuser_passwords()
    assert not machine.azure_notice_path.exists()


def test_notice_is_cleared_when_the_mapping_is_gone(tmp_path, monkeypatch, fake_bw, az):
    machine, home, _store = work_client(tmp_path, monkeypatch, fake_bw)
    machine.record_azure_notice()
    (home / ".env").write_text("OTHER=1\n")
    monkeypatch.delenv("AZKV_TECHUSERS", raising=False)
    machine.sync_techuser_passwords()
    assert not machine.azure_notice_path.exists()


def test_attention_login_action_without_az_clears_the_item(
    tmp_path, monkeypatch, fake_bw
):
    cli, machine, _home, _repo, _store = client(tmp_path, monkeypatch, fake_bw, "work")
    machine.record_azure_notice()
    monkeypatch.setattr(cli.system, "have", lambda name: False)
    assert machine._az_login_and_sync() == 0
    assert not machine.azure_notice_path.exists()


def test_step_survives_an_exception(tmp_path, monkeypatch, fake_bw, capsys):
    machine, _home, _store = work_client(tmp_path, monkeypatch, fake_bw)

    def boom(**_):
        raise SystemExit("bw exploded")

    monkeypatch.setattr(machine, "sync_techuser_passwords", boom)
    assert machine.sync_techuser_passwords_step() == 0
    shown = capsys.readouterr()
    assert "bw exploded" in shown.out + shown.err


def test_without_mapping_nothing_is_called(tmp_path, monkeypatch, fake_bw, az):
    machine, _home, _store = work_client(tmp_path, monkeypatch, fake_bw, mapping="")
    monkeypatch.delenv("AZKV_TECHUSERS", raising=False)
    assert machine.sync_techuser_passwords() == 0
    assert not az.exists()


def test_mapping_from_the_environment_when_no_file_sets_it(
    tmp_path, monkeypatch, fake_bw, az
):
    machine, _home, store = work_client(tmp_path, monkeypatch, fake_bw, mapping="")
    monkeypatch.setenv("AZKV_TECHUSERS", MAPPING)
    put_login(store, USER_A, "old")
    machine.sync_techuser_passwords()
    assert passwords(store)[ID_A] == NEW


def test_env_file_wins_over_the_environment(tmp_path, monkeypatch, fake_bw, az):
    machine, _home, _store = work_client(tmp_path, monkeypatch, fake_bw)
    monkeypatch.setenv("AZKV_TECHUSERS", "other=vault-x/secret-x")
    assert set(machine.techuser_mapping()) == {USER_A, USER_B}


def test_quoted_value_in_the_environment_is_accepted(
    tmp_path, monkeypatch, fake_bw, az
):
    machine, _home, _store = work_client(tmp_path, monkeypatch, fake_bw, mapping="")
    monkeypatch.setenv("AZKV_TECHUSERS", f'"{MAPPING}"')
    assert set(machine.techuser_mapping()) == {USER_A, USER_B}


def test_bitwarden_locked_reads_nothing(tmp_path, monkeypatch, fake_bw, az, capsys):
    machine, _home, store = work_client(tmp_path, monkeypatch, fake_bw)
    put_login(store, USER_A, "old")
    monkeypatch.delenv("BW_SESSION")
    assert machine.sync_techuser_passwords() == 0
    assert not az.exists()
    assert passwords(store) == {ID_A: "old"}
    shown = capsys.readouterr()
    assert "Bitwarden is not unlocked" in shown.out + shown.err


def test_bad_entry_is_ignored(tmp_path, monkeypatch, fake_bw, az):
    machine, _home, _store = work_client(
        tmp_path, monkeypatch, fake_bw, mapping=f"broken {USER_A}=vault-a/s"
    )
    assert machine.techuser_mapping() == {USER_A: ("vault-a", "s")}
