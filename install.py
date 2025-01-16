#!/usr/bin/env python3
import argparse
import io
import logging
import os
from pathlib import Path
import requests
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime
from typing import List
from urllib.parse import unquote


SCRIPT_DIR = Path(__file__).resolve().parent
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
HOME_DIR = Path.home()
BACKUP_DIR = HOME_DIR / f"dotfiles-backup-{timestamp}"

DOTFILES = [
    ".bashrc",
    ".gitconfig",
    ".gitconfig.shared",
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
    "flameshot",
    "fonts-firacode",
    "fonts-powerline",
    "fzf",
    "git",
    "git-lfs",
    "gnome-shell-extension-gpaste",
    "gnome-shell-extension-manager",
    "gnome-shell-extension-prefs",
    "gnome-shell-extensions-gpaste",
    "gnupg",
    "guake",
    "guake-indicator",
    "python-is-python3",
    "libsecret-tools",
    "tmux",
    "wget",
    "zsh",
]

PIP_MODULES = ["pre-commit", "pipenv", "pipx", "typer"]


def get_absolute_path(relative_path: str) -> Path:
    return SCRIPT_DIR / relative_path


def get_home_path(relative_path: str) -> Path:
    return HOME_DIR / relative_path


def get_backup_path(relative_path: str) -> Path:
    return BACKUP_DIR / relative_path


def verify_dotfiles_exist() -> None:
    logging.debug("Verifying dotfiles to be installed")
    missing_files = [
        dotfile
        for dotfile in DOTFILES
        if not get_absolute_path(dotfile).exists()
    ]
    if missing_files:
        logging.error(
            "The following dotfiles are missing in the repository: %s",
            ", ".join(missing_files),
        )
        sys.exit(1)
    logging.info("All required dotfiles are present")


def create_backup() -> None:
    logging.debug("Creating backup of existing dotfiles")
    did_backup = False
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    for dotfile in DOTFILES:
        source_path = get_home_path(dotfile)
        backup_path = get_backup_path(dotfile)
        if source_path.exists():
            if source_path.is_symlink():
                logging.debug("'%s' is a symlink, skipping backup", source_path)
                continue
            logging.debug("Backing up '%s' to '%s'", source_path, backup_path)
            shutil.copy2(source_path, backup_path)
            did_backup = True
        else:
            logging.debug("'%s' does not exist, skipping backup", source_path)
    if did_backup:
        logging.info("Existing dotfiles backed up to '%s'", BACKUP_DIR)
    else:
        BACKUP_DIR.rmdir()


def setup_dotfile_links(use_symlink: bool = False, skip_existing: bool = False) -> None:
    logging.debug("Setting up links for dotfiles in %s/", HOME_DIR)
    links_created = {}
    for dotfile in DOTFILES:
        source_path = get_absolute_path(dotfile)
        link_path = get_home_path(dotfile)
        if source_path.is_dir():
            result = create_links_for_directory(
                source_path, link_path, use_symlink, skip_existing
            )
            if result:
                links_created.update(result)
            else:
                logging.debug("No links created for directory '%s'", source_path)
            continue
        result = create_link_for_file(
            source_path, link_path, use_symlink, skip_existing
        )
        if result:
            links_created.update(result)
    logging.info(
        "Successfully set up %d %s-links for dotfiles in %s",
        len(links_created),
        "sym" if use_symlink else "hard",
        HOME_DIR,
    )


def create_links_for_directory(
    source_path: Path, link_path: Path, use_symlink: bool, skip_existing: bool
) -> dict:
    links_created = {}
    for root, _, files in os.walk(source_path):
        for name in files:
            source_file = Path(root) / name
            link_file = link_path / source_file.relative_to(source_path)
            result = create_link_for_file(
                source_file, link_file, use_symlink, skip_existing
            )
            if result:
                links_created.update(result)
    return links_created


