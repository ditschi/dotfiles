"""Low disk space: watched filesystems, thresholds, attention item, state and prompt."""

from __future__ import annotations

import importlib
import os
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

from package_sets import REPO

MACHINE = REPO / "machine_cli/machine"
GIB = 1024**3
MIB = 1024**2

sys.path.insert(0, str(REPO))
ds = importlib.import_module("machine_cli.disk_space")


def mountinfo(*rows: tuple[str, str, str, str]) -> str:
    """rows: (major:minor, mount point, type, options)."""
    return "".join(
        f"{n} 1 {dev} / {path} {opts},relatime shared:{n} - {fstype} /dev/x{n} {opts}\n"
        for n, (dev, path, fstype, opts) in enumerate(rows, 20)
    )


VM = mountinfo(
    ("253:0", "/", "ext4", "rw"),
    ("259:2", "/boot", "ext4", "rw"),
    ("259:1", "/boot/efi", "vfat", "rw"),
    ("253:1", "/mnt/data", "ext4", "rw"),
    ("0:25", "/run", "tmpfs", "rw"),
    ("7:3", "/snap/core/1", "squashfs", "ro"),
    ("0:50", "/mnt/nas", "nfs4", "rw"),
)


def paths(text: str, entries=()) -> list[str]:
    limits, _ = ds.parse_limits(list(entries))
    return [m.path for m in ds.watched_mounts(ds.parse_mountinfo(text), limits)]


# --- 2.1 watched filesystems ---------------------------------------------------


def test_vm_with_system_and_data_disk():
    assert paths(VM) == ["/", "/boot", "/boot/efi", "/mnt/data"]


def test_bind_mount_counts_once_under_the_shortest_path():
    text = mountinfo(
        ("253:1", "/srv/data", "ext4", "rw"), ("253:1", "/mnt/data", "ext4", "rw")
    )
    assert paths(text) == ["/mnt/data"]


def test_btrfs_subvolumes_count_once():
    text = mountinfo(
        ("0:40", "/home", "btrfs", "rw"),
        ("0:40", "/", "btrfs", "rw"),
        ("0:40", "/var/log", "btrfs", "rw"),
    )
    assert paths(text) == ["/"]


def test_container_overlay_root_is_not_watched():
    text = mountinfo(
        ("0:90", "/", "overlay", "rw"), ("0:91", "/dev/shm", "tmpfs", "rw")
    )
    assert paths(text) == []


def test_read_only_mount_is_not_watched():
    text = mountinfo(("253:1", "/mnt/backup", "ext4", "ro"))
    assert paths(text) == []


def test_named_mount_point_is_watched_whatever_its_type():
    assert paths(VM, [{"path": "/run", "min_free": "10M"}]) == [
        "/",
        "/boot",
        "/boot/efi",
        "/mnt/data",
        "/run",
    ]


def test_named_bind_mount_wins_over_the_shortest_path():
    text = mountinfo(
        ("253:1", "/mnt/data", "ext4", "rw"), ("253:1", "/srv/data", "ext4", "rw")
    )
    assert paths(text, [{"path": "/srv/data", "min_free": "1G"}]) == ["/srv/data"]


def test_named_mount_point_not_mounted_is_skipped():
    assert paths(VM, [{"path": "/mnt/gone", "min_free": "1G"}]) == paths(VM)


def test_ignored_mount_point_is_not_watched():
    assert "/mnt/data" not in paths(VM, [{"path": "/mnt/data", "ignore": True}])


def test_escaped_mount_point():
    text = mountinfo(("253:1", r"/mnt/my\040disk", "ext4", "rw"))
    assert paths(text) == ["/mnt/my disk"]


# --- 2.2 thresholds ------------------------------------------------------------


def statvfs_of(total: int, free: int, files: int = 0, ffree: int = 0, bfree=None):
    block = 4096
    return os.statvfs_result(
        (
            block,
            block,
            total // block,
            (free if bfree is None else bfree) // block,
            free // block,
            files,
            ffree,
            ffree,
            0,
            255,
        )
    )


def check(total, free, entries=(), files=0, ffree=0, path="/mnt/data"):
    limits, _ = ds.parse_limits(list(entries))
    mount = ds.Mount(path, "253:1", "ext4", False)
    return ds.check_mount(
        mount, limits.get(path), lambda _p: statvfs_of(total, free, files, ffree)
    )


def test_large_disk_with_enough_absolute_space_is_not_low():
    assert check(2048 * GIB, 60 * GIB) is None


