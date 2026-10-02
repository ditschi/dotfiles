"""Keep host-specific Git settings out of the shared dotfiles configuration."""

import argparse
import os
from pathlib import Path
import subprocess
import tempfile


HOST_ONLY = (
    r"^(user\.(name|email|signingkey)$|gpg\.|commit\.gpgsign$|tag\.gpgsign$"
    r"|safe\.|credential\.|https?\.|core\.sshcommand$)"
)


def git_config(path, *args):
    result = subprocess.run(
        ["git", "config", "--file", str(path), "--no-includes", *args],
        capture_output=True,
        text=True,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(f"cannot read or update Git configuration: {path}")
    return result


def host_settings(path):
    result = git_config(path, "--null", "--get-regexp", HOST_ONLY)
    entries = []
    for entry in result.stdout.split("\0"):
        if entry:
            key, separator, value = entry.partition("\n")
            entries.append((key, value if separator else "true"))
    return entries


def relocate(shared, local, check=False):
    if not shared.is_file():
        raise RuntimeError(f"shared Git configuration is missing: {shared}")
    entries = host_settings(shared)
    if not entries:
        return 0
    keys = sorted({entry[0] for entry in entries})
    if check:
        print("Host-only keys in shared Git config: " + ", ".join(keys))
        return 1
    if local.is_symlink():
        raise RuntimeError(
            f"host-local Git configuration must not be a symlink: {local}"
        )
    existing = host_settings(local) if local.exists() else []
    local_keys = {entry[0] for entry in existing}
    backup_root = Path.home() / ".local/share/machine/gitconfig-backup"
    backup_root.mkdir(parents=True, exist_ok=True)
    backup = Path(tempfile.mkdtemp(dir=backup_root))
    for source, name in ((shared, "gitconfig"), (local, "gitconfig.local")):
        if source.is_file():
            descriptor = os.open(
                backup / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
            )
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(source.read_bytes())
    local.parent.mkdir(parents=True, exist_ok=True)
    if not local.exists():
        descriptor = os.open(local, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(descriptor)
    local.chmod(0o600)
    for key, value in entries:
        if key not in local_keys:
            git_config(local, "--add", key, value)
    for key in keys:
        git_config(shared, "--unset-all", key)
    print(
        f"Removed host-only keys from {shared}; local settings: {local}; backup: {backup}"
    )
    conflicts = local_keys.intersection(keys)
    if conflicts:
        print("Kept existing local overrides for: " + ", ".join(sorted(conflicts)))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--shared",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "home/dot_gitconfig",
    )
    parser.add_argument("--local", type=Path, default=Path.home() / ".gitconfig.local")
    args = parser.parse_args()
    try:
        check = args.check or os.environ.get("CI", "").lower() in {"1", "true"}
        return relocate(args.shared, args.local, check)
    except (OSError, RuntimeError) as error:
        print(f"gitconfig: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
