"""Migration from the old root-symlink layout, and its rollback."""

from __future__ import annotations

import ast
import json
import os
import shlex
import shutil
import subprocess
import types
from datetime import datetime
from pathlib import Path
from typing import Optional


from . import system
from .core import (
    OLD_ROOT_LINK_NAMES,
    log,
    die,
    write_private,
)


class MigrationMixin:
    def needs_layout_migration(self) -> bool:
        if not self.chezmoi_config.is_file():
            for name in OLD_ROOT_LINK_NAMES:
                target = self.home / name
                if target.is_symlink():
                    try:
                        dest = target.resolve(strict=False)
                    except OSError:
                        return True
                    if dest == self.repo / name or str(dest).startswith(
                        str(self.repo / name)
                    ):
                        return True
                    # broken symlink that used to point into repo root
                    raw = os.readlink(target)
                    if raw.startswith(str(self.repo)) and "/home/" not in raw.replace(
                        str(self.repo), "", 1
                    ):
                        return True
            zsh = self.home / ".zsh"
            if zsh.is_symlink():
                raw = os.readlink(zsh)
                if raw.endswith("/.zsh") or raw == str(self.repo / ".zsh"):
                    return True
            # new layout present in repo but no chezmoi config yet
            if (self.repo / "home" / "dot_zshrc").is_file() and (
                self.repo / ".zshrc"
            ).exists() is False:
                # After checkout of new branch without chezmoi config
                for name in OLD_ROOT_LINK_NAMES:
                    target = self.home / name
                    if target.is_symlink():
                        raw = os.readlink(target)
                        if "dotfiles" in raw and "/home/dot_" not in raw:
                            return True
                if not self.chezmoi_config.is_file() and any(
                    (self.home / n).exists() for n in OLD_ROOT_LINK_NAMES
                ):
                    # Soft signal: home layout files exist, chezmoi missing,
                    # and repo already uses home/ source.
                    if (self.repo / "bootstrap").is_file() and (
                        self.repo / "home" / "dot_zshrc"
                    ).is_file():
                        # Only treat as migration if a root-style link is broken
                        # or still points outside home/
                        for name in OLD_ROOT_LINK_NAMES + [".zsh"]:
                            target = self.home / name
                            if not target.is_symlink():
                                continue
                            raw = os.readlink(target)
                            if (
                                "/home/dot_" in raw
                                or "/home/" in raw.split("dotfiles", 1)[-1]
                            ):
                                continue
                            if "dotfiles" in raw:
                                return True
        return False

    def write_rollback_script(self, old_sha: str) -> Path:
        self.ensure_dirs()
        path = self.state_dir / "rollback.sh"
        script = f"""#!/usr/bin/env bash
set -euo pipefail
REPO={shlex.quote(str(self.repo))}
OLD_SHA={shlex.quote(old_sha)}
cd "$REPO"
git checkout "$OLD_SHA"
python3 "$REPO/install.py" --update --force
echo "machine: restored checkout $OLD_SHA and re-linked with that install.py"
"""
        write_private(path, script.encode())
        path.chmod(0o700)
        return path

    def legacy_rollback_sha(self, requested: str = "") -> str:
        def is_legacy(commit: str) -> bool:
            root = system.run(
                ["git", "-C", str(self.repo), "cat-file", "-e", f"{commit}:.zshrc"],
                capture=True,
                check=False,
            )
            script = system.run(
                ["git", "-C", str(self.repo), "show", f"{commit}:install.py"],
                capture=True,
                check=False,
            )
            if root.returncode or script.returncode:
                return False
            try:
                tree = ast.parse(script.stdout)
            except SyntaxError:
                return False
            return any(
                isinstance(node, ast.FunctionDef)
                and node.name == "create_links_for_directory"
                for node in tree.body
            )

        if requested:
            result = system.run(
                [
                    "git",
                    "-C",
                    str(self.repo),
                    "rev-parse",
                    "--verify",
                    f"{requested}^{{commit}}",
                ],
                capture=True,
                check=False,
            )
            commit = result.stdout.strip()
            if result.returncode == 0 and is_legacy(commit):
                return commit
            die(f"rollback ref {requested!r} is not a legacy dotfiles commit")
        for command in (
            ["reflog", "--format=%H", "HEAD"],
            ["rev-list", "--first-parent", "HEAD"],
        ):
            result = system.run(
                ["git", "-C", str(self.repo), *command], capture=True, check=False
            )
            for commit in dict.fromkeys((result.stdout or "").splitlines()):
                if is_legacy(commit):
                    return commit
        die("no verified legacy commit found; fetch history or supply --rollback-ref")
        raise AssertionError

    def backup_migration_state(self, old_sha: str) -> Path:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup = self.state_dir / "migration" / stamp
        backup.mkdir(mode=0o700, parents=True, exist_ok=False)
        backup.chmod(0o700)
        self.migration_backup = backup
        meta = {
            "old_sha": old_sha,
            "repo": str(self.repo),
            "home": str(self.home),
            "hostname": system.hostname_short(),
            "links": {},
            "files": {},
        }
        names = set(
            OLD_ROOT_LINK_NAMES
            + [".zsh", ".gitconfig.local", ".env", ".env.local", ".zshrc-local"]
        )
        for name in sorted(names):
            target = self.home / name
            if target.is_symlink():
                meta["links"][name] = os.readlink(target)
            content = None
            if target.is_file():
                content = target.read_bytes()
            elif target.is_symlink() and name in OLD_ROOT_LINK_NAMES:
                try:
                    relative = target.resolve(strict=False).relative_to(self.repo)
                except (ValueError, OSError):
                    relative = None
                if relative:
                    result = subprocess.run(
                        [
                            "git",
                            "-C",
                            str(self.repo),
                            "cat-file",
                            "blob",
                            f"{old_sha}:{relative}",
                        ],
                        capture_output=True,
                    )
                    if result.returncode == 0:
                        content = result.stdout
            if content is not None:
                dest = backup / "files" / name
                write_private(dest, content)
                meta["files"][str(target)] = str(dest)
        tools = {}
        for tool, args in {
            "az": ["--version"],
            "gh": ["--version"],
            "docker": ["--version"],
            "yazi": ["--version"],
            "uv": ["--version"],
            "chezmoi": ["--version"],
            "ansible-playbook": ["--version"],
        }.items():
            executable = shutil.which(tool)
            result = (
                system.run([executable, *args], capture=True, check=False)
                if executable
                else None
            )
            tools[tool] = {
                "path": executable,
                "version": (result.stdout or "").splitlines()[:1] if result else [],
                "returncode": result.returncode if result else None,
            }
        if tools["docker"]["path"]:
            compose = system.run(
                [tools["docker"]["path"], "compose", "version"],
                capture=True,
                check=False,
            )
            tools["docker-compose"] = {
                "returncode": compose.returncode,
                "version": (compose.stdout or "").splitlines()[:1],
            }
        meta["tools"] = tools
        meta["git_status"] = system.run(
            ["git", "-C", str(self.repo), "status", "--porcelain"], capture=True
        ).stdout
        if system.have("dpkg-query"):
            packages = system.run(
                [
                    "dpkg-query",
                    "-W",
                    "-f=${binary:Package}\t${Version}\t${db:Status-Abbrev}\n",
                ],
                capture=True,
                check=False,
            )
            write_private(backup / "packages.txt", packages.stdout.encode())
        meta["system_backups"] = []
        system_paths = [
            Path("/etc/apt/sources.list"),
            Path("/etc/ssh/sshd_config"),
            Path("/etc/ssh/sshd_config.d/99-machine-port.conf"),
            Path("/etc/telegraf/telegraf.conf"),
            Path("/etc/systemd/system/stylus-touch-guard.service"),
        ]
        for directory in (
            "/etc/apt/sources.list.d",
            "/etc/apt/keyrings",
            "/etc/telegraf/telegraf.d",
        ):
            system_paths.extend(Path(directory).glob("*"))
        for target in system_paths:
            if not target.is_file():
                continue
            dest = backup / "system" / str(target).lstrip("/")
            try:
                write_private(dest, target.read_bytes())
                meta["system_backups"].append(
                    {"path": str(target), "backup": str(dest)}
                )
            except PermissionError:
                meta["system_backups"].append(
                    {
                        "path": str(target),
                        "warning": "unreadable; back up as administrator before enabling its role",
                    }
                )
        if system.have("systemctl"):
            meta["services"] = {}
            for unit in ("telegraf", "ssh", "docker", "stylus-touch-guard"):
                result = system.run(
                    ["systemctl", "is-active", unit], capture=True, check=False
                )
                meta["services"][unit] = (result.stdout or "").strip()
            result = system.run(
                ["systemctl", "--user", "is-enabled", "dotfiles-update-check.timer"],
                capture=True,
                check=False,
            )
            meta["services"]["dotfiles-update-check.timer"] = (
                result.stdout or ""
            ).strip()
        write_private(
            backup / "meta.json", (json.dumps(meta, indent=2) + "\n").encode()
        )
        report = [
            f"Migration backup: {backup}",
            f"Verified legacy commit: {old_sha}",
            "Recovery: check out the legacy commit and run python3 install.py --update --force.",
            "Review Git identity/signing/credentials/proxy and environment coverage.",
            "Unversioned files and system backups are for manual recovery; packages/services are not rolled back.",
        ]
        for target, dest in meta["files"].items():
            report.append(f"{target} -> {dest}")
        for entry in meta["system_backups"]:
            report.append(
                f"{entry['path']} -> {entry.get('backup', entry.get('warning'))}"
            )
        write_private(
            backup / "migration-report.txt", ("\n".join(report) + "\n").encode()
        )
        log(f"manual checks: {backup / 'migration-report.txt'}")
        for name in (".gitconfig", ".gitconfig.local", ".env", ".env.local"):
            log(
                f"review {self.home / name}; backup {backup / 'files' / name} (if present)"
            )
        return backup

    def preserve_git_host_settings(self) -> None:
        backup = getattr(self, "migration_backup", None)
        if not backup:
            return
        source = backup / "files/.gitconfig"
        local = self.home / ".gitconfig.local"
        if not source.is_file():
            return
        result = system.run(
            [
                "git",
                "config",
                "--file",
                str(source),
                "--no-includes",
                "--null",
                "--get-regexp",
                r"^(user\.(name|email|signingkey)|gpg\.|commit\.gpgsign|tag\.gpgsign"
                r"|safe\.|credential\.|https?\.|core\.sshcommand)",
            ],
            capture=True,
            check=False,
        )
        if result.returncode not in (0, 1):
            die(f"cannot parse saved Git settings; review {source}")
        old_local = backup / "files/.gitconfig.local"
        existing = (
            system.run(
                [
                    "git",
                    "config",
                    "--file",
                    str(old_local),
                    "--no-includes",
                    "--name-only",
                    "--list",
                ],
                capture=True,
                check=False,
            )
            if old_local.is_file()
            else None
        )
        keys = set((existing.stdout or "").splitlines()) if existing else set()
        entries = [
            entry.split("\n", 1) for entry in (result.stdout or "").split("\0") if entry
        ]
        if not local.is_file():
            log(
                f"Git overrides pending; create {local} with chezmoi, then review {source}"
            )
            return
        if local.is_symlink():
            write_private(local, local.read_bytes())
        migrated_keys = set()
        for key, value in entries:
            if key not in keys:
                if key not in migrated_keys:
                    system.run(
                        ["git", "config", "--file", str(local), "--unset-all", key],
                        capture=True,
                        check=False,
                    )
                system.run(
                    ["git", "config", "--file", str(local), "--add", key, value],
                    capture=True,
                )
                migrated_keys.add(key)
        includes = system.run(
            [
                "git",
                "config",
                "--file",
                str(source),
                "--no-includes",
                "--name-only",
                "--get-regexp",
                r"^include",
            ],
            capture=True,
            check=False,
        )
        if includes.stdout:
            log(
                "WARNING: included Git configuration needs manual review: "
                f"{self.home / '.gitconfig'}; original backup {source}"
            )
        log(f"preserved host Git settings in {local}; review backup {source}")

    def clear_stale_root_links(self) -> None:
        targets = [self.home / name for name in OLD_ROOT_LINK_NAMES + [".zsh"]]
        backup = getattr(self, "migration_backup", None)
        if backup:
            meta = json.loads((backup / "meta.json").read_text())
            # backup_migration_state records symlinks as {name in $HOME: target}
            targets.extend(self.home / name for name in meta.get("links", {}))
        for target in dict.fromkeys(targets):
            if not target.is_symlink():
                continue
            raw = os.readlink(target)
            if "/home/dot_" in raw:
                continue
            try:
                target.resolve(strict=False).relative_to(self.repo)
            except (ValueError, OSError):
                continue
            if "dotfiles" in raw or str(self.repo) in raw:
                log(f"removing stale symlink {target} -> {raw}")
                target.unlink()

    def handle_layout_gate(self, *, yes: bool, force: bool = False) -> Optional[str]:
        """Return 'migrate' if caller should run migrate, None to continue, die on abort."""
        if not self.needs_layout_migration():
            return None
        msg = (
            "Layout has switched to chezmoi under home/. "
            "A plain update cannot repair HOME links."
        )
        log(msg)
        if yes or force:
            die(
                "non-interactive update blocked; run: machine migrate --yes "
                "(or ./bootstrap)"
            )
        if not system.is_tty():
            die("layout migration needed; run: machine migrate")
        if system.prompt_yes_no("Run full setup / migration now?", True):
            return "migrate"
        die("aborted; when ready: machine migrate  or  ./bootstrap")
        return None

    def cmd_migrate(self, args: types.SimpleNamespace) -> int:
        old_sha = self.legacy_rollback_sha(getattr(args, "rollback_ref", ""))
        backup = self.backup_migration_state(old_sha)
        rollback = self.write_rollback_script(old_sha)
        log(f"migration backup: {backup}")
        log(f"rollback script: {rollback}")
        self.clear_stale_root_links()
        args.command = "migrate"
        return self.cmd_setup(args)

    def cmd_rollback(self) -> int:
        path = self.state_dir / "rollback.sh"
        if not path.is_file():
            die(
                f"missing {path}; only created by machine migrate. "
                "Manual revert: git checkout <old-sha> && python3 install.py --update --force"
            )
        log(f"running {path}")
        system.run(["bash", str(path)])
        return 0
