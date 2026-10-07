"""Bitwarden: ~/.env, per-host SSH keys, authorized_keys."""

from __future__ import annotations

import getpass
import hashlib
import json
import os
import re
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


class BitwardenMixin:
    def unlock_bitwarden(self, *, allow_login: bool = False) -> bool:
        if not system.have("bw"):
            return False
        if not os.environ.get("BW_SESSION"):
            if not system.is_tty():
                return False
            status = system.run(["bw", "status"], capture=True, check=False)
            status_text = status.stdout or ""
            if allow_login and "unauthenticated" in status_text.lower():
                log("Bitwarden login")
                system.run(["bw", "login"], check=False)
            log("unlocking Bitwarden")
            result = system.run(["bw", "unlock", "--raw"], capture=True, check=False)
            session = (result.stdout or "").strip()
            if result.returncode != 0 or not session:
                return False
            os.environ["BW_SESSION"] = session
        system.run(["bw", "sync"], check=False, capture=True)
        return True

    def maybe_login_bitwarden(self) -> bool:
        if not system.have("bw"):
            return False
        if os.environ.get("BW_SESSION"):
            return self.unlock_bitwarden()
        if not system.is_tty():
            log("Bitwarden CLI present; skip login (no TTY)")
            return False
        if not system.prompt_yes_no("Log in to Bitwarden now?", False):
            log("Bitwarden login skipped")
            return False
        return self.unlock_bitwarden(allow_login=True)

    def item_to_dotenv(self, item: dict) -> str:
        chunks: List[str] = []
        notes = (item.get("notes") or "").replace("\r\n", "\n").strip("\n")
        if notes.strip():
            chunks.append(notes.rstrip())
        for field in item.get("fields") or []:
            name = (field.get("name") or "").strip()
            value = field.get("value")
            if not name or value in (None, ""):
                continue
            chunks.append(f"{name}={value}")
        return "\n".join(chunks)

    def bw_get_item_raw(self, name: str) -> Optional[dict]:
        result = system.run(
            ["bw", "get", "item", name, "--raw"], capture=True, check=False
        )
        if result.returncode != 0 or not (result.stdout or "").strip():
            return None
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return None

    def bw_get_item_dotenv(self, name: str) -> Optional[str]:
        item = self.bw_get_item_raw(name)
        if not item:
            return None
        return self.item_to_dotenv(item)

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

    def bw_upsert_ssh_item(
        self, item_name: str, public_key: str, private_key: Optional[str] = None
    ) -> bool:
        if not system.have("bw") or not os.environ.get("BW_SESSION"):
            return False
        existing = self.bw_get_item_raw(item_name)
        fields = [
            {"name": "public_key", "value": public_key, "type": 0},
        ]
        if private_key:
            fields.append({"name": "private_key", "value": private_key, "type": 1})
        if existing:
            existing["fields"] = fields
            payload = json.dumps(existing)
            encoded = system.run(
                ["bw", "encode"], capture=True, input_text=payload, check=False
            )
            if encoded.returncode != 0:
                return False
            result = system.run(
                ["bw", "edit", "item", existing["id"]],
                capture=True,
                input_text=encoded.stdout,
                check=False,
            )
            return result.returncode == 0
        template = {
            "type": 2,
            "name": item_name,
            "notes": f"SSH host key for {system.hostname_short()}",
            "secureNote": {"type": 0},
            "fields": fields,
        }
        payload = json.dumps(template)
        encoded = system.run(
            ["bw", "encode"], capture=True, input_text=payload, check=False
        )
        if encoded.returncode != 0:
            return False
        result = system.run(
            ["bw", "create", "item"],
            capture=True,
            input_text=encoded.stdout,
            check=False,
        )
        return result.returncode == 0

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

    def cmd_env_status(self) -> int:
        if not system.have("bw"):
            die("bw CLI not found; install Bitwarden CLI")
        if not self.unlock_bitwarden(allow_login=system.is_tty()):
            die("Bitwarden is locked")
        print(f"profile: {self.current_profile()}")
        print(f"host: {system.hostname_short()}")
        found = missing = 0
        for name in self.env_item_names():
            result = system.run(["bw", "get", "item", name], capture=True, check=False)
            if result.returncode == 0:
                print(f"found   {name}")
                found += 1
            else:
                print(f"missing {name}")
                missing += 1
        print(
            f"found={found} missing={missing} (missing is ok until you create the item)"
        )
        return 0

    def cmd_env_pull(self) -> int:
        if not system.have("bw"):
            log("bw not installed; skip ~/.env sync")
            return 0
        if self.current_profile() == "container":
            log("container profile: skip ~/.env sync")
            return 0
        if not self.unlock_bitwarden():
            log("Bitwarden locked; skip ~/.env sync")
            return 0
        system.run(["bw", "sync"], check=False, capture=True)
        names = self.env_item_names()
        chunks = [
            "# generated by machine env pull — do not commit",
            "# overlay extra keys in ~/.env.local (not managed)",
            "# Bitwarden items (later files/fields win):",
        ]
        chunks.extend(f"# - {name}" for name in names)
        chunks.append("")
        got = 0
        for name in names:
            body = self.bw_get_item_dotenv(name)
            if body:
                chunks.extend(["", f"# --- {name} ---", body.rstrip("\n")])
                got += 1
                log(f"env from {name}")
            else:
                log(f"no Bitwarden item {name} (skip)")
        env_path = self.home / ".env"
        if got == 0:
            log("no env items in Bitwarden; left ~/.env unchanged")
            return 0
        backup_dir = self.state_dir / "env-backup"
        backup_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        backup_dir.chmod(0o700)
        generated = "\n".join(chunks).rstrip() + "\n"
        if env_path.is_file():
            existing = env_path.read_text(encoding="utf-8")
            header = "\n".join(existing.splitlines()[:3])
            if "# generated by machine env pull" not in header:
                digest = hashlib.sha256(existing.encode()).hexdigest()[:16]
                bak = backup_dir / f"env.{digest}"
                if not bak.exists():
                    write_private(bak, existing.encode())
                log(f"backed up existing ~/.env to {bak}")
            assignment = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=")
            generated_keys = {
                match.group(1)
                for line in generated.splitlines()
                if (match := assignment.match(line))
            }
            old_keys = {
                match.group(1)
                for line in existing.splitlines()
                if (match := assignment.match(line))
            }
            overlay = self.home / ".env.local"
            overlay_text = overlay.read_text() if overlay.is_file() else ""
            overlay_keys = {
                match.group(1)
                for line in overlay_text.splitlines()
                if (match := assignment.match(line))
            }
            missing = old_keys - generated_keys - overlay_keys
            opaque = [
                line
                for line in existing.splitlines()
                if line.strip()
                and not line.lstrip().startswith("#")
                and not assignment.match(line)
            ]
            if missing or opaque:
                review_backup = backup_dir / (
                    "env." + hashlib.sha256(existing.encode()).hexdigest()[:16]
                )
                if not review_backup.exists():
                    write_private(review_backup, existing.encode())
                safe_lines = []
                for line in existing.splitlines():
                    match = assignment.match(line)
                    if match and match.group(1) in missing:
                        try:
                            shlex.split(line, comments=True)
                        except ValueError:
                            opaque.append(line)
                        safe_lines.append(line)
                if opaque or overlay.exists():
                    log(
                        f"WARNING: keeping {env_path}; keys absent from vault/overlay: "
                        f"{', '.join(sorted(missing)) or 'complex shell content'}; "
                        f"review {overlay} and backup {review_backup}"
                    )
                    return 0
                write_private(overlay, ("\n".join(safe_lines) + "\n").encode())
                log(
                    f"preserved local-only keys in {overlay}; review backup {review_backup}"
                )
        write_private(env_path, generated.encode())
        log(f"wrote {env_path} from {got} Bitwarden item(s)")
        return 0

    def cmd_ssh(self, args: types.SimpleNamespace) -> int:
        if args.action == "publish":
            self.unattended = args.yes
            store = bool(args.private)
            if not args.yes and system.is_tty() and not store:
                store = system.prompt_yes_no("Also store the private key?", False)
            return self.publish_ssh_key(store_private=store)
        if args.action == "restore":
            return self.restore_ssh_key()
        die(f"unknown ssh action: {args.action}")
        return 1
