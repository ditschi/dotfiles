"""Install the user-space tools declared in the mise configuration."""

from __future__ import annotations

from pathlib import Path

from . import system
from .core import die, log, parse_profile_file

AZURE_FEATURE = "azure-cli"
AZURE_PACKAGE = "azure-cli"


class MiseToolsMixin:
    def run_tools_install(self) -> None:
        """`mise install` for missing tools, then the Azure CLI when the host wants it."""
        if not system.have("mise"):
            die("mise is not installed (run: ./bootstrap)")
        env = self.dotfiles_env()
        system.run(
            ["mise", "trust", str(Path(self.repo) / "mise.toml")],
            env=env,
            check=False,
            capture=True,
        )
        system.run(["mise", "install"], env=env, cwd=self.repo)
        features = parse_profile_file(self.profile_path)["features"]
        if AZURE_FEATURE in features:
            self.ensure_azure_cli(env)

    def ensure_azure_cli(self, env: dict) -> None:
        """Azure CLI as a uv tool on a uv-managed Python; the system Python stays untouched."""
        listed = system.run(
            ["mise", "exec", "--", "uv", "tool", "list"],
            env=env,
            check=False,
            capture=True,
        )
        installed = AZURE_PACKAGE in (listed.stdout or "")
        if installed:
            args = ["uv", "tool", "upgrade", AZURE_PACKAGE]
        else:
            args = [
                "uv",
                "tool",
                "install",
                AZURE_PACKAGE,
                "--python-preference",
                "only-managed",
            ]
        log(("upgrading" if installed else "installing") + " the Azure CLI")
        system.run(["mise", "exec", "--", *args], env=env)

    def _tools_install_quiet(self) -> bool:
        if not (system.have("mise") and self.mise_local_config.is_file()):
            return True
        try:
            self.run_tools_install()
        except (SystemExit, OSError):
            return False
        return True
