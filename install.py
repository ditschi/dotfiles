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
HOME_DIR = Path.home().resolve()
BACKUP_DIR = HOME_DIR / ".dotfiles-backup" / timestamp

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


def get_dotfiles_path(relative_path: str | Path) -> Path:
    return SCRIPT_DIR / relative_path


def get_home_path(relative_path: str| Path) -> Path:
    return HOME_DIR / relative_path


def get_backup_path(relative_path: str| Path) -> Path:
    return BACKUP_DIR / relative_path


def verify_dotfiles_exist() -> None:
    logging.debug("Verifying dotfiles to be installed")
    missing_files = [
        dotfile
        for dotfile in DOTFILES
        if not get_dotfiles_path(dotfile).exists()
    ]
    if (missing_files):
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

            message = "Backing up '%s' to '%s'", source_path, backup_path
            if dry_run:
                logging.debug("Dry-run:: " + message)
            else:
                logging.debug(message)
                shutil.copy2(source_path, backup_path)
            did_backup = True
        else:
            logging.debug("'%s' does not exist, skipping backup", source_path)
    if did_backup:
        logging.info("Existing dotfiles backed up to '%s'", BACKUP_DIR)
    else:
        if not dry_run:
            BACKUP_DIR.rmdir()


def setup_dotfile_links(use_symlink: bool = True, skip_existing: bool = False, dry_run: bool = False, force: bool = False) -> None:
    if skip_existing and force:
        logging.warning("Both 'skip_existing' and 'force' are set, Docker usecase 'skip_existing' will be")
        skip_existing = False

    logging.debug("Setting up links for dotfiles in %s/", HOME_DIR)
    links_created = {}
    for dotfile in DOTFILES:
        dotfile_path = get_dotfiles_path(dotfile)
        if dotfile_path.is_dir():
            result = create_links_for_directory(
                dotfile, use_symlink, skip_existing, dry_run, force
            )
            if result:
                links_created.update(result)
            else:
                logging.debug("No links created for directory '%s'", dotfile_path)
            continue

        target_path = get_home_path(dotfile)
        result = create_link_for_file(
            target_path, dotfile_path, use_symlink, skip_existing, dry_run, force
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
    dotfile_dir: Path, use_symlink: bool, skip_existing: bool, dry_run: bool, force: bool
) -> dict:
    links_created = {}
    for root, _, files in os.walk(dotfile_dir):
        logging.debug("Setting up link for files in folder '%s'", root)
        for name in files:
            relative_path = Path(root) / name

            dotfile_path = get_dotfiles_path(relative_path)
            target_path = get_home_path(relative_path)
            logging.debug("Setting up link for file in folder:  Target '%s' -> Link '%s'", target_path, dotfile_path)
            result = create_link_for_file(
                target_path, dotfile_path, use_symlink, skip_existing, dry_run, force
            )
            if result:
                links_created.update(result)
    return links_created


def _existing_link_correct(target_path: Path, dotfile_path: Path, use_symlink: bool) -> bool:
    if use_symlink:
        if target_path.is_symlink() and target_path.resolve() == dotfile_path.resolve():
            logging.debug("'%s' is already a symlink to '%s'", target_path, dotfile_path)
            return True
    else:
        if target_path.is_file() and not target_path.is_symlink() and target_path.samefile(dotfile_path):
            logging.debug("'%s' is already a hard link to '%s'", target_path, dotfile_path)
            return True
    return False



def create_link_for_file(
    target_path: Path, dotfile_path: Path, use_symlink: bool, skip_existing: bool, dry_run: bool, force: bool
) -> dict:
    if not dry_run:
        if  dotfile_path.absolute() == target_path.absolute():
            # dry run will not remove existing links, so check if the paths are the same will follow links and fail
            logging.error("Dotfile path and target path are the same: '%s'", dotfile_path)
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

        message = "Removing incorrect link '%s'" % target_abs_path
        if dry_run:
            logging.debug("Dry-run:: " + message)
        else:
            logging.debug(message)
            os.remove(target_abs_path)  # warning: target_path.unlink() for some reason will delete the linked destination
            if target_abs_path.exists():
                raise FileExistsError(f"Failed to remove incorrect link '{target_abs_path}'")
    else:
        logging.debug("Link '%s' does not exist yet", target_abs_path )

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



def install_apt_packages(dry_run: bool = False) -> None:
    logging.info("Installing apt packages: %s", ", ".join(APT_PACKAGES))
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

        packages_to_install = get_missing_apt_packages()
        if packages_to_install:
            logging.warning(
                "The following packages will be skipped during installation: %s",
                ", ".join(packages_to_install),
            )

        install_command = ["sudo", "apt-get", "install", "-y"] + packages_to_install
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


def get_missing_apt_packages() -> List[str]:
    return [
        package
        for package in APT_PACKAGES
        if subprocess.run(
            ["dpkg", "-s", package], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        ).returncode
        != 0
    ]


def install_pip_modules(dry_run: bool = False) -> None:
    logging.info("Installing pip modules: %s", ", ".join(PIP_MODULES))
    try:
        modules_to_install = get_missing_pip_modules()
        if modules_to_install:
            logging.warning(
                "The following modules will be skipped during installation: %s",
                ", ".join(modules_to_install),
            )

        install_command = [sys.executable, "-m", "pip", "install", *modules_to_install]
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


def setup_fonts(dry_run: bool = False) -> None:
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
            if not dry_run:
                copy_fonts_to_directory(Path(tmp_dir))

    logging.info("Downloading and installing individual font files")
    for file_url in font_files:
        request = requests.get(file_url, allow_redirects=True)
        with tempfile.TemporaryDirectory() as tmp_dir:
            filename = os.path.basename(unquote(file_url))
            filepath = Path(tmp_dir) / filename
            with open(filepath, "wb") as file:
                file.write(request.content)
            if not dry_run:
                copy_fonts_to_directory(filepath)
    command = "fc-cache -f -v"
    logging.info("Rebuilding font cache with command: '%s'", command)
    if not dry_run:
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
    logging.info("Running additional setup in container")
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
        create_backup(dry_run=args.dry_run)

    setup_dotfile_links(
        use_symlink=True, skip_existing=is_running_in_docker(), dry_run=args.dry_run, force=args.force
    )

    if is_running_in_docker():
        run_additional_setup_in_container()

    if args.new_host:
        setup_fonts(dry_run=args.dry_run)
        install_apt_packages(dry_run=args.dry_run)
        install_pip_modules(dry_run=args.dry_run)
        set_git_user_config()

    logging.info("Setup completed successfully")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.error("Installation was aborted by user")
