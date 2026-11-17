"""~/.netrc generated from Bitwarden by `machine env pull` and `machine env push`."""

from __future__ import annotations

import pytest

from machine_cli.netrc_sync import parse_netrc, replace_tokens
from test_update_and_env import (
    _answer,
    _bw_item,
    _bw_set_item,
    _env_machine,
    _item,
    _login,
    _yes_no,
    machine_system,
)

NOTES = """machine artifactory.example.com
  login {{bw:Work login/username}}
  password {{bw:Work login/field:artifactory-token}}

# azure
machine dev.azure.example
  login alice@example.com
  password {{bw:Work login/field:ado-token}}

machine legacy.example
  login bob
  password lit-1
"""

GENERATED = """machine artifactory.example.com
  login alice
  password tok-1

# azure
machine dev.azure.example
  login alice@example.com
  password ado-1

machine legacy.example
  login bob
  password lit-1
"""


def _work_login(**fields: str) -> dict:
    fields = {"artifactory-token": "tok-1", "ado-token": "ado-1", **fields}
    return _login("Work login", "pw", username="alice", **fields)


def _netrc_machine(
    tmp_path, monkeypatch, fake_bw, notes=NOTES, host_notes=None, **extra
):
    items = {
        "netrc/groups/work": {"id": "netrc-id", **_item(notes)},
        "Work login": _work_login(),
        **extra,
    }
    if host_notes is not None:
        items["netrc/hosts/testhost"] = {"id": "netrc-host-id", **_item(host_notes)}
    return _env_machine(tmp_path, monkeypatch, fake_bw, "work-machine", items)


def _pulled(tmp_path, monkeypatch, fake_bw, **kwargs):
    machine, home = _netrc_machine(tmp_path, monkeypatch, fake_bw, **kwargs)
    assert machine.cmd_env_pull() == 0
    return machine, home


def _edit(home, old, new):
    path = home / ".netrc"
    path.write_text(path.read_text().replace(old, new))


def _all_output(capsys) -> str:
    captured = capsys.readouterr()
    return captured.out + captured.err


# --- parsing ---------------------------------------------------------------


def test_parse_netrc_keeps_reference_tokens_with_spaces_whole():
    [block] = parse_netrc(
        "machine h\n  login {{bw:Bosch User -- X/username}}\n  password p\n"
    )
    assert block.host == "h"
    assert block.tokens() == [
        "machine",
        "h",
        "login",
        "{{bw:Bosch User -- X/username}}",
        "password",
        "p",
    ]


def test_parse_netrc_reads_one_line_blocks_default_and_leading_comments():
    blocks = parse_netrc(
        "# for api\nmachine a login token password t\n\ndefault login x password y\n"
    )
    assert [b.host for b in blocks] == ["a", "default"]
    assert blocks[0].lines[0] == "# for api"
    assert blocks[0].tokens()[:2] == ["machine", "a"]


def test_replace_tokens_swaps_the_nth_code_token():
    lines = ["# c", "machine h", "  login a password b"]
    assert replace_tokens(lines, {3: "A", 5: "B"}) == [
        "# c",
        "machine h",
        "  login A password B",
    ]


# --- pull ------------------------------------------------------------------


def test_pull_writes_blocks_with_resolved_references(tmp_path, monkeypatch, fake_bw):
    machine, home = _pulled(tmp_path, monkeypatch, fake_bw)

    netrc = home / ".netrc"
    assert netrc.read_text() == GENERATED
    assert netrc.stat().st_mode & 0o777 == 0o600
    assert "{{bw:" not in netrc.read_text()
    assert machine.netrc_attention() == []


def test_pull_runs_without_any_env_item(tmp_path, monkeypatch, fake_bw):
    machine, home = _netrc_machine(tmp_path, monkeypatch, fake_bw)

    assert not (home / ".env").exists()
    assert machine.cmd_env_pull() == 0
    assert (home / ".netrc").read_text() == GENERATED


