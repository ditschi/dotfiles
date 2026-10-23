"""Thin `bw` client: login/unlock, local settings, item get/upsert."""

from __future__ import annotations

import json
import os
import re
import shlex
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit

from . import system
from .core import (
    log,
    die,
    write_private,
)


DEFAULT_BW_EMAIL = "chris@ditschers.de"


class BwClientMixin:
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
                default_email = os.environ.get("BW_EMAIL") or DEFAULT_BW_EMAIL
                email = input(f"Bitwarden account email [{default_email}]: ").strip()
                result = system.run(
                    ["bw", "login", email or default_email, "--raw"],
                    interactive_stdout=True,
                    check=False,
                )
                if result.returncode != 0:
                    log("WARNING: Bitwarden login failed; environment sync skipped")
                    return False
                session = (result.stdout or "").strip()
                if session:
                    os.environ["BW_SESSION"] = session
                    return self.unlock_bitwarden()
            log("unlocking Bitwarden")
            result = system.run(
                ["bw", "unlock", "--raw"], interactive_stdout=True, check=False
            )
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
            if (
                not system.prompt_yes_no(
                    "Bitwarden CLI (bw) is not installed. Install it now?", True
                )
                or not self.ensure_bitwarden_cli()
            ):
                log("Bitwarden CLI not installed; nothing done")
                return False
        self.load_local_bitwarden_settings()
        if self.bitwarden_session_valid():
            return True
        if os.environ.get("BW_SESSION"):
            log("saved BW_SESSION is expired or invalid; log in again")
            os.environ.pop("BW_SESSION")
        if not interactive:
            log(
                "Bitwarden is installed but not unlocked (no BW_SESSION); "
                "run `machine env pull` in a terminal to log in"
            )
            return False
        log("Bitwarden is installed but not logged in/unlocked yet")
        return self.setup_bitwarden()

    def load_local_bitwarden_settings(self) -> None:
        """Export BW_SESSION and CA/proxy settings from ~/.env.local (env wins)."""
        local = self.home / ".env.local"
        if not local.is_file():
            return
        for line in local.read_text().splitlines():
            match = re.match(
                r"^\s*(?:export\s+)?"
                r"(BW_SESSION|NODE_EXTRA_CA_CERTS|NODE_USE_ENV_PROXY)=(.*)$",
                line,
            )
            if not match:
                continue
            try:
                value = shlex.split(match.group(2), comments=True)
            except ValueError:
                die(f"cannot parse {match.group(1)} in {local}; repair it first")
            if len(value) != 1:
                die(f"expected one literal value for {match.group(1)} in {local}")
            os.environ.setdefault(match.group(1), value[0])

    def bitwarden_session_valid(self) -> bool:
        if not os.environ.get("BW_SESSION"):
            return False
        result = system.run(["bw", "status"], capture=True, check=False)
        try:
            return json.loads(result.stdout or "{}").get("status") == "unlocked"
        except json.JSONDecodeError:
            return False

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

        self.load_local_bitwarden_settings()
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
            f"{key}={shlex.quote(value)}\n" for key, value in settings.items()
        )
        write_private(path, content.encode())
        log(f"saved Bitwarden local settings to {path} (mode 600); token not printed")

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
