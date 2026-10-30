"""Low disk space: watched filesystems, thresholds, cleanups and the recorded state."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from . import system
from .core import log, warn


MOUNTINFO = Path("/proc/self/mountinfo")
# Local block filesystems; tmpfs, overlay, squashfs and network mounts stay out.
WATCHED_TYPES = {"ext4", "xfs", "btrfs", "vfat"}
GIB = 1024**3
# Low when below both: large disks are judged by the amount, small ones by the share.
DEFAULT_MIN_FREE = 20 * GIB
DEFAULT_MIN_FREE_PERCENT = 5.0
MIN_FREE_INODES_PERCENT = 5.0
SIZE_UNITS = {"": 1, "K": 1024, "M": 1024**2, "G": GIB, "T": 1024**4}


@dataclass
class Mount:
    path: str
    device: str  # major:minor
    fstype: str
    read_only: bool


@dataclass
class Limit:
    min_free: Optional[int] = None
    min_free_percent: Optional[float] = None
    ignore: bool = False


@dataclass
class LowDisk:
    path: str
    device: str
    total: int
    free: int  # available to the user, without the root reserve
    used_percent: int
    space_low: bool
    inodes_free_percent: Optional[float]  # None: no inode counts (vfat, btrfs)
    inodes_low: bool

    def text(self) -> str:
        parts = []
        if self.space_low:
            parts.append(
                f"{self.path} is {self.used_percent} % full "
                f"({format_size(self.free)} free of {format_size(self.total)})"
            )
        if self.inodes_low:
            inodes = f"{self.inodes_free_percent:.1f} % free inodes"
            parts.append(
                f"{self.path} has only {inodes}" if not parts else f"only {inodes}"
            )
        return ", ".join(parts)

    def short(self) -> str:
        return (
            f"{self.path} {self.used_percent}%"
            if self.space_low
            else f"{self.path} inodes"
        )


def format_size(size: float) -> str:
    for unit, factor in (("TiB", 1024**4), ("GiB", GIB), ("MiB", 1024**2)):
        if size >= factor:
            value = size / factor
            return f"{value:.0f} {unit}" if value >= 10 else f"{value:.1f} {unit}"
    return f"{size / 1024:.0f} KiB"


def parse_size(value: object) -> int:
    """`100G`, `500M`, `1.5T`, `100GiB` or a plain number of bytes."""
    if isinstance(value, bool):
        raise ValueError(value)
    if isinstance(value, (int, float)):
        return int(value)
    match = re.fullmatch(r"\s*([0-9.]+)\s*([KMGT]?)(?:i?B)?\s*", str(value), re.I)
    if not match:
        raise ValueError(value)
    return int(float(match.group(1)) * SIZE_UNITS[match.group(2).upper()])


def parse_limits(entries: Sequence[object]) -> Tuple[Dict[str, Limit], List[str]]:
    """The `disk_space` entries of the host config by mount point, and warnings."""
    limits: Dict[str, Limit] = {}
    problems: List[str] = []
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get("path"):
            problems.append(f"disk_space entry without a path: {entry!r}")
            continue
        path = os.path.normpath(str(entry["path"]))
        try:
            limit = Limit(ignore=entry.get("ignore") is True)
            if entry.get("min_free") is not None:
                limit.min_free = parse_size(entry["min_free"])
            if entry.get("min_free_percent") is not None:
                limit.min_free_percent = float(entry["min_free_percent"])
        except (TypeError, ValueError):
            problems.append(f"disk_space entry for {path} has an unreadable limit")
            continue
        limits[path] = limit
    return limits, problems


def _unescape(field: str) -> str:
    # mountinfo writes space, tab, newline and backslash as \ooo
    return re.sub(r"\\([0-7]{3})", lambda m: chr(int(m.group(1), 8)), field)


def parse_mountinfo(text: str) -> List[Mount]:
    mounts = []
    for line in text.splitlines():
        fields = line.split()
        if "-" not in fields:
            continue
        sep = fields.index("-")
        if sep < 6 or len(fields) < sep + 3:
            continue
        options = fields[5].split(",") + fields[sep + 3].split(",")[:1]
        mounts.append(
            Mount(
                path=_unescape(fields[4]),
                device=fields[2],
                fstype=fields[sep + 1],
                read_only="ro" in options,
            )
        )
    return mounts


def watched_mounts(mounts: Sequence[Mount], limits: Dict[str, Limit]) -> List[Mount]:
    """One read-write mount per device: the listed types, plus mount points named
    in `disk_space`. A named mount point wins over the shortest one of its device."""
    by_device: Dict[str, Mount] = {}
    for mount in mounts:
        if mount.read_only:
            continue
        named = mount.path in limits
        if mount.fstype not in WATCHED_TYPES and not named:
            continue
        current = by_device.get(mount.device)
        if current is None:
            by_device[mount.device] = mount
        elif current.path not in limits and (
            named or (len(mount.path), mount.path) < (len(current.path), current.path)
        ):
            by_device[mount.device] = mount
    ignored = {
        mount.device
        for mount in mounts
        if mount.path in limits and limits[mount.path].ignore
    }
    return sorted(
        (m for m in by_device.values() if m.device not in ignored),
        key=lambda m: m.path,
    )


def check_mount(
    mount: Mount,
    limit: Optional[Limit],
    statvfs: Callable[[str], os.statvfs_result] = os.statvfs,
) -> Optional[LowDisk]:
    """The current values of one filesystem; None when it is not low or unreadable."""
    try:
        st = statvfs(mount.path)
    except OSError:
        return None
    total = st.f_blocks * st.f_frsize
    if total <= 0:
        return None
    free = st.f_bavail * st.f_frsize
    used = (st.f_blocks - st.f_bfree) * st.f_frsize
    used_percent = -(-100 * used // (used + free)) if used + free else 100
    free_percent = 100.0 * free / total
    if limit and (limit.min_free is not None or limit.min_free_percent is not None):
        # thresholds of the host config replace both defaults
        space_low = all(
            below
            for below in (
                limit.min_free is None or free < limit.min_free,
                limit.min_free_percent is None or free_percent < limit.min_free_percent,
            )
        )
    else:
        space_low = free_percent < DEFAULT_MIN_FREE_PERCENT and free < DEFAULT_MIN_FREE
    inodes_free = 100.0 * st.f_favail / st.f_files if st.f_files > 0 else None
    inodes_low = inodes_free is not None and inodes_free < MIN_FREE_INODES_PERCENT
    if not space_low and not inodes_low:
        return None
    return LowDisk(
        mount.path,
        mount.device,
        total,
        free,
        int(used_percent),
        space_low,
        inodes_free,
        inodes_low,
    )


def segment_text(lows: Sequence[LowDisk]) -> str:
    return "⚠ disk " + ", ".join(low.short() for low in lows) if lows else ""


def _device_of(path: Path) -> Optional[str]:
    try:
        st = os.stat(path)
    except OSError:
        return None
    return f"{os.major(st.st_dev)}:{os.minor(st.st_dev)}"


@dataclass
class SpaceUser:
    name: str
    path: Path
    clean: Optional[List[str]]  # None: shown with its size only


class DiskSpaceMixin:
    statvfs = staticmethod(os.statvfs)

    @property
    def mountinfo_path(self) -> Path:
        return Path(os.environ.get("MACHINE_MOUNTINFO", MOUNTINFO))

    @property
    def disk_state_file(self) -> Path:
        return Path(os.environ.get("MACHINE_DISK_STATE", self.state_dir / "disk-state"))

    def low_disks(self, quiet: bool = False) -> List[LowDisk]:
        """The watched filesystems that are low right now."""
        limits, problems = parse_limits(self.applied_host()["disk_space"])
        if not quiet:
            for problem in problems:
                warn(problem + " (the defaults apply)")
        try:
            text = self.mountinfo_path.read_text(encoding="utf-8")
        except OSError:
            return []
        lows = []
        for mount in watched_mounts(parse_mountinfo(text), limits):
            low = check_mount(mount, limits.get(mount.path), type(self).statvfs)
            if low:
                lows.append(low)
        return lows

    def record_disk_state(self, lows: Optional[Sequence[LowDisk]] = None) -> None:
        """Write the state the prompt reads; best effort, never fails a command."""
        try:
            if lows is None:
                lows = self.low_disks(quiet=True)
            path = self.disk_state_file
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(path.name + f".{os.getpid()}")
            tmp.write_text(
                f"segment={segment_text(lows)}\n"
                f"mounts={' '.join(low.path for low in lows)}\n",
                encoding="utf-8",
            )
            os.replace(tmp, path)
        except Exception as exc:  # noqa: BLE001 - the prompt state is optional
            log(f"could not record the disk state: {exc}")

    def cmd_disk(self, record: bool = False) -> int:
        lows = self.low_disks(quiet=record)
        self.record_disk_state(lows)
        if not record:
            for low in lows:
                print(low.text())
            if not lows:
                print("No filesystem is low on space.")
        return 0

    # --- guided cleanup ---------------------------------------------------------

    def _docker_root(self) -> Optional[Path]:
        if "docker" not in self.saved_features() or not system.have("docker"):
            return None
        result = system.run(
            ["docker", "info", "-f", "{{.DockerRootDir}}"], check=False, capture=True
        )
        root = (result.stdout or "").strip()
        return Path(root) if result.returncode == 0 and root else None

    def space_users(self) -> List[SpaceUser]:
        users = []
        docker = self._docker_root()
        if docker:
            users.append(
                SpaceUser("Docker data", docker, ["docker", "system", "prune"])
            )
        users.append(
            SpaceUser(
                "systemd journal",
                Path("/var/log/journal"),
                ["sudo", "journalctl", "--vacuum-size=200M"],
            )
        )
        users.append(
            SpaceUser(
                "apt cache",
                Path("/var/cache/apt/archives"),
                ["sudo", "apt-get", "clean"],
            )
        )
        if system.have("mise"):
            result = system.run(["mise", "cache", "path"], check=False, capture=True)
            cache = (result.stdout or "").strip()
            if result.returncode == 0 and cache:
                users.append(
                    SpaceUser("mise cache", Path(cache), ["mise", "cache", "clear"])
                )
        users.append(SpaceUser("~/.cache", self.home / ".cache", None))
        return users

    def _size(self, path: Path) -> Optional[int]:
        result = system.run(
            ["du", "-sxb", str(path)], check=False, capture=True
        )  # unreadable parts are left out, so the size is a lower bound
        try:
            return int((result.stdout or "").split()[0])
        except (IndexError, ValueError):
            return None

    def _show_biggest(self, low: LowDisk) -> None:
        du = ["du", "-xh", "-d", "2", low.path]
        if os.geteuid() != 0:
            du = ["sudo", *du]
        result = system.run(du, check=False, capture=True)
        lines = (result.stdout or "").splitlines()
        sort = system.run(
            ["sort", "-h"], check=False, capture=True, input_text="\n".join(lines)
        )
        print("\n".join((sort.stdout or "").splitlines()[-20:]))

    def resolve_low_disk(self, low: LowDisk) -> int:
        """Show the known space users on this filesystem and clean what the user picks."""
        users = [u for u in self.space_users() if _device_of(u.path) == low.device]
        if users:
            print(f"Known space users on {low.path}:")
        offered: Dict[str, SpaceUser] = {}
        for user in users:
            size = self._size(user.path)
            label = f"{user.name} ({format_size(size) if size is not None else '?'})"
            print(f"  {label:40} {user.path}")
            if user.clean:
                offered[label] = user
        if offered:
            picked = system.choose_many(
                "Clean up (none = nothing)",
                {name: " ".join(user.clean or []) for name, user in offered.items()},
                [],
            )
            for name in picked:
                system.run(offered[name].clean or [], check=False)
            if picked:
                print(f"{low.path}: {format_size(self._free(low.path))} free now")
        if system.prompt_yes_no(
            f"Show the biggest directories on {low.path} (du, slow)?", False
        ):
            self._show_biggest(low)
        return 0

    def _free(self, path: str) -> int:
        try:
            st = type(self).statvfs(path)
        except OSError:
            return 0
        return st.f_bavail * st.f_frsize
