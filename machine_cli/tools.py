"""Bootstrap tools and the git / ansible runners."""

from __future__ import annotations

import atexit
import getpass
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional


from . import system
from .bw_client import INFLUX_KEYS
from .core import (
    debug_enabled,
    log,
    die,
    parse_profile_file,
)


# The zsh check reports the first stderr line; this one only means a tool is not installed.
MISE_MISSING = re.compile(r"^zsh printed errors on startup: mise WARN\s+missing: ")


class ToolsMixin:
    def health_check_after_apply(self) -> bool:
        ok = True
        zsh = self.zsh_health_failure()
        if MISE_MISSING.match(zsh):
            log("zsh reports missing mise tools; running mise install once")
            system.run(
                ["mise", "install"], env=self.dotfiles_env(), cwd=self.repo, check=False
            )
            zsh = self.zsh_health_failure()
            if MISE_MISSING.match(zsh):
                zsh += " (run: mise install)"
        for reason in (zsh, self.dotfiles_health_failure()):
            if reason:
                log(f"health check failed: {reason}")
                ok = False
        # sshd config is validated as root inside the playbook (role sshd_home,
        # "Validate sshd configuration"). Here as a normal user `sshd -t` always
        # fails (host keys unreadable) and `sudo -n` fails without cached
        # credentials, which rolled back every successful apply.
        # Telegraf is reported, never reverted (spec system-provisioning).
        problem = self.telegraf_problem()
        if problem:
            log(f"health check: {self.telegraf_problem_text(problem)} (warn)")
        return ok

    def passwordless_sudo(self) -> bool:
        if os.geteuid() == 0:
            return True
        if not system.have("sudo"):
            return False
        result = system.run(["sudo", "-n", "true"], check=False, capture=True)
        return result.returncode == 0

    def install_pkg_if_missing(self, package: str) -> bool:
        check = system.run(["dpkg", "-s", package], check=False, capture=True)
        if check.returncode == 0:
            return True
        root = os.geteuid() == 0
        can_sudo = root or self.passwordless_sudo()
        if not can_sudo and not system.is_tty():
            log(f"missing {package} (no TTY for sudo); skip apt")
            return False
        apt = ["apt-get", "update", "-qq"]
        install = ["apt-get", "install", "-y", "--no-install-recommends", package]
        if not root:
            if not system.have("sudo"):
                log(f"missing {package} and no sudo; skip")
                return False
            prefix = ["sudo"]
            if can_sudo:
                prefix.append("-n")
            apt = [*prefix, *apt]
            install = [*prefix, *install]
        try:
            system.run(apt)
            system.run(install)
        except subprocess.CalledProcessError:
            return False
        return True

    def ensure_bitwarden_cli(self) -> bool:
        """Install the `bw` pinned in the core mise config (spec secret-tools).

        Reads the repository's config directly, so it also works in `machine setup`
        before ~/.config/mise is linked."""
        if system.have("bw"):
            return True
        if not system.have("mise"):
            log("mise is not installed; cannot install the Bitwarden CLI")
            return False
        env = dict(os.environ)
        env["MISE_CONFIG_DIR"] = str(self.repo / "home/core/.config/mise")
        log("installing the Bitwarden CLI (bw) with mise")
        install = system.run(["mise", "install", "bitwarden"], env=env, check=False)
        where = (
            system.run(
                ["mise", "where", "bitwarden"], env=env, check=False, capture=True
            )
            if install.returncode == 0
            else None
        )
        if where is None or where.returncode or not where.stdout.strip():
            log("could not install the Bitwarden CLI with mise")
            return False
        bin_dir = where.stdout.strip()
        os.environ["PATH"] = f"{bin_dir}:{os.environ.get('PATH', '')}"
        if not system.have("bw"):
            log(f"mise installed bitwarden, but {bin_dir} has no bw")
            return False
        log(f"installed bw to {bin_dir}")
        return True

    def remove_old_local_bw(self, env: dict) -> None:
        """Remove the bw that older versions downloaded to ~/.local/bin once mise has one.

        ~/.local/bin comes first on PATH, so the old binary would win over the pinned one.
        """
        old = self.home / ".local/bin/bw"
        if not (old.is_file() or old.is_symlink()):
            return
        result = system.run(
            ["mise", "which", "bw"], env=env, cwd=self.repo, check=False, capture=True
        )
        if result.returncode or not result.stdout.strip():
            return
        old.unlink()
        log(f"removed old {old}; bw now comes from mise ({result.stdout.strip()})")

    def ensure_uv(self) -> bool:
        if system.have("uv"):
            return True
        local_bin = self.home / ".local/bin"
        local_bin.mkdir(parents=True, exist_ok=True)
        log("installing uv to ~/.local/bin")
        os.environ["UV_INSTALL_DIR"] = str(local_bin)
        try:
            script = system.run(
                ["curl", "-LsSf", "https://astral.sh/uv/install.sh"], capture=True
            ).stdout
            system.run(["sh"], input_text=script)
        except subprocess.CalledProcessError:
            log("could not install uv")
            return False
        os.environ["PATH"] = f"{local_bin}:{os.environ.get('PATH', '')}"
        return system.have("uv")

    def ensure_bootstrap_tools(
        self, need_mise: bool, need_ansible: bool, need_bw: bool
    ) -> None:
        if not system.have("git") and not self.install_pkg_if_missing("git"):
            die("git is required")
        if not system.have("python3") and not self.install_pkg_if_missing("python3"):
            die("python3 is required")
        if not system.have("curl"):
            self.install_pkg_if_missing("curl")
        local_bin = self.home / ".local/bin"
        local_bin.mkdir(parents=True, exist_ok=True)
        os.environ["PATH"] = f"{local_bin}:{os.environ.get('PATH', '')}"
        if need_mise and not system.have("mise"):
            die("mise is not installed (run: ./bootstrap)")
        if need_ansible and not system.ansible_works():
            if self.ensure_uv():
                log("installing ansible-core via uv tool install")
                # --force replaces a shim whose venv broke (e.g. pipx venv
                # after a system Python upgrade).
                system.run(
                    ["uv", "tool", "install", "--force", "ansible-core"], check=False
                )
            if not system.ansible_works() and not (
                self.install_pkg_if_missing("ansible-core")
                or self.install_pkg_if_missing("ansible")
            ):
                die("could not install ansible-core (uv and apt both failed)")
        if need_ansible and system.have("ansible-galaxy"):
            req = self.ansible_dir / "requirements.yml"
            if req.is_file():
                system.run(
                    [
                        "ansible-galaxy",
                        "collection",
                        "install",
                        "-r",
                        str(req),
                    ],
                    check=False,
                    capture=True,
                )
        if need_bw:
            self.ensure_bitwarden_cli()

    def load_vault_password(self) -> None:
        if os.environ.get("ANSIBLE_VAULT_PASSWORD"):
            return
        pw_file = os.environ.get("ANSIBLE_VAULT_PASSWORD_FILE")
        if pw_file and Path(pw_file).is_file():
            return
        password = ""
        if self.unlock_bitwarden():
            result = system.run(
                ["bw", "get", "password", self.vault_item],
                capture=True,
                check=False,
            )
            if result.returncode == 0:
                password = (result.stdout or "").strip()
            else:
                log(f"Bitwarden item '{self.vault_item}' not found")
        if not password and system.is_tty():
            password = getpass.getpass("Ansible vault password (empty to skip): ")
        if password:
            handle = tempfile.NamedTemporaryFile("w", delete=False)
            handle.write(password)
            handle.close()
            os.chmod(handle.name, 0o600)
            os.environ["ANSIBLE_VAULT_PASSWORD_FILE"] = handle.name
            atexit.register(lambda: Path(handle.name).unlink(missing_ok=True))

    def ansible_inventory_args(self) -> List[str]:
        args = ["-i", str(self.ansible_dir / "inventory/local.yml")]
        hosts = self.ansible_dir / "inventory/hosts.yml"
        if hosts.is_file():
            args.extend(["-i", str(hosts)])
            self.load_vault_password()
        return args

    def run_ansible(
        self,
        playbook_name: str,
        limit: str = "",
        force_local: bool = False,
        ask_become: bool = True,
        extra_vars_file: Optional[Path] = None,
    ) -> None:
        playbook = self.ansible_dir / f"{playbook_name}.yml"
        if not playbook.is_file():
            die(f"playbook not found: {playbook}")
        cmd = ["ansible-playbook", str(playbook), *self.ansible_inventory_args()]
        extra: List[str] = []
        vars_file = extra_vars_file or self.applied_host_path
        influx_file: Optional[Path] = None
        if vars_file.is_file():
            extra.extend(["--extra-vars", f"@{vars_file}"])
            if "monitoring" in parse_profile_file(vars_file)["features"]:
                # Only Ansible gets the token; it never goes to ~/.env*.
                values = self.influx_credentials()
                if values:
                    influx_file = _private_file(
                        json.dumps({INFLUX_KEYS[k]: v for k, v in values.items()}),
                        prefix="machine-influx-",
                    )
                    extra.extend(["--extra-vars", f"@{influx_file}"])
        if force_local or not limit:
            cmd.extend(["--connection", "local", "--limit", "localhost"])
            extra.extend(["-e", "target_hosts=localhost"])
            extra.extend(
                ["-e", json.dumps({"machine_user_path": os.environ.get("PATH", "")})]
            )
            # sudo-rs (Ubuntu 25.10+) wraps the prompt as "[sudo: …]", which
            # Ansible's become plugin does not recognise; use classic sudo.
            if system.have("sudo.ws"):
                extra.extend(["-e", "ansible_become_exe=sudo.ws"])
        else:
            cmd.extend(["--limit", limit])
        password_file: Optional[Path] = None
        if ask_become and playbook_name != "homelab" and system.is_tty():
            local = force_local or not limit
            if not local:
                cmd.append("--ask-become-pass")
            else:
                password = self.local_become_password()
                if password is not None:
                    password_file = _private_file(password)
                    cmd.extend(["--become-password-file", str(password_file)])
        if debug_enabled():
            cmd.append("-v")
        cmd.extend(extra)
        log(f"ansible-playbook {playbook_name}.yml")
        try:
            system.run(cmd, cwd=self.ansible_dir)
        finally:
            for path in (password_file, influx_file):
                if path is not None:
                    path.unlink(missing_ok=True)
        if force_local or not limit:
            self.record_ansible_applied()

    def local_become_password(self) -> Optional[str]:
        """sudo password for local Ansible runs, checked first; None if none is needed.

        A cached sudo ticket does not help: it belongs to this terminal, and Ansible
        runs `sudo -n` without one. So the password is asked here (three tries, like
        sudo), verified with `sudo -S -k -v`, kept for the rest of this command (a
        revert runs Ansible again) and handed to Ansible in a private file."""
        cached = getattr(self, "_become_password", None)
        if cached is not None:
            return cached
        sudo = "sudo.ws" if system.have("sudo.ws") else "sudo"
        if not system.have(sudo):
            return None
        if system.run([sudo, "-n", "true"], check=False, capture=True).returncode == 0:
            return None  # passwordless sudo
        for _ in range(3):
            password = getpass.getpass("sudo password for Ansible: ")
            check = system.run(
                [sudo, "-S", "-k", "-p", "", "-v"],
                check=False,
                capture=True,
                input_text=password + "\n",
            )
            if check.returncode == 0:
                self._become_password = password
                return password
            print("Sorry, try again.")
        die("3 incorrect sudo password attempts")
        return None


def _private_file(content: str, prefix: str = "machine-become-") -> Path:
    """Write `content` to a new file only the user can read; the caller deletes it."""
    directory = os.environ.get("XDG_RUNTIME_DIR") or None
    fd, name = tempfile.mkstemp(prefix=prefix, dir=directory)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(content)
    return Path(name)
