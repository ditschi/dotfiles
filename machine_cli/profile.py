"""Host config: context, device and features of a host; applied copy; prompts."""

from __future__ import annotations

import getpass
import os
import re
import shutil
import sys
import types
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


from . import features as feature_table
from . import system
from .core import (
    CONTEXTS,
    DEVICES,
    ENV_GROUPS,
    SSH_CLASS,
    log,
    die,
    warn,
    parse_profile_file,
    parse_profile_text,
    format_profile_yaml,
    profile_fingerprint,
)

COMPANY_USER_RE = r"[a-zA-Z]{3}[0-9]{1,2}[a-zA-Z]{2,3}"


class ProfileMixin:
    # --- current and default values -------------------------------------------

    def applied_host(self) -> Dict[str, object]:
        return parse_profile_file(self.applied_host_path)

    def current_host(self) -> Tuple[str, str]:
        return self.current_context(), self.current_device()

    def current_context(self) -> str:
        data = self.applied_host()
        context = str(data["context"])
        if context in CONTEXTS:
            return context
        if data["device"] == "container":
            return ""
        return self.default_context()

    def current_device(self) -> str:
        device = str(self.applied_host()["device"])
        return device if device in DEVICES else self.default_device()

    def default_device(self) -> str:
        """Docker (unless overridden), saved, inherited, boot target."""
        if system.in_docker():
            override = os.environ.get("MACHINE_DEVICE_OVERRIDE", "")
            return override if override in DEVICES else "container"
        for path in (self.applied_host_path, self.host_config_path()):
            device = str(parse_profile_file(path)["device"])
            if device in DEVICES:
                return device
        inherited = os.environ.get("MACHINE_DEVICE", "")
        if inherited in DEVICES:
            return inherited
        return "desktop" if system.boots_graphical() else "server"

    def default_context(self) -> str:
        """Docker: none unless overridden; else saved, inherited, company user ID."""
        if system.in_docker():
            override = os.environ.get("MACHINE_CONTEXT_OVERRIDE", "")
            return override if override in CONTEXTS else ""
        for path in (self.applied_host_path, self.host_config_path()):
            context = str(parse_profile_file(path)["context"])
            if context in CONTEXTS:
                return context
        inherited = os.environ.get("MACHINE_CONTEXT", "")
        if inherited in CONTEXTS:
            return inherited
        user = os.environ.get("SUDO_USER") or getpass.getuser()
        if re.fullmatch(COMPANY_USER_RE, user):
            return "work"
        return "private"

    def default_features_for(self, context: str, device: str) -> List[str]:
        return feature_table.defaults(context, device) or ["zsh-full"]

    def saved_features(self) -> List[str]:
        return list(self.applied_host()["features"])

    def saved_ssh_allow_from(self) -> List[str]:
        return list(self.applied_host()["ssh_allow_from"])

    def saved_ansible(self) -> bool:
        """`ansible: false` in the repository host config or the applied copy."""
        for path in (self.host_config_path(), self.applied_host_path):
            if path.is_file():
                return bool(parse_profile_file(path)["ansible"])
        return True

    def allowed_features(
        self, features: Sequence[str], context: str, device: str
    ) -> List[str]:
        """The features the table allows for this host; warn about the others."""
        kept, dropped = feature_table.split(features, context, device)
        if dropped:
            where = f"{context or 'no context'}/{device}"
            warn(
                f"not applied on {where} (excluded or unknown): {', '.join(dropped)}; "
                "dropped the next time the host config is written"
            )
        return kept

    def ssh_class(self, context: Optional[str] = None) -> str:
        context = self.current_context() if context is None else context
        return SSH_CLASS.get(context, "")

    def env_item_names(self) -> List[str]:
        groups = ENV_GROUPS.get(self.current_context(), [])
        if not groups:
            return []
        return [
            *(f"env/groups/{group}" for group in groups),
            f"env/hosts/{system.hostname_short()}",
        ]

    def ssh_item_name(self, hostname: Optional[str] = None) -> str:
        klass = self.ssh_class()
        host = hostname or system.hostname_short()
        return f"ssh/{klass}/hosts/{host}"

    def host_key_paths(self) -> Tuple[Path, Path]:
        host = system.hostname_short()
        private = self.home / ".ssh" / f"id_ed25519_{host}"
        return private, Path(str(private) + ".pub")

    def ensure_dirs(self) -> None:
        (self.home / ".local/bin").mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.applied_host_path.parent.mkdir(parents=True, exist_ok=True)

    # --- applied host config and repository host config -----------------------

    def takeover_legacy_profile(self) -> None:
        """Move a former ~/.config/machine/profile.yml to the applied host config once."""
        legacy = self.legacy_profile_path
        if not legacy.is_file() or self.applied_host_path.is_file():
            return
        data = parse_profile_file(legacy)
        if not data["device"]:
            return
        self.ensure_dirs()
        self.applied_host_path.write_text(
            format_profile_yaml(
                str(data["context"]),
                str(data["device"]),
                list(data["features"]),
                list(data["ssh_allow_from"]),
                bool(data["ansible"]),
            ),
            encoding="utf-8",
        )
        self.applied_host_path.chmod(0o600)
        legacy.unlink()
        log(f"moved {legacy} to {self.applied_host_path}")

    def write_profile(
        self,
        context: str,
        device: str,
        features: Sequence[str],
        ssh_allow_from: Optional[Sequence[str]] = None,
        ansible: Optional[bool] = None,
    ) -> None:
        """Write the applied host config."""
        self.ensure_dirs()
        allow = (
            list(ssh_allow_from)
            if ssh_allow_from is not None
            else self.saved_ssh_allow_from()
        )
        ansible = self.saved_ansible() if ansible is None else ansible
        text = format_profile_yaml(context, device, features, allow, ansible)
        self.applied_host_path.write_text(text, encoding="utf-8")
        self.applied_host_path.chmod(0o600)

    def host_config_path(self, hostname: Optional[str] = None) -> Path:
        return self.host_configs_dir / f"{hostname or system.hostname_short()}.yml"

    def save_host_config_to_repo(
        self,
        context: str,
        device: str,
        features: Sequence[str],
        ssh_allow_from: Sequence[str],
        ansible: bool = True,
        hostname: Optional[str] = None,
    ) -> Path:
        self.host_configs_dir.mkdir(parents=True, exist_ok=True)
        path = self.host_config_path(hostname)
        path.write_text(
            format_profile_yaml(context, device, features, ssh_allow_from, ansible),
            encoding="utf-8",
        )
        log(f"wrote host config {path.relative_to(self.repo)}")
        return path

    def sync_host_config_from_repo(self, hostname: Optional[str] = None) -> bool:
        """Copy machine/hosts/<hostname>.yml → applied host config. True if changed."""
        path = self.host_config_path(hostname)
        if not path.is_file():
            return False
        self.ensure_dirs()
        before = profile_fingerprint(self.applied_host_path)
        old = self.applied_host()
        text = path.read_text(encoding="utf-8")
        self.applied_host_path.write_text(text, encoding="utf-8")
        self.applied_host_path.chmod(0o600)
        after = profile_fingerprint(self.applied_host_path)
        new = self.applied_host()
        self.allowed_features(new["features"], str(new["context"]), str(new["device"]))
        if before != after:
            changes = host_config_changes(old, parse_profile_text(text))
            log(
                f"applied host config {path.relative_to(self.repo)}"
                + (": " + "; ".join(changes) if changes else "")
            )
            self.write_dotfile_groups()
            return True
        return False

    def backup_applied_host(self) -> Optional[Path]:
        if not self.applied_host_path.is_file():
            return None
        backup_dir = self.state_dir / "host-backup"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        bak = backup_dir / f"applied-host.{stamp}.yml"
        shutil.copy2(self.applied_host_path, bak)
        return bak

    def restore_applied_host(self, backup: Path) -> None:
        self.ensure_dirs()
        shutil.copy2(backup, self.applied_host_path)
        self.applied_host_path.chmod(0o600)
        self.write_dotfile_groups()
        log(f"restored the applied host config from {backup}")

    def persist_host_config(
        self,
        context: str,
        device: str,
        features: Sequence[str],
        allow_from: Sequence[str],
        *,
        yes: bool,
    ) -> None:
        """The repository host config is the only source: write the selection there
        (no question, also with --yes); only committing stays an explicit offer."""
        if device == "container" or system.in_docker():
            return
        path = self.host_config_path()
        ansible = self.saved_ansible()
        new_text = format_profile_yaml(context, device, features, allow_from, ansible)
        old_text = path.read_text(encoding="utf-8") if path.is_file() else ""
        if old_text == new_text:
            return
        changes = host_config_changes(
            parse_profile_text(old_text), parse_profile_text(new_text)
        )
        self.save_host_config_to_repo(context, device, features, allow_from, ansible)
        if changes:
            log("host config changes: " + "; ".join(changes))
        if (
            system.is_tty()
            and not yes
            and system.prompt_yes_no("Commit now (machine commit)?", False)
        ):
            rel = str(path.relative_to(self.repo))
            system.run(["git", "-C", str(self.repo), "add", rel])
            system.run(
                [
                    "git",
                    "-C",
                    str(self.repo),
                    "commit",
                    "-m",
                    f"Add/update host config for {system.hostname_short()}",
                ],
                check=False,
            )
        else:
            log(f"commit and push {path.relative_to(self.repo)} to share the change")

    # --- prompts ----------------------------------------------------------------

    def prompt_choice(self, title: str, choices: Sequence[str], default: str) -> str:
        if system.is_tty():
            return system.choose(title, list(choices), default)
        print(f"{title}: {' '.join(choices)}", file=sys.stderr)
        answer = input(f"{title} [{default}]: ").strip()
        return answer or default

    def prompt_context(self, current: str) -> str:
        return self.prompt_choice("Context", CONTEXTS, current or "private")

    def prompt_device(self, current: str) -> str:
        return self.prompt_choice(
            "Device", [d for d in DEVICES if d != "container"], current or "desktop"
        )

    def prompt_features(
        self, context: str, device: str, selected: Sequence[str]
    ) -> List[str]:
        """Only the features the table offers for this host; `selected` preselected."""
        offered = feature_table.allowed(context, device)
        selected = [name for name in selected if name in offered]
        if system.is_tty():
            return system.choose_many("Features", offered, selected)
        print("Features (space-separated). Empty keeps defaults.", file=sys.stderr)
        for name, help_text in offered.items():
            mark = "*" if name in selected else " "
            print(f"  [{mark}] {name:20} {help_text}", file=sys.stderr)
        answer = input(f"Features [{(' '.join(selected))}]: ").strip()
        return answer.split() if answer else list(selected)

    def known_ssh_hosts(self, context: str) -> Dict[str, str]:
        """Hosts whose public key Ansible can install: {hostname: where the key is}."""
        hosts: Dict[str, str] = {}
        if self.ssh_class(context) == "home":  # the repo only holds home fleet keys
            for path in sorted((self.repo / "machine" / "ssh_keys").glob("*.pub")):
                hosts[path.stem] = "machine/ssh_keys"
        hosts.pop(system.hostname_short(), None)
        return hosts

    def prompt_ssh_allow_from(
        self, current: Sequence[str], context: Optional[str] = None
    ) -> List[str]:
        default = " ".join(current)
        if not system.is_tty():
            return list(current)
        hosts = self.known_ssh_hosts(
            self.current_context() if context is None else context
        )
        if hosts:
            # Keep already configured hosts selectable even if their key is gone.
            for host in current:
                hosts.setdefault(host, "configured, no key found")
            return system.choose_many(
                "Hosts that may SSH into this machine (none = leave authorized_keys alone)",
                hosts,
                current,
            )
        print(
            "Hosts that may SSH into this machine (same class only). Empty = leave authorized_keys alone.",
            file=sys.stderr,
        )
        answer = input(f"ssh_allow_from [{default}]: ").strip()
        if not answer:
            return list(current)
        return answer.split()

    def cmd_host(self, args: types.SimpleNamespace) -> int:
        if args.action == "show":
            repo_path = self.host_config_path()
            print(f"hostname: {system.hostname_short()}")
            print(f"applied: {self.applied_host_path}")
            if self.applied_host_path.is_file():
                print(self.applied_host_path.read_text(encoding="utf-8"), end="")
            else:
                print("(missing)")
            print(f"repo: {repo_path}")
            if repo_path.is_file():
                print(repo_path.read_text(encoding="utf-8"), end="")
                same = profile_fingerprint(
                    self.applied_host_path
                ) == profile_fingerprint(repo_path)
                print(f"in sync: {same}")
            else:
                print("(missing — run: machine host save)")
            return 0
        if args.action == "sync":
            changed = self.sync_host_config_from_repo()
            log("synced" if changed else "already in sync (or no host config)")
            return 0
        if args.action == "save":
            if not self.applied_host_path.is_file():
                die("no applied host config; run machine setup first")
            self.save_host_config_to_repo(
                self.current_context(),
                self.current_device(),
                self.saved_features(),
                self.saved_ssh_allow_from(),
                bool(self.applied_host()["ansible"]),
            )
            return 0
        die(f"unknown host action: {args.action}")
        return 1


def host_config_changes(old: dict, new: dict) -> list[str]:
    """Readable differences between two parsed host configs."""
    changes = []
    for key in ("context", "device"):
        if old.get(key) != new.get(key) and new.get(key):
            changes.append(f"{key} {old.get(key) or '(none)'} -> {new[key]}")
    if old.get("ansible", True) != new.get("ansible", True):
        changes.append(f"ansible {'on' if new.get('ansible', True) else 'off'}")
    for key, label in (("features", ""), ("ssh_allow_from", "ssh_allow_from ")):
        before, after = list(old.get(key) or []), list(new.get(key) or [])
        added = [x for x in after if x not in before]
        removed = [x for x in before if x not in after]
        if added or removed:
            parts = [f"+ {x}" for x in added] + [f"- {x}" for x in removed]
            changes.append(label + ", ".join(parts))
    return changes
