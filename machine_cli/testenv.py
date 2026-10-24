"""Throwaway test environment: the real $HOME in a container, behind an overlay.

The host home is bind-mounted read-only as the lower layer of an overlay; every
write inside the container goes to an upper layer on a Docker volume, so
`machine update` and friends can run against the real dotfiles state without
changing it. The volume is removed on exit unless --keep NAME is given.

Standard library only: it also runs straight from a checkout, before the
`machine` CLI on the host is fixed or updated:

    python3 machine_cli/testenv.py [--diff] [--keep NAME] [-- COMMAND...]
"""

from __future__ import annotations

import argparse
import hashlib
import os
import pwd
import shlex
import shutil
import socket
import subprocess
import sys
from pathlib import Path

IMAGE_PREFIX = "machine-testenv"
VOLUME_PREFIX = "machine-testenv-"
LOWER = "/testenv/lower"
RW = "/testenv/rw"
# Paths --diff summarises as a count instead of listing every file.
DIFF_NOISE = (
    ".cache",
    ".local/share/antidote",
    ".local/share/docker",
    ".local/share/mise",
    ".local/state",
    ".npm",
    "dotfiles/.git",
)

PACKAGES = (
    "bash ca-certificates curl file fuse-overlayfs git less locales openssh-client "
    "procps python3 sudo tzdata unzip util-linux xz-utils zsh"
)

# Rootless Docker maps container uid 0 to the host user, so the bind-mounted
# home is owned by uid 0 inside. The user then *is* uid 0: a passwd entry with
# the user's name and home placed before `root` makes whoami, ~ and getpwuid
# report the user. Rootful Docker gets a normal user with the host uid/gid.
DOCKERFILE = """\
FROM {base}
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \\
 && apt-get install -y --no-install-recommends {packages} \\
 && rm -rf /var/lib/apt/lists/* \\
 && (locale-gen {locale} en_US.UTF-8 || true)
RUN set -e; \\
    if [ "{rootless}" = 1 ]; then \\
        sed -i '/^{user}:/d' /etc/passwd /etc/shadow; \\
        sed -i '1i {user}:x:0:0:{user}:{home}:{shell}' /etc/passwd; \\
        sed -i '1i {user}:!:20000:0:99999:7:::' /etc/shadow; \\
    else \\
        for u in $(getent passwd {uid} | cut -d: -f1); do userdel "$u"; done; \\
        getent group {gid} >/dev/null || groupadd -g {gid} {user}; \\
        useradd -M -d {home} -s {shell} -u {uid} -g {gid} -G sudo {user}; \\
    fi; \\
    echo '{user} ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/testenv; \\
    mkdir -p {home}
"""

# Runs as container root: mount the overlay,
# run the command as the user, optionally list what changed.
ENTRY = r"""
set -eu
home=$1 uid=$2 gid=$3 diff=$4 noise=$5; shift 5
if [ ! -d "$RW/upper" ]; then
  # The overlay root takes owner and mode from the upper dir: match the home.
  mkdir -p "$RW/upper" "$RW/work"
  chown "$(stat -c %u:%g "$LOWER")" "$RW/upper"
  chmod "$(stat -c %a "$LOWER")" "$RW/upper"
fi
opts="lowerdir=$LOWER,upperdir=$RW/upper,workdir=$RW/work"
# Rootless: host ids other than the user's own are unmapped here; squash them
# so copy-up never has to chown to an id the container cannot represent.
# Rootful: the user is not the mounting root, so it needs allow_other.
if [ "$uid" = 0 ]; then opts="$opts,squash_to_root"; else opts="$opts,allow_other"; fi
if ! fuse-overlayfs -o "$opts" "$home" 2>/tmp/mount.err; then
  echo "testenv: cannot mount the overlay on $home: $(cat /tmp/mount.err)" >&2
  exit 125
fi
# SYS_ADMIN was only needed for the mount: dropping it from the bounding set
# keeps the command (even via sudo) from remounting the host home read-write.
as_user() {
  if [ "$uid" = 0 ]; then
    setpriv --bounding-set -sys_admin "$@"
  else
    setpriv --bounding-set -sys_admin --reuid "$uid" --regid "$gid" --init-groups "$@"
  fi
}
cd "$home"
set +e
as_user "$@"
rc=$?
set -e
if [ "$diff" = 1 ]; then
  echo "testenv: changes in $home (D = deleted):" >&2
  (cd "$RW/upper" && find . -mindepth 1 \( -name '.wh..wh..opq' -o -name '.wh..opq' \) -prune -o \
      \( -type c -o -name '.wh.*' \) -printf 'D %P\n' -o ! -type d ! -type s -printf 'M %P\n') \
    | sed 's|\.wh\.||' | sort -k2 >/tmp/changes
  grep -v -E " ($noise)/" /tmp/changes >&2 || true
  for dir in $(echo "$noise" | tr '|' ' '); do
    n=$(grep -c " $dir/" /tmp/changes || true)
    [ "$n" = 0 ] || echo "… $n under $(echo "$dir" | tr -d '\\')/" >&2
  done
fi
exit $rc
"""


