"""Host profile: local answers, versioned host files, prompts."""

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


from . import system
from .core import (
    PROFILES,
    FEATURE_HELP,
    FEATURES,
    ENV_GROUPS,
    SSH_CLASS,
    log,
    die,
    parse_profile_file,
    parse_profile_text,
    format_profile_yaml,
    profile_fingerprint,
)


class ProfileMixin:
    def ansible_profile_path(self, profile: str) -> Path:
        return self.ansible_dir / "profiles" / f"{profile}.yml"

    def default_features_for(self, profile: str) -> List[str]:
        """Feature defaults from ansible/profiles/<profile>.yml (single source)."""
        path = self.ansible_profile_path(profile)
        data = parse_profile_file(path)
        feats = data.get("features") or []
        if isinstance(feats, list) and feats:
            return [str(x) for x in feats]
        return ["zsh-full"]

    def current_profile(self) -> str:
        data = parse_profile_file(self.profile_path)
        profile = str(data.get("profile") or "home-laptop")
        if profile in PROFILES:
            return profile
        return self.repair_unknown_profile(profile)

    def repair_unknown_profile(self, profile: str) -> str:
        if getattr(self, "unattended", False) or not system.is_tty():
            die(
                f"unknown profile {profile!r} in {self.profile_path}; "
                f"valid: {', '.join(PROFILES)}. Run `machine setup` to fix it"
            )
        log(f"unknown profile {profile!r} in {self.profile_path}")
        chosen = system.choose(
            "Select the machine type", PROFILES, self.default_profile()
        )
        self.write_profile(chosen, self.saved_features())
        log(f"profile updated to {chosen}")
        return chosen

    def default_profile(self) -> str:
        if system.in_docker():
            override = os.environ.get("MACHINE_PROFILE_OVERRIDE", "")
            return override if override in PROFILES else "container"
        for path in (self.profile_path, self.host_profile_path()):
            profile = str(parse_profile_file(path).get("profile") or "")
            if profile in PROFILES:
                return profile
        inherited = os.environ.get("MACHINE_PROFILE", "")
        if inherited in PROFILES:
            return inherited
        user = os.environ.get("SUDO_USER") or getpass.getuser()
        if re.fullmatch(r"[a-zA-Z]{3}[0-9]{1,2}[a-zA-Z]{2,3}", user):
            return "work-machine"
        return "home-laptop"

    def saved_features(self) -> List[str]:
        data = parse_profile_file(self.profile_path)
        feats = data.get("features") or []
        return list(feats) if isinstance(feats, list) else []

    def saved_ssh_allow_from(self) -> List[str]:
        data = parse_profile_file(self.profile_path)
        allow = data.get("ssh_allow_from") or []
        return list(allow) if isinstance(allow, list) else []

    def ssh_class(self, profile: Optional[str] = None) -> str:
        profile = profile or self.current_profile()
        return SSH_CLASS.get(profile, "home")

    def env_item_names(self) -> List[str]:
        groups = ENV_GROUPS.get(self.current_profile(), [])
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
        (self.home / ".config/machine").mkdir(parents=True, exist_ok=True)
        (self.home / ".local/bin").mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def write_profile(
        self,
        profile: str,
        features: Sequence[str],
        ssh_allow_from: Optional[Sequence[str]] = None,
    ) -> None:
        self.ensure_dirs()
        allow = (
            list(ssh_allow_from)
            if ssh_allow_from is not None
            else self.saved_ssh_allow_from()
        )
        text = format_profile_yaml(profile, features, allow)
        self.profile_path.write_text(text, encoding="utf-8")
        self.profile_path.chmod(0o600)

    def host_profile_path(self, hostname: Optional[str] = None) -> Path:
        return self.host_profiles_dir / f"{hostname or system.hostname_short()}.yml"

    def save_host_profile_to_repo(
        self,
        profile: str,
        features: Sequence[str],
        ssh_allow_from: Sequence[str],
        hostname: Optional[str] = None,
    ) -> Path:
        self.host_profiles_dir.mkdir(parents=True, exist_ok=True)
        path = self.host_profile_path(hostname)
        path.write_text(
            format_profile_yaml(profile, features, ssh_allow_from), encoding="utf-8"
        )
        log(f"wrote repo host profile {path.relative_to(self.repo)}")
        return path

    def sync_host_profile_from_repo(self, hostname: Optional[str] = None) -> bool:
        """Copy machine/hosts/<hostname>.yml → local profile.yml. Return True if changed."""
        path = self.host_profile_path(hostname)
        if not path.is_file():
            return False
        self.ensure_dirs()
        before = profile_fingerprint(self.profile_path)
        old = parse_profile_file(self.profile_path)
        text = path.read_text(encoding="utf-8")
        self.profile_path.write_text(text, encoding="utf-8")
        self.profile_path.chmod(0o600)
        after = profile_fingerprint(self.profile_path)
        if before != after:
            changes = profile_changes(old, parse_profile_text(text))
            log(
                f"applied host profile {path.relative_to(self.repo)}"
                + (": " + "; ".join(changes) if changes else "")
            )
            data = parse_profile_file(self.profile_path)
            self.write_dotfile_groups(str(data.get("profile") or "home-laptop"))
            return True
        return False

    def backup_local_profile(self) -> Optional[Path]:
        if not self.profile_path.is_file():
            return None
        backup_dir = self.state_dir / "profile-backup"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        bak = backup_dir / f"profile.{stamp}.yml"
        shutil.copy2(self.profile_path, bak)
        return bak

    def restore_local_profile(self, backup: Path) -> None:
        self.ensure_dirs()
        shutil.copy2(backup, self.profile_path)
        self.profile_path.chmod(0o600)
        data = parse_profile_file(self.profile_path)
        self.write_dotfile_groups(str(data.get("profile") or "home-laptop"))
        log(f"restored local profile from {backup}")

    def maybe_persist_host_profile(
        self,
        profile: str,
        features: Sequence[str],
        allow_from: Sequence[str],
        *,
        yes: bool,
    ) -> None:
        """The repository host file is the only source: write the selection there
        (no question, also with --yes); only committing stays an explicit offer."""
        if profile == "container" or system.in_docker():
            return
        path = self.host_profile_path()
        new_text = format_profile_yaml(profile, features, allow_from)
        old_text = path.read_text(encoding="utf-8") if path.is_file() else ""
        if old_text == new_text:
            return
        changes = profile_changes(
            parse_profile_text(old_text), parse_profile_text(new_text)
        )
        self.save_host_profile_to_repo(profile, features, allow_from)
        if changes:
            log("host profile changes: " + "; ".join(changes))
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
                    f"Add/update host profile for {system.hostname_short()}",
                ],
                check=False,
            )
        else:
            log(f"commit and push {path.relative_to(self.repo)} to share the change")

    def prompt_profile(self, current: str) -> str:
        default = current or "home-laptop"
        if system.is_tty():
            return system.choose("Machine profile", PROFILES, default)
        print(f"Profiles: {' '.join(PROFILES)}", file=sys.stderr)
        answer = input(f"Profile [{default}]: ").strip()
        return answer or default

    def prompt_features(self, defaults: Sequence[str]) -> List[str]:
        if system.is_tty():
            return system.choose_many("Features", FEATURE_HELP, defaults)
        print("Features (space-separated). Empty keeps defaults.", file=sys.stderr)
        for name in FEATURES:
            mark = "*" if name in defaults else " "
            help_text = FEATURE_HELP.get(name, "")
            print(f"  [{mark}] {name:20} {help_text}", file=sys.stderr)
        answer = input(f"Features [{(' '.join(defaults))}]: ").strip()
        return answer.split() if answer else list(defaults)

    def known_ssh_hosts(self, profile: str) -> Dict[str, str]:
        """Hosts whose public key we can install: {hostname: where the key is}."""
        hosts: Dict[str, str] = {}
        if self.ssh_class(profile) == "home":  # the repo only holds home fleet keys
            for path in sorted((self.repo / "machine" / "ssh_keys").glob("*.pub")):
                hosts[path.stem] = "machine/ssh_keys"
        for host in self.bw_ssh_hosts(profile):
            hosts[host] = f"{hosts[host]} + Bitwarden" if host in hosts else "Bitwarden"
        hosts.pop(system.hostname_short(), None)
        return hosts

    def prompt_ssh_allow_from(
        self, current: Sequence[str], profile: Optional[str] = None
    ) -> List[str]:
        default = " ".join(current)
        if not system.is_tty():
            return list(current)
        hosts = self.known_ssh_hosts(profile or self.current_profile())
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

    def cmd_profile(self, args: types.SimpleNamespace) -> int:
        if args.action == "show":
            repo_path = self.host_profile_path()
            print(f"hostname: {system.hostname_short()}")
            print(f"local: {self.profile_path}")
            if self.profile_path.is_file():
                print(self.profile_path.read_text(encoding="utf-8"), end="")
            else:
                print("(missing)")
            print(f"repo: {repo_path}")
            if repo_path.is_file():
                print(repo_path.read_text(encoding="utf-8"), end="")
                same = profile_fingerprint(self.profile_path) == profile_fingerprint(
                    repo_path
                )
                print(f"in sync: {same}")
            else:
                print("(missing — run: machine profile save)")
            return 0
        if args.action == "sync":
            changed = self.sync_host_profile_from_repo()
            log("synced" if changed else "already in sync (or no repo host file)")
            return 0
        if args.action == "save":
            if not self.profile_path.is_file():
                die("no local profile; run machine setup first")
            self.save_host_profile_to_repo(
                self.current_profile(),
                self.saved_features(),
                self.saved_ssh_allow_from(),
            )
            return 0
        die(f"unknown profile action: {args.action}")
        return 1


def profile_changes(old: dict, new: dict) -> list[str]:
    """Readable differences between two parsed profiles (profile, features, ssh)."""
    changes = []
    if old.get("profile") != new.get("profile") and new.get("profile"):
        changes.append(f"profile {old.get('profile') or '(none)'} -> {new['profile']}")
    for key, label in (("features", ""), ("ssh_allow_from", "ssh_allow_from ")):
        before, after = list(old.get(key) or []), list(new.get(key) or [])
        added = [x for x in after if x not in before]
        removed = [x for x in before if x not in after]
        if added or removed:
            parts = [f"+ {x}" for x in added] + [f"- {x}" for x in removed]
            changes.append(label + ", ".join(parts))
    return changes