def test_host_item_comes_first_and_both_items_stay_as_they_are(
    tmp_path, monkeypatch, fake_bw
):
    host_notes = (
        "machine artifactory.example.com\n  login host\n  password hostpw\n\n"
        "machine extra.example\n  login e\n  password x\n"
    )
    _machine, home = _pulled(tmp_path, monkeypatch, fake_bw, host_notes=host_notes)

    blocks = parse_netrc((home / ".netrc").read_text())
    assert [b.host for b in blocks] == [
        "artifactory.example.com",
        "extra.example",
        "artifactory.example.com",
        "dev.azure.example",
        "legacy.example",
    ]
    assert blocks[0].tokens()[-1] == "hostpw"
    assert blocks[2].tokens()[-1] == "tok-1"


def test_pull_skips_a_block_with_an_unresolvable_reference(
    tmp_path, monkeypatch, fake_bw, capsys
):
    notes = NOTES.replace("field:ado-token", "field:missing-token")
    machine, home = _pulled(tmp_path, monkeypatch, fake_bw, notes=notes)

    text = (home / ".netrc").read_text()
    assert "dev.azure.example" not in text
    assert "artifactory.example.com" in text and "legacy.example" in text
    output = _all_output(capsys)
    assert "dev.azure.example" in output and "missing-token" in output
    assert "tok-1" not in output and "ado-1" not in output
    [item] = machine.netrc_attention()
    assert "dev.azure.example" in item and "ado-1" not in item


@pytest.mark.parametrize("bad", ["tok 1", "tok'1", 'tok"1', "tok\\1"])
def test_pull_skips_a_block_whose_value_cannot_be_written_unchanged(
    tmp_path, monkeypatch, fake_bw, capsys, bad
):
    machine, home = _netrc_machine(
        tmp_path,
        monkeypatch,
        fake_bw,
        **{"Work login": _work_login(**{"artifactory-token": bad})},
    )

    assert machine.cmd_env_pull() == 0
    text = (home / ".netrc").read_text()
    assert "artifactory.example.com" not in text and "dev.azure.example" in text
    assert bad not in _all_output(capsys)


def test_pull_leaves_netrc_alone_without_netrc_items(tmp_path, monkeypatch, fake_bw):
    machine, home = _env_machine(tmp_path, monkeypatch, fake_bw, "work-machine", {})
    (home / ".netrc").write_text("machine hand.example login x password y\n")

    assert machine.cmd_env_pull() == 0
    assert (home / ".netrc").read_text() == "machine hand.example login x password y\n"


def test_pull_leaves_netrc_alone_when_bitwarden_stays_locked(
    tmp_path, monkeypatch, fake_bw
):
    machine, home = _netrc_machine(tmp_path, monkeypatch, fake_bw)
    monkeypatch.setattr(machine, "unlock_bitwarden", lambda **kw: False)
    (home / ".netrc").write_text("machine hand.example login x password y\n")

    assert machine.cmd_env_pull() == 0
    assert (home / ".netrc").read_text() == "machine hand.example login x password y\n"


def test_pull_leaves_netrc_alone_when_items_cannot_be_listed(
    tmp_path, monkeypatch, fake_bw
):
    machine, home = _netrc_machine(tmp_path, monkeypatch, fake_bw)
    monkeypatch.setattr(machine, "bw_items_named", lambda name: None)
    (home / ".netrc").write_text("machine hand.example login x password y\n")

    assert machine.cmd_env_pull() == 0
    assert (home / ".netrc").read_text() == "machine hand.example login x password y\n"


def test_pull_replaces_a_hand_written_netrc_after_a_backup(
    tmp_path, monkeypatch, fake_bw
):
    machine, home = _netrc_machine(tmp_path, monkeypatch, fake_bw)
    (home / ".netrc").write_text("machine hand.example login x password y\n")

    assert machine.cmd_env_pull() == 0
    assert (home / ".netrc").read_text() == GENERATED
    backups = list((machine.state_dir / "env-backup").glob("netrc.*"))
    assert any("hand.example" in p.read_text() for p in backups)


