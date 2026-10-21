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
from urllib.parse import urlsplit


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
                result = system.run(["bw", "login", "--raw"], capture=True, check=False)
                if result.returncode != 0:
                    log("WARNING: Bitwarden login failed; environment sync skipped")
                    return False
                session = (result.stdout or "").strip()
                if session:
                    os.environ["BW_SESSION"] = session
                    return self.unlock_bitwarden()
            log("unlocking Bitwarden")
            result = system.run(["bw", "unlock", "--raw"], capture=True, check=False)
            session = (result.stdout or "").strip()
            if result.returncode != 0 or not session:
                log("WARNING: Bitwarden unlock failed; environment sync skipped")
                return False
            os.environ["BW_SESSION"] = session
        result = system.run(["bw", "sync"], check=False, capture=True)
        if result.returncode:
            log(
                "WARNING: Bitwarden sync failed; check server, network and unlock session"
            )
            return False
        return True

    def require_bitwarden(self) -> bool:
        """Explicit commands: report what is missing and offer to set it up."""
        interactive = system.is_tty() and not getattr(self, "unattended", False)
        if not system.have("bw"):
            if not interactive:
                log(
                    "Bitwarden CLI (bw) is not installed; run `machine env pull` "
                    "in a terminal to install and set it up"
                )
                return False
            if not system.prompt_yes_no(
                "Bitwarden CLI (bw) is not installed. Install it now?", True
            ) or not self.ensure_bitwarden_cli():
                log("Bitwarden CLI not installed; nothing done")
                return False
        if os.environ.get("BW_SESSION"):
            return True
        if not interactive:
            log(
                "Bitwarden is installed but not unlocked (no BW_SESSION); "
                "run `machine env pull` in a terminal to log in"
            )
            return False
        log("Bitwarden is installed but not logged in/unlocked yet")
        return self.setup_bitwarden()

    def setup_bitwarden(self) -> bool:
        if getattr(self, "unattended", False) or not system.is_tty():
            log(
                "Bitwarden setup skipped (non-interactive); run machine setup to log in"
            )
            return False
        if not system.have("bw"):
            log("WARNING: Bitwarden CLI unavailable; login setup skipped")
            return False
        if not system.prompt_yes_no("Configure Bitwarden and log in now?", False):
            log("Bitwarden setup skipped")
            return False

        settings = {}
        local = self.home / ".env.local"
        if local.is_file():
            for line in local.read_text().splitlines():
                match = re.match(
                    r"^\s*(?:export\s+)?"
                    r"(BW_SESSION|NODE_EXTRA_CA_CERTS|NODE_USE_ENV_PROXY)=(.*)$",
                    line,
                )
                if match:
                    try:
                        value = shlex.split(match.group(2), comments=True)
                    except ValueError:
                        die(
                            f"cannot parse {match.group(1)} in {local}; repair it first"
                        )
                    if len(value) != 1:
                        die(
                            f"expected one literal value for {match.group(1)} in {local}"
                        )
                    settings[match.group(1)] = value[0]
        for key, value in settings.items():
            os.environ.setdefault(key, value)
        status = self.bitwarden_setup_status()
        if status.get("status") != "unlocked":
            os.environ.pop("BW_SESSION", None)
        if status.get("status") == "unauthenticated":
            current = status.get("serverUrl") or "https://vault.bitwarden.com"
            server = input(f"Bitwarden server URL [{current}]: ").strip() or current
            parsed = urlsplit(server)
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.query
                or parsed.fragment
            ):
                die("Bitwarden server must be an HTTPS URL without credentials")
            system.run(["bw", "config", "server", server], capture=True)
        else:
            log(f"using configured Bitwarden server: {status.get('serverUrl', '')}")

        if not self.unlock_bitwarden(allow_login=True):
            log("WARNING: Bitwarden setup incomplete; local settings not saved")
            return False
        if system.prompt_yes_no(
            "Save the unlock token and CA/proxy settings in ~/.env.local "
            "(mode 600)? The token grants vault access until invalidated.",
            False,
        ):
            self.save_bitwarden_local_settings()
        return True

    def bitwarden_setup_status(self) -> dict:
        attempted = set()
        while True:
            result = system.run(["bw", "status"], capture=True, check=False)
            error = (result.stderr or "").lower()
            certificate_error = any(
                message in error
                for message in (
                    "unable_to_get_issuer_cert",
                    "unable to get local issuer certificate",
                    "self_signed_cert",
                    "self signed certificate",
                )
            )
            network_error = any(
                message in error
                for message in ("enotfound", "econnrefused", "etimedout", "eai_again")
            )
            ca_bundle = Path("/etc/ssl/certs/ca-certificates.crt")
            key = ""
            value = ""
            question = ""
            if (
                certificate_error
                and not os.environ.get("NODE_EXTRA_CA_CERTS")
                and ca_bundle.is_file()
            ):
                key, value = "NODE_EXTRA_CA_CERTS", str(ca_bundle)
                question = (
                    "Bitwarden reported a certificate trust error. "
                    "Retry using Ubuntu's CA bundle (TLS verification stays enabled)?"
                )
            elif (
                network_error
                and os.environ.get("NODE_USE_ENV_PROXY") != "1"
                and any(os.environ.get(name) for name in ("HTTPS_PROXY", "https_proxy"))
            ):
                key, value = "NODE_USE_ENV_PROXY", "1"
                question = (
                    "Bitwarden reported a DNS/connection error while an HTTPS proxy "
                    "is configured. Retry with Node environment-proxy support?"
                )
            if key and key not in attempted:
                attempted.add(key)
                if system.prompt_yes_no(question, False):
                    os.environ[key] = value
                    continue
            if result.returncode or certificate_error or network_error:
                die(
                    "Bitwarden connection check failed; check server, Kerberos/proxy "
                    "and certificate trust. Local settings were not changed."
                )
            try:
                status = json.loads(result.stdout)
            except json.JSONDecodeError:
                die("cannot read Bitwarden status; local settings were not changed")
            if not isinstance(status, dict) or status.get("status") not in {
                "unauthenticated",
                "locked",
                "unlocked",
            }:
                die("invalid Bitwarden status; local settings were not changed")
            return status

    def save_bitwarden_local_settings(self) -> None:
        settings = {
            key: os.environ[key]
            for key in ("BW_SESSION", "NODE_EXTRA_CA_CERTS", "NODE_USE_ENV_PROXY")
            if os.environ.get(key)
        }
        if "BW_SESSION" not in settings:
            die("no Bitwarden unlock session to save")
        path = self.home / ".env.local"
        existing = path.read_text() if path.is_file() else ""
        assignment = re.compile(
            r"^\s*(?:export\s+)?(BW_SESSION|NODE_EXTRA_CA_CERTS|NODE_USE_ENV_PROXY)="
        )
        lines = []
        for line in existing.splitlines(keepends=True):
            match = assignment.match(line)
            if not match or match.group(1) not in settings:
                lines.append(line)
        content = "".join(lines)
        if content and not content.endswith("\n"):
            content += "\n"
        content += "".join(
            f"export {key}={shlex.quote(value)}\n" for key, value in settings.items()
        )
        write_private(path, content.encode())
        log(f"saved Bitwarden local settings to {path} (mode 600); token not printed")

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
        if not self.require_bitwarden() or not self.unlock_bitwarden():
            die("Bitwarden is not ready; see the messages above")
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

    def cmd_env_pull(self, interactive: bool = False) -> int:
        if self.current_profile() == "container":
            log("container profile: skip ~/.env sync")
            return 0
        if interactive:
            if not self.require_bitwarden():
                return 1
        elif not system.have("bw"):
            log("Bitwarden CLI (bw) not installed; skip ~/.env sync (machine env pull)")
            return 0
        if not self.unlock_bitwarden():
            log("Bitwarden not unlocked; skip ~/.env sync (run machine env pull)")
            return 1 if interactive else 0
        system.run(["bw", "sync"], capture=True)
        names = self.env_item_names()
        assignment = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=")
        env_path = self.home / ".env"
        host_path = self.home / ".env.host"
        chunks = {
            path: [
                "# generated by machine env pull — do not commit",
                "# local overrides in ~/.env.local (never overwritten)",
                "# Bitwarden items (later files/fields win):",
                *(f"# - {name}" for name in selected),
                "",
            ]
            for path, selected in (
                (env_path, names[:-1]),
                (host_path, names[-1:]),
            )
        }
        got = 0
        for name in names:
            body = self.bw_get_item_dotenv(name)
            if body:
                if any(
                    match.group(1) == "BW_SESSION"
                    for line in body.splitlines()
                    if (match := assignment.match(line))
                ):
                    die(f"BW_SESSION must remain local; remove it from {name}")
                path = host_path if name == names[-1] else env_path
                chunks[path].extend(["", f"# --- {name} ---", body.rstrip("\n")])
                got += 1
                log(f"env from {name}")
            else:
                log(f"no Bitwarden item {name} (skip)")
        if got == 0:
            log("no env items in Bitwarden; left ~/.env and ~/.env.host unchanged")
            return 0
        backup_dir = self.state_dir / "env-backup"
        backup_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        backup_dir.chmod(0o700)
        generated = {
            path: "\n".join(lines).rstrip("\n") + "\n" for path, lines in chunks.items()
        }
        generated_keys = {
            match.group(1)
            for content in generated.values()
            for line in content.splitlines()
            if (match := assignment.match(line))
        }
        overlay = self.home / ".env.local"
        overlay_text = overlay.read_text() if overlay.is_file() else ""
        overlay_keys = {
            match.group(1)
            for line in overlay_text.splitlines()
            if (match := assignment.match(line))
        }
        safe_lines = []
        blocked = False
        for path, content in generated.items():
            if not path.is_file():
                continue
            existing = path.read_text(encoding="utf-8")
            if existing != content:
                digest = hashlib.sha256(existing.encode()).hexdigest()[:16]
                bak = backup_dir / f"{path.name.lstrip('.')}.{digest}"
                if not bak.exists():
                    write_private(bak, existing.encode())
                log(f"backed up existing {path} to {bak}")
            else:
                continue
            old_keys = {
                match.group(1)
                for line in existing.splitlines()
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
                        f"WARNING: keeping environment files; review {path}; "
                        "keys absent from vault/overlay: "
                        f"{', '.join(sorted(missing)) or 'complex shell content'}; "
                        f"review {overlay} and backup {bak}"
                    )
                    blocked = True
        if blocked:
            die("environment sync aborted; resolve local-only content before retrying")
        if safe_lines:
            write_private(overlay, ("\n".join(safe_lines) + "\n").encode())
            log(f"preserved local-only keys in {overlay}; review {backup_dir}")
        for path, content in generated.items():
            write_private(path, content.encode())
        log(f"wrote {env_path} and {host_path} from {got} Bitwarden item(s)")
        return 0

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