def die(message: str, code: int = 1) -> None:
    print(f"testenv: {message}", file=sys.stderr)
    raise SystemExit(code)


def docker(*args: str, capture: bool = False, check: bool = True, **kw):
    cmd = ["docker", *args]
    if capture:
        return subprocess.run(cmd, check=check, text=True, capture_output=True, **kw)
    return subprocess.run(cmd, check=check, **kw)


def docker_rootless() -> bool:
    out = docker("info", "--format", "{{json .SecurityOptions}}", capture=True)
    return "rootless" in out.stdout


def os_release() -> tuple[str, str]:
    data = {}
    for line in Path("/etc/os-release").read_text().splitlines():
        key, _, value = line.partition("=")
        data[key] = value.strip('"')
    return data.get("ID", "ubuntu"), data.get("VERSION_ID", "latest")


def image_spec(rootless: bool) -> tuple[str, str]:
    """Return (tag, Dockerfile) for this host and user."""
    entry = pwd.getpwuid(os.getuid())
    shell = (
        entry.pw_shell if Path(entry.pw_shell).name in ("bash", "zsh") else "/bin/bash"
    )
    distro, version = os_release()
    locale = (os.environ.get("LANG") or "en_US.UTF-8").split(":")[0]
    dockerfile = DOCKERFILE.format(
        base=f"{distro}:{version}",
        packages=PACKAGES,
        locale=locale,
        rootless=int(rootless),
        user=entry.pw_name,
        uid=entry.pw_uid,
        gid=entry.pw_gid,
        home=entry.pw_dir,
        shell=shell,
    )
    digest = hashlib.sha256(dockerfile.encode()).hexdigest()[:12]
    return f"{IMAGE_PREFIX}:{distro}-{version}-{digest}", dockerfile


def ensure_image(rootless: bool, rebuild: bool) -> str:
    tag, dockerfile = image_spec(rootless)
    exists = docker("image", "inspect", tag, capture=True, check=False).returncode == 0
    if rebuild or not exists:
        print(f"testenv: building {tag}", file=sys.stderr)
        mode = "--pull" if rebuild else "--quiet"
        docker("build", mode, "-t", tag, "-", input=dockerfile.encode())
    return tag


def volume_name(name: str) -> str:
    return VOLUME_PREFIX + name


