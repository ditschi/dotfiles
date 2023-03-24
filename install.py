#!/usr/bin/python3
import os
import logging
import subprocess
import sys
from datetime import datetime


logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
HOME_DIR = os.path.expanduser("~")
BACKUP_DIR = os.path.join(HOME_DIR, f"dotfiles-backup-{timestamp}")

FILES_TO_INSTALL = [".bashrc", ".gitconfig", ".p10k.zsh", ".zprofile", ".zsh/", ".zshrc"]
APT_PACKAGES_TO_INSTALL = "zsh git wget autojump fonts-powerline fonts-firacode fzf"

def _source_path(rel_path):
    return os.path.abspath(os.path.join(SCRIPT_DIR, rel_path))

def _home_path(rel_path):
    return os.path.abspath(os.path.join(HOME_DIR, rel_path))

def _backup_path(rel_path):
    return os.path.abspath(os.path.join(BACKUP_DIR, rel_path))


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
        if os.path.islink(symlink_path):
            logging.debug("removing existing symlink '%s'", symlink_path)
            os.remove(symlink_path)
        logging.debug("creating symlink '%s' -> '%s'", source_path, symlink_path)
        os.symlink(source_path, symlink_path, target_is_directory=os.path.isdir(source_path))
    logging.info("Successfully set up symlinks for dotfiles in %s", HOME_DIR)



def _install_software():
    logging.info("Installing default apt packages (%s)", APT_PACKAGES_TO_INSTALL)
    update_command = f"sudo apt-get update && sudo apt-get install {APT_PACKAGES_TO_INSTALL}"

    setup_command = f"sudo apt-get update && sudo apt-get install {APT_PACKAGES_TO_INSTALL}"

    try:
        subprocess.run(update_command, check=True, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf-8')
        result = subprocess.run(setup_command, check=True, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf-8')
    except subprocess.CalledProcessError as cpe:
        logging.error("Installing software failed with message:\n %s", cpe.stderr)
        sys.exit(1)
    logging.info("Successfully installed apt packages")
    logging.debug(result.stdout)
    # git clone https://github.com/clvv/fasd.git ~/fasd && cd ~/fasd && sudo make install

def main():
    _check_files_to_install()
    _create_backup()
    _setup_symlinks()
    _install_software()
    logging.info("Finished setup successfully :)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.error("Installation was aborted by user")


#
