#!/usr/bin/env python3
import argparse
import os
import logging
import subprocess
import requests
import zipfile
import sys
import io
import shutil
import tempfile
from urllib.parse import unquote
from datetime import datetime
from typing import List


SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
HOME_DIR = os.path.expanduser("~")
BACKUP_DIR = os.path.realpath(os.path.join(HOME_DIR, f"dotfiles-backup-{timestamp}"))

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
    "guake",
    "guake-indicator",
    "python-is-python3",
    "libsecret-tools",
    "tmux",
    "wget",
    "zsh",
]

PIP_MODULES = ["pre-commit", "pipenv", "pipx", "typer"]


def get_absolute_path(relative_path: str) -> str:
    return os.path.realpath(os.path.join(SCRIPT_DIR, relative_path))


def get_home_path(relative_path: str) -> str:
    return os.path.join(HOME_DIR, relative_path)


def get_backup_path(relative_path: str) -> str:
    return os.path.join(BACKUP_DIR, relative_path)


def verify_dotfiles_exist() -> None:
    logging.debug("Verifying dotfiles to be installed")
    missing_files = [
        dotfile
        for dotfile in DOTFILES
        if not os.path.exists(get_absolute_path(dotfile))
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
    os.makedirs(BACKUP_DIR)
    for dotfile in DOTFILES:
        source_path = get_home_path(dotfile)
        backup_path = get_backup_path(dotfile)
        if os.path.exists(source_path):
            if os.path.islink(source_path):
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
        os.removedirs(BACKUP_DIR)


def setup_dotfile_links(use_symlink: bool = False) -> None:
    logging.debug("Setting up links for dotfiles in %s/", HOME_DIR)
    links_created = {}
    for dotfile in DOTFILES:
        source_path = get_absolute_path(dotfile)
        link_path = get_home_path(dotfile)
        if os.path.isdir(source_path):
            result = create_links_for_directory(source_path, link_path, use_symlink)
            if result:
                links_created.update(result)
            else:
                logging.debug("No links created for directory '%s'", source_path)
            continue
        result = create_link_for_file(source_path, link_path, use_symlink)
        if result:
            links_created.update(result)
    logging.info(
        "Successfully set up %d %s-links for dotfiles in %s",
        len(links_created),
        "sym" if use_symlink else "hard",
        HOME_DIR,
    )


def create_links_for_directory(
    source_path: str, link_path: str, use_symlink: bool
) -> dict:
    links_created = {}
    for root, _, files in os.walk(source_path):
        for name in files:
            source_file = os.path.join(root, name)
            link_file = os.path.join(
                link_path, os.path.relpath(source_file, source_path)
            )
            result = create_link_for_file(source_file, link_file, use_symlink)
            if result:
                links_created.update(result)
    return links_created


def create_link_for_file(source_path: str, link_path: str, use_symlink: bool) -> dict:
    if os.path.exists(link_path):
        if use_symlink and os.path.islink(link_path):
            if os.readlink(link_path) == os.path.relpath(
                source_path, os.path.dirname(link_path)
            ):
                logging.debug(
                    "'%s' is already a symlink to '%s'", link_path, source_path
                )
                return None
        elif not use_symlink and os.path.samefile(source_path, link_path):
            logging.debug("'%s' is already a hard link to '%s'", link_path, source_path)
            return None
        else:
            logging.debug("Removing existing file '%s'", link_path)
            os.remove(link_path)

    # Ensure the parent directory of the link path exists
    os.makedirs(os.path.dirname(link_path), exist_ok=True)

    if use_symlink:
        relative_link = os.path.relpath(source_path, os.path.dirname(link_path))
        logging.debug("Creating symlink '%s' -> '%s'", link_path, relative_link)
        os.symlink(
            relative_link, link_path, target_is_directory=os.path.isdir(source_path)
        )
        return {link_path: source_path}
    else:
        logging.debug("Creating hard link '%s' -> '%s'", link_path, source_path)
        os.link(source_path, link_path)
        return {link_path: source_path}


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
            copy_fonts_to_directory(tmp_dir)

    logging.info("Downloading and installing individual font files")
    for file_url in font_files:
        request = requests.get(file_url, allow_redirects=True)
        with tempfile.TemporaryDirectory() as tmp_dir:
            filename = os.path.basename(unquote(file_url))
            filepath = os.path.join(tmp_dir, filename)
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


def copy_fonts_to_directory(source: str) -> None:
    font_dir = os.path.expanduser("~/.local/share/fonts")
    os.makedirs(font_dir, exist_ok=True)

    if os.path.isfile(source):
        destination = os.path.join(font_dir, os.path.basename(source))
        logging.debug("Moving font file '%s' to '%s'", source, font_dir)
        shutil.move(source, destination)
        return

    logging.debug("Moving all font files from directory '%s' to '%s'", source, font_dir)
    for file in os.listdir(source):
        file_path = os.path.join(source, file)
        if file.endswith((".ttf", ".otf", ".ttc")):
            destination = os.path.join(font_dir, file)
            logging.debug("Moving file '%s' to '%s'", file_path, destination)
            shutil.move(file_path, destination)
        else:
            logging.debug("Skipping non-font file '%s'", file_path)


def run_additional_setup_in_container() -> None:
    extension_scripts = [
        get_absolute_path("setup_in_container.sh"),
        os.path.expanduser("~/setup_in_container.sh"),
    ]

    for script in extension_scripts:
        if os.path.isfile(script):
            logging.info("Running additional setup script: %s", script)
            result = subprocess.run(
                [script],
                check=True,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                encoding="utf-8",
            )
            logging.debug(result.stdout)
        else:
            logging.info("No additional setup script found at %s", script)


def is_running_in_docker() -> bool:
    return os.path.isfile("/.dockerenv")


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

    setup_dotfile_links()

    if is_running_in_docker():
        run_additional_setup_in_container()

    if args.new_host:
        setup_fonts()
        install_apt_packages()
        install_pip_modules()

    logging.info("Setup completed successfully")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.error("Installation was aborted by user")