def create_link_for_file(
    source_path: Path, link_path: Path, use_symlink: bool, skip_existing: bool
) -> dict:
    if link_path.exists():
        if skip_existing:
            return
        if use_symlink and link_path.is_symlink():
            if link_path.resolve() == source_path:
                logging.debug(
                    "'%s' is already a symlink to '%s'", link_path, source_path
                )
                return None
        elif (
            not use_symlink
            and not link_path.is_symlink()
            and link_path.samefile(source_path)
        ):
            logging.debug("'%s' is already a hard link to '%s'", link_path, source_path)
            return None
        else:
            logging.debug("Removing existing file '%s'", link_path)

            max_retries = 5
            delay_seconds = 1

            for attempt in range(max_retries):
                try:
                    link_path.unlink()
                    break
                except OSError as e:
                    if e.errno == 16:  # Device or resource busy
                        logging.debug(
                            "Attempt %d: Failed to remove '%s' due to resource busy. Retrying in %d seconds...",
                            attempt + 1,
                            link_path,
                            delay_seconds,
                        )
                        time.sleep(delay_seconds)
                    else:
                        logging.warning("Failed to remove '%s': %s", link_path, e)
                        raise
            else:
                logging.error(
                    "Failed to remove '%s' after %d attempts", link_path, max_retries
                )
                sys.exit(1)

    # Ensure the parent directory of the link path exists
    link_path.parent.mkdir(parents=True, exist_ok=True)

    if use_symlink:
        relative_link = os.path.relpath(source_path, link_path.parent)
        logging.debug("Creating symlink '%s' -> '%s'", link_path, relative_link)
        link_path.symlink_to(relative_link, target_is_directory=source_path.is_dir())
        return {str(link_path): str(source_path)}
    else:
        logging.debug("Creating hard link '%s' -> '%s'", link_path, source_path)
        link_path.hardlink_to(source_path)
        return {str(link_path): str(source_path)}


def install_apt_packages() -> None:
    logging.info("Installing apt packages: %s", ", ".join(APT_PACKAGES))
    update_command = ["sudo", "apt-get", "update"]

    try:
        subprocess.run(
            update_command,
            check=True,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            encoding="utf-8",
        )

        packages_to_install = get_missing_apt_packages()
        if packages_to_install:
            logging.warning(
                "The following packages will be skipped during installation: %s",
                ", ".join(packages_to_install),
            )

        install_command = ["sudo", "apt-get", "install", "-y"] + packages_to_install
        result = subprocess.run(
            install_command,
            check=True,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            encoding="utf-8",
        )
    except subprocess.CalledProcessError as cpe:
        logging.error("Failed to install apt packages: %s", cpe.stderr)
        sys.exit(1)
    logging.debug(result.stdout)
    logging.info("Successfully installed apt packages")


def get_missing_apt_packages() -> List[str]:
    return [
        package
        for package in APT_PACKAGES
        if subprocess.run(
            ["dpkg", "-s", package], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        ).returncode
        != 0
    ]


def install_pip_modules() -> None:
    logging.info("Installing pip modules: %s", ", ".join(PIP_MODULES))
    try:
        modules_to_install = get_missing_pip_modules()
        if modules_to_install:
            logging.warning(
                "The following modules will be skipped during installation: %s",
                ", ".join(modules_to_install),
            )

        install_command = [sys.executable, "-m", "pip", "install", *modules_to_install]
        result = subprocess.run(
            install_command,
            check=True,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            encoding="utf-8",
        )
        logging.debug(result.stdout)
    except subprocess.CalledProcessError as cpe:
        logging.error("Failed to install pip modules: %s", cpe.stderr)
        sys.exit(1)
    logging.info("Successfully installed pip modules")


def get_missing_pip_modules() -> List[str]:
    return [
        module
        for module in PIP_MODULES
        if subprocess.run(
            [sys.executable, "-m", "pip", "show", module],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).returncode
        != 0
    ]


