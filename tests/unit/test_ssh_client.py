"""SSH client config: base config, host list from Bitwarden, host keys, commands."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


from machine_loader import load_machine_module
from package_sets import REPO
from test_ssh_host_keys import fingerprint, make_key

MACHINE = REPO / "machine_cli/machine"
BASE = REPO / "home/core/.ssh/config"
HOST = "unit-test-host"
NOTE = "ssh/home/config"
LIST = """\
Host homeserver
  User ditschi
  HostKeyAlias homeserver
  ProxyCommand ~/.local/bin/ssh-route %k lan=192.168.1.4:22 jump=oracle:2223

Host nas
  HostName 192.168.1.222
  User superditschi
"""


def client(tmp_path, monkeypatch, fake_bw, context="private", git=False):
    bw, store = fake_bw
    repo = tmp_path / "dotfiles"
    (repo / "home/core/.ssh").mkdir(parents=True)
    (repo / "machine/ssh_host_keys").mkdir(parents=True)
    (repo / "machine/ssh_keys").mkdir(parents=True)
    if git:
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
    else:
        (repo / ".git").mkdir()
    home = tmp_path / "home"
    (home / ".ssh").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CACHE_HOME", str(home / ".cache"))
    monkeypatch.setenv("DOTFILES_REPO", str(repo))
    monkeypatch.setenv("PATH", f"{bw.parent}:{os.environ.get('PATH', '')}")
    monkeypatch.setenv("BW_SESSION", "fake-session")
    monkeypatch.setenv("MACHINE_APPLIED_HOST_FILE", str(home / ".config/machine/p.yml"))
    monkeypatch.setenv(
        "MISE_LOCAL_CONFIG", str(home / ".config/mise/config.local.toml")
    )
    monkeypatch.setenv("MACHINE_STATE_DIR", str(home / ".local/share/machine"))
    cli = load_machine_module("machine_ssh_client", MACHINE)
    monkeypatch.setattr(cli.system, "in_docker", lambda: False)
    monkeypatch.setattr(cli.system, "is_tty", lambda: False)
    monkeypatch.setattr(cli.system, "hostname_short", lambda: HOST)
    machine = cli.Machine()
    machine.write_profile(context, "desktop", ["zsh-full", "ssh-host-key"], [])
    return cli, machine, home, repo, store


def put_note(store: Path, text: str, name: str = NOTE) -> None:
    data = json.loads(store.read_text())
    data.setdefault("items", {})["note-1"] = {
        "id": "note-1",
        "type": 2,
        "name": name,
        "notes": text,
        "secureNote": {"type": 0},
    }
    store.write_text(json.dumps(data))


def note_text(store: Path, name: str = NOTE) -> str:
    data = json.loads(store.read_text())
    return next(i["notes"] for i in data["items"].values() if i["name"] == name)


def ssh_g(config: Path, host: str) -> dict:
    out = subprocess.run(
        ["ssh", "-G", "-F", str(config), host],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    values: dict = {}
    for line in out.splitlines():
        key, _, value = line.partition(" ")
        values.setdefault(key, value)
    return values


# --- base config -------------------------------------------------------------


def base_in(home: Path) -> Path:
    path = home / ".ssh/config"
    path.write_text(BASE.read_text().replace("~/", f"{home}/"))
    return path


def test_base_config_without_includes(tmp_path):
    (tmp_path / ".ssh").mkdir()
    values = ssh_g(base_in(tmp_path), "anything")
    assert values["serveraliveinterval"] == "30"
    assert values["controlmaster"] == "auto"
    assert values["identitiesonly"] == "yes"
    assert values["userknownhostsfile"].endswith(".ssh/known_hosts.d/home")


def test_host_only_and_list_order(tmp_path):
    home = tmp_path
    (home / ".ssh/config.d").mkdir(parents=True)
    config = base_in(home)
    (home / ".ssh/config.d/20-home").write_text(
        "Host nas\n  User fromlist\n  Port 2200\n"
    )
    assert ssh_g(config, "nas")["user"] == "fromlist"
    (home / ".ssh/config.local").write_text("Host nas\n  User fromlocal\n")
    values = ssh_g(config, "nas")
    assert values["user"] == "fromlocal"
    assert values["port"] == "2200"


def test_base_config_sets_no_agent_or_strict_options():
    text = BASE.read_text().lower()
    for option in ("forwardagent", "addkeystoagent", "stricthostkeychecking"):
        assert option not in text
    assert "192.168." not in text


# --- apply ---------------------------------------------------------------------


def test_apply_creates_dirs_fixes_mode_and_writes_known_hosts(
    tmp_path, monkeypatch, fake_bw
):
    _cli, machine, home, repo, _store = client(tmp_path, monkeypatch, fake_bw)
    base = repo / "home/core/.ssh/config"
    base.write_text(BASE.read_text())
    base.chmod(0o664)
    (repo / "machine/ssh_host_keys/nas.pub").write_text("ssh-ed25519 AAAAnas nas\n")
    machine.apply_ssh_client()
    assert (home / ".ssh/cm").stat().st_mode & 0o777 == 0o700
    assert (home / ".ssh/config.d").stat().st_mode & 0o777 == 0o700
    assert base.stat().st_mode & 0o777 == 0o644
    known = (home / ".ssh/known_hosts.d/home").read_text()
    assert "nas ssh-ed25519 AAAAnas\n" in known


def test_work_host_gets_no_managed_known_hosts(tmp_path, monkeypatch, fake_bw):
    _cli, machine, home, repo, _store = client(tmp_path, monkeypatch, fake_bw, "work")
    (repo / "machine/ssh_host_keys/nas.pub").write_text("ssh-ed25519 AAAAnas nas\n")
    (home / ".ssh/known_hosts.d").mkdir()
    (home / ".ssh/known_hosts.d/home").write_text("old\n")
    machine.apply_ssh_client()
    assert not (home / ".ssh/known_hosts.d/home").exists()


def test_managed_key_is_trusted_through_alias(tmp_path, monkeypatch, fake_bw):
    _cli, machine, home, repo, _store = client(tmp_path, monkeypatch, fake_bw)
    public = make_key(tmp_path / "hostkey")
    (repo / "machine/ssh_host_keys/privatecloud.pub").write_text(public + "\n")
    machine.write_known_hosts()
    found = subprocess.run(
        [
            "ssh-keygen",
            "-F",
            "privatecloud",
            "-f",
            str(home / ".ssh/known_hosts.d/home"),
        ],
        capture_output=True,
        text=True,
    )
    assert public.split()[1] in found.stdout


def test_replaced_config_is_moved_aside(tmp_path):
    from machine_cli.dotfiles import clear_conflicting_targets

    repo = tmp_path / "repo"
    (repo / "home/core/.ssh").mkdir(parents=True)
    (repo / "home/core/.ssh/config").write_text(BASE.read_text())
    home = tmp_path / "home"
    (home / ".ssh").mkdir(parents=True)
    (home / ".ssh/config").write_text("Host old\n  HostName 10.0.0.1\n")
    changed = clear_conflicting_targets(repo, home, ["core"])
    assert (home / ".ssh/config.pre-dotfiles").read_text().startswith("Host old")
    assert any("moved aside" in what for _t, what in changed)


def test_legacy_hosts_fill_only_gaps(tmp_path, monkeypatch, fake_bw):
    _cli, machine, home, _repo, _store = client(tmp_path, monkeypatch, fake_bw)
    (home / ".ssh/config.pre-dotfiles").write_text(
        "IdentityFile ~/.ssh/id_ed25519\n\nHost nas\n  Port 5115\n\nHost rinkhals\n  User root\n"
    )
    (home / ".ssh/config.d").mkdir()
    (home / ".ssh/config.d/20-home").write_text(LIST)
    machine.write_legacy_ssh_config()
    legacy = (home / ".ssh/config.d/90-legacy").read_text()
    assert "Host rinkhals" in legacy and "Host nas" not in legacy
    assert "IdentityFile ~/.ssh/id_ed25519" in legacy
    [item] = [i for i in machine.ssh_attention() if "replaced" in i[1]]
    assert "rinkhals" in item[1]


def test_legacy_resolution_moves_and_drops(tmp_path, monkeypatch, fake_bw):
    cli, machine, home, _repo, _store = client(tmp_path, monkeypatch, fake_bw)
    (home / ".ssh/config.pre-dotfiles").write_text(
        "Host rinkhals\n  User root\n\nHost old\n  User x\n"
    )
    machine.write_legacy_ssh_config()
    answers = iter(["move to ~/.ssh/config.local", "drop it"])
    monkeypatch.setattr(cli.system, "choose", lambda *_a, **_k: next(answers))
    machine.resolve_legacy_ssh_config()
    assert "Host rinkhals" in (home / ".ssh/config.local").read_text()
    assert not (home / ".ssh/config.pre-dotfiles").exists()
    assert not (home / ".ssh/config.d/90-legacy").exists()


# --- host list -------------------------------------------------------------------


def test_pull_writes_list_for_private_host(tmp_path, monkeypatch, fake_bw):
    _cli, machine, home, _repo, store = client(tmp_path, monkeypatch, fake_bw)
    put_note(store, LIST)
    put_note_work = json.loads(store.read_text())
    put_note_work["items"]["note-2"] = {
        "id": "note-2", "type": 2, "name": "ssh/work/config", "notes": "Host ci\n",
    }  # fmt: skip
    store.write_text(json.dumps(put_note_work))
    assert machine.pull_ssh_host_list() == 0
    path = home / ".ssh/config.d/20-home"
    assert "Host homeserver" in path.read_text()
    assert "Host ci" not in path.read_text()
    assert path.stat().st_mode & 0o777 == 0o600
    assert not (home / ".ssh/config.d/20-work").exists()


def test_work_host_reads_only_work_list(tmp_path, monkeypatch, fake_bw):
    _cli, machine, home, _repo, store = client(tmp_path, monkeypatch, fake_bw, "work")
    put_note(store, "Host ci-agent-07\n  HostName ci7\n", "ssh/work/config")
    machine.pull_ssh_host_list()
    assert "ci-agent-07" in (home / ".ssh/config.d/20-work").read_text()
    assert not (home / ".ssh/config.d/20-home").exists()


def test_missing_note_writes_nothing(tmp_path, monkeypatch, fake_bw, capsys):
    _cli, machine, home, _repo, _store = client(tmp_path, monkeypatch, fake_bw)
    assert machine.pull_ssh_host_list() == 0
    assert not (home / ".ssh/config.d/20-home").exists()
    assert "machine ssh add" in capsys.readouterr().out


def test_invalid_note_keeps_existing_file(tmp_path, monkeypatch, fake_bw, capsys):
    _cli, machine, home, _repo, store = client(tmp_path, monkeypatch, fake_bw)
    (home / ".ssh/config.d").mkdir()
    (home / ".ssh/config.d/20-home").write_text("old\n")
    put_note(store, "Host nas\n  NoSuchOption yes\n")
    machine.pull_ssh_host_list()
    assert (home / ".ssh/config.d/20-home").read_text() == "old\n"
    captured = capsys.readouterr()
    assert "ssh/home/config not written" in captured.out + captured.err


def test_without_session_list_is_kept(tmp_path, monkeypatch, fake_bw, capsys):
    _cli, machine, home, _repo, store = client(tmp_path, monkeypatch, fake_bw)
    put_note(store, LIST)
    monkeypatch.setattr(machine, "bitwarden_session_ready", lambda: False)
    machine.pull_ssh_host_list()
    assert not (home / ".ssh/config.d/20-home").exists()
    captured = capsys.readouterr()
    assert "machine env pull" in captured.out + captured.err


def local_block_setup(tmp_path, monkeypatch, fake_bw):
    cli, machine, home, repo, store = client(tmp_path, monkeypatch, fake_bw)
    put_note(store, LIST)
    machine.pull_ssh_host_list()
    path = home / ".ssh/config.d/20-home"
    path.write_text(path.read_text() + "\nHost test-vm\n  HostName 10.1.1.1\n")
    return cli, machine, home, store, path


def test_local_block_is_carried_and_listed(tmp_path, monkeypatch, fake_bw):
    _cli, machine, _home, store, path = local_block_setup(
        tmp_path, monkeypatch, fake_bw
    )
    machine.pull_ssh_host_list()
    text = path.read_text()
    assert text.index("local only") < text.index("Host test-vm")
    assert "test-vm" not in note_text(store)
    assert any("test-vm" in item[1] for item in machine.ssh_attention())
    # a second run keeps it exactly once
    machine.pull_ssh_host_list()
    assert path.read_text().count("Host test-vm") == 1


def test_local_block_to_bitwarden(tmp_path, monkeypatch, fake_bw):
    cli, machine, _home, store, path = local_block_setup(tmp_path, monkeypatch, fake_bw)
    monkeypatch.setattr(cli.system, "is_tty", lambda: True)
    monkeypatch.setattr(cli.system, "choose", lambda _t, choices, _d: choices[0])
    machine.pull_ssh_host_list()
    assert "Host test-vm" in note_text(store)
    assert f"# added from {HOST}" in note_text(store)
    assert "local only" not in path.read_text()
    assert "Host test-vm" in path.read_text()


def test_local_block_to_config_local(tmp_path, monkeypatch, fake_bw):
    cli, machine, home, _store, path = local_block_setup(tmp_path, monkeypatch, fake_bw)
    monkeypatch.setattr(cli.system, "is_tty", lambda: True)
    monkeypatch.setattr(cli.system, "choose", lambda _t, choices, _d: choices[1])
    machine.pull_ssh_host_list()
    assert "Host test-vm" in (home / ".ssh/config.local").read_text()
    assert "test-vm" not in path.read_text()


def test_block_deleted_in_vault_is_not_local(tmp_path, monkeypatch, fake_bw):
    _cli, machine, _home, store, path = local_block_setup(
        tmp_path, monkeypatch, fake_bw
    )
    put_note(store, "Host homeserver\n  User ditschi\n")
    machine.pull_ssh_host_list()
    text = path.read_text()
    assert "Host nas" not in text  # came from Bitwarden before, removed there
    assert "Host test-vm" in text  # added by hand


def test_failed_write_keeps_block_local(tmp_path, monkeypatch, fake_bw):
    cli, machine, _home, store, path = local_block_setup(tmp_path, monkeypatch, fake_bw)
    monkeypatch.setattr(cli.system, "is_tty", lambda: True)
    monkeypatch.setattr(cli.system, "choose", lambda _t, choices, _d: choices[0])
    monkeypatch.setattr(machine, "_add_to_bitwarden", lambda *_a: False)
    machine.pull_ssh_host_list()
    assert "local only" in path.read_text()
    assert any("test-vm" in item[1] for item in machine.ssh_attention())


# --- repository key files -------------------------------------------------------------


def test_repo_key_files_written_without_bitwarden(tmp_path, monkeypatch, fake_bw):
    _cli, machine, home, repo, _store = client(tmp_path, monkeypatch, fake_bw)
    monkeypatch.delenv("BW_SESSION")
    public = make_key(home / ".ssh/id_ed25519")
    machine.remember_ssh_key(home / ".ssh/id_ed25519")
    (repo / f"machine/ssh_keys/{HOST}.pub").write_text(
        public + "\nssh-rsa AAAAextra x\n"
    )
    host_key = tmp_path / "ssh_host_ed25519_key.pub"
    host_key.write_text("ssh-ed25519 AAAAhost root@x\n")
    monkeypatch.setenv("MACHINE_SSH_HOST_KEY_FILE", str(host_key))
    machine.sync_repo_key_files()
    assert (repo / f"machine/ssh_keys/{HOST}.pub").read_text() == public + "\n"
    assert (repo / f"machine/ssh_host_keys/{HOST}.pub").read_text() == (
        f"ssh-ed25519 AAAAhost {HOST}\n"
    )


def test_unpushed_key_files_item(tmp_path, monkeypatch, fake_bw):
    _cli, machine, _home, repo, _store = client(
        tmp_path, monkeypatch, fake_bw, git=True
    )
    (repo / "machine/ssh_host_keys/nas.pub").write_text("ssh-ed25519 AAAAnas nas\n")
    [item] = [i for i in machine.ssh_attention() if "not pushed" in i[1]]
    assert "machine/ssh_host_keys/nas.pub" in item[1]


# --- known hosts and gateways --------------------------------------------------------


def test_known_hosts_add_confirms_and_writes(tmp_path, monkeypatch, fake_bw):
    cli, machine, home, repo, _store = client(tmp_path, monkeypatch, fake_bw)
    public = make_key(tmp_path / "device")
    monkeypatch.setattr(cli.system, "is_tty", lambda: True)
    monkeypatch.setattr(
        machine, "scan_host_key", lambda *_a: " ".join(public.split()[:2])
    )
    monkeypatch.setattr(cli.system, "prompt_yes_no", lambda q, d=False: True)
    assert machine.add_known_host("nas", "192.168.1.222", 22) == 0
    assert (
        (repo / "machine/ssh_host_keys/nas.pub")
        .read_text()
        .startswith(public.split()[0])
    )
    assert "nas " in (home / ".ssh/known_hosts.d/home").read_text()


def test_known_hosts_changed_key_defaults_to_keep(tmp_path, monkeypatch, fake_bw):
    cli, machine, _home, repo, _store = client(tmp_path, monkeypatch, fake_bw)
    old = make_key(tmp_path / "old")
    new = make_key(tmp_path / "new")
    (repo / "machine/ssh_host_keys/nas.pub").write_text(old + "\n")
    monkeypatch.setattr(cli.system, "is_tty", lambda: True)
    monkeypatch.setattr(machine, "scan_host_key", lambda *_a: " ".join(new.split()[:2]))
    monkeypatch.setattr(cli.system, "prompt_yes_no", lambda q, d=False: d)
    machine.add_known_host("nas", "192.168.1.222", 22)
    assert (repo / "machine/ssh_host_keys/nas.pub").read_text() == old + "\n"
    assert fingerprint(new)


def test_second_home_gateway_item_and_cleanup(tmp_path, monkeypatch, fake_bw):
    cli, machine, home, _repo, _store = client(tmp_path, monkeypatch, fake_bw)
    cache = home / ".cache/ssh-route/networks"
    cache.parent.mkdir(parents=True)
    cache.write_text(json.dumps({
        "aa": {"state": "home", "seen": 1}, "bb": {"state": "home", "seen": 2},
        "cc": {"state": "away", "seen": 3},
    }))  # fmt: skip
    assert machine.old_home_gateways() == ["aa"]
    assert any("home gateway" in i[1] for i in machine.ssh_attention())
    monkeypatch.setattr(cli.system, "choose", lambda _t, choices, d: d)
    machine.resolve_home_gateways()
    assert set(json.loads(cache.read_text())) == {"bb", "cc"}
    assert machine.old_home_gateways() == []


# --- commands -----------------------------------------------------------------------------


def prompts(monkeypatch, cli, answers: dict, yes=True, choice=0):
    from machine_cli import ssh_client

    def prompt(text, default=None, **_k):
        return answers.get(text, default)

    monkeypatch.setattr(ssh_client.click, "prompt", prompt)
    monkeypatch.setattr(cli.system, "is_tty", lambda: True)
    monkeypatch.setattr(
        cli.system,
        "prompt_yes_no",
        lambda q, d=False: (
            yes if q.startswith(("Write", "Replace", "Remove", "Add this")) else d
        ),
    )
    monkeypatch.setattr(cli.system, "choose", lambda _t, choices, _d: choices[choice])


def test_add_work_host_to_list(tmp_path, monkeypatch, fake_bw):
    cli, machine, home, repo, store = client(tmp_path, monkeypatch, fake_bw, "work")
    put_note(store, "", "ssh/work/config")
    prompts(monkeypatch, cli, {"Address": "ci7.example.internal"})
    monkeypatch.setattr(machine, "ssh_login_test", lambda alias: True)
    assert machine.cmd_ssh_add("ci-agent-07") == 0
    text = note_text(store, "ssh/work/config")
    assert "Host ci-agent-07" in text and "HostName ci7.example.internal" in text
    assert "HostKeyAlias" not in text
    assert "ci-agent-07" in (home / ".ssh/config.d/20-work").read_text()
    assert not list((repo / "machine/ssh_host_keys").glob("*.pub"))


def test_add_home_host_with_routes(tmp_path, monkeypatch, fake_bw):
    cli, machine, _home, _repo, store = client(tmp_path, monkeypatch, fake_bw)
    put_note(store, LIST)
    prompts(
        monkeypatch,
        cli,
        {"Address": "192.168.1.9", "Tunnel port on the jump host": 2225},
    )
    monkeypatch.setattr(
        cli.system,
        "prompt_yes_no",
        lambda q, d=False: q.startswith(("Home host", "Write")) or d,
    )
    monkeypatch.setattr(machine, "ssh_login_test", lambda alias: True)
    monkeypatch.setattr(machine, "add_known_host", lambda *a: 0)
    machine.cmd_ssh_add("newbox")
    text = note_text(store)
    assert (
        "ProxyCommand ~/.local/bin/ssh-route %k lan=192.168.1.9:22 jump=oracle:2225"
        in text
    )
    assert "HostKeyAlias newbox" in text
    assert "Host homeserver" in text


def test_add_existing_alias_defaults_to_no(tmp_path, monkeypatch, fake_bw):
    cli, machine, _home, _repo, store = client(tmp_path, monkeypatch, fake_bw)
    put_note(store, LIST)
    prompts(monkeypatch, cli, {}, yes=False)
    machine.cmd_ssh_add("nas")
    assert note_text(store) == LIST


def test_add_to_config_local(tmp_path, monkeypatch, fake_bw):
    cli, machine, home, _repo, store = client(tmp_path, monkeypatch, fake_bw)
    put_note(store, LIST)
    prompts(monkeypatch, cli, {"Address": "10.0.0.5"}, choice=1)
    monkeypatch.setattr(machine, "ssh_login_test", lambda alias: True)
    monkeypatch.setattr(machine, "add_known_host", lambda *a: 0)
    machine.cmd_ssh_add("lab")
    assert "Host lab" in (home / ".ssh/config.local").read_text()
    assert note_text(store) == LIST


def test_login_test_failure_names_next_steps(tmp_path, monkeypatch, fake_bw, capsys):
    cli, machine, *_ = client(tmp_path, monkeypatch, fake_bw)
    monkeypatch.setattr(
        cli.system,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(
            a, 255, "", "Permission denied (publickey)."
        ),
    )
    assert machine.ssh_login_test("nas") is False
    out = capsys.readouterr().out
    assert "ssh-copy-id nas" in out and "ssh_allow_from" in out


def test_remove_home_host(tmp_path, monkeypatch, fake_bw):
    cli, machine, home, repo, store = client(tmp_path, monkeypatch, fake_bw)
    put_note(store, LIST)
    (repo / "machine/ssh_host_keys/homeserver.pub").write_text(
        "ssh-ed25519 AAAA homeserver\n"
    )
    prompts(monkeypatch, cli, {})
    assert machine.cmd_ssh_remove("homeserver") == 0
    assert "homeserver" not in note_text(store)
    assert "Host nas" in note_text(store)
    assert not (repo / "machine/ssh_host_keys/homeserver.pub").exists()
    assert "homeserver" not in (home / ".ssh/config.d/20-home").read_text()


def test_edit_rejects_invalid_text(tmp_path, monkeypatch, fake_bw):
    cli, machine, _home, _repo, store = client(tmp_path, monkeypatch, fake_bw)
    put_note(store, LIST)
    editor = tmp_path / "editor"
    editor.write_text("#!/bin/sh\necho '  BadOption yes' >> \"$1\"\n")
    editor.chmod(0o755)
    monkeypatch.setenv("EDITOR", str(editor))
    monkeypatch.setattr(cli.system, "is_tty", lambda: True)
    monkeypatch.setattr(cli.system, "choose", lambda _t, choices, _d: choices[1])
    machine.cmd_ssh_edit()
    assert note_text(store) == LIST


def test_edit_saves_valid_text(tmp_path, monkeypatch, fake_bw):
    cli, machine, home, _repo, store = client(tmp_path, monkeypatch, fake_bw)
    put_note(store, LIST)
    editor = tmp_path / "editor"
    editor.write_text("#!/bin/sh\nprintf '\\nHost extra\\n  User x\\n' >> \"$1\"\n")
    editor.chmod(0o755)
    monkeypatch.setenv("EDITOR", str(editor))
    monkeypatch.setattr(cli.system, "is_tty", lambda: True)
    machine.cmd_ssh_edit()
    assert "Host extra" in note_text(store)
    assert "Host extra" in (home / ".ssh/config.d/20-home").read_text()


def test_setup_offer_only_when_missing(tmp_path, monkeypatch, fake_bw):
    cli, machine, _home, _repo, store = client(tmp_path, monkeypatch, fake_bw)
    put_note(store, LIST + f"\nHost {HOST}\n  User me\n")
    asked = []
    monkeypatch.setattr(cli.system, "is_tty", lambda: True)
    monkeypatch.setattr(
        cli.system, "prompt_yes_no", lambda q, d=False: asked.append(q) or False
    )
    machine.offer_self_in_host_list(False)
    assert asked == []
    put_note(store, LIST)
    machine.offer_self_in_host_list(False)
    assert asked == [f"Add this host to the SSH host list {NOTE}?"]
    assert note_text(store) == LIST  # declined: nothing changes


def test_add_keeps_change_made_on_another_host(tmp_path, monkeypatch, fake_bw):
    cli, machine, _home, _repo, store = client(tmp_path, monkeypatch, fake_bw)
    put_note(store, LIST)
    prompts(monkeypatch, cli, {"Address": "10.0.0.7"})

    def confirm(question, default=False):
        if question.startswith("Write"):
            put_note(store, LIST + "\nHost other\n  User y\n")  # written meanwhile
            return True
        return default

    monkeypatch.setattr(cli.system, "prompt_yes_no", confirm)
    monkeypatch.setattr(machine, "ssh_login_test", lambda alias: True)
    monkeypatch.setattr(machine, "add_known_host", lambda *a: 0)
    machine.cmd_ssh_add("lab")
    text = note_text(store)
    assert "Host other" in text and "Host lab" in text