def test_pull_warns_for_github_com_only(tmp_path, monkeypatch, fake_bw, capsys):
    notes = "machine github.com\n  login t\n  password p\n"
    _machine, home = _pulled(tmp_path, monkeypatch, fake_bw, notes=notes)
    assert "machine github.com" in (home / ".netrc").read_text()
    assert "github.com" in _all_output(capsys)


def test_pull_does_not_warn_for_an_enterprise_github_host(
    tmp_path, monkeypatch, fake_bw, capsys
):
    notes = "machine github.example.com\n  login t\n  password p\n"
    _pulled(tmp_path, monkeypatch, fake_bw, notes=notes)
    assert "credential helpers" not in _all_output(capsys)


def test_pull_keeps_comment_lines(tmp_path, monkeypatch, fake_bw):
    _machine, home = _pulled(tmp_path, monkeypatch, fake_bw)
    assert "# azure\nmachine dev.azure.example" in (home / ".netrc").read_text()


# --- unpushed local edits ---------------------------------------------------


def test_pull_keeps_unpushed_edits_without_a_terminal(tmp_path, monkeypatch, fake_bw):
    machine, home = _pulled(tmp_path, monkeypatch, fake_bw)
    _edit(home, "tok-1", "tok-2")
    edited = (home / ".netrc").read_text()

    assert machine.cmd_env_pull() == 0
    assert (home / ".netrc").read_text() == edited
    [item] = machine.netrc_attention()
    assert "artifactory.example.com" in item and "tok-2" not in item


def test_pull_asks_with_skip_preselected(tmp_path, monkeypatch, fake_bw):
    machine, home = _pulled(tmp_path, monkeypatch, fake_bw)
    _edit(home, "tok-1", "tok-2")
    edited = (home / ".netrc").read_text()
    asked = _answer(monkeypatch, machine, "skip")

    assert machine.cmd_env_pull() == 0
    [(choices, default)] = asked
    assert [c.split(" ")[0] for c in choices] == ["push", "discard", "skip"]
    assert default.startswith("skip")
    assert (home / ".netrc").read_text() == edited


def test_pull_discards_edits_after_a_backup(tmp_path, monkeypatch, fake_bw):
    machine, home = _pulled(tmp_path, monkeypatch, fake_bw)
    _edit(home, "tok-1", "tok-2")
    _answer(monkeypatch, machine, "discard")

    assert machine.cmd_env_pull() == 0
    assert (home / ".netrc").read_text() == GENERATED
    backups = (machine.state_dir / "env-backup").glob("netrc.*")
    assert any("tok-2" in p.read_text() for p in backups)
    assert machine.netrc_attention() == []


# --- push --------------------------------------------------------------------


def test_pull_pushes_a_changed_referenced_value_into_the_referenced_item(
    tmp_path, monkeypatch, fake_bw
):
    machine, home = _pulled(tmp_path, monkeypatch, fake_bw)
    _edit(home, "tok-1", "tok-2")
    _answer(monkeypatch, machine, "push")
    _yes_no(monkeypatch)

    assert machine.cmd_env_pull() == 0
    fields = {f["name"]: f["value"] for f in _bw_item(fake_bw, "Work login")["fields"]}
    assert fields["artifactory-token"] == "tok-2"
    assert _bw_item(fake_bw, "netrc/groups/work")["notes"] == NOTES
    assert "password tok-2" in (home / ".netrc").read_text()
    assert machine.netrc_attention() == []