def setup_fonts() -> None:
    font_zips = [
        "https://github.com/ryanoasis/nerd-fonts/releases/download/v2.3.3/FiraCode.zip",
        "https://github.com/ryanoasis/nerd-fonts/releases/download/v2.3.3/RobotoMono.zip",
        "https://github.com/ryanoasis/nerd-fonts/releases/download/v2.3.3/SourceCodePro.zip",
        "https://github.com/ryanoasis/nerd-fonts/releases/download/v2.3.3/Hack.zip",
        "https://github.com/ryanoasis/nerd-fonts/releases/download/v2.3.3/Meslo.zip",
    ]
    font_files = [
        "https://github.com/romkatv/powerlevel10k-media/raw/master/MesloLGS%20NF%20Regular.ttf",
        "https://github.com/romkatv/powerlevel10k-media/raw/master/MesloLGS%20NF%20Bold.ttf",
        "https://github.com/romkatv/powerlevel10k-media/raw/master/MesloLGS%20NF%20Italic.ttf",
        "https://github.com/romkatv/powerlevel10k-media/raw/master/MesloLGS%20NF%20Bold%20Italic.ttf",
    ]
    logging.info("Downloading and installing fonts from zip files")
    for zip_url in font_zips:
        request = requests.get(zip_url, allow_redirects=True)
        request.raise_for_status()
        zip_file = zipfile.ZipFile(io.BytesIO(request.content))
        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_file.extractall(tmp_dir)
            copy_fonts_to_directory(Path(tmp_dir))

    logging.info("Downloading and installing individual font files")
    for file_url in font_files:
        request = requests.get(file_url, allow_redirects=True)
        with tempfile.TemporaryDirectory() as tmp_dir:
            filename = os.path.basename(unquote(file_url))
            filepath = Path(tmp_dir) / filename
            with open(filepath, "wb") as file:
                file.write(request.content)
            copy_fonts_to_directory(filepath)
    command = "fc-cache -f -v"
    logging.info("Rebuilding font cache with command: '%s'", command)
    subprocess.check_call(command, shell=True)
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
    extension_scripts = [
        SCRIPT_DIR / "setup_in_container.sh",
        HOME_DIR / "setup_in_container.sh",
    ]

    zinit_cache_path = Path(".local") / "share" / "zinit"
    host_home_mount_path =  Path("/mnt/host_home")
    host_zinit_cache = host_home_mount_path / zinit_cache_path
    container_zinit_cache = HOME_DIR / zinit_cache_path

    if host_zinit_cache.exists() and not container_zinit_cache.exists():
        logging.info(
            "Linking host zsh cache environment from '%s' to '%s'",
            host_zinit_cache,
            container_zinit_cache,
        )
        container_zinit_cache.parent.mkdir(parents=True, exist_ok=True)
        container_zinit_cache.symlink_to(host_zinit_cache)
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


def is_running_in_docker() -> bool:
    return Path("/.dockerenv").is_file()


def parse_arguments():
    parser = argparse.ArgumentParser(description="Setup dotfiles")
    parser.add_argument(
        "--new-host",
        action="store_true",
        help="Install apt packages, pip modules, and fonts",
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
        help="Create a backup before setting up dotfiles",
    )
    return parser.parse_args()


def set_git_user_config() -> None:
    logging.info("Setting git user configuration for dotfiles repository")
    try:
        subprocess.run(
            ["git", "config", "user.name", "Christian Ditscher"],
            check=True,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            encoding="utf-8",
            cwd=SCRIPT_DIR,
        )
        subprocess.run(
            ["git", "config", "user.email", "chris@ditscher.me"],
            check=True,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            encoding="utf-8",
            cwd=SCRIPT_DIR,
        )
        subprocess.run(
            ["git", "config", "commit.gpgsign", "false"],
            check=True,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            encoding="utf-8",
        )
        logging.info("Git user configuration set successfully")
    except subprocess.CalledProcessError as cpe:
        logging.error("Failed to set git user configuration: %s", cpe.stderr)
        sys.exit(1)


def main() -> None:
    args = parse_arguments()
    log_format = "%(asctime)s %(levelname)s: %(message)s"
    if args.debug:
        logging.basicConfig(level=logging.DEBUG, format=log_format)
    else:
        logging.basicConfig(level=logging.INFO, format=log_format)

    verify_dotfiles_exist()

    if args.backup:
        create_backup()

    setup_dotfile_links(
        use_symlink=is_running_in_docker(), skip_existing=is_running_in_docker()
    )

    if is_running_in_docker():
        run_additional_setup_in_container()

    if args.new_host:
        setup_fonts()
        install_apt_packages()
        install_pip_modules()
        set_git_user_config()

    logging.info("Setup completed successfully")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.error("Installation was aborted by user")