def test_large_disk_below_both_defaults_is_low():
    low = check(500 * GIB, 12 * GIB)
    assert low and low.space_low
    assert low.text() == "/mnt/data is 98 % full (12 GiB free of 500 GiB)"


def test_small_boot_partition_is_low():
    low = check(2 * GIB, 80 * MIB, path="/boot")
    assert low and low.space_low


def test_out_of_inodes():
    low = check(100 * GIB, 50 * GIB, files=1000, ffree=20)
    assert low and low.inodes_low and not low.space_low
    assert "2.0 % free inodes" in low.text()


def test_filesystem_without_inode_counts_checks_only_space():
    assert check(100 * GIB, 50 * GIB, files=0, ffree=0) is None


def test_space_freed_is_no_longer_low():
    assert check(500 * GIB, 12 * GIB)
    assert check(500 * GIB, 40 * GIB) is None


def test_min_free_replaces_both_defaults():
    entries = [{"path": "/mnt/data", "min_free": "100G"}]
    low = check(2048 * GIB, 80 * GIB, entries)
    assert low and low.space_low
    assert check(2048 * GIB, 120 * GIB, entries) is None


def test_min_free_percent_alone():
    entries = [{"path": "/mnt/data", "min_free_percent": 3}]
    assert check(100 * GIB, 2 * GIB, entries)
    assert check(100 * GIB, 4 * GIB, entries) is None


def test_both_limits_must_be_undershot():
    entries = [{"path": "/mnt/data", "min_free": "100G", "min_free_percent": 3}]
    assert check(2048 * GIB, 80 * GIB, entries) is None  # 3.9 %
    assert check(2048 * GIB, 50 * GIB, entries)


def test_invalid_entries_warn_and_keep_defaults():
    limits, problems = ds.parse_limits(
        [{"min_free": "1G"}, {"path": "/mnt/data", "min_free": "lots"}, "x"]
    )
    assert limits == {}
    assert len(problems) == 3
    assert any("/mnt/data" in p for p in problems)


@pytest.mark.parametrize(
    "value, size",
    [
        ("100G", 100 * GIB),
        ("100GiB", 100 * GIB),
        ("1.5T", int(1.5 * 1024 * GIB)),
        ("500M", 500 * MIB),
        (1024, 1024),
    ],
)
def test_parse_size(value, size):
    assert ds.parse_size(value) == size


def test_unreadable_filesystem_is_skipped():
    def fail(_path):
        raise PermissionError

    assert ds.check_mount(ds.Mount("/x", "1:1", "ext4", False), None, fail) is None


# --- 3.x attention item and cleanup -------------------------------------------


@pytest.fixture
def disk_machine(tmp_path, monkeypatch):
    """A Machine with the VM mountinfo; `sizes` maps a mount point to (total, free)."""
    repo = tmp_path / "dotfiles"
    (repo / "home").mkdir(parents=True)
    (repo / ".git").mkdir()
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("DOTFILES_REPO", str(repo))
    monkeypatch.setenv(
        "MACHINE_APPLIED_HOST_FILE", str(home / ".local/share/machine/applied-host.yml")
    )
    monkeypatch.setenv(
        "MISE_LOCAL_CONFIG", str(home / ".config/mise/config.local.toml")
    )
    monkeypatch.setenv("MACHINE_STATE_DIR", str(home / ".local/share/machine"))
    info = tmp_path / "mountinfo"
    info.write_text(VM, encoding="utf-8")
    monkeypatch.setenv("MACHINE_MOUNTINFO", str(info))
    cli = SourceFileLoader("machine_disk", str(MACHINE)).load_module()
    monkeypatch.setattr(cli.system, "in_docker", lambda: False)
    monkeypatch.setattr(cli.system, "is_tty", lambda: False)
    machine = cli.Machine()
    machine.write_profile("work", "desktop", ["zsh-full", "docker"], [])
    sizes = {p: (100 * GIB, 50 * GIB) for p in ("/", "/boot", "/boot/efi", "/mnt/data")}

    def fake_statvfs(path):
        return statvfs_of(*sizes[path])

    monkeypatch.setattr(cli.Machine, "statvfs", staticmethod(fake_statvfs))
    return cli, machine, sizes


def test_two_low_filesystems_give_two_items(disk_machine):
    _cli, machine, sizes = disk_machine
    sizes["/"] = (200 * GIB, 6 * GIB)
    sizes["/mnt/data"] = (500 * GIB, 12 * GIB)
    items = [i for i in machine.attention_items() if i.kind == "disk"]
    assert [i.text for i in items] == [
        "/ is 97 % full (6.0 GiB free of 200 GiB)",
        "/mnt/data is 98 % full (12 GiB free of 500 GiB)",
    ]