def test_push_replaces_a_changed_literal_in_the_notes(tmp_path, monkeypatch, fake_bw):
    machine, home = _pulled(tmp_path, monkeypatch, fake_bw)
    _edit(home, "lit-1", "lit-2")
    _answer(monkeypatch, machine, "push")
    _yes_no(monkeypatch)

    assert machine.cmd_env_pull() == 0
    assert _bw_item(fake_bw, "netrc/groups/work")["notes"] == NOTES.replace(
        "lit-1", "lit-2"
    )


def test_push_appends_a_new_block(tmp_path, monkeypatch, fake_bw, capsys):
    machine, home = _pulled(tmp_path, monkeypatch, fake_bw)
    with (home / ".netrc").open("a") as handle:
        handle.write("\nmachine new.example\n  login me\n  password pw-new\n")
    _answer(monkeypatch, machine, "push")
    _yes_no(monkeypatch)

    assert machine.cmd_env_pull() == 0
    notes = _bw_item(fake_bw, "netrc/groups/work")["notes"]
    assert notes.endswith("machine new.example\n  login me\n  password pw-new")
    assert "# added from testhost on" in notes
    output = _all_output(capsys)
    assert "add     new.example" in output and "pw-new" not in output


def test_push_adds_a_reference_and_resolves_it(tmp_path, monkeypatch, fake_bw):
    machine, home = _pulled(tmp_path, monkeypatch, fake_bw)
    with (home / ".netrc").open("a") as handle:
        handle.write(
            "\nmachine new.example\n  login {{bw:Work login/username}}\n"
            "  password {{bw:Work login/field:ado-token}}\n"
        )
    _answer(monkeypatch, machine, "push")
    _yes_no(monkeypatch)

    assert machine.cmd_env_pull() == 0
    assert (
        "password {{bw:Work login/field:ado-token}}"
        in _bw_item(fake_bw, "netrc/groups/work")["notes"]
    )
    assert (
        "login alice\n  password ado-1"
        in (home / ".netrc").read_text().split("machine new.example")[1]
    )


def test_push_with_a_reference_typo_writes_nothing(
    tmp_path, monkeypatch, fake_bw, capsys
):
    machine, home = _pulled(tmp_path, monkeypatch, fake_bw)
    _edit(home, "tok-1", "{{bw:Nope/password}}")
    edited = (home / ".netrc").read_text()
    _answer(monkeypatch, machine, "push")
    _yes_no(monkeypatch)

    assert machine.cmd_env_pull() == 0
    assert _bw_item(fake_bw, "netrc/groups/work")["notes"] == NOTES
    fields = {f["name"]: f["value"] for f in _bw_item(fake_bw, "Work login")["fields"]}
    assert fields["artifactory-token"] == "tok-1"
    assert (home / ".netrc").read_text() == edited
    assert "Nope" in _all_output(capsys)


def test_push_writes_nothing_when_not_confirmed(tmp_path, monkeypatch, fake_bw):
    machine, home = _pulled(tmp_path, monkeypatch, fake_bw)
    _edit(home, "lit-1", "lit-2")
    edited = (home / ".netrc").read_text()
    _answer(monkeypatch, machine, "push")
    _yes_no(monkeypatch, False)

    assert machine.cmd_env_pull() == 0
    assert _bw_item(fake_bw, "netrc/groups/work")["notes"] == NOTES
    assert (home / ".netrc").read_text() == edited


def test_push_offers_removal_with_no_preselected(tmp_path, monkeypatch, fake_bw):
    machine, home = _pulled(tmp_path, monkeypatch, fake_bw)
    path = home / ".netrc"
    path.write_text(
        path.read_text().replace(
            "machine legacy.example\n  login bob\n  password lit-1\n", ""
        )
    )
    _answer(monkeypatch, machine, "push")
    asked = _yes_no(monkeypatch)

    assert machine.cmd_env_pull() == 0
    [(question, default)] = asked[:1]
    assert "Remove legacy.example" in question and default is False
    assert "legacy.example" in _bw_item(fake_bw, "netrc/groups/work")["notes"]


