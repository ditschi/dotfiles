"""machine/ssh_tunnel/device-tunnel.sh under BusyBox sh with a fake ssh."""

from __future__ import annotations

import shutil
import subprocess
import time

import pytest

from package_sets import REPO

SCRIPT = REPO / "machine/ssh_tunnel/device-tunnel.sh"
BUSYBOX = shutil.which("busybox")
pytestmark = pytest.mark.skipif(not BUSYBOX, reason="busybox not installed")


@pytest.fixture
def device(tmp_path):
    calls = tmp_path / "calls"
    fake = tmp_path / "ssh"
    # Exits 0 at once, as ssh did under ControlMaster: the loop must start it again.
    fake.write_text(f'#!/bin/sh\necho "$*" >>"{calls}"\nexit 0\n')
    fake.chmod(0o755)
    conf = tmp_path / "tunnel.conf"
    conf.write_text(
        "JUMP_HOST=jump.example\nPORT=2225\nKEY=/root/.ssh/tunnel_oracle\n"
        "KNOWN_HOSTS=/root/.ssh/tunnel_known_hosts\n"
        f"PIDFILE={tmp_path}/tunnel.pid\nRETRY=1\nSSH={fake}\n"
    )
    # The loop runs under BusyBox sh too, as on the NAS.
    shell = tmp_path / "busybox-sh"
    shell.write_text(f'#!/bin/sh\nexec {BUSYBOX} sh "$@"\n')
    shell.chmod(0o755)
    env = {
        "PATH": f"{tmp_path}:/usr/bin:/bin",
        "TUNNEL_CONF": str(conf),
        "TUNNEL_SHELL": str(shell),
    }

    def run(action):
        return subprocess.run(
            [BUSYBOX, "sh", str(SCRIPT), action],
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )

    yield run, calls, tmp_path
    run("stop")
    time.sleep(0.5)
    # A loop that outlives stop keeps running after the test, without its config.
    assert loops(tmp_path) == []


def loops(tmp_path):
    """Loop processes of this test's config, without their children: BusyBox runs
    a backgrounded applet (sleep) in a fork that keeps the loop's command line.
    Loops of other tests or test runs do not count."""
    out = subprocess.run(
        ["pgrep", "-f", f"sh {SCRIPT} run"], capture_output=True, text=True
    )
    conf = f"TUNNEL_CONF={tmp_path / 'tunnel.conf'}".encode()
    parents = {}
    for pid in out.stdout.split():
        try:
            stat = open(f"/proc/{pid}/stat").read()
            environ = open(f"/proc/{pid}/environ", "rb").read().split(b"\0")
        except OSError:
            continue
        if conf in environ:
            parents[pid] = stat.rsplit(")", 1)[1].split()[1]
    pids = set(parents)
    return sorted(pid for pid, parent in parents.items() if parent not in pids)


def test_syntax_under_busybox():
    subprocess.run([BUSYBOX, "sh", "-n", str(SCRIPT)], check=True)


def test_start_twice_runs_one_loop_that_restarts_ssh(device):
    run, calls, tmp_path = device
    assert run("start").returncode == 0
    assert run("start").returncode == 0
    time.sleep(2.5)
    assert len(loops(tmp_path)) == 1
    assert run("status").returncode == 0
    lines = calls.read_text().splitlines()
    assert len(lines) >= 2  # restarted after exit status 0
    args = lines[0]
    for option in (
        "-F /dev/null -N",
        "ControlMaster=no",
        "ControlPath=none",
        "ExitOnForwardFailure=yes",
        "ServerAliveInterval=30",
        "StrictHostKeyChecking=yes",
        "UserKnownHostsFile=/root/.ssh/tunnel_known_hosts",
        "HostKeyAlias=oracle",
        "-i /root/.ssh/tunnel_oracle",
        "-R 127.0.0.1:2225:localhost:22 tunnel@jump.example",
    ):
        assert option in args


def test_stop_ends_the_loop(device):
    run, _calls, tmp_path = device
    run("start")
    time.sleep(0.5)
    assert run("stop").returncode == 0
    time.sleep(0.5)
    assert loops(tmp_path) == []
    assert run("status").returncode == 1


def test_missing_setting_stops_with_78(device, tmp_path):
    run, *_ = device
    conf = tmp_path / "tunnel.conf"
    conf.write_text(conf.read_text().replace("PORT=2225\n", ""))
    assert run("start").returncode == 78
    assert loops(tmp_path) == []


def test_parallel_starts_run_one_loop(device):
    _run, _calls, tmp_path = device
    env = {
        "PATH": f"{tmp_path}:/usr/bin:/bin",
        "TUNNEL_CONF": str(tmp_path / "tunnel.conf"),
        "TUNNEL_SHELL": str(tmp_path / "busybox-sh"),
    }
    starts = [
        subprocess.Popen([BUSYBOX, "sh", str(SCRIPT), "start"], env=env)
        for _ in range(4)
    ]
    for start in starts:
        start.wait(timeout=10)
    time.sleep(1)
    assert len(loops(tmp_path)) == 1


def test_start_right_after_start_runs_one_loop(device):
    """The second start must not take the first loop's PID, still in its exec chain
    (empty or start's command line), for a stale one."""
    run, _calls, tmp_path = device
    for _ in range(15):
        run("start")
        run("start")
        time.sleep(0.2)
        assert len(loops(tmp_path)) == 1
        run("stop")
        time.sleep(0.2)
        assert loops(tmp_path) == []


def test_stale_pid_of_another_program_is_not_the_loop(device):
    run, _calls, tmp_path = device
    other = subprocess.Popen(["sleep", "30"])
    try:
        (tmp_path / "tunnel.pid").write_text(f"{other.pid}\n")
        assert run("status").returncode == 1
        assert run("start").returncode == 0
        time.sleep(0.5)
        assert len(loops(tmp_path)) == 1
    finally:
        other.kill()
