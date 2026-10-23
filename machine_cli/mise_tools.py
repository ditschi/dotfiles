"""Install the user-space tools declared in the mise configuration."""

from __future__ import annotations

from pathlib import Path

from . import system, terminal_fonts
from .core import die, log, parse_profile_file

AZURE_FEATURE = "azure-cli"
AZURE_PACKAGE = "azure-cli"
FONT_FEATURE = "fonts"
FONT_TOOL = "github:ryanoasis/nerd-fonts"
FONT_LINK = "FiraCodeNerdFont"


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
        self.link_fonts(env, FONT_FEATURE in features)
        if FONT_FEATURE in features:
            self.set_terminal_fonts()

    def link_fonts(self, env: dict, wanted: bool) -> None:
        """Link the installed Nerd Font into ~/.local/share/fonts (or drop the link)."""
        link = self.home / ".local" / "share" / "fonts" / FONT_LINK
        current = link.resolve() if link.is_symlink() else None
        if not wanted:
            if current is not None and "mise" in link.resolve().parts:
                link.unlink()
                log("removed the Nerd Font link")
            return
        where = system.run(
            ["mise", "where", FONT_TOOL], env=env, check=False, capture=True
        )
        installed = Path((where.stdout or "").strip())
        if not (where.stdout or "").strip() or not installed.is_dir():
            log("Nerd Font is not installed; skipping the font link")
            return
        if current == installed.resolve():
            return
        link.parent.mkdir(parents=True, exist_ok=True)
        if link.is_symlink():
            link.unlink()
        link.symlink_to(installed)
        log(f"linked the Nerd Font into {link.parent}")
        if system.have("fc-cache"):
            system.run(["fc-cache", "-f", str(link.parent)], check=False, capture=True)

    def set_terminal_fonts(self) -> None:
        terminal_fonts.set_guake_font()
        terminal_fonts.set_vscode_font(self.home)

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
