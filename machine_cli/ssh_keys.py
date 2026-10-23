"""Per-host SSH keys in Bitwarden, authorized_keys, Tailscale login."""

from __future__ import annotations

import getpass
import json
import os
import shlex
import types
from pathlib import Path
from typing import List, Optional, Sequence

from . import system
from .core import (
    log,
    die,
    write_private,
)


class SshKeysMixin:
    def bw_ssh_hosts(self, profile: Optional[str] = None) -> List[str]:
        """Hostnames with a published SSH key in the profile's class (home / work)."""
        klass = self.ssh_class(profile)
        if not klass or not system.have("bw") or not os.environ.get("BW_SESSION"):
            return []
        prefix = f"ssh/{klass}/hosts/"
        result = system.run(
            ["bw", "list", "items", "--search", prefix], capture=True, check=False
        )
        try:
            items = json.loads(result.stdout or "[]")
        except json.JSONDecodeError:
            return []
        names = [str(item.get("name") or "") for item in items]
        return sorted({n.removeprefix(prefix) for n in names if n.startswith(prefix)})

    def ensure_host_ssh_key(self, store_private: bool = False) -> Optional[Path]:
        ssh_dir = self.home / ".ssh"
        ssh_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        selection = self.state_dir / "ssh-key-path"
        explicit = os.environ.get("MACHINE_SSH_KEY", "")
        saved = selection.read_text().strip() if selection.is_file() else ""
        candidates = []
        for path in sorted(ssh_dir.iterdir()):
            if not path.is_file() or path.suffix == ".pub":
                continue
            try:
                with path.open("rb") as handle:
                    header = handle.readline(256)
            except OSError:
                log(f"cannot inspect SSH file {path}; skipping key creation")
                return None
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
                return None
        elif saved and Path(saved).is_file():
            private = Path(saved)
        elif candidates:
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
                    return None
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
                        return None
                    private = candidates[0]
            log(f"reusing SSH key {private}")
        elif private.exists() or private.is_symlink() or public.exists():
            log(f"existing SSH key material at {private}; skipping creation")
            return None
        else:
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
        public = Path(str(private) + ".pub")
        if not public.is_file():
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
        self.ensure_dirs()
        write_private(selection, (str(private) + "\n").encode())
        return public

    def publish_ssh_key(self, store_private: bool = False) -> int:
        klass = self.ssh_class()
        if not klass:
            log("container profile: skip SSH Bitwarden publish")
            return 0
        public = self.ensure_host_ssh_key(store_private=store_private)
        if not public:
            return 1
        pub_text = public.read_text(encoding="utf-8").strip()
        private_text = None
        if store_private:
            private = public.with_suffix("")
            private_text = private.read_text(encoding="utf-8")
        if not self.unlock_bitwarden():
            log("Bitwarden locked; key kept local (machine ssh publish later)")
            return 0
        item = self.ssh_item_name()
        if self.bw_upsert_ssh_item(item, pub_text, private_text):
            log(f"published SSH public key to {item}")
            return 0
        log(f"failed to publish SSH key to {item}")
        return 1

    def restore_ssh_key(self) -> int:
        if not self.unlock_bitwarden(allow_login=system.is_tty()):
            die("Bitwarden locked")
        item = self.bw_get_item_raw(self.ssh_item_name())
        if not item:
            die(f"no Bitwarden item {self.ssh_item_name()}")
        private_value = ""
        for field in item.get("fields") or []:
            if field.get("name") == "private_key":
                private_value = field.get("value") or ""
        if not private_value:
            die("item has no private_key field")
        private, public = self.host_key_paths()
        if private.exists() or private.is_symlink():
            die(
                f"refusing to overwrite existing SSH key {private}; move it deliberately before restore"
            )
        private.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        write_private(private, private_value.encode())
        system.run(["ssh-keygen", "-y", "-f", str(private)], check=False)
        pub = system.run(
            ["ssh-keygen", "-y", "-f", str(private)], capture=True, check=False
        )
        if pub.returncode == 0 and pub.stdout:
            public.write_text(pub.stdout.strip() + "\n", encoding="utf-8")
            public.chmod(0o644)
        log(f"restored {private}")
        return 0

    def apply_authorized_keys_from_bw(self, allow_from: Sequence[str]) -> None:
        if not allow_from:
            return
        klass = self.ssh_class()
        if not klass or not self.unlock_bitwarden():
            log("skip authorized_keys (no class or Bitwarden locked)")
            return
        keys: List[str] = []
        for host in allow_from:
            item = self.bw_get_item_raw(f"ssh/{klass}/hosts/{host}")
            if not item:
                log(f"missing ssh/{klass}/hosts/{host}")
                continue
            for field in item.get("fields") or []:
                if field.get("name") == "public_key" and field.get("value"):
                    keys.append(str(field["value"]).strip())
        if not keys:
            return
        auth = self.home / ".ssh" / "authorized_keys"
        auth.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        existing = auth.read_text(encoding="utf-8") if auth.is_file() else ""
        lines = [line for line in existing.splitlines() if line.strip()]
        for key in keys:
            if key not in lines:
                lines.append(key)
        auth.write_text("\n".join(lines) + "\n", encoding="utf-8")
        auth.chmod(0o600)
        log(f"updated {auth} with {len(keys)} key(s)")

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
        if args.action == "publish":
            self.unattended = args.yes
            store = bool(args.private)
            if not args.yes and system.is_tty() and not store:
                store = system.prompt_yes_no("Also store the private key?", False)
            self.require_bitwarden()
            return self.publish_ssh_key(store_private=store)
        if args.action == "restore":
            self.require_bitwarden()
            return self.restore_ssh_key()
        die(f"unknown ssh action: {args.action}")
        return 1
