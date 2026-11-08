"""Shared Syncthing ignore rules: include line, shared file, conflict copies, defaults."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from package_sets import REPO

sys.path.insert(0, str(REPO))

from machine_cli import syncthing_ignores as st  # noqa: E402
from machine_cli.machine import Machine  # noqa: E402

RULES_TEXT = (REPO / st.RULES).read_text(encoding="utf-8")
DEFAULTS = ["(?d)@eaDir", "(?d)#recycle", "(?d)#snapshot", "__*"]
HEAD = "#include .stglobalignore\n!/.stglobalignore\n"
GUI = '<gui tls="false"><address>127.0.0.1:8384</address><apikey>k</apikey></gui>'


class FakeApi(st.Api):
    """Answers like a running Syncthing; records every call."""

    def __init__(self, known=(), deleted=(), defaults=None, status=200):
        self.known = set(known)
        self.deleted = set(deleted)
        self.defaults = list(DEFAULTS if defaults is None else defaults)
        self.status = status  # 0: not running, 403: key rejected
        self.calls = []

    def call(self, method, path, body=None):
        self.calls.append((method, path, body))
        if self.status != 200:
            return self.status, None
        if path.startswith("db/file?"):
            folder = path.split("folder=")[1].split("&")[0]
            if folder in self.known | self.deleted:
                return 200, {"global": {"deleted": folder in self.deleted}}
            return 404, "No such object in the index"
        if path == "config/defaults/ignores":
            if method == "PUT":
                self.defaults = list(body["lines"])
                return 200, None
            return 200, {"lines": list(self.defaults)}
        return 404, ""


def _config(tmp_path, folders, gui=GUI):
    entries = "".join(
        f'<folder id="{fid}" path="{path}">'
        f"<paused>{'true' if paused else 'false'}</paused></folder>"
        for fid, path, paused in folders
    )
    # The <defaults><folder> template must not count as a folder.
    defaults = '<defaults><folder id="" path="~"></folder></defaults>'
    config = tmp_path / "config.xml"
    config.write_text(f"<configuration>{entries}{defaults}{gui}</configuration>")
    return config


def _folder(tmp_path, name, stignore=None, shared=None):
    path = tmp_path / name
    path.mkdir()
    if stignore is not None:
        (path / ".stignore").write_text(stignore)
    if shared is not None:
        (path / st.GLOBAL).write_text(shared)
    return st.Folder(name, path, False)


def _stignore(folder):
    return (folder.path / ".stignore").read_text()


def test_include_and_unignore_on_top_and_local_lines_kept(tmp_path):
    folder = _folder(
        tmp_path, "docs", stignore="(?d)@eaDir\n__*\nKlettern\n", shared="x\n"
    )
    assert st.ensure_folder(FakeApi(), folder, RULES_TEXT) == "added the include line"
    assert _stignore(folder) == HEAD + "(?d)@eaDir\n__*\nKlettern\n"


@pytest.mark.parametrize(
    "variant",
    [
        "#include .stglobalignore",
        "#include  .stglobalignore",
        "#include\t./.stglobalignore",
        "  #include .stglobalignore  ",
    ],
)
def test_include_variants_further_down_are_replaced_once(tmp_path, variant):
    folder = _folder(
        tmp_path, "docs", stignore=f"a\n{variant}\n!.stglobalignore\nb\n", shared="x\n"
    )
    st.ensure_folder(FakeApi(), folder, RULES_TEXT)
    assert _stignore(folder) == HEAD + "a\nb\n"


def test_bom_is_dropped_and_not_taken_for_a_line(tmp_path):
    folder = _folder(
        tmp_path, "docs", stignore="﻿#include .stglobalignore\na\n", shared="x\n"
    )
    st.ensure_folder(FakeApi(), folder, RULES_TEXT)
    assert _stignore(folder) == HEAD + "a\n"


def test_in_place_folder_is_not_rewritten(tmp_path):
    folder = _folder(tmp_path, "docs", stignore=HEAD + "a\n", shared="x\n")
    stignore = folder.path / ".stignore"
    os.utime(stignore, (1, 1))
    assert st.ensure_folder(FakeApi(), folder, RULES_TEXT) == ""
    assert stignore.stat().st_mtime == 1


def test_missing_stignore_gets_only_the_two_lines(tmp_path):
    folder = _folder(tmp_path, "docs", shared="x\n")
    st.ensure_folder(FakeApi(), folder, RULES_TEXT)
    assert _stignore(folder) == HEAD


def test_existing_shared_file_is_never_changed(tmp_path):
    folder = _folder(tmp_path, "docs", stignore="", shared="!keep\n(?d)**/target\n")
    shared = folder.path / st.GLOBAL
    os.utime(shared, (1, 1))
    st.ensure_folder(FakeApi(), folder, RULES_TEXT)
    assert (
        shared.read_text() == "!keep\n(?d)**/target\n" and shared.stat().st_mtime == 1
    )


def test_allow_list_folder_gets_unignore_shared_file_and_include_at_once(tmp_path):
    folder = _folder(tmp_path, "photos", stignore="!2026\n(?d)*\n")
    api = FakeApi()

    outcome = st.ensure_folder(api, folder, RULES_TEXT)

    assert outcome == (
        "added !/.stglobalignore and created .stglobalignore and added the include line"
    )
    assert (folder.path / st.GLOBAL).read_text() == RULES_TEXT
    assert _stignore(folder) == HEAD + "!2026\n(?d)*\n"
    assert ("POST", "db/scan?folder=photos", None) in api.calls


def test_bom_in_an_otherwise_wired_file_is_removed(tmp_path):
    folder = _folder(tmp_path, "docs", stignore="\ufeff" + HEAD + "a\n", shared="x\n")
    assert st.ensure_folder(FakeApi(), folder, RULES_TEXT) == "added the include line"
    assert _stignore(folder) == HEAD + "a\n"


def test_include_without_the_shared_file_is_removed(tmp_path):
    # An include of a missing file keeps the folder in an error state.
    folder = _folder(tmp_path, "docs", stignore="#include .stglobalignore\na\n")
    outcome = st.ensure_folder(FakeApi(known={"docs"}), folder, RULES_TEXT)
    assert outcome.startswith("waiting")
    assert _stignore(folder) == "!/.stglobalignore\na\n"


def test_shared_file_deleted_on_a_peer_is_left_alone_quietly(tmp_path):
    folder = _folder(tmp_path, "docs", stignore="!/.stglobalignore\na\n")
    assert st.ensure_folder(FakeApi(deleted={"docs"}), folder, RULES_TEXT) == ""
    assert not (folder.path / st.GLOBAL).exists()


@pytest.mark.parametrize(
    ("api", "paused", "reason"),
    [
        (FakeApi(known={"photos"}), False, "exists on another device"),
        (FakeApi(status=403), False, "rejected the API key"),
        (FakeApi(status=0), False, "not reachable"),
        (FakeApi(), True, "folder paused"),
    ],
)
def test_shared_file_not_created_when_syncthing_cannot_rule_it_out(
    tmp_path, api, paused, reason
):
    folder = _folder(tmp_path, "photos", stignore="!/.stglobalignore\nlocal\n")
    folder.paused = paused
    outcome = st.ensure_folder(api, folder, RULES_TEXT)
    assert outcome.startswith("waiting") and reason in outcome
    assert not (folder.path / st.GLOBAL).exists()
    assert _stignore(folder) == "!/.stglobalignore\nlocal\n"
    if paused:
        assert api.calls == []


def test_missing_or_read_only_folder_is_skipped(tmp_path):
    missing = st.Folder("gone", tmp_path / "gone", False)
    assert st.ensure_folder(FakeApi(), missing, RULES_TEXT).startswith("skipped")
    folder = _folder(tmp_path, "ro", shared="x\n")
    folder.path.chmod(0o555)
    try:
        if os.access(folder.path, os.W_OK):
            pytest.skip("running as root")
        assert "not writable" in st.ensure_folder(FakeApi(), folder, RULES_TEXT)
    finally:
        folder.path.chmod(0o755)


def test_conflict_copies_identical_removed_different_kept(tmp_path):
    folder = _folder(tmp_path, "docs", shared="rules\n")
    same = folder.path / ".sync-conflict-20261108-214840-RHX7ZDM.stglobalignore"
    same.write_text("rules\n")
    other = folder.path / ".sync-conflict-20261108-214841-ABCDEFG.stglobalignore"
    other.write_text("!exception\nrules\n")
    unrelated = folder.path / "notes.sync-conflict-20261108-214840-RHX7ZDM.txt"
    unrelated.write_text("rules\n")

    messages = st.clean_conflicts(folder.path)

    assert not same.exists() and other.exists() and unrelated.exists()
    assert any("removed" in m for m in messages)
    assert any(str(other) in m and "by hand" in m for m in messages)


def test_defaults_shared_rules_first_own_lines_kept():
    api = FakeApi()
    rules = st.rule_lines(RULES_TEXT)
    assert st.ensure_defaults(api, rules) == (True, 200)
    assert api.defaults == [*rules, "__*"]
    assert api.defaults.count("(?d)@eaDir") == 1
    assert not any(line.startswith("#include") for line in api.defaults)
    api.calls.clear()
    assert st.ensure_defaults(api, rules) == (False, 200)
    assert [c[0] for c in api.calls] == ["GET"]


def test_defaults_not_checked_when_syncthing_does_not_answer():
    assert st.ensure_defaults(FakeApi(status=0), ["x"]) == (None, 0)


def test_rule_list_holds_the_agreed_rules():
    rules = st.rule_lines(RULES_TEXT)
    for rule in (
        "(?d)@eaDir",
        "(?d)#recycle",
        "(?d)#snapshot",
        "(?d)**/target",
        "(?d)**/node_modules",
        "**/.claude/worktrees",
    ):
        assert rule in rules
    assert "__*" not in rules and not any(r.startswith("#include") for r in rules)


def test_api_reads_address_key_and_tls(tmp_path):
    config = _config(
        tmp_path,
        [],
        gui='<gui tls="true"><address>127.0.0.1:8385</address><apikey>abc</apikey></gui>',
    )
    api = st.Api(config)
    assert api.base == "https://127.0.0.1:8385/rest/" and api.key == "abc"


def test_api_without_a_usable_address_does_not_call(tmp_path):
    for address in ("/run/syncthing.sock", ":8384"):
        config = _config(
            tmp_path,
            [],
            gui=f"<gui><address>{address}</address><apikey>k</apikey></gui>",
        )
        assert st.Api(config).call("GET", "system/ping") == (0, None)


def test_folders_read_paused_element_expand_home_and_skip_relative(tmp_path):
    config = _config(
        tmp_path,
        [
            ("a", "~/Sync", False),
            ("b", "/srv/x", True),
            ("c", "relative", False),
            ("d", "", False),
        ],
    )
    found = st.folders(config, tmp_path)
    assert [(f.id, f.path, f.paused) for f in found] == [
        ("a", tmp_path / "Sync", False),
        ("b", st.Path("/srv/x"), True),
    ]


# --- the step on a Machine -------------------------------------------------


@pytest.fixture
def host(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("DOTFILES_REPO", str(REPO))
    monkeypatch.setenv("MACHINE_APPLIED_HOST_FILE", str(tmp_path / "profile.yml"))
    machine = Machine()
    paths_output = {"text": ""}

    def run(args, **_kw):
        return subprocess.CompletedProcess(
            args, 0, stdout=paths_output["text"], stderr=""
        )

    monkeypatch.setattr(st.system, "run", run)
    monkeypatch.setattr(st.system, "have", lambda name: name == "syncthing")
    return machine, paths_output


@pytest.fixture
def messages(monkeypatch):
    """What the step prints through log and warn (the machine logger does not propagate)."""
    seen: list[str] = []
    monkeypatch.setattr(st, "log", seen.append)
    monkeypatch.setattr(st, "warn", lambda m: seen.append(f"WARN {m}"))
    return seen


def _profile(machine, features, device="desktop"):
    machine.applied_host_path.write_text(
        f"context: private\ndevice: {device}\nfeatures:\n"
        + "".join(f"  - {f}\n" for f in features)
    )


def _wire(host, tmp_path, monkeypatch, folders, api):
    machine, paths_output = host
    config = _config(tmp_path, [(f.id, f.path, f.paused) for f in folders])
    paths_output["text"] = f"Configuration file:\n\t{config}\n"
    monkeypatch.setattr(st, "Api", lambda _config: api)
    return machine


def test_step_does_nothing_without_the_feature(host, monkeypatch):
    machine, _ = host
    _profile(machine, ["zsh-full"])
    monkeypatch.setattr(st, "find_config", lambda home: pytest.fail("config read"))
    machine.run_syncthing_ignores()


def test_step_is_silent_without_a_syncthing_config(host, messages):
    machine, _ = host
    _profile(machine, ["syncthing"])
    machine.run_syncthing_ignores()
    assert messages == []


def test_find_config_uses_what_syncthing_paths_prints(host, tmp_path):
    _machine, paths_output = host
    live = tmp_path / ".config/syncthing"
    live.mkdir(parents=True)
    _config(live, [])
    (tmp_path / ".local/state/syncthing").mkdir(parents=True)
    _config(tmp_path / ".local/state/syncthing", [])
    paths_output["text"] = (
        f"Configuration file:\n\t{live / 'config.xml'}\n\nDatabase location:\n"
    )
    assert st.find_config(tmp_path) == live / "config.xml"
    paths_output["text"] = ""
    assert st.find_config(tmp_path) == tmp_path / ".local/state/syncthing/config.xml"


def test_step_wires_up_every_folder_and_is_quiet_afterwards(
    host, tmp_path, monkeypatch, messages
):
    docs = _folder(tmp_path, "docs", stignore="__*\n", shared="!keep\n")
    photos = _folder(tmp_path, "photos", stignore="(?d)*\n")
    api = FakeApi()
    machine = _wire(host, tmp_path, monkeypatch, [docs, photos], api)
    _profile(machine, ["syncthing"])

    machine.run_syncthing_ignores()

    assert _stignore(docs) == HEAD + "__*\n"
    assert (photos.path / st.GLOBAL).read_text() == RULES_TEXT
    assert _stignore(photos) == HEAD + "(?d)*\n"
    assert api.defaults[-1] == "__*"
    messages.clear()
    machine.run_syncthing_ignores()
    assert messages == []


def test_step_is_quiet_when_syncthing_is_not_running_and_all_is_in_place(
    host, tmp_path, monkeypatch, messages
):
    docs = _folder(tmp_path, "docs", stignore=HEAD, shared="x\n")
    machine = _wire(host, tmp_path, monkeypatch, [docs], FakeApi(status=0))
    _profile(machine, ["syncthing"])
    machine.run_syncthing_ignores()
    assert messages == []


def test_step_warns_when_the_api_key_is_rejected(host, tmp_path, monkeypatch, messages):
    docs = _folder(tmp_path, "docs", stignore=HEAD, shared="x\n")
    machine = _wire(host, tmp_path, monkeypatch, [docs], FakeApi(status=403))
    _profile(machine, ["syncthing"])
    machine.run_syncthing_ignores()
    assert any("API key" in m for m in messages)


def test_one_broken_folder_does_not_stop_the_others(
    host, tmp_path, monkeypatch, messages
):
    broken = _folder(tmp_path, "broken", shared="x\n")
    (broken.path / ".stignore").mkdir()  # reading it fails
    docs = _folder(tmp_path, "docs", shared="x\n")
    api = FakeApi()
    machine = _wire(host, tmp_path, monkeypatch, [broken, docs], api)
    _profile(machine, ["syncthing"])

    machine.run_syncthing_ignores()

    assert any("broken" in m and "skipped" in m for m in messages)
    assert _stignore(docs) == HEAD
    assert api.defaults[-1] == "__*"


def test_step_on_a_server_with_the_feature(host, tmp_path, monkeypatch):
    folder = _folder(tmp_path, "docs", shared="x\n")
    machine = _wire(host, tmp_path, monkeypatch, [folder], FakeApi())
    _profile(machine, ["syncthing"], device="server")
    machine.run_syncthing_ignores()
    assert _stignore(folder) == HEAD
