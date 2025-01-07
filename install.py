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

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s %(levelname)s: %(message)s"
)

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
HOME_DIR = os.path.expanduser("~")
BACKUP_DIR = os.path.realpath(os.path.join(HOME_DIR, f"dotfiles-backup-{timestamp}"))

FILES_TO_INSTALL = [
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

APT_PACKAGES_TO_INSTALL = [
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

PIP_MODULES_TO_INSTALL = ["pre-commit", "pipenv", "pipx", "typer"]


def _source_path(rel_path: str) -> str:
    return os.path.realpath(os.path.join(SCRIPT_DIR, rel_path))


def _home_path(rel_path: str) -> str:
    return os.path.join(HOME_DIR, rel_path)


def _backup_path(rel_path: str) -> str:
    return os.path.join(BACKUP_DIR, rel_path)


def _check_files_to_install() -> None:
    logging.debug("Checking to be installed files")
    missing_files = [
        to_install
        for to_install in FILES_TO_INSTALL
        if not os.path.exists(_source_path(to_install))
    ]
    if missing_files:
        logging.error(
            "Paths were specified to be copied but do not exist in this repository: %s",
            ", ".join(missing_files),
        )
        sys.exit(1)
    logging.info("All required input files were found")


def _create_backup() -> None:
    logging.debug("Creating backup of existing files")
    did_backup = False
    os.makedirs(BACKUP_DIR)
    for to_copy in FILES_TO_INSTALL:
        source_path = _home_path(to_copy)
        backup_path = _backup_path(to_copy)
        if os.path.exists(source_path):
            if os.path.islink(source_path):
                logging.debug(
                    "'%s' is already a symlink -> not backing up", source_path
                )
                continue
            logging.debug("Backing up '%s' to '%s'", source_path, backup_path)
            os.rename(source_path, backup_path)
            did_backup = True
        else:
            logging.debug("'%s' does not exist -> not backing up", source_path)
    if did_backup:
        logging.info("Existing files moved to backup at '%s'", BACKUP_DIR)
    else:
        os.removedirs(BACKUP_DIR)


def _setup_links(force: bool = False, symlink: bool = False) -> None:
    logging.debug("Setting up links for dotfiles in %s/", HOME_DIR)
    links_created = {}
    for to_link in FILES_TO_INSTALL:
        source_path = _source_path(to_link)
        link_path = _home_path(to_link)
        if os.path.isdir(source_path):
            result = create_links_for_directory(source_path, link_path, force, symlink)
            if result:
                links_created.update(result)
            else:
                logging.warning(
                    "No links created for source directory '%s'", source_path
                )
            continue
        logging.debug("      source_path '%s'", source_path)
        logging.debug("      link_path '%s'", link_path)

        if os.path.exists(link_path) or os.path.islink(link_path):
            if force and os.path.isfile(link_path):
                logging.debug("removing existing file '%s'", link_path)
                os.remove(link_path)
            elif os.path.islink(link_path):
                logging.debug("removing existing symlink '%s'", link_path)
                os.remove(link_path)
            elif os.path.samefile(source_path, link_path):
                logging.debug(
                    "'%s' is already a hard link to '%s'", link_path, source_path
                )
                continue
        links_created.update(create_link_for_file(source_path, link_path, symlink))
    logging.info(
        f"Successfully set up {len(links_created)} links for dotfiles in {HOME_DIR}"
    )


def create_link_for_file(source_path: str, link_path: str, symlink: bool) -> dict:
    links_created = {}
    if symlink:
        relative_link = os.path.relpath(source_path, os.path.dirname(link_path))
        logging.debug("creating symlink '%s' -> '%s'", link_path, relative_link)
        os.symlink(
            relative_link, link_path, target_is_directory=os.path.isdir(source_path)
        )
        links_created[link_path] = relative_link
    else:
        logging.debug("creating hard link '%s' -> '%s'", link_path, source_path)
        os.makedirs(os.path.dirname(link_path), exist_ok=True)
        os.link(source_path, link_path)
        links_created[link_path] = source_path
    return links_created


def create_links_for_directory(
    source_path: str, link_path: str, force: bool, symlink: bool
) -> dict:
    links_created = {}
    for root, _, files in os.walk(source_path):
        for name in files:
            source_file = os.path.join(root, name)
            link_file = os.path.join(
                link_path, os.path.relpath(source_file, source_path)
            )
            links_created.update(create_link_for_file(source_file, link_file, symlink))


def _install_software() -> None:
    logging.info(
        "Installing default apt packages (%s)", ", ".join(APT_PACKAGES_TO_INSTALL)
    )
    update_command = ["sudo", "apt-get", "update"]

    try:
        subprocess.run(
            update_command,
            check=True,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            encoding="utf-8",
        )

        packages_to_install = _get_installed_apt_packages()
        missing_packages = set(APT_PACKAGES_TO_INSTALL) - set(packages_to_install)
        if missing_packages:
            logging.warning(
                "The following packages were not found and will be skipped during installation: %s",
                ", ".join(missing_packages),
            )

        setup_command = ["sudo", "apt-get", "install", "-y"] + packages_to_install
        result = subprocess.run(
            setup_command,
            check=True,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            encoding="utf-8",
        )
    except subprocess.CalledProcessError as cpe:
        logging.error("Installing software failed with message:\n %s", cpe.stderr)
        sys.exit(1)
    logging.debug(result.stdout)
    logging.info("Successfully installed apt packages")


def _get_installed_apt_packages() -> List[str]:
    return [
        package
        for package in APT_PACKAGES_TO_INSTALL
        if subprocess.run(
            ["dpkg", "-s", package], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        ).returncode
        != 0
    ]


def _install_pip_modules() -> None:
    logging.info(
        "Installing default pip modules (%s)", ", ".join(PIP_MODULES_TO_INSTALL)
    )
    try:
        modules_to_install = _get_installed_pip_modules()
        missing_modules = set(PIP_MODULES_TO_INSTALL) - set(modules_to_install)
        if missing_modules:
            logging.warning(
                "The following modules were not found and will be skipped during installation: %s",
                ", ".join(missing_modules),
            )

        setup_command = [
            sys.executable,
            "-m",
            "pip",
            "install",
            *modules_to_install,
        ]
        result = subprocess.run(
            setup_command,
            check=True,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            encoding="utf-8",
        )
        logging.debug(result.stdout)

    except subprocess.CalledProcessError as cpe:
        logging.error("Installing software failed with message:\n %s", cpe.stderr)
        sys.exit(1)
    logging.info("Successfully installed pip modules")


def _get_installed_pip_modules() -> List[str]:
    return [
        module
        for module in PIP_MODULES_TO_INSTALL
        if subprocess.run(
            [sys.executable, "-m", "pip", "show", module],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).returncode
        != 0
    ]


def _setup_fonts() -> None:
    zips_to_download = [
        "https://github.com/ryanoasis/nerd-fonts/releases/download/v2.3.3/FiraCode.zip",
        "https://github.com/ryanoasis/nerd-fonts/releases/download/v2.3.3/RobotoMono.zip",
        "https://github.com/ryanoasis/nerd-fonts/releases/download/v2.3.3/SourceCodePro.zip",
        "https://github.com/ryanoasis/nerd-fonts/releases/download/v2.3.3/Hack.zip",
        "https://github.com/ryanoasis/nerd-fonts/releases/download/v2.3.3/Meslo.zip",
    ]
    font_files_to_download = [
        "https://github.com/romkatv/powerlevel10k-media/raw/master/MesloLGS%20NF%20Regular.ttf",
        "https://github.com/romkatv/powerlevel10k-media/raw/master/MesloLGS%20NF%20Bold.ttf",
        "https://github.com/romkatv/powerlevel10k-media/raw/master/MesloLGS%20NF%20Italic.ttf",
        "https://github.com/romkatv/powerlevel10k-media/raw/master/MesloLGS%20NF%20Bold%20Italic.ttf",
    ]
    logging.info(f"Installing fonts by downloading '{len(zips_to_download)}' zip files")
    for zip_url in zips_to_download:
        request = requests.get(zip_url, allow_redirects=True)
        zip_file = zipfile.ZipFile(io.BytesIO(request.content))
        with tempfile.TemporaryDirectory() as tmp_dirname:
            zip_file.extractall(tmp_dirname)
            _copy_to_font_dir(tmp_dirname)

    logging.info(
        f"Installing '{len(font_files_to_download)}' fonts by downloading font files"
    )
    for file_url in font_files_to_download:
        request = requests.get(file_url, allow_redirects=True)
        with tempfile.TemporaryDirectory() as tmp_dirname:
            filename = os.path.basename(unquote(file_url))
            filepath = os.path.join(tmp_dirname, filename)
            with open(filepath, "wb") as file:
                file.write(request.content)
            _copy_to_font_dir(filepath)
    command = "fc-cache -f -v"
    logging.info(f"Rebuilding font cache using '{command}'")
    subprocess.check_call(command, shell=True)
    logging.info(
        "Hint: Remember to configure font 'MesloLGS NF' as default "
        + "(see https://github.com/romkatv/powerlevel10k/blob/master/font.md)"
    )


def _copy_to_font_dir(source: str) -> None:
    font_dir = os.path.expanduser("~/.local/share/fonts")
    os.makedirs(font_dir, exist_ok=True)

    if os.path.isfile(source):
        destination = os.path.join(font_dir, os.path.basename(source))
        logging.debug(f"moving single font file '{source}' to '{font_dir}'")
        shutil.move(source, destination)
        return

    logging.debug(f"moving all font files from directory '{source}' to '{font_dir}'")
    for file in os.listdir(source):
        file_path = os.path.join(source, file)
        if file.endswith((".ttf", ".otf", ".ttc")):
            destination = os.path.join(font_dir, file)
            logging.debug(f"moving file '{file_path}' to '{destination}'")
            shutil.move(file_path, destination)
        else:
            logging.debug(f"skipping file '{file_path}' without font filetype")


def _run_additional_setup_in_container() -> None:
    extension_script_paths = [
        _source_path("setup_in_container.sh"),
        os.path.expanduser("~/setup_in_container.sh"),
    ]

    for script in extension_script_paths:
        if os.path.isfile(script):
            logging.info(f"Running additional setup script: {script}")
            result = subprocess.run(
                [script],
                check=True,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                encoding="utf-8",
            )
            logging.debug(result.stdout)
        else:
            logging.info(
                f"Extension point for creating links not used. If needed you can create it at {script}"
            )


def is_running_in_docker() -> bool:
    return os.path.isfile("/.dockerenv")


def parse_args():

    parser = argparse.ArgumentParser(description="Setup dotfiles")
    parser.add_argument(
        "--new-host",
        action="store_true",
        help="Also install apt + pip packages and fonts",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if is_running_in_docker():
        _check_files_to_install()
        _setup_links(force=True)
        _run_additional_setup_in_container()
    else:
        _check_files_to_install()
        _create_backup()
        _setup_links()

    if args.new_host:
        _setup_fonts()
        _install_software()
        _install_pip_modules()

    logging.info("Finished setup successfully :)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.error("Installation was aborted by user")
