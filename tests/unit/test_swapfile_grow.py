"""swapfile-grow against a fake /proc/swaps and stub swap, disk and filesystem commands."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from package_sets import ANSIBLE

SCRIPT = ANSIBLE / "roles/memory_headroom/files/swapfile-grow"
GIB = 1024**3
CHANGED = 3


def _stub(bin_dir: Path, name: str, body: str = "") -> None:
    stub = bin_dir / name
    stub.write_text(
        "#!/bin/sh\n"
        f'echo "{name} $*" >>"{bin_dir}/calls"\n'
        f'if [ -n "$FAIL_{name.upper()}" ]; then exit 1; fi\n' + body
    )
    stub.chmod(0o755)


def _env(
    tmp_path: Path,
    *,
    swaps: str = "",
    fstype: str = "ext4",
    avail_gib: int = 200,
    size_gib: int = 500,
    mem_available_gib: int = 8,
) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    # fallocate -l <bytes> <file> / dd ... of=<file>: create a sparse file of that size.
    _stub(bin_dir, "fallocate", 'truncate -s "$2" "$3"\n')
    _stub(
        bin_dir,
        "dd",
        'for a; do case "$a" in of=*) f="${a#of=}";; seek=*) s="${a#seek=}";;'
        ' count=*) c="${a#count=}";; esac; done\n'
        'truncate -s "$(( (s + c) * 1024 * 1024 ))" "$f"\n',
    )
    swaps_file = tmp_path / "swaps"
    _stub(bin_dir, "mkswap")
    # swapon/swapoff update the fake /proc/swaps like the kernel does.
    _stub(
        bin_dir,
        "swapon",
        'for f; do :; done; p=-1; [ "$1" = -p ] && p=$2\n'
        f'printf "%s\\tfile\\t0\\t0\\t%s\\n" "$f" "$p" >>"{swaps_file}"\n',
    )
    _stub(
        bin_dir,
        "swapoff",
        f'awk -v f="$1" \'$1 != f\' "{swaps_file}" >"{swaps_file}.tmp"'
        f' && mv "{swaps_file}.tmp" "{swaps_file}"\n',
    )
    _stub(bin_dir, "blkid", 'echo "${BLKID_TYPE-swap}"\n')
    _stub(bin_dir, "findmnt", f'echo "{fstype}"\n')
    _stub(bin_dir, "df", f'echo "{avail_gib * GIB} {size_gib * GIB}"\n')
    (tmp_path / "meminfo").write_text(
        f"MemTotal:       15508476 kB\nMemAvailable:   {mem_available_gib * 1024 * 1024} kB\n"
    )
    (tmp_path / "swaps").write_text(
        "Filename\t\t\t\tType\t\tSize\t\tUsed\t\tPriority\n" + swaps
    )
    return bin_dir


def _run(tmp_path: Path, path: Path, size_gib: int = 16, **env: str):
    return subprocess.run(
        ["bash", str(SCRIPT), str(path), str(size_gib), "20"],
        env={
            **os.environ,
            "PATH": f"{tmp_path / 'bin'}:{os.environ['PATH']}",
            "SWAPFILE_GROW_PROC_SWAPS": str(tmp_path / "swaps"),
            "SWAPFILE_GROW_PROC_MEMINFO": str(tmp_path / "meminfo"),
            **env,
        },
        capture_output=True,
        text=True,
    )


def _calls(bin_dir: Path) -> list[str]:
    log = bin_dir / "calls"
    lines = log.read_text().splitlines() if log.exists() else []
    return [c for c in lines if c.split()[0] not in ("findmnt", "df", "blkid")]


def _active(path: Path, size_gib: int, priority: int = -2, used_gib: int = 0) -> str:
    kib = 1024 * 1024
    return f"{path}\tfile\t\t{size_gib * kib}\t\t{used_gib * kib}\t\t{priority}\n"


def _swap_file(tmp_path: Path, size_gib: int) -> Path:
    swap = tmp_path / "swap.img"
    swap.touch()
    os.truncate(swap, size_gib * GIB)
    return swap


def test_grows_the_active_file_in_place(tmp_path):
    swap = _swap_file(tmp_path, 4)
    bin_dir = _env(tmp_path, swaps=_active(swap, 4, -1, used_gib=3))

    result = _run(tmp_path, swap)

    assert result.returncode == CHANGED, result.stdout + result.stderr
    assert _calls(bin_dir) == [
        f"swapoff {swap}",
        f"fallocate -l {16 * GIB} {swap}",
        f"mkswap {swap}",
        f"swapon -p -1 {swap}",
    ]
    assert swap.stat().st_size == 16 * GIB
    assert oct(swap.stat().st_mode & 0o777) == "0o600"
    assert f"path={swap}" in result.stdout


def test_kernel_assigned_priority_is_left_to_the_kernel(tmp_path):
    swap = _swap_file(tmp_path, 4)
    bin_dir = _env(tmp_path, swaps=_active(swap, 4, -2))

    assert _run(tmp_path, swap).returncode == CHANGED
    assert _calls(bin_dir)[-1] == f"swapon {swap}"


def test_too_little_free_ram_skips_with_a_warning(tmp_path):
    swap = _swap_file(tmp_path, 4)
    # 3 GiB used + 2 GiB reserve > 4 GiB available.
    bin_dir = _env(
        tmp_path, swaps=_active(swap, 4, -1, used_gib=3), mem_available_gib=4
    )

    result = _run(tmp_path, swap)

    assert result.returncode == 0, result.stdout + result.stderr
    assert _calls(bin_dir) == []
    assert "WARNING" in result.stdout and "free RAM" in result.stdout
    assert f"sudo swapoff {swap}" in result.stdout


def test_large_enough_file_is_left_alone(tmp_path):
    swap = _swap_file(tmp_path, 16)
    bin_dir = _env(tmp_path, swaps=_active(swap, 16))

    result = _run(tmp_path, swap)

    assert result.returncode == 0, result.stdout + result.stderr
    assert _calls(bin_dir) == []
    assert f"path={swap}" in result.stdout


def test_too_little_free_space_skips_with_a_warning(tmp_path):
    swap = _swap_file(tmp_path, 4)
    # 22 GiB free - 12 GiB growth = 10 GiB left, below the 20 GiB minimum.
    bin_dir = _env(tmp_path, swaps=_active(swap, 4), avail_gib=22)

    result = _run(tmp_path, swap)

    assert result.returncode == 0, result.stdout + result.stderr
    assert _calls(bin_dir) == []
    assert "WARNING" in result.stdout and "10 GiB" in result.stdout
    assert swap.stat().st_size == 4 * GIB


def test_five_percent_of_a_large_disk_must_stay_free(tmp_path):
    swap = _swap_file(tmp_path, 4)
    # 2000 GiB disk: 5 % is 100 GiB; 110 GiB free - 12 GiB growth = 98 GiB left.
    bin_dir = _env(tmp_path, swaps=_active(swap, 4), avail_gib=110, size_gib=2000)

    result = _run(tmp_path, swap)

    assert result.returncode == 0 and _calls(bin_dir) == []
    assert "WARNING" in result.stdout and "5 %" in result.stdout


def test_btrfs_skips_with_a_warning(tmp_path):
    swap = _swap_file(tmp_path, 4)
    bin_dir = _env(tmp_path, swaps=_active(swap, 4), fstype="btrfs")

    result = _run(tmp_path, swap)

    assert result.returncode == 0, result.stdout + result.stderr
    assert _calls(bin_dir) == []
    assert "WARNING" in result.stdout and "btrfs" in result.stdout


def test_failed_swapoff_changes_nothing(tmp_path):
    swap = _swap_file(tmp_path, 4)
    bin_dir = _env(tmp_path, swaps=_active(swap, 4, -1))

    result = _run(tmp_path, swap, FAIL_SWAPOFF="1")

    assert result.returncode == 1
    assert _calls(bin_dir) == [f"swapoff {swap}"]
    assert swap.stat().st_size == 4 * GIB
    assert "by hand" in result.stderr


def test_failed_mkswap_turns_the_old_file_on_again(tmp_path):
    swap = _swap_file(tmp_path, 4)
    bin_dir = _env(tmp_path, swaps=_active(swap, 4, -1))

    result = _run(tmp_path, swap, FAIL_MKSWAP="1")

    assert result.returncode == 1
    assert _calls(bin_dir)[-1] == f"swapon -p -1 {swap}"
    assert "mkswap" in result.stderr


def test_failed_swapon_is_reported(tmp_path):
    swap = _swap_file(tmp_path, 4)
    _env(tmp_path, swaps=_active(swap, 4, -1))

    result = _run(tmp_path, swap, FAIL_SWAPON="1")

    assert result.returncode == 1
    assert "could not be turned on again" in result.stderr


def test_failed_mkswap_removes_a_file_this_run_created(tmp_path):
    swap = tmp_path / "swap.img"
    _env(tmp_path)

    result = _run(tmp_path, swap, FAIL_MKSWAP="1")

    assert result.returncode == 1
    assert not swap.exists()


def test_leftover_full_size_file_without_signature_is_formatted(tmp_path):
    swap = _swap_file(tmp_path, 16)
    bin_dir = _env(tmp_path)

    result = _run(tmp_path, swap, BLKID_TYPE="")

    assert result.returncode == CHANGED, result.stdout + result.stderr
    assert _calls(bin_dir) == [f"mkswap {swap}", f"swapon -p -1 {swap}"]


def test_inactive_full_size_swap_file_is_left_alone(tmp_path):
    swap = _swap_file(tmp_path, 16)
    bin_dir = _env(tmp_path)

    assert _run(tmp_path, swap).returncode == 0
    assert _calls(bin_dir) == []


def test_interrupted_run_turns_the_file_on_again(tmp_path):
    swap = _swap_file(tmp_path, 4)
    bin_dir = _env(tmp_path, swaps=_active(swap, 4, -1))
    # mkswap sends TERM to the script (its parent) and then fails.
    (bin_dir / "mkswap").write_text(
        f'#!/bin/sh\necho "mkswap $*" >>"{bin_dir}/calls"\nkill -TERM $PPID\nexit 1\n'
    )

    result = _run(tmp_path, swap)

    assert result.returncode == 1
    assert "interrupted run" in result.stderr
    assert _calls(bin_dir)[-1] == f"swapon -p -1 {swap}"


def test_dd_fallback_rounds_up_to_the_target(tmp_path):
    swap = tmp_path / "swap.img"
    swap.touch()
    os.truncate(swap, 4 * GIB + 1000)  # not a whole MiB
    _env(tmp_path, swaps=_active(swap, 4, -1))

    result = _run(tmp_path, swap, FAIL_FALLOCATE="1")

    assert result.returncode == CHANGED, result.stdout + result.stderr
    assert swap.stat().st_size >= 16 * GIB


def test_fallocate_unsupported_appends_with_dd(tmp_path):
    swap = _swap_file(tmp_path, 4)
    bin_dir = _env(tmp_path, swaps=_active(swap, 4, -1))

    result = _run(tmp_path, swap, FAIL_FALLOCATE="1")

    assert result.returncode == CHANGED, result.stdout + result.stderr
    dd = [c for c in _calls(bin_dir) if c.startswith("dd ")][0]
    assert f"of={swap}" in dd and "seek=4096" in dd and "count=12288" in dd
    assert "conv=notrunc" in dd
    assert swap.stat().st_size == 16 * GIB


def test_without_an_active_swap_file_the_configured_path_is_created(tmp_path):
    swap = tmp_path / "swap.img"
    bin_dir = _env(tmp_path, swaps="/dev/zram0\tpartition\t7753724\t0\t100\n")

    result = _run(tmp_path, swap)

    assert result.returncode == CHANGED, result.stdout + result.stderr
    assert _calls(bin_dir) == [
        f"fallocate -l {16 * GIB} {swap}",
        f"mkswap {swap}",
        f"swapon -p -1 {swap}",
    ]
    assert swap.stat().st_size == 16 * GIB
    assert oct(swap.stat().st_mode & 0o777) == "0o600"


def test_the_one_active_swap_file_wins_over_the_configured_path(tmp_path):
    other = tmp_path / "swapfile"
    other.touch()
    os.truncate(other, 16 * GIB)
    bin_dir = _env(tmp_path, swaps=_active(other, 16))

    result = _run(tmp_path, tmp_path / "swap.img")

    assert result.returncode == 0 and _calls(bin_dir) == []
    assert f"path={other}" in result.stdout
    assert not (tmp_path / "swap.img").exists()


def test_with_several_active_files_only_the_configured_one_is_touched(tmp_path):
    swap = _swap_file(tmp_path, 4)
    other = tmp_path / "swapfile"
    swaps = _active(swap, 4, -1) + _active(other, 2, -3)
    bin_dir = _env(tmp_path, swaps=swaps)

    result = _run(tmp_path, swap)

    assert result.returncode == CHANGED, result.stdout + result.stderr
    calls = _calls(bin_dir)
    assert calls[0] == f"swapoff {swap}" and f"swapoff {other}" not in calls
