"""Technical-user passwords: Azure Key Vault is the source, Bitwarden follows (spec techuser-password-sync)."""

from __future__ import annotations

import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Dict, Optional, Tuple

from . import system
from .core import log, warn

TECHUSERS_KEY = "AZKV_TECHUSERS"
ENTRY = re.compile(r"^([A-Za-z0-9_.-]+)=([A-Za-z0-9-]+)/([A-Za-z0-9-]+)$")
ASSIGNMENT = re.compile(rf"^\s*(?:export\s+)?{TECHUSERS_KEY}=(.*)$")
BW_LOGIN = 1
AZ_TIMEOUT = 30
# A vault that refuses this client (firewall, VPN) is out of reach, like a missing login.
OUT_OF_REACH = (
    "ForbiddenByFirewall",
    "ForbiddenByConnection",
    "Public network access",
    "Client address is not authorized",
)
# az messages about one secret, not about the login or the network
SECRET_PROBLEMS = {
    "SecretNotFound": "secret not found",  # pragma: allowlist secret
    "Forbidden": "no access to the secret",
    "AuthorizationFailed": "no access to the secret",
}


class TechuserSyncMixin:
    @property
    def azure_notice_path(self) -> Path:
        return self.state_dir / "azure-state"

    def techuser_mapping(self) -> Dict[str, Tuple[str, str]]:
        """user -> (vault, secret) from AZKV_TECHUSERS.

        The env files win, because env pull has just written them; the process
        environment counts only when no file sets the key. Nothing is executed."""
        value: Optional[str] = None
        for name in (".env", ".env.host", ".env.local"):
            path = self.home / name
            if not path.is_file():
                continue
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                match = ASSIGNMENT.match(line)
                if not match:
                    continue
                try:
                    value = " ".join(shlex.split(match.group(1), comments=True))
                except ValueError:
                    warn(f"cannot parse {TECHUSERS_KEY} in {path}")
        if value is None:
            # a plain env file keeps the quotes around the value in the environment
            value = os.environ.get(TECHUSERS_KEY, "").replace('"', "").replace("'", "")
        mapping: Dict[str, Tuple[str, str]] = {}
        for entry in value.split():
            match = ENTRY.match(entry)
            if match:
                mapping[match.group(1)] = (match.group(2), match.group(3))
            else:
                warn(
                    f"{TECHUSERS_KEY}: ignoring '{entry.split('=')[0]}', expected user=vault/secret"
                )
        return mapping

    def keyvault_secret(self, vault: str, secret: str) -> Tuple[Optional[str], str]:
        """(password, "") or (None, reason); reason "login" means az or the vault is out of reach."""
        try:
            result = subprocess.run(
                [
                    "az",
                    "keyvault",
                    "secret",
                    "show",
                    "--id",
                    f"https://{vault}.vault.azure.net/secrets/{secret}",
                    "--query",
                    "value",
                    "-o",
                    "tsv",
                ],
                capture_output=True,
                text=True,
                timeout=AZ_TIMEOUT,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return None, "login"
        value = (result.stdout or "").rstrip("\n")
        if result.returncode == 0 and value:
            return value, ""
        stderr = result.stderr or ""
        if any(marker in stderr for marker in OUT_OF_REACH):
            return None, "login"
        for marker, reason in SECRET_PROBLEMS.items():
            if marker in stderr:
                return None, reason
        return None, "login"

    def _techuser_bitwarden_ready(self, login: bool) -> bool:
        if not system.have("bw"):
            log(
                "technical user passwords not synced: Bitwarden CLI (bw) is not installed"
            )
            return False
        if login:
            ready = self.require_bitwarden() and self.unlock_bitwarden()
        else:
            ready = self.bitwarden_session_ready()
        if not ready:
            log(
                "technical user passwords not synced: Bitwarden is not unlocked "
                "(log in with `machine env pull` in a terminal)"
            )
        return ready

    def record_azure_notice(self) -> None:
        try:
            self.state_dir.mkdir(parents=True, exist_ok=True)
            self.azure_notice_path.write_text("az login needed\n", encoding="utf-8")
        except OSError:
            pass

    def clear_azure_notice(self) -> None:
        try:
            self.azure_notice_path.unlink(missing_ok=True)
        except OSError:
            pass

    def sync_techuser_passwords_step(self) -> int:
        """The update step: whatever goes wrong, the update goes on."""
        try:
            return self.sync_techuser_passwords(login=system.is_tty())
        except (SystemExit, OSError, ValueError, subprocess.CalledProcessError) as exc:
            warn(f"technical user passwords not synced: {exc or type(exc).__name__}")
            return 0

    def sync_techuser_passwords(
        self, interactive: bool = False, login: bool = False
    ) -> int:
        """Copy each Key Vault password into the existing Bitwarden login item of the same name.

        Only a differing password is written. Items are never created, and a missing
        az login is an attention item, not a failure."""
        users = self.techuser_mapping()
        if not users:
            self.clear_azure_notice()
            if interactive:
                log(f"{TECHUSERS_KEY} is not set; nothing to sync")
            return 0
        if not system.have("az"):
            self.clear_azure_notice()
            log("technical user passwords not synced: Azure CLI (az) is not installed")
            return 1 if interactive else 0
        if not self._techuser_bitwarden_ready(interactive or login):
            return 1 if interactive else 0
        system.run(["bw", "sync"], capture=True, check=False)
        failed = False
        for user, (vault, secret) in users.items():
            password, reason = self.keyvault_secret(vault, secret)
            if password is None:
                if reason == "login":
                    self.record_azure_notice()
                    warn(
                        "technical user passwords not synced: az is not logged in or "
                        f"{vault} is not reachable (listed in machine attention)"
                    )
                    return 1 if interactive else 0
                warn(f"{user}: Key Vault {vault}: {reason}")
                failed = True
                continue
            failed |= not self._sync_techuser_item(user, password)
        self.clear_azure_notice()
        return 1 if failed and interactive else 0

    def _sync_techuser_item(self, user: str, password: str) -> bool:
        items = self.bw_items_named(user)
        if items is None:
            warn(f"cannot list Bitwarden items; {user} not synced")
            return False
        logins = [item for item in items if item.get("type") == BW_LOGIN]
        if not logins:
            warn(f"no Bitwarden login item named {user}; nothing created")
            return False
        if len(logins) > 1:
            warn(f"several Bitwarden login items named {user}; left alone")
            return False
        item = logins[0]
        login = item.setdefault("login", {})
        if login.get("password") == password:
            return True
        login["password"] = password
        if not self.bw_edit_item(item):
            warn(f"could not update the Bitwarden item {user}")
            return False
        log(f"{user}: Bitwarden password updated from Key Vault")
        return True
