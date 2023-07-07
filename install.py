#!/usr/bin/python3
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

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s')

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
HOME_DIR = os.path.expanduser("~")
BACKUP_DIR = os.path.realpath(os.path.join(HOME_DIR, f"dotfiles-backup-{timestamp}"))

FILES_TO_INSTALL = [".bashrc", ".gitconfig", ".p10k.zsh", ".zprofile", ".zsh", ".zshrc", "setup_links_in_container.sh"]
APT_PACKAGES_TO_INSTALL = "zsh git wget autojump fonts-powerline fonts-firacode fzf"

def _source_path(rel_path):
    return os.path.realpath(os.path.join(SCRIPT_DIR, rel_path))

def _home_path(rel_path):
    return os.path.join(os.path.realpath(HOME_DIR), rel_path)


def _backup_path(rel_path):
    return os.path.join(BACKUP_DIR, rel_path)


def _check_files_to_install():
    logging.debug("Checking to be installed files")
    missing_files = [ to_install for to_install in FILES_TO_INSTALL if not os.path.exists(_source_path(to_install)) ]
    if missing_files:
        logging.error("Paths were specified to be copied but to not exist in this repository: %s", ", ".join(missing_files))
        sys.exit(1)
    logging.info("All required input files were found")


def _create_backup():
    logging.debug("Creating backup of existing files")
    did_backup = False
    os.makedirs(BACKUP_DIR)
    for to_copy in FILES_TO_INSTALL:
        source_path = _home_path(to_copy)
        backup_path = _backup_path(to_copy)
        if os.path.exists(source_path):
            if os.path.islink(source_path):
                logging.debug("'%s' is already a symlink -> not backing up", source_path)
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


def _setup_symlinks():
    logging.debug("Setting up symlinks for dotfiles in %s/", HOME_DIR)
    for to_symlink in FILES_TO_INSTALL:
        source_path = _source_path(to_symlink)
        symlink_path = _home_path(to_symlink)
        logging.debug("      source_path '%s'", source_path)
        logging.debug("      symlink_path '%s'", symlink_path)

        relative_link = os.path.relpath(source_path, os.path.dirname(symlink_path))
        if os.path.islink(symlink_path):
            logging.debug("removing existing symlink '%s'", symlink_path)
            os.remove(symlink_path)
        logging.debug("creating symlink '%s' -> '%s'", symlink_path, relative_link)
        os.symlink(relative_link, symlink_path, target_is_directory=os.path.isdir(source_path))
    logging.info("Successfully set up symlinks for dotfiles in %s", HOME_DIR)


def _install_software():
    logging.info("Installing default apt packages (%s)", APT_PACKAGES_TO_INSTALL)
    update_command = f"sudo apt-get update"

    setup_command = f"sudo apt-get install -y {APT_PACKAGES_TO_INSTALL}"

    try:
        subprocess.run(update_command, check=True, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf-8')
        result = subprocess.run(setup_command, check=True, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf-8')
    except subprocess.CalledProcessError as cpe:
        logging.error("Installing software failed with message:\n %s", cpe.stderr)
        sys.exit(1)
    logging.info("Successfully installed apt packages")
    logging.debug(result.stdout)
    # git clone https://github.com/clvv/fasd.git ~/fasd && cd ~/fasd && sudo make install


def _setup_fonts():
    zips_to_download = [
        "https://github.com/ryanoasis/nerd-fonts/releases/download/v2.3.3/FiraCode.zip",
        "https://github.com/ryanoasis/nerd-fonts/releases/download/v2.3.3/RobotoMono.zip",
        "https://github.com/ryanoasis/nerd-fonts/releases/download/v2.3.3/SourceCodePro.zip",
        "https://github.com/ryanoasis/nerd-fonts/releases/download/v2.3.3/Hack.zip",
        "https://github.com/ryanoasis/nerd-fonts/releases/download/v2.3.3/Meslo.zip"

        ]
    font_files_to_download = [
        "https://github.com/romkatv/powerlevel10k-media/raw/master/MesloLGS%20NF%20Regular.ttf",
        "https://github.com/romkatv/powerlevel10k-media/raw/master/MesloLGS%20NF%20Bold.ttf",
        "https://github.com/romkatv/powerlevel10k-media/raw/master/MesloLGS%20NF%20Italic.ttf",
        "https://github.com/romkatv/powerlevel10k-media/raw/master/MesloLGS%20NF%20Bold%20Italic.ttf"
        ]
    logging.info(f"Installing fronts by downloading '{len(zips_to_download)}' zip files")
    for zip in zips_to_download:
        request = requests.get(zip, allow_redirects=True)
        zip_file = zipfile.ZipFile(io.BytesIO(request.content))
        with tempfile.TemporaryDirectory() as tmp_dirname:
            zip_file.extractall(tmp_dirname)
            _copy_to_font_dir(tmp_dirname)

    logging.info(f"Installing '{len(font_files_to_download)}' fronts by downloading font files")
    for file_url in font_files_to_download:
        request = requests.get(file_url, allow_redirects=True)
        with tempfile.TemporaryDirectory() as tmp_dirname:
            filename = os.path.basename(unquote(file_url))
            filename = os.path.join(tmp_dirname, filename)
            with open(filename, "wb") as file:
                file.write(request.content)
            _copy_to_font_dir(filename)
    command = "fc-cache -f -v"
    logging.info(f"Rebuilding font cache using '{command}'")
    subprocess.check_call(command, shell=True)
    logging.info(f"Hint: Remember to configure font 'MesloLGS NF' as default (see https://github.com/romkatv/powerlevel10k/blob/master/font.md)")


def _copy_to_font_dir(source):
    font_dir = os.path.expanduser("~/.local/share/fonts")
    os.makedirs(font_dir, exist_ok=True)

    if os.path.isfile(source):
        destination = os.path.join(font_dir, os.path.basename(source))
        logging.debug(f"moving single font file '{source}' to '{font_dir}'")
        shutil.move(source, destination)
        return

    logging.debug(f"moving all font files from directory '{source}' to '{font_dir}'")
    for file in os.listdir(source):
        file = os.path.join(source, file)
        destination = os.path.join(font_dir, file)
        if file.endswith('.ttf') or file.endswith('.otf') or file.endswith('.ttc'):
            logging.debug(f"moving file '{file}'")
            shutil.move(file, destination)
        else:
            logging.debug(f"skipping file '{file}' without font filetype")


def main():
    _check_files_to_install()
    _create_backup()
    _setup_symlinks()
    _setup_fonts()
    _install_software()
    logging.info("Finished setup successfully :)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.error("Installation was aborted by user")
