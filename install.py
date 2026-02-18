#!/usr/bin/env python3
import argparse
import importlib.util
import io
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime
from typing import List, Set, Tuple, Union
from urllib.parse import unquote


SCRIPT_DIR = Path(__file__).resolve().parent
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
HOME_DIR = Path.home().resolve()
BACKUP_DIR = HOME_DIR / ".dotfiles-backup" / timestamp
INSTALLER_VENV_DIR = HOME_DIR / ".local" / "share" / "dotfiles-installer" / "venv"
INSTALLER_REQUIRED_PACKAGES = ["requests"]

DOTFILES = [
    ".bashrc",
    ".config/starship.toml",
    ".config/systemd/user/dotfiles-update-check.service",
    ".config/systemd/user/dotfiles-update-check.timer",
    ".gitconfig",
    ".local/bin/dotfiles-update-check-job",
    ".p10k.zsh",
    ".profile",
    ".tmux.conf",
    ".zprofile",
    ".zsh",
    ".zshrc",
]

APT_PACKAGES = [
    "autojump",
    "curl",
    "eza",
    "fonts-firacode",
    "fonts-powerline",
    "fzf",
    "git",
    "git-lfs",
    "gnupg",
    "golang",
    "libsecret-tools",
    "jq",
    "luajit",
    "pipx",
    "python-is-python3",
    "python3-venv",
    "tmux",
    "wget",
    "zsh",
]

# UI-dependent packages that should be skipped in headless mode
UI_PACKAGES = [
    "flameshot",
    "gnome-shell-extension-gpaste",
    "gnome-shell-extension-manager",
    "gnome-shell-extension-prefs",
    "gnome-shell-extensions-gpaste",
    "guake",
    "guake-indicator",
]


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _installer_venv_python() -> Path:
    return INSTALLER_VENV_DIR / "bin" / "python3"


def _format_subprocess_error(cpe: subprocess.CalledProcessError) -> str:
    stderr = (cpe.stderr or "").strip()
    stdout = (cpe.stdout or "").strip()
    output = stderr or stdout or "<no output>"
    return f"exit code {cpe.returncode}; output: {output}"


def _reset_installer_venv_dir() -> None:
    if INSTALLER_VENV_DIR.exists():
        try:
            shutil.rmtree(INSTALLER_VENV_DIR)
        except OSError as exc:
            print(
                "Failed to clean existing installer venv directory at "
                f"'{INSTALLER_VENV_DIR}'.\nDetails: {exc}",
                file=sys.stderr,
            )
            sys.exit(1)


def _try_install_python_venv_with_apt() -> bool:
    apt_get = shutil.which("apt-get")
    if apt_get is None:
        return False

    if os.geteuid() == 0:
        update_command = [apt_get, "update"]
        install_command = [apt_get, "install", "-y", "python3-venv"]
    else:
        sudo = shutil.which("sudo")
        if sudo is None:
            print(
                "python3-venv is required but 'sudo' is not available for apt install.",
                file=sys.stderr,
            )
            return False
        update_command = [sudo, apt_get, "update"]
        install_command = [sudo, apt_get, "install", "-y", "python3-venv"]

    try:
        subprocess.run(
            update_command,
            check=True,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            encoding="utf-8",
        )
        subprocess.run(
            install_command,
            check=True,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            encoding="utf-8",
        )
        return True
    except subprocess.CalledProcessError as cpe:
        print(
            "Automatic apt install of 'python3-venv' failed.\n"
            f"Details: {_format_subprocess_error(cpe)}",
            file=sys.stderr,
        )
        return False


def _try_create_installer_venv_with_uv() -> bool:
    uv = shutil.which("uv")
    if uv is None:
        return False

    commands = [
        [uv, "venv", str(INSTALLER_VENV_DIR), "--python", sys.executable],
        [uv, "venv", str(INSTALLER_VENV_DIR)],
    ]
    last_error: Union[subprocess.CalledProcessError, None] = None
    for command in commands:
        try:
            subprocess.run(
                command,
                check=True,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                encoding="utf-8",
            )
            return True
        except subprocess.CalledProcessError as cpe:
            last_error = cpe

    if last_error is not None:
        print(
            "Automatic uv-based venv creation failed.\n"
            f"Details: {_format_subprocess_error(last_error)}",
            file=sys.stderr,
        )
    return False


