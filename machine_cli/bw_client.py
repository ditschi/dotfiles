"""Thin `bw` client: login/unlock, local settings, item get/upsert."""

from __future__ import annotations

import json
import os
import re
import shlex
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlsplit

from . import system
from .core import (
    log,
    die,
    write_private,
)


DEFAULT_BW_EMAIL = "chris@ditschers.de"
# Variables read from the Telegraf item (spec secret-tools, "Influx item layout")
# and the Ansible variables they become (group_vars/all/packages.yml).
INFLUX_KEYS = {
    "INFLUX_URL": "influx_url",
    "INFLUX_TOKEN": "influx_token",
    "INFLUX_ORG": "influx_org",
    "INFLUX_BUCKET": "influx_bucket",
    "INFLUX_TELEGRAF_CONFIG_BASE": "influx_telegraf_config_base",
    "INFLUXDB_USER": "influx_username",
    "INFLUXDB_USER_PASSWORD": "influx_password",  # pragma: allowlist secret
    "INFLUXDB_DB": "influx_database",
}


class BwClientMixin:
    def unlock_bitwarden(
        self, *, allow_login: bool = False, _fresh: bool = False
    ) -> bool:
        if not system.have("bw"):
            return False
        # Reuse a saved session (~/.env.local; the environment wins) so repeated
        # setup/update runs do not ask for the master password again; drop it only
        # when bw no longer accepts it.
        if not _fresh:
            self.load_local_bitwarden_settings()
        if (
            not _fresh
            and os.environ.get("BW_SESSION")
            and not self.bitwarden_session_valid()
        ):
            log("saved BW_SESSION is expired or invalid; unlocking again")
            os.environ.pop("BW_SESSION")
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
                    return self.unlock_bitwarden(_fresh=True)
            log("unlocking Bitwarden")
            result = system.run(
                ["bw", "unlock", "--raw"], interactive_stdout=True, check=False
            )
            session = (result.stdout or "").strip()
            if result.returncode != 0 or not session:
                log("WARNING: Bitwarden unlock failed; environment sync skipped")
                return False
            os.environ["BW_SESSION"] = session
            self._bw_new_session = True
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
        if system.have("bw"):
            self.load_local_bitwarden_settings()
            if self.bitwarden_session_valid():
                return True
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
        self._bw_new_session = False  # asked here; env pull must not ask again
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

    def offer_saving_bitwarden_session(self) -> None:
        """After a fresh interactive unlock: offer (default no) to keep the token in
        ~/.env.local, so later setup/update runs need no master password."""
        if not getattr(self, "_bw_new_session", False):
            return
        self._bw_new_session = False
        if getattr(self, "unattended", False) or not system.is_tty():
            return
        if system.prompt_yes_no(
            "Save the Bitwarden unlock token in ~/.env.local (mode 600) so the next "
            "setup/update does not ask again? It grants vault access until locked.",
            False,
        ):
            self.save_bitwarden_local_settings()

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

    def influx_credentials(self) -> Dict[str, str]:
        """INFLUX_* values of the Telegraf item; empty when bw is missing or locked.

        Custom fields named like the variables win; a login item's password and
        first URI fill INFLUX_TOKEN and INFLUX_URL. Read once per command."""
        cached = getattr(self, "_influx_credentials", None)
        if cached is not None:
            return cached
        values: Dict[str, str] = {}
        if not self.unlock_bitwarden():
            log(f"Bitwarden not unlocked; Telegraf without item '{self.influx_item}'")
        else:
            item = self.bw_get_item_raw(self.influx_item)
            if not item:
                log(f"Bitwarden item '{self.influx_item}' not found")
            else:
                login = item.get("login") or {}
                uris = [u.get("uri") for u in login.get("uris") or [] if u.get("uri")]
                if login.get("password"):
                    values["INFLUX_TOKEN"] = login["password"]
                if uris:
                    values["INFLUX_URL"] = uris[0]
                for field in item.get("fields") or []:
                    name = (field.get("name") or "").strip()
                    if name in INFLUX_KEYS and field.get("value"):
                        values[name] = str(field["value"])
        self._influx_credentials = values
        return values

    def bw_items_named(self, name: str) -> Optional[List[dict]]:
        """Items whose name is exactly `name`; None when bw cannot list them."""
        result = system.run(
            ["bw", "list", "items", "--search", name], capture=True, check=False
        )
        if result.returncode != 0:
            return None
        try:
            items = json.loads(result.stdout or "[]")
        except json.JSONDecodeError:
            return None
        return [item for item in items if item.get("name") == name]

    def _bw_send_item(self, command: List[str], item: dict) -> Optional[dict]:
        encoded = system.run(
            ["bw", "encode"], capture=True, input_text=json.dumps(item), check=False
        )
        if encoded.returncode != 0:
            return None
        result = system.run(
            ["bw", *command], capture=True, input_text=encoded.stdout, check=False
        )
        if result.returncode != 0:
            return None
        try:
            return json.loads(result.stdout or "{}")
        except json.JSONDecodeError:
            return {}

    def bw_create_item(self, item: dict) -> Optional[dict]:
        return self._bw_send_item(["create", "item"], item)

    def bw_edit_item(self, item: dict) -> bool:
        return self._bw_send_item(["edit", "item", item["id"]], item) is not None
