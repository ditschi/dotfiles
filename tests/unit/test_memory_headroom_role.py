"""memory_headroom role: oomd drop-ins and fstab entry without root; no swap change."""

from __future__ import annotations

import json
import os
import shutil
import subprocess

import pytest

from package_sets import ANSIBLE

ROLE = ANSIBLE / "roles/memory_headroom"

pytestmark = pytest.mark.skipif(
    not shutil.which("ansible-playbook"), reason="ansible-playbook not installed"
)


@pytest.fixture
def apply_role(tmp_path):
    """Run the role on localhost with paths under tmp_path and services off."""
    etc = tmp_path / "etc"
    etc.mkdir()
    (etc / "fstab").write_text("UUID=1234 / ext4 defaults 0 1\n")
    playbook = tmp_path / "play.yml"
    playbook.write_text(
        json.dumps(
            [
                {
                    "hosts": "localhost",
                    "connection": "local",
                    "gather_facts": False,
                    "vars": {
                        "machine_manage_services": False,
                        "machine_lib_dir": str(tmp_path / "lib"),
                        "memory_headroom_swapfile": str(tmp_path / "swap.img"),
                        "memory_headroom_fstab": str(etc / "fstab"),
                        "memory_headroom_oomd_dropin": str(
                            etc / "user@.service.d/90-oomd-limit.conf"
                        ),
                        "memory_headroom_oomd_swap_dropin": str(
                            etc / "-.slice.d/90-oomd-no-swap-kill.conf"
                        ),
                    },
                    "roles": [{"role": str(ROLE)}],
                }
            ]
        ),
        encoding="utf-8",
    )

    def run() -> str:
        result = subprocess.run(
            ["ansible-playbook", "-i", "localhost,", str(playbook)],
            env={**os.environ, "ANSIBLE_NOCOLOR": "1"},
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return result.stdout

    return tmp_path, run


def _settings(path) -> list[str]:
    return [
        line
        for line in path.read_text().splitlines()
        if line and not line.startswith("#")
    ]


def test_role_writes_oomd_dropins_and_fstab_without_touching_swap(apply_role):
    tmp_path, run = apply_role
    swap = tmp_path / "swap.img"
    swap.write_bytes(b"")
    run()
    etc = tmp_path / "etc"

    assert _settings(etc / "user@.service.d/90-oomd-limit.conf") == [
        "[Service]",
        "ManagedOOMMemoryPressureLimit=80%",
    ]
    assert _settings(etc / "-.slice.d/90-oomd-no-swap-kill.conf") == [
        "[Slice]",
        "ManagedOOMSwap=auto",
    ]
    for dropin in etc.glob("*.d/*.conf"):
        assert oct(dropin.stat().st_mode & 0o777) == "0o644"
    assert f"{swap}\tnone\tswap\tsw\t0\t0" in (etc / "fstab").read_text().splitlines()
    assert (etc / "fstab").read_text().startswith("UUID=1234 / ext4")
    # Without managed services the swap script is installed but never run.
    assert (tmp_path / "lib/swapfile-grow").exists()
    assert swap.stat().st_size == 0


def test_no_fstab_entry_without_a_swap_file(apply_role):
    tmp_path, run = apply_role
    run()
    assert (tmp_path / "etc/fstab").read_text() == "UUID=1234 / ext4 defaults 0 1\n"
    assert not (tmp_path / "swap.img").exists()


def test_second_run_changes_nothing(apply_role):
    tmp_path, run = apply_role
    (tmp_path / "swap.img").write_bytes(b"")
    run()
    assert "changed=0" in run()


def test_existing_fstab_entry_is_kept(apply_role):
    tmp_path, run = apply_role
    swap = tmp_path / "swap.img"
    swap.write_bytes(b"")
    fstab = tmp_path / "etc/fstab"
    fstab.write_text(f"{swap}  none  swap  sw,pri=-1  0  0\n")
    run()
    assert fstab.read_text() == f"{swap}  none  swap  sw,pri=-1  0  0\n"
