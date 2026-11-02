"""get-password, the shared env-file loader and the work-net tool."""

from __future__ import annotations

import importlib.machinery
import os
import shutil
import subprocess
import sys
import time
import types
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
GET_PASSWORD = REPO / "home/core/.local/bin/get-password"
ENVIRONMENT = REPO / "home/core/.shell/common/environment.sh"


@pytest.fixture(autouse=True)
def isolated_work_net_state(tmp_path, monkeypatch):
    monkeypatch.setenv("WORK_NET_STATE_DIR", str(tmp_path / "state"))


def _stub(bin_dir: Path, name: str, body: str) -> None:
    path = bin_dir / name
    path.write_text("#!/bin/sh\n" + body)
    path.chmod(0o755)


def _keyring(tmp_path: Path, locked: bool | None, secret: str = "") -> Path:
    """Stub busctl and secret-tool; locked=None means no session bus."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    calls = tmp_path / "secret-tool.calls"
    if locked is None:
        _stub(bin_dir, "busctl", "exit 1\n")
    else:
        _stub(bin_dir, "busctl", f"echo 'b {str(locked).lower()}'\n")
    _stub(
        bin_dir,
        "secret-tool",
        f'echo "$@" >>"{calls}"\n'
        f'[ "$1" = lookup ] && printf %s "{secret}"\n'
        "exit 0\n",
    )
    return calls


def _home(tmp_path: Path, **files: str) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    for name, content in files.items():
        path = home / f".{name.replace('_', '.')}"
        path.write_text(content)
        path.chmod(0o600)
    return home


def _get_password(tmp_path: Path, home: Path, **extra: str):
    env = {
        "HOME": str(home),
        "PATH": f"{tmp_path / 'bin'}:/usr/bin:/bin",
        **extra,
    }
    return subprocess.run(
        ["bash", str(GET_PASSWORD), "tester"],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_env_file_wins_over_a_differing_keyring_entry(tmp_path):
    calls = _keyring(tmp_path, locked=False, secret="old-secret")
    home = _home(tmp_path, env="PASSWORD=new-secret\n")
    result = _get_password(tmp_path, home)
    assert result.returncode == 0
    assert result.stdout == "new-secret\n"
    assert not calls.exists()


def test_later_env_file_wins(tmp_path):
    _keyring(tmp_path, locked=False)
    home = _home(tmp_path, env="PASSWORD=group\n", env_local="PASSWORD=local\n")
    assert _get_password(tmp_path, home).stdout == "local\n"


def test_environment_variable_wins_over_env_files(tmp_path):
    _keyring(tmp_path, locked=False)
    home = _home(tmp_path, env="PASSWORD=from-file\n")
    result = _get_password(tmp_path, home, PASSWORD="from-environment")
    assert result.stdout == "from-environment\n"


@pytest.mark.parametrize(
    "line, expected",
    [
        ('PASSWORD=a$b "c" #d e', 'a$b "c" #d e'),
        ("PASSWORD=x'y\\z", "x'y\\z"),
        ("PASSWORD=-n", "-n"),
    ],
)
def test_plain_env_values_come_out_unchanged(tmp_path, line, expected):
    _keyring(tmp_path, locked=False)
    home = _home(tmp_path, env=f"# comment\n\n{line}\n")
    assert _get_password(tmp_path, home).stdout == f"{expected}\n"


def test_export_env_file_is_sourced(tmp_path):
    _keyring(tmp_path, locked=False)
    home = _home(tmp_path, env="export PASSWORD='p w'\nexport OTHER=$UNSET_VAR\n")
    assert _get_password(tmp_path, home).stdout == "p w\n"


def test_keyring_used_when_no_env_password(tmp_path):
    calls = _keyring(tmp_path, locked=False, secret="from-keyring")
    home = _home(tmp_path, env="OTHER=1\n")
    result = _get_password(tmp_path, home)
    assert result.stdout == "from-keyring\n"
    assert calls.read_text() == "lookup password tester\n"


def test_locked_keyring_is_not_read(tmp_path):
    calls = _keyring(tmp_path, locked=True, secret="from-keyring")
    home = _home(tmp_path)
    result = _get_password(tmp_path, home)
    assert result.returncode == 1
    assert result.stdout == ""
    assert not calls.exists()


def test_no_session_bus_skips_the_keyring(tmp_path):
    calls = _keyring(tmp_path, locked=None, secret="from-keyring")
    result = _get_password(tmp_path, _home(tmp_path))
    assert result.returncode == 1
    assert not calls.exists()


def test_hanging_keyring_lookup_is_stopped(tmp_path):
    _keyring(tmp_path, locked=False)
    _stub(tmp_path / "bin", "secret-tool", "sleep 30\n")
    result = _get_password(tmp_path, _home(tmp_path), GET_PASSWORD_KEYRING_TIMEOUT="1")
    assert result.returncode == 1


def test_open_permissions_warn_on_stderr_only(tmp_path):
    _keyring(tmp_path, locked=False)
    home = _home(tmp_path, env="PASSWORD=secret\n")
    (home / ".env").chmod(0o644)
    result = _get_password(tmp_path, home)
    assert result.stdout == "secret\n"
    assert "chmod 600" in result.stderr


@pytest.mark.parametrize("shell", ["bash", "zsh"])
def test_shell_loader_still_exports_env_files(tmp_path, shell):
    if not shutil.which(shell):
        pytest.skip(f"{shell} is not installed")
    home = _home(
        tmp_path,
        env="A=plain ${HOME}\n",
        env_host="export B='exported'\n",
        env_local="A=local\n",
    )
    result = subprocess.run(
        [
            shell,
            "-c",
            '. "$1" >/dev/null; printf "%s\\n" "$A" "$B"; '
            "typeset -f dotfiles_load_envfiles >/dev/null && echo leaked || true",
            "_",
            str(ENVIRONMENT),
        ],
        env={"HOME": str(home), "PATH": os.environ["PATH"]},
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.splitlines() == ["local", "exported"]


WORK_NET = REPO / "home/work/.local/bin/work-net"


def _load_work_net():
    loader = importlib.machinery.SourceFileLoader("work_net", str(WORK_NET))
    module = types.ModuleType(loader.name)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    return module


def _sync_env(tmp_path: Path, *, locked: bool, env_pw: str, stored: str) -> Path:
    """Stubs for keyring sync; returns the file that records secret-tool calls."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls = tmp_path / "calls"
    _stub(bin_dir, "busctl", f"echo 'b {str(locked).lower()}'\n")
    _stub(bin_dir, "get-password", f"printf '%s\\n' '{env_pw}'\n")
    _stub(
        bin_dir,
        "secret-tool",
        f'echo "args: $*" >>"{calls}"\n'
        f"[ \"$1\" = lookup ] && printf %s '{stored}'\n"
        f'[ "$1" = store ] && {{ printf "stdin: "; cat; echo; }} >>"{calls}"\n'
        "exit 0\n",
    )
    return calls