def test_no_low_filesystem_gives_no_item(disk_machine):
    _cli, machine, _sizes = disk_machine
    assert not [i for i in machine.attention_items() if i.kind == "disk"]


def test_non_interactive_attention_lists_without_measuring(
    disk_machine, monkeypatch, capsys
):
    _cli, machine, sizes = disk_machine
    sizes["/mnt/data"] = (500 * GIB, 12 * GIB)

    def no_measuring(*_a, **_k):
        raise AssertionError("measured without a terminal")

    monkeypatch.setattr(machine, "space_users", no_measuring)
    monkeypatch.setattr(machine, "_size", no_measuring)
    assert machine.cmd_attention() == 0
    assert "[disk] /mnt/data is 98 % full" in capsys.readouterr().out


def test_host_config_limit_and_invalid_entry(disk_machine, capsys):
    _cli, machine, sizes = disk_machine
    machine.applied_host_path.write_text(
        "---\ncontext: work\ndevice: desktop\nfeatures: [zsh-full]\n"
        "disk_space:\n  - path: /mnt/data\n    min_free: 100G\n  - min_free: 1G\n",
        encoding="utf-8",
    )
    sizes["/mnt/data"] = (2048 * GIB, 80 * GIB)
    assert [low.path for low in machine.low_disks()] == ["/mnt/data"]
    assert "disk_space entry without a path" in capsys.readouterr().out


def _resolve_setup(cli, machine, monkeypatch, users, picked, scan=False):
    monkeypatch.setattr(machine, "space_users", lambda: users)
    monkeypatch.setattr(machine, "_size", lambda _p: 3 * GIB)
    monkeypatch.setattr(
        ds, "_device_of", lambda p: "253:0" if "docker" in str(p) else "253:1"
    )
    offered = {}

    def choose_many(_title, choices, selected):
        offered.update(choices)
        assert selected == []  # nothing preselected
        return picked(choices)

    ran = []
    monkeypatch.setattr(cli.system, "choose_many", choose_many)
    monkeypatch.setattr(cli.system, "prompt_yes_no", lambda *_a: scan)
    monkeypatch.setattr(cli.system, "run", lambda args, **_k: ran.append(list(args)))
    return offered, ran


def _users(cli, home):
    SU = ds.SpaceUser
    return [
        SU("Docker data", Path("/var/lib/docker"), ["docker", "system", "prune"]),
        SU(
            "systemd journal",
            Path("/mnt/data/journal"),
            ["sudo", "journalctl", "--vacuum-size=200M"],
        ),
        SU("apt cache", Path("/mnt/data/apt"), ["sudo", "apt-get", "clean"]),
        SU("~/.cache", home / ".cache", None),
    ]


def _low_data(machine, sizes):
    sizes["/mnt/data"] = (500 * GIB, 12 * GIB)
    (low,) = machine.low_disks()
    return low


def test_default_cleans_nothing(disk_machine, monkeypatch, capsys):
    cli, machine, sizes = disk_machine
    low = _low_data(machine, sizes)
    offered, ran = _resolve_setup(
        cli, machine, monkeypatch, _users(cli, machine.home), lambda _c: []
    )
    assert machine.resolve_low_disk(low) == 0
    assert ran == []
    out = capsys.readouterr().out
    assert "systemd journal" in out and "~/.cache" in out
    # Docker data is on another device; ~/.cache is only shown
    assert not any(name.startswith("Docker") for name in offered)
    assert not any(name.startswith("~/.cache") for name in offered)


def test_picked_cleanups_run_and_free_space_is_shown(disk_machine, monkeypatch, capsys):
    cli, machine, sizes = disk_machine
    low = _low_data(machine, sizes)
    _offered, ran = _resolve_setup(
        cli, machine, monkeypatch, _users(cli, machine.home), lambda c: list(c)
    )
    machine.resolve_low_disk(low)
    assert ran == [
        ["sudo", "journalctl", "--vacuum-size=200M"],
        ["sudo", "apt-get", "clean"],
    ]
    assert "/mnt/data: 12 GiB free now" in capsys.readouterr().out


def test_directory_scan_only_on_request(disk_machine, monkeypatch):
    cli, machine, sizes = disk_machine
    low = _low_data(machine, sizes)
    _offered, ran = _resolve_setup(
        cli, machine, monkeypatch, [], lambda _c: [], scan=False
    )
    machine.resolve_low_disk(low)
    assert ran == []
    scans = []
    monkeypatch.setattr(machine, "_show_biggest", lambda low: scans.append(low.path))
    monkeypatch.setattr(cli.system, "prompt_yes_no", lambda *_a: True)
    machine.resolve_low_disk(low)
    assert scans == ["/mnt/data"]