def build_run_args(
    image: str,
    command: list[str],
    *,
    rootless: bool,
    keep: str = "",
    diff: bool = False,
    tty: bool = False,
    profile: str = "",
) -> list[str]:
    entry = pwd.getpwuid(os.getuid())
    home = entry.pw_dir
    uid, gid = (0, 0) if rootless else (entry.pw_uid, entry.pw_gid)
    rw = f"type=volume,dst={RW}" + (f",src={volume_name(keep)}" if keep else "")
    env = {
        "HOME": home,
        "USER": entry.pw_name,
        "LOGNAME": entry.pw_name,
        "SHELL": entry.pw_shell,
        "TERM": os.environ.get("TERM", "xterm-256color"),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "MACHINE_TESTENV": "1",
        # In Docker the machine CLI and the shells default to the container
        # profile; the override makes them behave like this host.
        "MACHINE_PROFILE_OVERRIDE": profile,
        "LOWER": LOWER,
        "RW": RW,
    }
    args = ["run", "--rm", "--init"]
    if tty:
        args += ["-it"]
    elif not sys.stdin.isatty():
        args += ["-i"]
    args += [
        "--hostname",
        socket.gethostname(),
        # FUSE mount for the overlay; nothing else needs extra privileges.
        "--cap-add",
        "SYS_ADMIN",
        "--device",
        "/dev/fuse",
        "--security-opt",
        "apparmor=unconfined",
        "-v",
        f"{home}:{LOWER}:ro",
        "--mount",
        rw,
        "--label",
        "machine-testenv=1",
    ]
    for key, value in env.items():
        args += ["-e", f"{key}={value}"]
    noise = "|".join(DIFF_NOISE).replace(".", "\\.")
    args += [image, "/bin/sh", "-c", ENTRY, "testenv"]
    args += [home, str(uid), str(gid), str(int(diff)), noise]
    return args + command


def host_profile(home: Path) -> str:
    """The saved profile of this host (what `machine` would use outside Docker)."""
    for path in (
        home / ".config/machine/profile.yml",
        home / "dotfiles/machine/hosts" / f"{socket.gethostname()}.yml",
    ):
        try:
            for line in path.read_text().splitlines():
                key, _, value = line.partition(":")
                if key == "profile" and value.strip():
                    return value.strip().strip("'\"")
        except OSError:
            continue
    return ""


def shell_command(command: list[str]) -> list[str]:
    """Wrap the user command in a login shell so PATH and env match a terminal."""
    shell = os.environ.get("SHELL") or pwd.getpwuid(os.getuid()).pw_shell or "/bin/bash"
    if Path(shell).name not in ("bash", "zsh"):
        shell = "/bin/bash"
    if not command:
        return [shell, "-l"]
    script = command[0] if len(command) == 1 else shlex.join(command)
    return [shell, "-lc", script]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="machine testenv",
        description="Run COMMAND (default: an interactive login shell) against the real "
        "home in a container; nothing on the host changes.",
        epilog="Quote shell syntax so the host shell does not run it: "
        "machine testenv -- 'machine update && machine'",
    )
    add = parser.add_argument
    add("--keep", metavar="NAME", default="", help="keep the changes in a named volume")
    add(
        "--reset",
        action="store_true",
        help="with --keep: start from the real home again",
    )
    add(
        "--profile",
        default=None,
        help="machine profile inside (default: this host's saved one; '' for container)",
    )
    add(
        "--diff", action="store_true", help="list the files the command changed in home"
    )
    add(
        "--rebuild",
        action="store_true",
        help="rebuild the image (pulls the base image)",
    )
    add("--list", action="store_true", help="list kept environments and exit")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="command after --")
    args = parser.parse_args(argv)
    if args.command[:1] == ["--"]:
        args.command = args.command[1:]
    if args.reset and not args.keep:
        parser.error("--reset needs --keep NAME")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if not shutil.which("docker"):
        die("docker is required")
    if args.list:
        docker(
            "volume",
            "ls",
            "--filter",
            f"name=^{VOLUME_PREFIX}",
            "--format",
            "{{.Name}}",
        )
        return 0
    rootless = docker_rootless()
    image = ensure_image(rootless, args.rebuild)
    if args.reset:
        docker("volume", "rm", "--force", volume_name(args.keep), capture=True)
    command = shell_command(args.command)
    run = build_run_args(
        image,
        command,
        rootless=rootless,
        keep=args.keep,
        diff=args.diff,
        tty=sys.stdin.isatty() and sys.stdout.isatty(),
        profile=host_profile(Path.home()) if args.profile is None else args.profile,
    )
    return docker(*run, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