def _work_net(tmp_path: Path, *args: str):
    return subprocess.run(
        [sys.executable, str(WORK_NET), *args],
        env={"HOME": str(tmp_path), "PATH": f"{tmp_path / 'bin'}:/usr/bin:/bin"},
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_keyring_sync_replaces_a_stale_entry(tmp_path):
    calls = _sync_env(tmp_path, locked=False, env_pw="new pw", stored="old pw")
    result = _work_net(tmp_path, "-v", "keyring", "sync")
    assert result.returncode == 0
    lines = calls.read_text().splitlines()
    assert lines[0].startswith("args: lookup password ")
    assert lines[1].startswith("args: store --label=get-password (")
    assert lines[2] == "stdin: new pw"
    assert "new pw" not in lines[1] and "new pw" not in result.stdout + result.stderr


def test_keyring_sync_leaves_an_equal_entry(tmp_path):
    calls = _sync_env(tmp_path, locked=False, env_pw="same", stored="same")
    assert _work_net(tmp_path, "keyring", "sync").returncode == 0
    assert "store" not in calls.read_text()


def test_keyring_sync_skips_a_locked_keyring(tmp_path):
    calls = _sync_env(tmp_path, locked=True, env_pw="new", stored="old")
    assert _work_net(tmp_path, "keyring", "sync").returncode == 0
    assert not calls.exists()


def test_run_stops_a_hanging_command():
    work_net = _load_work_net()
    started = time.monotonic()
    result = work_net.run(["sleep", "30"], timeout=0.5)
    assert result.timed_out and not result.ok
    assert time.monotonic() - started < 5


def test_run_passes_input_not_arguments():
    work_net = _load_work_net()
    result = work_net.run(["cat"], timeout=5, input="secret")
    assert result.ok and result.stdout == "secret"


# --- failure guard ------------------------------------------------------------


class Clock:
    def __init__(self) -> None:
        self.now = 1_000_000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def wn(tmp_path, monkeypatch):
    module = _load_work_net()
    monkeypatch.setenv("WORK_NET_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.delenv("DBUS_SESSION_BUS_ADDRESS", raising=False)
    notes: list[str] = []
    monkeypatch.setattr(module, "notify", lambda summary, body: notes.append(body))
    module.notes = notes
    return module


def _guard(wn, clock):
    return wn.Guard(wn.state_dir(), clock)


def test_network_errors_are_not_counted(wn):
    stop = _guard(wn, Clock())
    stop.record("network", "pw")
    stop.record("timeout", "pw")
    assert stop.blocked("pw") is None and stop.describe() == "ok"


def test_two_rejections_15_minutes_apart_stop(wn):
    clock = Clock()
    stop = _guard(wn, clock)
    stop.record("rejected", "stale")
    clock.now += 15 * 60
    assert stop.blocked("stale") is None
    stop.record("rejected", "stale")
    assert stop.blocked("stale").startswith("stopped: the password was rejected")
    assert len(wn.notes) == 1 and "kinit-pw" in wn.notes[0]


def test_second_attempt_waits_15_minutes(wn):
    clock = Clock()
    stop = _guard(wn, clock)
    stop.record("rejected", "stale")
    clock.now += 14 * 60
    assert stop.blocked("stale") == "waiting 15 minutes after a rejected password"


def test_unknown_failures_count_like_rejections(wn):
    clock = Clock()
    stop = _guard(wn, clock)
    stop.record("unknown", "pw")
    clock.now += 16 * 60
    stop.record("unknown", "pw")
    assert stop.blocked("pw").startswith("stopped")


@pytest.mark.parametrize("outcome", ["locked", "expired"])
def test_locked_or_expired_stop_at_once(wn, outcome):
    stop = _guard(wn, Clock())
    stop.record(outcome, "pw")
    assert stop.blocked("pw").startswith("stopped")
    assert wn.notes


def test_changed_password_resets_the_guard(wn):
    stop = _guard(wn, Clock())
    stop.record("locked", "old")
    assert stop.blocked("new") is None
    assert stop.blocked("old") is None


def test_manual_reset_and_a_manual_failure_counts_again(wn):
    clock = Clock()
    stop = _guard(wn, clock)
    stop.record("rejected", "pw")
    clock.now += 16 * 60
    stop.record("rejected", "pw")
    stop.reset("manual run")
    assert stop.blocked("pw") is None
    stop.record("rejected", "pw")
    assert stop.blocked("pw") == "waiting 15 minutes after a rejected password"


def test_guard_file_is_private_and_holds_no_password(wn):
    stop = _guard(wn, Clock())
    stop.record("rejected", "secret-value")
    path = wn.state_dir() / "guard.json"
    assert path.stat().st_mode & 0o777 == 0o600
    assert "secret-value" not in path.read_text()


def test_guard_lock_serialises_access(wn):
    import threading

    first, second = _guard(wn, Clock()), _guard(wn, Clock())
    entered = threading.Event()

    def contender() -> None:
        with second.locked():
            entered.set()

    with first.locked():
        thread = threading.Thread(target=contender)
        thread.start()
        assert not entered.wait(0.3)
    assert entered.wait(5)
    thread.join()


# --- Kerberos -----------------------------------------------------------------

KLIST = """Ticket cache: FILE:/tmp/krb5cc_1
Default principal: USER@EXAMPLE.COM

Valid starting     Expires            Service principal
{start}  {end}  krbtgt/EXAMPLE.COM@EXAMPLE.COM
        renew until {renew}
{start}  {end}  HTTP/proxy.example.com@EXAMPLE.COM
"""


def _klist_text(start: float, end: float, renew: float) -> str:
    def fmt(epoch: float) -> str:
        return time.strftime("%m/%d/%y %H:%M:%S", time.localtime(epoch))

    return KLIST.format(start=fmt(start), end=fmt(end), renew=fmt(renew))


def test_parse_klist_reads_the_tgt_of_the_default_principal(wn):
    now = int(time.time())
    ticket = wn.parse_klist(_klist_text(now, now + 3600, now + 7200))
    assert ticket.principal == "USER@EXAMPLE.COM"
    assert ticket.expires == now + 3600 and ticket.renew_until == now + 7200
    assert wn.parse_klist("klist: No credentials cache found\n") is None


def test_klist_runs_in_the_c_locale(wn, monkeypatch):
    seen = {}

    def fake_run(cmd, **kwargs):
        seen.update(kwargs)
        return wn.Result(1)

    monkeypatch.setattr(wn, "run", fake_run)
    assert wn.current_ticket() is None
    assert seen["env"] == {"LC_ALL": "C"}


@pytest.mark.parametrize(
    "stderr, outcome",
    [
        ("kinit: Cannot contact any KDC for realm 'X' while getting", "network"),
        ("kinit: Password incorrect while getting initial credentials", "rejected"),
        ("kinit: Client's credentials have been revoked while getting", "locked"),
        ("kinit: Password has expired while getting initial credentials", "expired"),
        ("kinit: something new", "unknown"),
    ],
)
def test_classify_kinit(wn, stderr, outcome):
    assert wn.classify_kinit(wn.Result(1, stderr=stderr)) == outcome


def _kerberos(wn, monkeypatch, ticket, *, reachable=True, results=None):
    calls: list[tuple] = []
    results = list(results or [])

    def fake_run(cmd, **kwargs):
        calls.append((tuple(cmd), kwargs.get("input")))
        return results.pop(0) if results else wn.Result(0)

    monkeypatch.setattr(wn, "current_ticket", lambda: ticket)
    monkeypatch.setattr(wn, "kdc_reachable", lambda realm: reachable)
    monkeypatch.setattr(wn, "default_realm", lambda: "EXAMPLE.COM")
    monkeypatch.setattr(wn, "get_password", lambda: "pw")
    monkeypatch.setattr(wn, "keyring_sync", lambda user: 0)
    monkeypatch.setattr(wn, "run", fake_run)
    return calls


def test_valid_ticket_is_left_alone(wn, monkeypatch):
    now = time.time()
    ticket = wn.Ticket("U@EXAMPLE.COM", now + 3 * 3600, now + 20 * 3600)
    calls = _kerberos(wn, monkeypatch, ticket)
    assert wn.kerberos_refresh(auto=True) == 0
    assert calls == []


def test_ticket_close_to_expiry_is_renewed_without_password(wn, monkeypatch):
    now = time.time()
    ticket = wn.Ticket("U@EXAMPLE.COM", now + 3600, now + 20 * 3600)
    calls = _kerberos(wn, monkeypatch, ticket)
    assert wn.kerberos_refresh(auto=True) == 0
    assert calls == [(("kinit", "-R"), None)]


def test_renewal_threshold_can_be_raised_for_tests(wn, monkeypatch):
    now = time.time()
    ticket = wn.Ticket("U@EXAMPLE.COM", now + 10 * 3600, now + 20 * 3600)
    calls = _kerberos(wn, monkeypatch, ticket)
    assert wn.kerberos_refresh(auto=True) == 0 and calls == []
    monkeypatch.setenv("WORK_NET_RENEW_BEFORE_HOURS", "12")
    assert wn.kerberos_refresh(auto=True) == 0
    assert calls == [(("kinit", "-R"), None)]


def test_expired_ticket_is_requested_with_the_password(wn, monkeypatch):
    now = time.time()
    ticket = wn.Ticket("U@EXAMPLE.COM", now - 60, now + 3600)
    calls = _kerberos(wn, monkeypatch, ticket)
    assert wn.kerberos_refresh(auto=True) == 0
    assert calls == [(("kinit",), "pw\n")]


def test_no_ticket_and_kdc_unreachable_does_nothing(wn, monkeypatch):
    calls = _kerberos(wn, monkeypatch, None, reachable=False)
    assert wn.kerberos_refresh(auto=True) == 0
    assert calls == []
    assert wn.guard().describe() == "ok"


def test_hanging_kinit_is_not_counted(wn, monkeypatch):
    _kerberos(wn, monkeypatch, None, results=[wn.Result(-9, timed_out=True)])
    assert wn.kerberos_refresh(auto=True) == 1
    assert wn.guard().describe() == "ok"


def test_stopped_guard_blocks_automatic_kinit_only(wn, monkeypatch):
    calls = _kerberos(wn, monkeypatch, None)
    wn.guard().record("locked", "pw")
    assert wn.kinit_with_password(auto=True) == 0
    assert calls == []
    assert wn.kinit_with_password(auto=False) == 0
    assert calls == [(("kinit",), "pw\n")]


def test_status_names_a_stop_and_the_reset(wn, monkeypatch, capsys):
    _kerberos(wn, monkeypatch, None, reachable=False)
    wn.guard().record("expired", "secret-value")
    assert wn.status() == 0
    out = capsys.readouterr().out
    assert "stopped: the password has expired" in out and "kinit-pw" in out
    assert "secret-value" not in out


KINIT_PW = REPO / "home/core/.local/bin/kinit-pw"


def test_kinit_pw_without_terminal_obeys_the_guard(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls = tmp_path / "calls"
    _stub(bin_dir, "work-net", f'echo "$@" >"{calls}"\n')
    subprocess.run(
        ["bash", str(KINIT_PW), "user@EXAMPLE.COM"],
        env={"PATH": f"{bin_dir}:/usr/bin:/bin", "HOME": str(tmp_path)},
        stdin=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        check=True,
    )
    assert calls.read_text() == "kerberos kinit --auto -- user@EXAMPLE.COM\n"


# --- units, enabling, migration, shell start ----------------------------------

UNITS = REPO / "home/work/.config/systemd/user"


def test_kerberos_timer_runs_the_refresh_every_10_minutes():
    timer = (UNITS / "work-net-kerberos.timer").read_text()
    service = (UNITS / "work-net-kerberos.service").read_text()
    assert "OnBootSec=1min" in timer and "OnUnitActiveSec=10min" in timer
    assert "Unit=work-net-kerberos.service" in timer
    assert "ExecStart=%h/.local/bin/work-net kerberos refresh --auto" in service


@pytest.fixture
def machine(tmp_path, monkeypatch):
    from machine_loader import load_machine_module

    home = tmp_path / "home"
    (home / ".config/systemd/user").mkdir(parents=True)
    repo = tmp_path / "dotfiles"
    (repo / ".git").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("DOTFILES_REPO", str(repo))
    monkeypatch.setenv(
        "MACHINE_APPLIED_HOST_FILE", str(home / ".local/share/machine/applied.yml")
    )
    monkeypatch.setenv("MACHINE_STATE_DIR", str(home / ".local/share/machine"))
    cli = load_machine_module("machine_work_net", REPO / "machine_cli/machine")
    monkeypatch.setattr(cli.system, "in_docker", lambda: False)
    ran: list[list[str]] = []
    crontab = {"text": ""}

    def fake_run(args, **kwargs):
        ran.append(list(args))
        if list(args) == ["crontab", "-l"]:
            return subprocess.CompletedProcess(args, 0, crontab["text"], "")
        if list(args) == ["crontab", "-"]:
            crontab["text"] = kwargs["input_text"]
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(cli.system, "have", lambda name: True)
    monkeypatch.setattr(cli.system, "run", fake_run)
    instance = cli.Machine()
    monkeypatch.setattr(instance, "ensure_linger", lambda: None)
    instance.ran, instance.crontab = ran, crontab
    return instance


@pytest.mark.parametrize(
    "features, action",
    [(["zsh-full", "kerberos"], "enable"), (["zsh-full"], "disable")],
)
def test_kerberos_timer_follows_the_feature(machine, features, action):
    (machine.home / ".config/systemd/user/work-net-kerberos.timer").write_text("")
    machine.write_profile("work", "server", features, [])
    machine.ensure_update_timer()
    assert ["systemctl", "--user", action, "--now", "work-net-kerberos.timer"] in (
        machine.ran
    )


def test_hosts_without_work_net_units_are_untouched(machine):
    machine.ensure_update_timer()
    assert machine.ran == []


CRON = (
    "MAILTO=''\n"
    "# BEGIN ensure-kerberos-token - dotfiles\n"
    "*/15 * * * * PATH=/x /home/u/.local/bin/ensure-kerberos-token-cron\n"
    "# END ensure-kerberos-token - dotfiles\n"
    "0 3 * * * backup\n"
)


def test_update_removes_the_kerberos_cron_job(machine):
    (machine.home / ".config/systemd/user/work-net-kerberos.timer").write_text("")
    wrapper = machine.home / ".local/bin/ensure-kerberos-token-cron"
    wrapper.parent.mkdir(parents=True)
    wrapper.write_text("#!/bin/sh\n")
    machine.write_profile("work", "desktop", ["kerberos"], [])
    machine.crontab["text"] = CRON
    machine.ensure_update_timer()
    assert machine.crontab["text"] == "MAILTO=''\n0 3 * * * backup\n"
    assert not wrapper.exists()
    machine.ran.clear()
    machine.ensure_update_timer()
    assert ["crontab", "-"] not in machine.ran


def test_work_shell_start_requests_no_ticket(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls = tmp_path / "calls"
    for name in ("kinit", "klist", "kinit-pw", "ensure-kerberos-token", "crontab"):
        _stub(bin_dir, name, f'echo {name} >>"{calls}"\n')
    subprocess.run(
        [
            "bash",
            "-c",
            '. "$1"',
            "_",
            str(REPO / "home/work/.shell/work/common/environment.sh"),
        ],
        env={
            "HOME": str(tmp_path),
            "PATH": f"{bin_dir}:/usr/bin:/bin",
            "WORK_SETUP": "true",
            "TERM": "dumb",
        },
        capture_output=True,
        check=True,
    )
    assert not calls.exists()


# --- VPN ----------------------------------------------------------------------

CONNECT_STUB = """#!/bin/bash
# Stub of connect_vpn.sh; MODE selects the behaviour.
case "$(cat "$STUB_DIR/mode")" in
ok) echo "INFO Establishing VPN session"; read -r pw; echo "used:$pw" >"$STUB_DIR/used" ;;
cert) read -r -p "Press [Enter]" _; read -r pw; echo "used:$pw" >"$STUB_DIR/used" ;;
gateway) echo "[ERROR] Unable to reach the gateway 'x'"; exit 1 ;;
rejected) read -r pw; echo "[ERROR] Failed to connect VPN: auth failed"; exit 1 ;;
hang) sleep 30 ;;
esac
"""


@pytest.fixture
def vpn(wn, tmp_path, monkeypatch):
    osd = tmp_path / "osd"
    osd.mkdir()
    (osd / "connect_vpn.sh").write_text(CONNECT_STUB)
    (osd / "disconnect_vpn.sh").write_text("#!/bin/sh\necho disconnected\n")
    for script in osd.iterdir():
        script.chmod(0o755)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    _stub(bin_dir, "sudo", '[ "$1" = -n ] && shift\nexec "$@"\n')
    monkeypatch.setenv("PATH", f"{bin_dir}:/usr/bin:/bin")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("STUB_DIR", str(tmp_path))
    monkeypatch.setenv("WORK_NET_OSD_DIR", str(osd))
    monkeypatch.setattr(wn, "get_password", lambda: "s3cret")
    refreshed: list[bool] = []
    monkeypatch.setattr(wn, "kerberos_refresh", lambda auto: refreshed.append(auto))
    prefs = tmp_path / ".wifivpn/vpn_preferences.ini"
    prefs.parent.mkdir()
    prefs.write_text("USER_NAME=tester\nUSE_KEYRING=1\nUSE_NETWORKMANAGER=0\n")

    def connect(mode: str, auto: bool = True) -> int:
        (tmp_path / "mode").write_text(mode)
        return wn.vpn_connect(auto)

    wn.connect, wn.prefs, wn.refreshed, wn.stub_dir = (
        connect,
        prefs,
        refreshed,
        tmp_path,
    )
    return wn


def test_vpn_connect_uses_the_env_password_without_keyring(vpn, capsys):
    assert vpn.connect("ok") == 0
    assert (vpn.stub_dir / "used").read_text() == "used:s3cret\n"
    assert vpn.prefs.read_text().splitlines() == [
        "USER_NAME=tester",
        "USE_NETWORKMANAGER=0",
        "USE_KEYRING=0",
    ]
    out = capsys.readouterr().out
    assert "Establishing VPN session" in out and "s3cret" not in out
    assert vpn.refreshed == [True]
    log_text = (vpn.state_dir() / "work-net.log").read_text()
    assert "| INFO Establishing VPN session" in log_text and "VPN connected" in log_text
    assert "s3cret" not in log_text


def test_log_file_is_capped(wn, monkeypatch):
    monkeypatch.setattr(wn, "LOG_MAX_BYTES", 100)
    for index in range(20):
        wn.log(f"line {index}")
    assert (wn.state_dir() / "work-net.log.1").exists()
    assert (wn.state_dir() / "work-net.log").stat().st_size < 200


def test_certificate_prompt_does_not_block(vpn):
    assert vpn.connect("cert") == 0
    assert (vpn.stub_dir / "used").read_text() == "used:s3cret\n"


def test_unreachable_gateway_is_not_counted(vpn):
    assert vpn.connect("gateway") == 1
    assert vpn.guard().describe() == "ok"


def test_rejected_vpn_password_is_counted(vpn):
    assert vpn.connect("rejected") == 1
    assert vpn.guard().describe().startswith("1 rejected password")


def test_missing_sudo_rule_is_not_counted(vpn):
    _stub(vpn.stub_dir / "bin", "sudo", 'echo "sudo: a password is required"\nexit 1\n')
    assert vpn.connect("ok") == 1
    assert vpn.guard().describe() == "ok"
    assert vpn.notes


def test_hanging_connect_is_stopped_and_not_counted(vpn, monkeypatch):
    monkeypatch.setattr(vpn, "VPN_CONNECT_TIMEOUT", 0.5)
    started = time.monotonic()
    assert vpn.connect("hang") == 1
    assert time.monotonic() - started < 10
    assert vpn.guard().describe() == "ok"


def test_stopped_guard_blocks_automatic_connect_only(vpn):
    vpn.guard().record("locked", "s3cret")
    assert vpn.connect("ok", auto=True) == 0
    assert not (vpn.stub_dir / "used").exists()
    assert vpn.connect("ok", auto=False) == 0
    assert (vpn.stub_dir / "used").exists()


def _facts(wn, **changes):
    base = dict(
        network=True,
        kdc=False,
        client=False,
        connecting=False,
        paused=False,
        guard="ok",
        since_event=100.0,
    )
    return wn.Facts(**{**base, **changes})


@pytest.mark.parametrize(
    "changes, action",
    [
        ({"kdc": True}, "kerberos"),
        ({"network": False}, "wait"),
        ({}, "connect"),
        ({"client": True, "since_event": 10.0}, "wait"),
        ({"connecting": True, "since_event": 10.0}, "wait"),
        ({"client": True, "since_event": 50.0}, "connect"),
        ({"paused": True}, "wait"),
        ({"guard": "stopped: the account is locked"}, "wait"),
    ],
)
def test_decide(wn, changes, action):
    assert wn.decide(_facts(wn, **changes))[0] == action


def test_watcher_debounces_a_burst_into_one_check(wn):
    acts: list[str] = []
    watcher = wn.Watcher(lambda since: _facts(wn), lambda a, r: acts.append(a), 0.0)
    watcher.check(0.0)
    for t in (10.0, 11.0, 12.0):
        watcher.on_event("network", t)
        assert not watcher.due(t + 1)
    assert watcher.due(15.0)
    watcher.check(15.0)
    assert acts == ["connect", "connect"] and not watcher.due(16.0)


def test_watcher_waits_for_the_own_reconnect_then_connects(wn):
    state = {"client": True}
    watcher = wn.Watcher(
        lambda since: _facts(wn, client=state["client"], since_event=since),
        lambda a, r: None,
        0.0,
    )
    watcher.on_event("wake", 0.0)
    assert watcher.check(3.0)[0] == "wait"
    assert not watcher.due(40.0) and watcher.due(46.0)
    assert watcher.check(46.0)[0] == "connect"


def test_watcher_ticks_every_2_minutes(wn):
    watcher = wn.Watcher(lambda since: _facts(wn, kdc=True), lambda a, r: None, 0.0)
    watcher.check(0.0)
    assert not watcher.due(119.0) and watcher.due(120.0)


@pytest.mark.parametrize(
    "line, kind",
    [
        (
            "/org/freedesktop/login1: org.freedesktop.login1.Manager.PrepareForSleep "
            "(false,)",
            "wake",
        ),
        (
            "/org/freedesktop/login1: org.freedesktop.login1.Manager.PrepareForSleep "
            "(true,)",
            None,
        ),
        (
            "/org/freedesktop/NetworkManager: org.freedesktop.NetworkManager."
            "StateChanged (uint32 70,)",
            "network",
        ),
        (
            "/org/freedesktop/NetworkManager/Devices/4: org.freedesktop.DBus."
            "Properties.PropertiesChanged ('org.freedesktop.NetworkManager.Device."
            "Wireless', {'LastScan': <int64 1>}, @as [])",
            None,
        ),
    ],
)
def test_parse_event(wn, line, kind):
    assert wn.parse_event(line) == kind


def test_ended_monitor_is_restarted(wn):
    events: list[str] = []
    line = (
        "/org/freedesktop/NetworkManager: org.freedesktop.NetworkManager."
        "StateChanged (uint32 70,)"
    )
    wn.follow(["echo", line], events.append, sleep=lambda s: None, rounds=2)
    assert events == ["network", "network", "network", "network"]


def test_dry_run_only_prints(wn, monkeypatch, capsys):
    acted: list[str] = []
    monkeypatch.setattr(wn, "gather", lambda since: _facts(wn))
    monkeypatch.setattr(wn, "act", lambda a, r: acted.append(a))
    assert wn.vpn_check(dry_run=True) == 0
    assert (
        capsys.readouterr().out == "would connect the VPN: work network not reachable\n"
    )
    assert acted == []


def test_manual_disconnect_pauses_until_wake(vpn, capsys):
    assert vpn.vpn_disconnect() == 0
    assert "disconnected" in capsys.readouterr().out
    assert vpn.pause_marker().exists()
    watcher = vpn.Watcher(lambda since: _facts(vpn), lambda a, r: None, 0.0)
    watcher.on_event("wake", 1.0)
    assert not vpn.pause_marker().exists()


def test_manual_connect_ends_the_pause(vpn):
    vpn.vpn_disconnect()
    assert vpn.connect("ok", auto=False) == 0
    assert not vpn.pause_marker().exists()


def test_vpn_aliases_use_work_net():
    source = (REPO / "home/work/.shell/work/common/environment.sh").read_text()
    assert "alias vpn-pw='work-net vpn connect'" in source
    assert "alias osd-vpn-disconnect='work-net vpn disconnect'" in source


@pytest.mark.parametrize("days, shown", [(12, True), (25, False)])
def test_certificate_notice_once_a_day(wn, monkeypatch, days, shown):
    monkeypatch.setattr(wn, "cert_days_left", lambda: days)
    wn.cert_notice()
    wn.cert_notice()
    assert len(wn.notes) == (1 if shown else 0)
    if shown:
        assert "12 days" in wn.notes[0] and "osd-wifivpn-enroll" in wn.notes[0]


def test_status_shows_the_vpn(vpn, monkeypatch, capsys):
    monkeypatch.setattr(vpn, "current_ticket", lambda: None)
    monkeypatch.setattr(vpn, "default_realm", lambda: None)
    monkeypatch.setattr(vpn, "cert_days_left", lambda: 30)
    vpn.vpn_disconnect()
    capsys.readouterr()
    vpn.status()
    out = capsys.readouterr().out
    assert "VPN client:" in out and "paused until login or wake" in out
    assert "30 days left" in out


@pytest.mark.parametrize(
    "device, tool, action",
    [
        ("desktop", True, "enable"),
        ("server", True, "disable"),
        ("desktop", False, "disable"),
    ],
)
def test_vpn_watcher_only_on_desktops_with_the_osd_tool(
    machine, monkeypatch, tmp_path, device, tool, action
):
    updates = sys.modules["machine_cli.updates"]
    osd_tool = tmp_path / "osd-vpn-connect"
    if tool:
        osd_tool.write_text("")
    monkeypatch.setattr(updates, "OSD_VPN_CONNECT", osd_tool)
    (machine.home / ".config/systemd/user/work-net-vpn-watch.service").write_text("")
    machine.write_profile("work", device, ["kerberos"], [])
    machine.ensure_update_timer()
    assert ["systemctl", "--user", action, "--now", "work-net-vpn-watch.service"] in (
        machine.ran
    )


def test_vpn_watch_unit_follows_the_graphical_session():
    unit = (UNITS / "work-net-vpn-watch.service").read_text()
    assert "PartOf=graphical-session.target" in unit
    assert "WantedBy=graphical-session.target" in unit
    assert "ExecStart=%h/.local/bin/work-net vpn watch" in unit
    assert "ExecStop" not in unit