def test_docker_is_offered_only_with_the_feature(disk_machine, monkeypatch):
    cli, machine, _sizes = disk_machine
    monkeypatch.setattr(cli.system, "have", lambda name: name == "docker")

    class Result:
        returncode = 0
        stdout = "/var/lib/docker\n"

    monkeypatch.setattr(cli.system, "run", lambda *_a, **_k: Result())
    assert "Docker data" in [u.name for u in machine.space_users()]
    machine.write_profile("work", "desktop", ["zsh-full"], [])
    assert "Docker data" not in [u.name for u in machine.space_users()]
    assert all(u.clean is None for u in machine.space_users() if u.name == "~/.cache")


# --- 4.1 recorded state --------------------------------------------------------


def _state(machine) -> dict:
    lines = machine.disk_state_file.read_text(encoding="utf-8").splitlines()
    return dict(line.split("=", 1) for line in lines)


def test_record_names_all_low_mounts(disk_machine):
    _cli, machine, sizes = disk_machine
    sizes["/"] = (200 * GIB, 6 * GIB)
    sizes["/mnt/data"] = (500 * GIB, 12 * GIB)
    assert machine.cmd_disk(record=True) == 0
    assert machine.disk_state_file == machine.state_dir / "disk-state"
    assert _state(machine) == {
        "segment": "⚠ disk / 97%, /mnt/data 98%",
        "mounts": "/ /mnt/data",
    }


def test_record_without_low_mount_is_empty(disk_machine):
    _cli, machine, sizes = disk_machine
    sizes["/mnt/data"] = (500 * GIB, 12 * GIB)
    machine.record_disk_state()
    sizes["/mnt/data"] = (500 * GIB, 100 * GIB)
    machine.record_disk_state()
    assert _state(machine) == {"segment": "", "mounts": ""}


def test_failed_record_does_not_fail(disk_machine, monkeypatch, tmp_path):
    _cli, machine, _sizes = disk_machine
    blocker = tmp_path / "file"
    blocker.write_text("", encoding="utf-8")
    monkeypatch.setenv("MACHINE_DISK_STATE", str(blocker / "disk-state"))
    machine.record_disk_state()  # no exception
    assert machine.cmd_disk(record=True) == 0


def test_every_command_records_the_state(tmp_path):
    import subprocess

    home = tmp_path / "home"
    home.mkdir()
    state = tmp_path / "disk-state"
    env = {
        **os.environ,
        "HOME": str(home),
        "DOTFILES_REPO": str(REPO),
        "MACHINE_STATE_DIR": str(home / ".local/share/machine"),
        "MACHINE_DISK_STATE": str(state),
        "MACHINE_MOUNTINFO": os.devnull,
    }
    subprocess.run(
        ["python3", str(MACHINE), "commit", "--help"],
        env=env,
        check=True,
        capture_output=True,
    )
    assert state.read_text(encoding="utf-8") == "segment=\nmounts=\n"


# --- 4.2 timer -----------------------------------------------------------------


def test_timer_units_run_the_record_every_15_minutes():
    units = REPO / "home/systemd/.config/systemd/user"
    timer = (units / "machine-disk-check.timer").read_text(encoding="utf-8")
    service = (units / "machine-disk-check.service").read_text(encoding="utf-8")
    assert "OnUnitActiveSec=15min" in timer
    assert "Unit=machine-disk-check.service" in timer
    assert "ExecStart=%h/.local/bin/machine disk --record" in service


def test_both_timers_are_enabled(disk_machine, monkeypatch):
    cli, machine, _sizes = disk_machine
    units = machine.home / ".config/systemd/user"
    units.mkdir(parents=True)
    for name in ("dotfiles-update-check.timer", "machine-disk-check.timer"):
        (units / name).write_text("", encoding="utf-8")
    ran = []
    monkeypatch.setattr(cli.system, "have", lambda name: name == "systemctl")
    monkeypatch.setattr(cli.system, "run", lambda args, **_k: ran.append(list(args)))
    monkeypatch.setattr(machine, "ensure_linger", lambda: None)
    machine.ensure_update_timer()
    assert ["systemctl", "--user", "enable", "--now", "machine-disk-check.timer"] in ran
    assert [
        "systemctl",
        "--user",
        "enable",
        "--now",
        "dotfiles-update-check.timer",
    ] in ran
