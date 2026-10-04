"""Bootstrap tools and the git / ansible / chezmoi runners."""

from __future__ import annotations

import atexit
import getpass
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import List, Optional


from . import system
from .core import (
    log,
    die,
)


class ToolsMixin:
    def health_check_after_apply(self) -> bool:
        ok = True
        # sshd config is validated as root inside the playbook (role sshd_home,
        # "Validate sshd configuration"). Here as a normal user `sshd -t` always
        # fails (host keys unreadable) and `sudo -n` fails without cached
        # credentials, which rolled back every successful apply.
        if "monitoring" in self.saved_features() and system.have("systemctl"):
            result = system.run(
                ["systemctl", "is-active", "telegraf"],
                check=False,
                capture=True,
            )
            status = (result.stdout or "").strip()
            if status not in {"active", "activating"} and result.returncode != 0:
                # telegraf may not be installed yet from apt — warn only
                log(f"health check: telegraf status={status or 'unknown'} (warn)")
        return ok

    def git_dirty(self) -> bool:
        result = system.run(
            ["git", "-C", str(self.repo), "status", "--porcelain"],
            capture=True,
            check=False,
        )
        return bool((result.stdout or "").strip())

    def git_head(self) -> str:
        result = system.run(
            ["git", "-C", str(self.repo), "rev-parse", "HEAD"],
            capture=True,
            check=False,
        )
        return (result.stdout or "").strip()

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

    def ensure_gum(self) -> None:
        if system.have("gum") or not system.is_tty() or system.in_docker():
            return
        arch = platform.machine()
        arch_map = {"x86_64": "amd64", "aarch64": "arm64", "armv7l": "armv7"}
        gum_arch = arch_map.get(arch)
        if not gum_arch:
            return
        version = "0.14.5"
        url = (
            f"https://github.com/charmbracelet/gum/releases/download/v{version}/"
            f"gum_{version}_Linux_{gum_arch}.tar.gz"
        )
        local_bin = self.home / ".local/bin"
        local_bin.mkdir(parents=True, exist_ok=True)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                archive = Path(tmp) / "gum.tgz"
                urllib.request.urlretrieve(url, archive)
                system.run(["tar", "-xzf", str(archive), "-C", tmp], check=True)
                binary = next(Path(tmp).rglob("gum"), None)
                if binary and binary.is_file():
                    dest = local_bin / "gum"
                    shutil.copy2(binary, dest)
                    dest.chmod(0o755)
                    os.environ["PATH"] = f"{local_bin}:{os.environ.get('PATH', '')}"
                    log(f"installed gum to {dest}")
        except (OSError, subprocess.CalledProcessError, StopIteration):
            log("could not install gum; using plain prompts")

    def ensure_bitwarden_cli(self) -> bool:
        if system.have("bw"):
            return True
        arch = platform.machine()
        arch_map = {"x86_64": "x64", "aarch64": "arm64"}
        bw_arch = arch_map.get(arch)
        if not bw_arch:
            log(f"no Bitwarden CLI build for {arch}")
            return False
        local_bin = self.home / ".local/bin"
        local_bin.mkdir(parents=True, exist_ok=True)
        url = (
            "https://github.com/bitwarden/clients/releases/download/"
            f"cli-v2024.12.0/bw-linux-{bw_arch}.zip"
        )
        try:
            with tempfile.TemporaryDirectory() as tmp:
                archive = Path(tmp) / "bw.zip"
                urllib.request.urlretrieve(url, archive)
                system.run(["unzip", "-o", "-q", str(archive), "-d", tmp], check=True)
                binary = Path(tmp) / "bw"
                if not binary.is_file():
                    return False
                dest = local_bin / "bw"
                shutil.copy2(binary, dest)
                dest.chmod(0o755)
                os.environ["PATH"] = f"{local_bin}:{os.environ.get('PATH', '')}"
                log(f"installed bw to {dest}")
                return True
        except (OSError, subprocess.CalledProcessError):
            log("could not install Bitwarden CLI")
            return False

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
        self, need_chezmoi: bool, need_ansible: bool, need_bw: bool
    ) -> None:
        if not system.have("git") and not self.install_pkg_if_missing("git"):
            die("git is required")
        if not system.have("python3") and not self.install_pkg_if_missing("python3"):
            die("python3 is required")
        if not system.have("curl"):
            self.install_pkg_if_missing("curl")
        if not system.have("unzip"):
            self.install_pkg_if_missing("unzip")
        local_bin = self.home / ".local/bin"
        local_bin.mkdir(parents=True, exist_ok=True)
        os.environ["PATH"] = f"{local_bin}:{os.environ.get('PATH', '')}"
        self.ensure_gum()
        if need_chezmoi and not system.have("chezmoi"):
            log("installing chezmoi to ~/.local/bin")
            script = system.run(
                ["curl", "-fsLS", "get.chezmoi.io"], capture=True
            ).stdout
            system.run(["sh", "-s", "--", "-b", str(local_bin)], input_text=script)
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
        vars_file = extra_vars_file or self.profile_path
        if vars_file.is_file():
            extra.extend(["--extra-vars", f"@{vars_file}"])
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
        if ask_become and playbook_name != "homelab" and system.is_tty():
            cmd.append("--ask-become-pass")
        cmd.extend(extra)
        log(f"ansible-playbook {playbook_name}.yml")
        system.run(cmd, cwd=self.ansible_dir)

    def run_chezmoi_apply(self) -> None:
        if not system.have("chezmoi"):
            die("chezmoi is not installed")
        if not self.chezmoi_config.is_file():
            die(f"missing {self.chezmoi_config} (run: machine setup)")
        system.run(
            [
                "chezmoi",
                "apply",
                "--source",
                str(self.chezmoi_source),
                "--destination",
                str(self.home),
                "--config",
                str(self.chezmoi_config),
            ]
        )

    def sanitize_git_config(self) -> None:
        shared = self.chezmoi_source / "dot_gitconfig"
        if shared.is_file():
            system.run(
                [
                    sys.executable,
                    str(self.repo / "machine/gitconfig.py"),
                    "--shared",
                    str(shared),
                    "--local",
                    str(self.home / ".gitconfig.local"),
                ]
            )
