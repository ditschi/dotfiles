"""Per-host SSH keys: Bitwarden SSH key items, repo public keys, Tailscale login."""

from __future__ import annotations

import getpass
import os
import shlex
import types
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence, Tuple

from . import system
from .core import (
    log,
    die,
    warn,
    write_private,
)

SSH_KEY = 5


def key_blob(public_key: str) -> str:
    """Key type and data without the comment, for comparing public keys."""
    return " ".join(public_key.split()[:2])


def key_fingerprint(public_key: str) -> str:
    if not public_key.strip():
        return ""
    result = system.run(
        ["ssh-keygen", "-l", "-E", "sha256", "-f", "-"],
        capture=True,
        input_text=public_key.strip() + "\n",
        check=False,
    )
    fields = (result.stdout or "").split()
    return fields[1] if result.returncode == 0 and len(fields) > 1 else ""


def item_keys(item: dict) -> Tuple[str, str]:
    """(private, public) of an SSH key item."""
    ssh_key = item.get("sshKey") or {}
    return ssh_key.get("privateKey") or "", ssh_key.get("publicKey") or ""


class SshKeysMixin:
    def select_host_ssh_key(self) -> Tuple[Optional[Path], bool]:
        """The host's existing key in the usual order, never creating one.

        (path, True) for a key, (None, True) when the host has none, (None, False)
        when the choice is unclear and nothing may be created or restored.
        """
        ssh_dir = self.home / ".ssh"
        ssh_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        explicit = os.environ.get("MACHINE_SSH_KEY", "")
        saved = self.saved_ssh_key()
        candidates = []
        for path in sorted(ssh_dir.iterdir()):
            if not path.is_file() or path.suffix == ".pub":
                continue
            try:
                with path.open("rb") as handle:
                    header = handle.readline(256)
            except OSError:
                log(f"cannot inspect SSH file {path}; skipping key creation")
                return None, False
            if header.startswith(b"-----BEGIN ") and b"PRIVATE KEY-----" in header:
                candidates.append(path)
        config = ssh_dir / "config"
        if config.is_file():
            for line in config.read_text().splitlines():
                try:
                    fields = shlex.split(line, comments=True)
                except ValueError:
                    continue
                if len(fields) == 2 and fields[0].lower() == "identityfile":
                    path = Path(fields[1].replace("%d", str(self.home))).expanduser()
                    if path.is_file() and path not in candidates:
                        candidates.append(path)
        private, public = self.host_key_paths()
        if explicit:
            private = Path(explicit).expanduser()
            if not private.is_file():
                log(f"selected SSH key missing: {private}; skipping creation")
                return None, False
            return private, True
        if saved:
            return saved, True
        if candidates:
            if (
                system.is_tty()
                and not getattr(self, "unattended", False)
                and len(candidates) > 1
            ):
                for index, path in enumerate(candidates, 1):
                    print(f"{index}: {path}")
                answer = input(
                    "Existing SSH key to reuse (number; empty skips): "
                ).strip()
                if not answer.isdigit() or not 1 <= int(answer) <= len(candidates):
                    log("SSH selection skipped; existing keys kept")
                    return None, False
                private = candidates[int(answer) - 1]
            else:
                preferred = [ssh_dir / "id_ed25519", ssh_dir / "id_rsa", private]
                private = next((path for path in preferred if path in candidates), None)
                if private is None:
                    if len(candidates) != 1:
                        log(
                            "ambiguous existing SSH keys; set MACHINE_SSH_KEY; "
                            + ", ".join(map(str, candidates))
                        )
                        return None, False
                    private = candidates[0]
            log(f"reusing SSH key {private}")
            return private, True
        if private.exists() or private.is_symlink() or public.exists():
            log(f"existing SSH key material at {private}; skipping creation")
            return None, False
        return None, True

    def saved_ssh_key(self) -> Optional[Path]:
        """The key chosen by an earlier run (MACHINE_SSH_KEY wins), if it still exists."""
        explicit = os.environ.get("MACHINE_SSH_KEY", "")
        if explicit:
            path = Path(explicit).expanduser()
            return path if path.is_file() else None
        selection = self.state_dir / "ssh-key-path"
        saved = selection.read_text().strip() if selection.is_file() else ""
        return Path(saved) if saved and Path(saved).is_file() else None

    def remember_ssh_key(self, private: Path) -> None:
        self.ensure_dirs()
        write_private(self.state_dir / "ssh-key-path", (str(private) + "\n").encode())

    def generate_host_ssh_key(self) -> Path:
        """ed25519 without passphrase: unattended Git/SSH use must not prompt."""
        private, _ = self.host_key_paths()
        log(f"generating {private}")
        system.run(
            [
                "ssh-keygen",
                "-t",
                "ed25519",
                "-f",
                str(private),
                "-N",
                "",
                "-C",
                f"{getpass.getuser()}@{system.hostname_short()}",
            ]
        )
        return private

    def ensure_public_key(self, private: Path) -> Optional[Path]:
        public = Path(str(private) + ".pub")
        if public.is_file():
            return public
        result = system.run(
            ["ssh-keygen", "-y", "-P", "", "-f", str(private)],
            capture=True,
            check=False,
        )
        if result.returncode != 0:
            log(f"cannot derive {public} without a passphrase; existing key kept")
            return None
        public.write_text(result.stdout.strip() + "\n")
        public.chmod(0o644)
        return public

    def bitwarden_session_ready(self) -> bool:
        """A session that works without a prompt (environment or ~/.env.local)."""
        if not system.have("bw"):
            return False
        self.load_local_bitwarden_settings()
        return self.bitwarden_session_valid()

    def host_ssh_item(self) -> Tuple[bool, Optional[dict]]:
        """(listed, SSH key item named like the host); secure notes are ignored."""
        items = self.bw_items_named(self.ssh_item_name())
        if items is None:
            log(f"cannot list Bitwarden items; {self.ssh_item_name()} not checked")
            return False, None
        return True, next((i for i in items if i.get("type") == SSH_KEY), None)

    def local_ssh_key(self, private: Path, public: Path) -> Optional[dict]:
        public_text = public.read_text(encoding="utf-8").strip()
        fingerprint = key_fingerprint(public_text)
        if not fingerprint:
            log(f"cannot read the fingerprint of {public}")
            return None
        return {
            "privateKey": private.read_text(encoding="utf-8"),
            "publicKey": public_text,
            "keyFingerprint": fingerprint,
        }

    def provision_host_ssh_key(self) -> int:
        """Setup: restore, else back up the local key, else generate one; no questions
        and no extra unlock prompt (only the session setup already has)."""
        if not self.ssh_class():
            log("no context (container): no SSH host key")
            return 0
        if not self.bitwarden_session_ready():
            log(
                "Bitwarden not unlocked; SSH host key not provisioned. With Bitwarden, "
                "the next `machine update` backs up an existing key and "
                "`machine setup` provisions a new host"
            )
            return 1
        private, ok = self.select_host_ssh_key()
        if not ok:
            return 1
        listed, item = self.host_ssh_item()
        if not listed:
            return 1
        generated = False
        if private is None and item:
            private = self.restore_key_from_item(item)
            if private is None:
                return 1
        if private is None:
            private = self.generate_host_ssh_key()
            generated = True
        public = self.ensure_public_key(private)
        if not public:
            return 1
        self.remember_ssh_key(private)
        if generated:
            self.print_new_key_hint(public)
        self.save_ssh_public_key_to_repo(public)
        return 0 if self.back_up_ssh_key(private, public, item) else 1

    def back_up_ssh_key(
        self, private: Path, public: Path, item: Optional[dict]
    ) -> bool:
        """Create a missing item; a different key only becomes an attention item."""
        name = self.ssh_item_name()
        local = self.local_ssh_key(private, public)
        if not local:
            return False
        if not item:
            return self.create_ssh_item(name, local) is not None
        stored = item_keys(item)[1]
        if key_blob(stored) == key_blob(local["publicKey"]):
            self.ssh_key_attention.unlink(missing_ok=True)
            return True
        reason = (
            f"{name} holds another key: Bitwarden {key_fingerprint(stored) or 'unknown'}, "
            f"local {local['keyFingerprint']} ({private})"
        )
        self.ensure_dirs()
        self.ssh_key_attention.write_text(reason + "\n", encoding="utf-8")
        log(f"{reason}; both kept, choose with: machine attention")
        return True

    def create_ssh_item(self, name: str, local: dict) -> Optional[dict]:
        """Create the SSH key item and read it back; None unless it is confirmed."""
        created = self.bw_create_item(
            {
                "type": SSH_KEY,
                "name": name,
                "notes": f"SSH host key for {system.hostname_short()}",
                "sshKey": local,
            }
        )
        item = (
            self.bw_get_item_raw(created["id"])
            if created and created.get("id")
            else None
        )
        if not item or key_fingerprint(item_keys(item)[1]) != local["keyFingerprint"]:
            log(f"failed to store the SSH key in {name}")
            return None
        log(f"stored the SSH key in {name}")
        return item

    def store_ssh_key(self, item: Optional[dict], local: dict) -> bool:
        """Overwrite the item with `local`, or create it."""
        name = self.ssh_item_name()
        if not item:
            return self.create_ssh_item(name, local) is not None
        item["sshKey"] = local
        if not self.bw_edit_item(item):
            log(f"failed to update {name}")
            return False
        log(f"updated {name}")
        return True

    def print_new_key_hint(self, public: Path) -> None:
        log(
            f"new SSH key {public}: {public.read_text().strip()}; register it "
            f"where needed (for example: gh ssh-key add {public})"
        )

    def save_ssh_public_key_to_repo(self, public: Path) -> None:
        """Home hosts: machine/ssh_keys/<hostname>.pub feeds authorized_keys via
        Ansible. Written without a question; committing stays manual."""
        if self.ssh_class() != "home" or system.in_docker():
            return
        path = self.repo / "machine" / "ssh_keys" / f"{system.hostname_short()}.pub"
        text = public.read_text(encoding="utf-8").strip() + "\n"
        if path.is_file() and key_blob(path.read_text(encoding="utf-8")) == key_blob(
            text
        ):
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        rel = path.relative_to(self.repo)
        log(f"wrote {rel}; commit and push it so other hosts can trust this key")

    def restore_key_from_item(self, item: dict) -> Optional[Path]:
        private, public = self.host_key_paths()
        if private.exists() or private.is_symlink():
            log(f"existing SSH key {private} kept; not restored from Bitwarden")
            return None
        return self.write_key_from_item(item, private)

    def write_key_from_item(self, item: dict, private: Path) -> Optional[Path]:
        private_text, public_text = item_keys(item)
        name = item.get("name") or self.ssh_item_name()
        if not private_text:
            log(f"{name} has no private key")
            return None
        if not private_text.endswith("\n"):
            private_text += "\n"
        write_private(private, private_text.encode())
        public = Path(str(private) + ".pub")
        if not public_text:
            result = system.run(
                ["ssh-keygen", "-y", "-P", "", "-f", str(private)],
                capture=True,
                check=False,
            )
            public_text = result.stdout if result.returncode == 0 else ""
        if public_text.strip():
            public.write_text(public_text.strip() + "\n", encoding="utf-8")
            public.chmod(0o644)
        log(f"restored {private} from {name}")
        return private

    def keep_old_key(self, private: Path) -> None:
        """Rename a key and its .pub to <key>.old-<YYYYMMDD> (never overwritten)."""
        stamp = datetime.now().strftime("%Y%m%d")
        suffix, number = f".old-{stamp}", 1
        while any(
            Path(f"{path}{suffix}").exists() for path in (private, f"{private}.pub")
        ):
            number += 1
            suffix = f".old-{stamp}-{number}"
        for path in (private, Path(f"{private}.pub")):
            if path.exists() or path.is_symlink():
                path.rename(f"{path}{suffix}")
                log(f"kept the old key as {path}{suffix}")

    @property
    def ssh_key_attention(self) -> Path:
        return self.state_dir / "ssh-key-attention"

    def check_ssh_key_backup(self) -> None:
        """Manual `machine update`: back up a missing item, report a different key;
        never prompts, generates or restores."""
        if (
            "ssh-host-key" not in self.saved_features()
            or not self.ssh_class()
            or system.in_docker()
            or os.environ.get("MACHINE_SKIP_BW") == "1"
        ):
            return
        if not self.bitwarden_session_ready():
            warn(
                "SSH host key not checked: Bitwarden is not unlocked. "
                "Log in with `machine env pull` in a terminal"
            )
            return
        private = self.saved_ssh_key()
        public = Path(str(private) + ".pub") if private else None
        if not public or not public.is_file():
            return
        if system.run(["bw", "sync"], capture=True, check=False).returncode:
            warn("SSH host key not checked: Bitwarden sync failed")
            return
        listed, item = self.host_ssh_item()
        if listed:
            self.back_up_ssh_key(private, public, item)

    def resolve_ssh_key_difference(self) -> int:
        """`machine ssh sync` / attention: ask which key wins when they differ."""
        if not self.ssh_class():
            log("no context (container): no SSH host key")
            return 0
        interactive = system.is_tty() and not getattr(self, "unattended", False)
        if not self.bitwarden_session_ready() and not (
            interactive and self.unlock_bitwarden()
        ):
            log("Bitwarden not unlocked; log in with `machine env pull` in a terminal")
            return 1
        private = self.saved_ssh_key()
        if private is None:
            private, ok = self.select_host_ssh_key()
            if not ok or private is None:
                log("no local SSH key selected; run machine setup")
                return 1
        public = self.ensure_public_key(private)
        local = self.local_ssh_key(private, public) if public else None
        listed, item = self.host_ssh_item()
        if not local or not listed:
            return 1
        self.remember_ssh_key(private)
        self.save_ssh_public_key_to_repo(public)
        if not item or key_blob(item_keys(item)[1]) == key_blob(local["publicKey"]):
            ok = bool(item) or self.store_ssh_key(None, local)
            if ok:
                log(f"{self.ssh_item_name()} holds the local key")
                self.ssh_key_attention.unlink(missing_ok=True)
            return 0 if ok else 1
        stored_fp = key_fingerprint(item_keys(item)[1]) or "unknown"
        log(
            f"{self.ssh_item_name()} holds another key: Bitwarden {stored_fp}, "
            f"local {local['keyFingerprint']} ({private})"
        )
        if not interactive:
            log("both keys unchanged; choose in a terminal: machine ssh sync")
            return 1
        choice = system.choose(
            "Which key wins? local (overwrite Bitwarden) / bitwarden (replace the "
            "local key, old one kept) / later",
            ["local", "bitwarden", "later"],
            "later",
        )
        if choice == "later":
            log("both keys unchanged")
            return 0
        if choice == "local":
            ok = self.store_ssh_key(item, local)
        else:
            self.keep_old_key(private)
            ok = self.write_key_from_item(item, private) is not None
            if ok:
                self.save_ssh_public_key_to_repo(Path(f"{private}.pub"))
        if ok:
            self.ssh_key_attention.unlink(missing_ok=True)
        return 0 if ok else 1

    def rotate_ssh_key(self) -> int:
        """New ed25519 key at id_ed25519_<hostname>, old one kept, item overwritten."""
        if not self.ssh_class():
            log("no context (container): no SSH host key")
            return 0
        if not self.unlock_bitwarden(allow_login=system.is_tty()):
            log("Bitwarden not unlocked; log in with `machine env pull` in a terminal")
            return 1
        listed, item = self.host_ssh_item()
        if not listed:
            return 1
        private, _ = self.host_key_paths()
        self.keep_old_key(private)
        self.generate_host_ssh_key()
        public = self.ensure_public_key(private)
        local = self.local_ssh_key(private, public) if public else None
        if not local:
            return 1
        self.remember_ssh_key(private)
        self.save_ssh_public_key_to_repo(public)
        self.print_new_key_hint(public)
        if not self.store_ssh_key(item, local):
            return 1
        self.ssh_key_attention.unlink(missing_ok=True)
        return 0

    def maybe_tailscale_login(self, features: Sequence[str]) -> None:
        if "tailscale" not in features:
            return
        if not system.have("tailscale"):
            log("tailscale feature set; package install via ansible")
            return
        if not system.is_tty():
            log("run: sudo tailscale up")
            return
        if system.prompt_yes_no("Log in to Tailscale now?", False):
            system.run(["sudo", "tailscale", "up"], check=False)
        else:
            log("skipped; later: sudo tailscale up")

    def cmd_ssh(self, args: types.SimpleNamespace) -> int:
        self.unattended = args.yes
        if args.action == "sync":
            return self.resolve_ssh_key_difference()
        if args.action == "rotate":
            return self.rotate_ssh_key()
        die(f"unknown ssh action: {args.action}")
        return 1