def ensure_runtime_environment() -> None:
    """Run installer from dedicated venv and ensure required Python deps exist.

    Many modern distros block system/user pip installs (PEP 668). To keep setup
    reproducible we bootstrap a private venv and re-exec the installer there.
    """
    in_bootstrap = os.environ.get("DOTFILES_INSTALLER_VENV_ACTIVE") == "1"
    missing_packages = [pkg for pkg in INSTALLER_REQUIRED_PACKAGES if not _module_available(pkg)]
    if not missing_packages and in_bootstrap:
        return

    venv_python = _installer_venv_python()

    if not venv_python.exists():
        _reset_installer_venv_dir()

        venv_creation_error = None
        try:
            subprocess.run(
                [sys.executable, "-m", "venv", str(INSTALLER_VENV_DIR)],
                check=True,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                encoding="utf-8",
            )
        except subprocess.CalledProcessError as cpe:
            venv_creation_error = cpe

        if venv_creation_error is not None:
            print(
                "Initial venv creation failed. Trying to install 'python3-venv' via apt.",
                file=sys.stderr,
            )
            if _try_install_python_venv_with_apt():
                _reset_installer_venv_dir()
                try:
                    subprocess.run(
                        [sys.executable, "-m", "venv", str(INSTALLER_VENV_DIR)],
                        check=True,
                        stderr=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        encoding="utf-8",
                    )
                    venv_creation_error = None
                except subprocess.CalledProcessError as cpe:
                    venv_creation_error = cpe

        if venv_creation_error is not None:
            print(
                "Trying uv fallback for installer venv creation.",
                file=sys.stderr,
            )
            _reset_installer_venv_dir()
            if _try_create_installer_venv_with_uv():
                venv_creation_error = None

        if venv_creation_error is not None:
            print(
                "Failed to create installer venv at "
                f"'{INSTALLER_VENV_DIR}'.\n"
                "Install 'python3-venv' (apt) or 'uv', then retry.\n"
                f"Details: {_format_subprocess_error(venv_creation_error)}",
                file=sys.stderr,
            )
            sys.exit(1)

    if not venv_python.exists():
        print(
            f"Installer venv python not found at '{venv_python}'.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        subprocess.run(
            [str(venv_python), "-m", "pip", "install", "--upgrade", "pip"],
            check=True,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            encoding="utf-8",
        )
        subprocess.run(
            [str(venv_python), "-m", "pip", "install"] + INSTALLER_REQUIRED_PACKAGES,
            check=True,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            encoding="utf-8",
        )
    except subprocess.CalledProcessError as cpe:
        print(
            "Failed to install installer dependencies in venv.\n"
            f"Details: {_format_subprocess_error(cpe)}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Re-exec under dedicated installer interpreter exactly once.
    if not in_bootstrap or missing_packages:
        env = os.environ.copy()
        env["DOTFILES_INSTALLER_VENV_ACTIVE"] = "1"
        result = subprocess.run([str(venv_python), __file__, *sys.argv[1:]], env=env)
        sys.exit(result.returncode)


def get_dotfiles_path(relative_path: Union[str, Path]) -> Path:
    return SCRIPT_DIR / relative_path


def get_home_path(relative_path: Union[str, Path]) -> Path:
    return HOME_DIR / relative_path


def get_backup_path(relative_path: Union[str, Path]) -> Path:
    return BACKUP_DIR / relative_path


def verify_dotfiles_exist() -> None:
    logging.debug("Verifying dotfiles to be installed")
    missing_files = [
        dotfile for dotfile in DOTFILES if not get_dotfiles_path(dotfile).exists()
    ]
    if missing_files:
        logging.error(
            "The following dotfiles are missing in the repository: %s",
            ", ".join(missing_files),
        )
        sys.exit(1)
    logging.info("All required dotfiles are present")


def create_backup(dry_run: bool = False) -> None:
    logging.debug("Creating backup of existing dotfiles")
    did_backup = False
    if not dry_run:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    for dotfile in DOTFILES:
        source_path = get_home_path(dotfile)
        backup_path = get_backup_path(dotfile)
        if source_path.exists():
            if source_path.is_symlink():
                logging.debug("'%s' is a symlink, skipping backup", source_path)
                continue

            message = "Backing up '%s' to '%s'" % (source_path, backup_path)
            if dry_run:
                logging.debug("Dry-run:: " + message)
            else:
                logging.debug(message)
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                if backup_path.exists() or backup_path.is_symlink():
                    if backup_path.is_dir() and not backup_path.is_symlink():
                        shutil.rmtree(backup_path)
                    else:
                        backup_path.unlink()
                if source_path.is_dir():
                    shutil.copytree(source_path, backup_path, symlinks=True)
                else:
                    shutil.copy2(source_path, backup_path)
            did_backup = True
        else:
            logging.debug("'%s' does not exist, skipping backup", source_path)
    if did_backup:
        logging.info("Existing dotfiles backed up to '%s'", BACKUP_DIR)
    else:
        if not dry_run:
            BACKUP_DIR.rmdir()


def setup_dotfile_links(
    use_symlink: bool = True,
    skip_existing: bool = False,
    dry_run: bool = False,
    force: bool = False,
) -> None:
    if skip_existing and force:
        logging.warning(
            "Both 'skip_existing' and 'force' are set, Docker usecase 'skip_existing' will be"
        )
        skip_existing = False

    logging.debug("Setting up links for dotfiles in %s/", HOME_DIR)
    links_created = {}
    used_directory_symlink_fallback = False
    for dotfile in DOTFILES:
        dotfile_path = get_dotfiles_path(dotfile)
        target_path = get_home_path(dotfile)
        if dotfile_path.is_dir():
            # Directories cannot be hard-linked. Fall back to symlink mode.
            link_as_symlink = use_symlink
            if not use_symlink:
                link_as_symlink = True
                used_directory_symlink_fallback = True
                logging.warning(
                    "Hard links are not supported for directories. Falling back to symlink for '%s'",
                    dotfile_path,
                )
            result = create_link_for_file(
                target_path, dotfile_path, link_as_symlink, skip_existing, dry_run, force
            )
            if result:
                links_created.update(result)
            else:
                logging.debug("No link created for directory '%s'", dotfile_path)
            continue

        result = create_link_for_file(
            target_path, dotfile_path, use_symlink, skip_existing, dry_run, force
        )
        if result:
            links_created.update(result)
    mode_label = "sym" if use_symlink else "hard"
    if used_directory_symlink_fallback:
        mode_label = "hard (directory entries as sym)"
    logging.info(
        "Successfully set up %d %s-links for dotfiles in %s",
        len(links_created),
        mode_label,
        HOME_DIR,
    )


def create_links_for_directory(
    dotfile_dir: Path,
    use_symlink: bool,
    skip_existing: bool,
    dry_run: bool,
    force: bool,
) -> dict:
    links_created = {}
    for root, _, files in os.walk(dotfile_dir):
        logging.debug("Setting up link for files in folder '%s'", root)
        for name in files:
            relative_path = Path(root) / name

            dotfile_path = get_dotfiles_path(relative_path)
            target_path = get_home_path(relative_path)
            logging.debug(
                "Setting up link for file in folder:  Target '%s' -> Link '%s'",
                target_path,
                dotfile_path,
            )
            result = create_link_for_file(
                target_path, dotfile_path, use_symlink, skip_existing, dry_run, force
            )
            if result:
                links_created.update(result)
    return links_created


def _existing_link_correct(
    target_path: Path, dotfile_path: Path, use_symlink: bool
) -> bool:
    if use_symlink:
        if target_path.is_symlink() and target_path.resolve() == dotfile_path.resolve():
            logging.debug(
                "'%s' is already a symlink to '%s'", target_path, dotfile_path
            )
            return True
    else:
        if (
            target_path.is_file()
            and not target_path.is_symlink()
            and target_path.samefile(dotfile_path)
        ):
            logging.debug(
                "'%s' is already a hard link to '%s'", target_path, dotfile_path
            )
            return True
    return False


def create_link_for_file(
    target_path: Path,
    dotfile_path: Path,
    use_symlink: bool,
    skip_existing: bool,
    dry_run: bool,
    force: bool,
) -> dict:
    if not dry_run:
        if dotfile_path.absolute() == target_path.absolute():
            # dry run will not remove existing links, so check if the paths are the same will follow links and fail
            logging.error(
                "Dotfile path and target path are the same: '%s'", dotfile_path
            )
            sys.exit(1)

    target_abs_path = target_path.absolute()
    if target_abs_path.exists() or target_abs_path.is_symlink():
        if not force:
            if skip_existing:
                logging.debug("Skipping existing file '%s'", target_abs_path)
                return None

            if _existing_link_correct(target_path, dotfile_path, use_symlink):
                logging.info("Correct link already exists: '%s'", target_abs_path)
                return None

        if target_abs_path.is_dir() and not target_abs_path.is_symlink():
            message = "Removing incorrect directory '%s'" % target_abs_path
        else:
            message = "Removing incorrect link '%s'" % target_abs_path
        if dry_run:
            logging.debug("Dry-run:: " + message)
        else:
            logging.debug(message)
            if target_abs_path.is_dir() and not target_abs_path.is_symlink():
                shutil.rmtree(target_abs_path)
            else:
                os.remove(target_abs_path)
            if target_abs_path.exists():
                raise FileExistsError(
                    f"Failed to remove incorrect link '{target_abs_path}'"
                )
    else:
        logging.debug("Link '%s' does not exist yet", target_abs_path)

    if not dry_run:
        target_path.parent.mkdir(parents=True, exist_ok=True)

    if use_symlink:
        # Note: failed trying to get relative path using pathlib
        relative_link = Path(os.path.relpath(dotfile_path, target_abs_path.parent))
        message = f"Creating symlink: Target '{target_path}' -> Link '{relative_link}'"
        if dry_run:
            logging.debug("Dry-run:: " + message)
        else:
            logging.debug(message)
            target_path.absolute().symlink_to(relative_link)
    else:
        message = f"Creating hard link: Target '{target_path}' -> Link '{dotfile_path}'"
        if dry_run:
            logging.debug("Dry-run:: " + message)
        else:
            logging.debug(message)
            target_path.absolute().hardlink_to(dotfile_path)

    return {str(target_path): str(dotfile_path)}


def install_apt_packages(dry_run: bool = False, ui: bool = False) -> None:
    if shutil.which("apt-get") is None:
        logging.info("apt-get not found. Skipping apt package installation.")
        return

    packages = APT_PACKAGES.copy()

    # Add UI packages if not headless mode
    if ui:
        packages.extend(UI_PACKAGES)
    else:
        logging.info("Not installing UI packages.")

    logging.info("Installing apt packages: %s", ", ".join(packages))
    update_command = ["sudo", "apt-get", "update"]

    try:
        if not dry_run:
            subprocess.run(
                update_command,
                check=True,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                encoding="utf-8",
            )

        (
            available_packages,
            unavailable_packages,
            already_installed_packages,
        ) = classify_apt_packages(packages)

        if not available_packages and not unavailable_packages:
            logging.info("All packages are already installed")
            return
        if unavailable_packages:
            logging.warning(
                "Packages not found in apt repositories (skipped): %s",
                ", ".join(unavailable_packages),
            )

        if available_packages:
            logging.info(
                "The following packages will be installed: %s",
                ", ".join(available_packages),
            )
        else:
            if already_installed_packages:
                logging.info(
                    "All available packages are already installed. Nothing to do."
                )
            else:
                logging.warning(
                    "No installable apt packages left after availability check."
                )
            return

        install_command = ["sudo", "apt-get", "install", "-y"] + available_packages
        if not dry_run:
            result = subprocess.run(
                install_command,
                check=True,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                encoding="utf-8",
            )
            logging.debug(result.stdout)
    except subprocess.CalledProcessError as cpe:
        logging.error("Failed to install apt packages: %s", cpe.stderr)
        sys.exit(1)
    logging.info("Successfully installed apt packages")


def classify_apt_packages(packages: List[str]) -> Tuple[List[str], List[str], List[str]]:
    """
    Return (available_and_missing, unavailable, already_installed).
    """
    if shutil.which("apt-cache") is None:
        logging.info(
            "apt-cache not found. Missing packages cannot be verified and will be skipped."
        )
        available = []
        unavailable = []
        already_installed = []
        for package in packages:
            if (
                subprocess.run(
                    ["dpkg", "-s", package],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                ).returncode
                == 0
            ):
                already_installed.append(package)
            else:
                # Availability cannot be verified without apt-cache.
                # Keep behavior conservative and skip unverified packages.
                unavailable.append(package)
        return available, unavailable, already_installed

    available = []
    unavailable = []
    already_installed = []
    for package in packages:
        if (
            subprocess.run(
                ["dpkg", "-s", package], stdout=subprocess.PIPE, stderr=subprocess.PIPE
            ).returncode
            == 0
        ):
            already_installed.append(package)
            continue

        result = subprocess.run(
            ["apt-cache", "show", package],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
        )
        if result.returncode == 0 and result.stdout.strip():
            available.append(package)
        else:
            unavailable.append(package)
    return available, unavailable, already_installed


def get_installed_font_families() -> Set[str]:
    if shutil.which("fc-list") is None:
        logging.debug("fc-list not found; font presence checks are disabled.")
        return set()

    result = subprocess.run(
        ["fc-list", ":", "family"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )
    if result.returncode != 0:
        logging.debug("fc-list failed: %s", result.stderr.strip())
        return set()

    families: Set[str] = set()
    for line in result.stdout.splitlines():
        for entry in line.split(","):
            family = entry.strip().lower()
            if family:
                families.add(family)
    return families


def _normalize_font_token(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def _has_font_family(
    installed_families: Set[str], family_hints: Union[str, List[str]]
) -> bool:
    hints = [family_hints] if isinstance(family_hints, str) else family_hints
    normalized_hints = {
        _normalize_font_token(hint) for hint in hints if _normalize_font_token(hint)
    }
    normalized_families = {
        _normalize_font_token(family)
        for family in installed_families
        if _normalize_font_token(family)
    }
    return any(hint in normalized_families for hint in normalized_hints)


def setup_fonts(dry_run: bool = False) -> None:
    import requests

    font_zips = [
        (
            ["firacode", "fira code"],
            "https://github.com/ryanoasis/nerd-fonts/releases/download/v2.3.3/FiraCode.zip",
        ),
        (
            ["robotomono", "roboto mono"],
            "https://github.com/ryanoasis/nerd-fonts/releases/download/v2.3.3/RobotoMono.zip",
        ),
        (
            ["sourcecodepro", "source code pro", "saucecodepro"],
            "https://github.com/ryanoasis/nerd-fonts/releases/download/v2.3.3/SourceCodePro.zip",
        ),
        (
            ["hack"],
            "https://github.com/ryanoasis/nerd-fonts/releases/download/v2.3.3/Hack.zip",
        ),
        (
            ["meslolgs", "meslo lgs"],
            "https://github.com/ryanoasis/nerd-fonts/releases/download/v2.3.3/Meslo.zip",
        ),
    ]
    font_files = [
        "https://github.com/romkatv/powerlevel10k-media/raw/master/MesloLGS%20NF%20Regular.ttf",
        "https://github.com/romkatv/powerlevel10k-media/raw/master/MesloLGS%20NF%20Bold.ttf",
        "https://github.com/romkatv/powerlevel10k-media/raw/master/MesloLGS%20NF%20Italic.ttf",
        "https://github.com/romkatv/powerlevel10k-media/raw/master/MesloLGS%20NF%20Bold%20Italic.ttf",
    ]
    # Initial snapshot; during this run we update in-memory hints instead of
    # repeatedly calling fc-list (which is comparatively expensive).
    installed_families = set() if dry_run else get_installed_font_families()

    logging.info("Downloading and installing fonts from zip files")
    for idx, (family_hints, zip_url) in enumerate(font_zips, start=1):
        if _has_font_family(installed_families, family_hints):
            logging.info(
                "[%d/%d] Skipping %s zip (already installed)",
                idx,
                len(font_zips),
                family_hints[0],
            )
            continue

        logging.info("[%d/%d] Downloading %s", idx, len(font_zips), zip_url)
        request = requests.get(zip_url, allow_redirects=True, timeout=(10, 180))
        request.raise_for_status()
        zip_file = zipfile.ZipFile(io.BytesIO(request.content))
        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_file.extractall(tmp_dir)
            if not dry_run:
                copy_fonts_to_directory(Path(tmp_dir))
                for family_hint in family_hints:
                    installed_families.add(family_hint.lower())

    logging.info("Downloading and installing individual font files")
    for idx, file_url in enumerate(font_files, start=1):
        filename = os.path.basename(unquote(file_url))
        target_file = HOME_DIR / ".local" / "share" / "fonts" / filename
        if target_file.exists():
            logging.info(
                "[%d/%d] Skipping %s (already installed)",
                idx,
                len(font_files),
                filename,
            )
            continue

        logging.info("[%d/%d] Downloading %s", idx, len(font_files), filename)
        request = requests.get(file_url, allow_redirects=True, timeout=(10, 120))
        request.raise_for_status()
        with tempfile.TemporaryDirectory() as tmp_dir:
            filepath = Path(tmp_dir) / filename
            with open(filepath, "wb") as file:
                file.write(request.content)
            if not dry_run:
                copy_fonts_to_directory(filepath)
    command = "fc-cache -f"
    logging.info("Rebuilding font cache with command: '%s'", command)
    if not dry_run:
        result = subprocess.run(
            ["fc-cache", "-f"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
        )
        logging.debug(result.stdout)
    logging.info(
        "Remember to configure 'MesloLGS NF' as the default font "
        + "(see https://github.com/romkatv/powerlevel10k/blob/master/font.md)"
    )


def copy_fonts_to_directory(source: Path) -> None:
    font_dir = HOME_DIR / ".local" / "share" / "fonts"
    font_dir.mkdir(parents=True, exist_ok=True)

    if source.is_file():
        destination = font_dir / source.name
        logging.debug("Moving font file '%s' to '%s'", source, font_dir)
        shutil.move(str(source), str(destination))
        return

    logging.debug("Moving all font files from directory '%s' to '%s'", source, font_dir)
    for file in source.iterdir():
        if file.suffix in (".ttf", ".otf", ".ttc"):
            destination = font_dir / file.name
            logging.debug("Moving file '%s' to '%s'", file, destination)
            shutil.move(str(file), str(destination))
        else:
            logging.debug("Skipping non-font file '%s'", file)


def run_additional_setup_in_container() -> None:
    logging.info("Running additional setup in container")
    extension_scripts = [
        SCRIPT_DIR / "setup_in_container.sh",
        HOME_DIR / "setup_in_container.sh",
    ]

    zinit_cache_path = Path(".local") / "share" / "zinit"
    host_home_mount_path = Path("/mnt/host_home")
    host_zinit_cache = host_home_mount_path / zinit_cache_path
    container_zinit_cache = HOME_DIR / zinit_cache_path

    if host_zinit_cache.exists() and not container_zinit_cache.exists():
        logging.info(
            "Linking host zsh cache environment from '%s' to '%s'",
            host_zinit_cache,
            container_zinit_cache,
        )
        container_zinit_cache.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(host_zinit_cache, container_zinit_cache)
    else:
        logging.debug(
            "Cached zsh environment not linked: source exists: %s, destination exists: %s",
            host_zinit_cache.exists(),
            container_zinit_cache.exists(),
        )

    for script in extension_scripts:
        if script.is_file():
            logging.info("Running additional setup script: %s", script)
            result = subprocess.run(
                [str(script)],
                check=True,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                encoding="utf-8",
            )
            logging.debug(result.stdout)
        else:
            logging.info("No additional setup script found at %s", script)


def setup_update_timer(dry_run: bool = False) -> None:
    timer_unit = "dotfiles-update-check.timer"
    if shutil.which("systemctl") is None:
        logging.info("systemctl not found. Skipping timer setup.")
        return

    commands = [
        ["systemctl", "--user", "daemon-reload"],
        ["systemctl", "--user", "enable", "--now", timer_unit],
    ]
    for command in commands:
        command_str = " ".join(command)
        logging.info("Configuring user timer: %s", command_str)
        if dry_run:
            logging.debug("Dry-run:: %s", command_str)
            continue
        try:
            subprocess.run(
                command,
                check=True,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                encoding="utf-8",
            )
        except subprocess.CalledProcessError as cpe:
            logging.warning(
                "Failed to run '%s'. Timer setup skipped for now: %s",
                command_str,
                cpe.stderr.strip(),
            )
            return


def install_starship(dry_run: bool = False) -> None:
    if shutil.which("starship") is not None:
        logging.info("starship is already installed")
        return

    install_command = (
        "curl -fsSL https://starship.rs/install.sh | sh -s -- -y "
        f"--bin-dir {HOME_DIR / '.local' / 'bin'}"
    )
    logging.info("Installing starship")
    logging.debug("Running command: %s", install_command)
    if dry_run:
        logging.debug("Dry-run:: %s", install_command)
        return

    try:
        subprocess.run(
            install_command,
            check=True,
            shell=True,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            encoding="utf-8",
        )
        logging.info("starship installed successfully")
    except subprocess.CalledProcessError as cpe:
        logging.warning("Failed to install starship: %s", cpe.stderr.strip())


def is_running_in_docker() -> bool:
    return Path("/.dockerenv").is_file()


def has_ui_environment() -> bool:
    """Detect if the system has a UI environment (X11, Wayland, or GNOME)"""
    # Check for DISPLAY environment variable (X11)
    if os.environ.get("DISPLAY"):
        return True

    # Check for Wayland
    if os.environ.get("WAYLAND_DISPLAY"):
        return True

    # Check if GNOME is installed
    result = subprocess.run(
        ["which", "gnome-shell"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode == 0:
        return True

    # Check for other display managers
    for dm in ["gdm", "gdm3", "lightdm", "sddm"]:
        result = subprocess.run(
            ["systemctl", "is-active", dm],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode == 0:
            return True

    return False


def has_previous_installation() -> bool:
    """Check if dotfiles have been previously installed by looking for symlinks"""
    for dotfile in DOTFILES:
        target_path = get_home_path(dotfile)
        dotfile_path = get_dotfiles_path(dotfile)

        if target_path.is_symlink():
            resolved_path = target_path.resolve()
            if resolved_path == dotfile_path.resolve():
                logging.debug(
                    "Found existing installation: '%s' points to '%s'",
                    target_path,
                    resolved_path,
                )
                return True

        if (
            target_path.exists()
            and target_path.is_file()
            and not target_path.is_symlink()
            and dotfile_path.exists()
            and dotfile_path.is_file()
            and target_path.samefile(dotfile_path)
        ):
            logging.debug(
                "Found existing installation: '%s' is hard-linked to '%s'",
                target_path,
                dotfile_path,
            )
            return True
    return False


def prompt_ui_setup() -> bool:
    """Prompt user if they want to install additional desktop/UI tools."""
    try:
        response = input(
            "UI environment detected. Install additional desktop/UI packages "
            "(e.g. flameshot, guake)? [y/N]: "
        )
        return response.strip().lower() in ["y", "yes"]
    except (EOFError, KeyboardInterrupt):
        print()
        return False


def prompt_new_host_setup() -> bool:
    """Prompt user if they want to run new host setup"""
    try:
        response = input(
            "No previous installation detected. Do you want to run full new host setup? "
            "(Install base packages, terminal fonts, starship, git config) [y/N]: "
        )
        return response.strip().lower() in ["y", "yes"]
    except (EOFError, KeyboardInterrupt):
        print()
        return False


def parse_arguments():
    parser = argparse.ArgumentParser(description="Setup dotfiles")
    parser.add_argument(
        "--new-host",
        action="store_true",
        help="Install apt packages and fonts",
    )
    parser.add_argument(
        "--ui",
        action="store_true",
        help="Install UI-dependent packages",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create a backup before setting up dotfiles",
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making any changes",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete all target files and create correct links",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Disable interactive prompts and use safe defaults",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Run update workflow (non-interactive relink, skip host/UI provisioning)",
    )
    return parser.parse_args()


def set_git_user_config(dry_run: bool = False) -> None:
    logging.info("Setting git user configuration for dotfiles repository")
    if dry_run:
        logging.debug(
            "Dry-run:: skipping git config changes for dotfiles repository"
        )
        return

    try:
        subprocess.run(
            ["git", "config", "--local", "user.name", "Christian Ditscher"],
            check=True,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            encoding="utf-8",
            cwd=SCRIPT_DIR,
        )
        subprocess.run(
            ["git", "config", "--local", "user.email", "chris@ditscher.me"],
            check=True,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            encoding="utf-8",
            cwd=SCRIPT_DIR,
        )
        subprocess.run(
            ["git", "config", "--local", "commit.gpgsign", "false"],
            check=True,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            encoding="utf-8",
            cwd=SCRIPT_DIR,
        )
        logging.info("Git user configuration set successfully")
    except subprocess.CalledProcessError as cpe:
        logging.error("Failed to set git user configuration: %s", cpe.stderr)
        sys.exit(1)


def main() -> None:
    ensure_runtime_environment()

    args = parse_arguments()
    log_format = "%(asctime)s %(levelname)s: %(message)s"
    if args.debug:
        logging.basicConfig(level=logging.DEBUG, format=log_format)
    else:
        logging.basicConfig(level=logging.INFO, format=log_format)

    verify_dotfiles_exist()

    if args.update:
        args.non_interactive = True
        args.new_host = False
        args.ui = False
        logging.info("Running update workflow (--update, non-interactive)")
    elif args.ui and not args.new_host:
        logging.info("--ui selected without --new-host; enabling --new-host as prerequisite.")
        args.new_host = True

    if args.backup:
        create_backup(dry_run=args.dry_run)

    setup_dotfile_links(
        use_symlink=True,
        skip_existing=is_running_in_docker(),
        dry_run=args.dry_run,
        force=args.force,
    )

    if is_running_in_docker():
        run_additional_setup_in_container()

    setup_update_timer(dry_run=args.dry_run)

    # Auto-detect and prompt if no previous installation and not explicitly set
    if not args.update:
        if not args.new_host and not has_previous_installation():
            logging.info("No previous dotfiles installation detected")
            if args.non_interactive:
                logging.info("Non-interactive mode: skipping new host prompt")
            else:
                args.new_host = prompt_new_host_setup()

        if args.new_host and not args.ui and has_ui_environment():
            if args.non_interactive:
                logging.info("Non-interactive mode: skipping UI setup prompt")
            else:
                args.ui = prompt_ui_setup()

    if args.update:
        # Keep update runs in sync with prior update behavior.
        install_apt_packages(dry_run=args.dry_run, ui=False)
        setup_fonts(dry_run=args.dry_run)
        install_starship(dry_run=args.dry_run)

    if args.new_host:
        install_apt_packages(dry_run=args.dry_run, ui=args.ui)
        setup_fonts(dry_run=args.dry_run)
        install_starship(dry_run=args.dry_run)
        set_git_user_config(dry_run=args.dry_run)

    logging.info("Setup completed successfully")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.error("Installation was aborted by user")
