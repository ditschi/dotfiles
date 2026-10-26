"""Install the user-space tools declared in the mise configuration."""

from __future__ import annotations

import hashlib
import stat
import urllib.request
from pathlib import Path

from . import features as feature_table
from . import system, terminal_fonts
from .core import die, log, parse_profile_file, warn

AZURE_FEATURE = "azure-cli"
AZURE_PACKAGE = "azure-cli"
FONT_FEATURE = "fonts"
FONT_TOOL = "github:ryanoasis/nerd-fonts"
FONT_LINK = "FiraCodeNerdFont"
# Bridge extension of thunderbird-cli (feature thunderbird). Downloaded, not installed:
# it connects to any bridge on 127.0.0.1:7701, also one started by another local user,
# so the owner installs it by hand in their own Thunderbird profile only.
THUNDERBIRD_FEATURE = "thunderbird"
TB_EXTENSION_URL = (
    "https://github.com/vitalio-sh/thunderbird-cli/releases/download/v1.1.0/"
    "thunderbird_ai_bridge-2.1.0-tb.xpi"
)
TB_EXTENSION_SHA256 = "999a3ef550153d49946007375109379d3c69d01701e5ee2f5df2a3ab43f3bdc9"  # pragma: allowlist secret
GNOME_FEATURE = "gnome"
GNOME_EXTENSIONS = (
    "ddterm@amezin.github.com",
    "gTile@vibou",
    "clipboard-indicator@tudmotu.com",
    "quick-settings-audio-panel@rayzeq.github.io",
    "quicksettings-audio-devices-hider@marcinjahn.com",
    "monitor@astraext.github.io",  # Astra Monitor
)
# Shipped by Ubuntu in /usr/share/gnome-shell/extensions: enabled, never installed.
GNOME_SYSTEM_EXTENSIONS = ("tiling-assistant@ubuntu.com",)
GNOME_SETTINGS_DIR = Path("home/gnome/.config/machine/dconf")
GNOME_SETTINGS_MARKER = Path(".local/state/machine/gnome-extension-settings")


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
        features, _ = feature_table.split(
            parse_profile_file(self.applied_host_path)["features"],
            self.current_context(),
            self.current_device(),
        )
        if AZURE_FEATURE in features:
            self.ensure_azure_cli(env)
        self.link_fonts(env, FONT_FEATURE in features)
        if THUNDERBIRD_FEATURE in features:
            self.download_thunderbird_extension()
        if FONT_FEATURE in features:
            self.set_terminal_fonts()
        if GNOME_FEATURE in features:
            self.ensure_gnome_extensions(env)

    def download_thunderbird_extension(self) -> None:
        """Put the pinned bridge extension into downloads/ (gitignored) for a manual install."""
        target = Path(self.repo) / "downloads" / TB_EXTENSION_URL.rsplit("/", 1)[1]
        if target.is_file() and _sha256(target.read_bytes()) == TB_EXTENSION_SHA256:
            return
        try:
            with urllib.request.urlopen(TB_EXTENSION_URL, timeout=60) as response:
                data = response.read()
        except OSError as exc:
            warn(f"could not download the Thunderbird bridge extension: {exc}")
            return
        if _sha256(data) != TB_EXTENSION_SHA256:
            warn("Thunderbird bridge extension: checksum mismatch, not saved")
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        log(
            f"downloaded {target.name} to {target.parent}; install it once in Thunderbird: "
            "Add-ons and Themes -> gear -> Install Add-on From File"
        )

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

    def ensure_gnome_extensions(self, env: dict) -> None:
        """Install and enable the GNOME Shell extensions without root, then load their settings once."""
        if not system.have("gnome-shell"):
            return
        user_dir = self.home / ".local" / "share" / "gnome-shell" / "extensions"
        system_dir = Path("/usr/share/gnome-shell/extensions")
        failed = False
        for uuid in (*GNOME_EXTENSIONS, *GNOME_SYSTEM_EXTENSIONS):
            present = (user_dir / uuid).is_dir() or (system_dir / uuid).is_dir()
            if not present and uuid in GNOME_EXTENSIONS:
                log(f"installing the GNOME extension {uuid}")
                done = system.run(
                    ["mise", "exec", "--", "gext", "-F", "install", uuid],
                    env=env,
                    check=False,
                    capture=True,
                )
                if done.returncode != 0:
                    log(f"could not install {uuid}; skipping it")
                    failed = True
                    continue
            elif not present:
                log(f"{uuid} is not installed on this system; skipping it")
                continue
            if uuid == "ddterm@amezin.github.com":
                launcher = user_dir / uuid / "bin" / "com.github.amezin.ddterm"
                try:
                    if launcher.is_file():
                        mode = launcher.stat().st_mode
                        if not mode & stat.S_IXUSR:
                            launcher.chmod(mode | stat.S_IXUSR)
                except OSError as exc:
                    warn(f"could not repair the Ddterm launcher permissions: {exc}")
                    failed = True
                    continue
            system.run(
                ["mise", "exec", "--", "gext", "-F", "enable", uuid],
                env=env,
                check=False,
                capture=True,
            )
        log("log out and in to load new GNOME extensions")
        if not failed:
            self.load_gnome_extension_settings()

    def load_gnome_extension_settings(self) -> None:
        """`dconf load` of the shipped settings, once per host; later GUI changes are kept."""
        marker = self.home / GNOME_SETTINGS_MARKER
        if marker.exists() or not system.have("dconf"):
            return
        for ini in sorted((Path(self.repo) / GNOME_SETTINGS_DIR).glob("*.ini")):
            done = system.run(
                ["dconf", "load", f"/org/gnome/shell/extensions/{ini.stem}/"],
                input_text=ini.read_text(encoding="utf-8"),
                check=False,
                capture=True,
            )
            if done.returncode != 0:
                log(f"could not load the settings of {ini.stem}")
                return
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()
        log("loaded the GNOME extension settings")

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


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