def test_push_removes_a_block_after_a_yes(tmp_path, monkeypatch, fake_bw):
    machine, home = _pulled(tmp_path, monkeypatch, fake_bw)
    path = home / ".netrc"
    path.write_text(
        path.read_text().replace(
            "machine legacy.example\n  login bob\n  password lit-1\n", ""
        )
    )
    _answer(monkeypatch, machine, "push")
    _yes_no(monkeypatch, True, True)

    assert machine.cmd_env_pull() == 0
    notes = _bw_item(fake_bw, "netrc/groups/work")["notes"]
    assert "legacy.example" not in notes and "artifactory.example.com" in notes
    assert "legacy.example" not in path.read_text()


def test_push_leaves_a_block_changed_only_in_bitwarden_alone(
    tmp_path, monkeypatch, fake_bw
):
    machine, home = _pulled(tmp_path, monkeypatch, fake_bw)
    _edit(home, "lit-1", "lit-2")
    _bw_set_item(
        fake_bw,
        "netrc/groups/work",
        {"id": "netrc-id", **_item(NOTES.replace("bob", "bobby"))},
    )
    _answer(monkeypatch, machine, "push")
    asked = _yes_no(monkeypatch)

    assert machine.cmd_env_pull() == 0
    assert any("legacy.example" in q and "overwrite" in q for q, _d in asked)
    assert "lit-2" not in _bw_item(fake_bw, "netrc/groups/work")["notes"]


def test_the_same_new_value_on_both_sides_is_no_edit(tmp_path, monkeypatch, fake_bw):
    machine, home = _pulled(tmp_path, monkeypatch, fake_bw)
    _edit(home, "lit-1", "lit-2")
    _bw_set_item(
        fake_bw,
        "netrc/groups/work",
        {"id": "netrc-id", **_item(NOTES.replace("lit-1", "lit-2"))},
    )
    asked = _answer(monkeypatch, machine, "skip")

    assert machine.cmd_env_pull() == 0
    assert asked == []
    assert "password lit-2" in (home / ".netrc").read_text()
    assert machine.netrc_attention() == []


def _push(machine, monkeypatch, *answers):
    monkeypatch.setattr(machine_system(), "is_tty", lambda: True)
    monkeypatch.setattr(machine_system(), "choose", lambda _t, _c, default: default)
    monkeypatch.setattr(machine, "offer_saving_bitwarden_session", lambda: None)
    asked = _yes_no(monkeypatch, *answers)
    return machine.cmd_env_push(), asked


def test_env_push_pushes_netrc_edits_too(tmp_path, monkeypatch, fake_bw):
    machine, home = _pulled(tmp_path, monkeypatch, fake_bw)
    _edit(home, "lit-1", "lit-2")

    code, asked = _push(machine, monkeypatch)
    assert code == 0
    assert asked[-1][0] == "Write 1 change(s) to Bitwarden?"
    assert "lit-2" in _bw_item(fake_bw, "netrc/groups/work")["notes"]
    assert machine.netrc_attention() == []


def test_env_push_refuses_netrc_without_a_pulled_state(
    tmp_path, monkeypatch, fake_bw, capsys
):
    machine, home = _netrc_machine(tmp_path, monkeypatch, fake_bw)
    (home / ".netrc").write_text("machine hand.example login x password y\n")

    code, _asked = _push(machine, monkeypatch)
    assert code == 1
    assert "run: machine env pull" in _all_output(capsys)


# --- review findings ---------------------------------------------------------


def test_blocks_keep_the_order_of_the_notes_including_default(
    tmp_path, monkeypatch, fake_bw
):
    notes = "default\n  login d\n  password p\n\nmachine a.example\n  login a\n  password b\n"
    host_notes = "machine h.example\n  login h\n  password x\n"
    _machine, home = _pulled(
        tmp_path, monkeypatch, fake_bw, notes=notes, host_notes=host_notes
    )

    hosts = [b.host for b in parse_netrc((home / ".netrc").read_text())]
    assert hosts == ["h.example", "default", "a.example"]


def test_pull_leaves_netrc_alone_when_every_block_is_skipped(
    tmp_path, monkeypatch, fake_bw
):
    notes = "machine a.example\n  login a\n  password {{bw:Nope/password}}\n"
    machine, home = _netrc_machine(tmp_path, monkeypatch, fake_bw, notes=notes)
    (home / ".netrc").write_text("machine hand.example login x password y\n")

    assert machine.cmd_env_pull() == 0
    assert (home / ".netrc").read_text() == "machine hand.example login x password y\n"
    [item] = machine.netrc_attention()
    assert "a.example" in item


def test_attention_clears_when_the_netrc_items_disappear(
    tmp_path, monkeypatch, fake_bw
):
    notes = NOTES.replace("field:ado-token", "field:missing-token")
    machine, _home = _pulled(tmp_path, monkeypatch, fake_bw, notes=notes)
    assert machine.netrc_attention()

    import json

    data = json.loads(fake_bw[1].read_text())
    del data["items"]["netrc/groups/work"]
    fake_bw[1].write_text(json.dumps(data))

    assert machine.cmd_env_pull() == 0
    assert machine.netrc_attention() == []


def test_pull_drops_a_comment_that_contains_a_reference(tmp_path, monkeypatch, fake_bw):
    notes = (
        "# was {{bw:Work login/password}}\nmachine a.example\n  login a\n  password b\n"
    )
    _machine, home = _pulled(tmp_path, monkeypatch, fake_bw, notes=notes)

    assert (
        home / ".netrc"
    ).read_text() == "machine a.example\n  login a\n  password b\n"


def test_pull_matches_github_com_in_any_case(tmp_path, monkeypatch, fake_bw, capsys):
    notes = "machine GitHub.com\n  login t\n  password p\n"
    _pulled(tmp_path, monkeypatch, fake_bw, notes=notes)
    assert "credential helpers" in _all_output(capsys)


def test_a_netrc_that_is_not_utf8_survives_the_backup(tmp_path, monkeypatch, fake_bw):
    machine, home = _netrc_machine(tmp_path, monkeypatch, fake_bw)
    (home / ".netrc").write_bytes(b"machine hand.example login lat\xe9 password y\n")

    assert machine.cmd_env_pull() == 0
    assert (home / ".netrc").read_text() == GENERATED
    backups = (machine.state_dir / "env-backup").glob("netrc.*")
    assert any(b"lat\xe9" in p.read_bytes() for p in backups)
    assert machine.netrc_attention() == []


@pytest.mark.parametrize(
    "old, new",
    [("password two", "password three"), ("password one", "password zero")],
)
def test_push_edits_the_matching_block_of_a_repeated_host(
    tmp_path, monkeypatch, fake_bw, old, new
):
    notes = (
        "machine d.example\n  login a\n  password one\n\n"
        "machine d.example\n  login a\n  password two\n"
    )
    machine, home = _pulled(tmp_path, monkeypatch, fake_bw, notes=notes)
    _edit(home, old, new)
    _answer(monkeypatch, machine, "push")
    _yes_no(monkeypatch)

    assert machine.cmd_env_pull() == 0
    assert _bw_item(fake_bw, "netrc/groups/work")["notes"] == notes.replace(old, new)


def test_push_refuses_a_new_value_that_a_netrc_cannot_hold(
    tmp_path, monkeypatch, fake_bw, capsys
):
    machine, home = _pulled(tmp_path, monkeypatch, fake_bw)
    _edit(home, "lit-1", "lit'2")
    _answer(monkeypatch, machine, "push")
    _yes_no(monkeypatch)

    assert machine.cmd_env_pull() == 0
    assert _bw_item(fake_bw, "netrc/groups/work")["notes"] == NOTES
    assert "cannot be written unchanged" in _all_output(capsys)
