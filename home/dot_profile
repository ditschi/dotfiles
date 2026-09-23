# ~/.profile: executed by the command interpreter for login shells.
# This file is not read by bash(1), if ~/.bash_profile or ~/.bash_login
# exists.
# see /usr/share/doc/bash/examples/startup-files for examples.
# the files are located in the bash-doc package.

# the default umask is set in /etc/profile; for setting the umask
# for ssh logins, install and configure the libpam-umask package.
#umask 022

# if running bash
if [ -n "$BASH_VERSION" ]; then
    # include .bashrc if it exists
    if [ -f "$HOME/.bashrc" ]; then
        . "$HOME/.bashrc"
    fi
fi

# set PATH so it includes user's private bin if it exists
if [ -d "$HOME/bin" ]; then
    PATH="$HOME/bin:$PATH"
fi

# set PATH so it includes user's private bin if it exists
if [ -d "$HOME/.local/bin" ]; then
    PATH="$HOME/.local/bin:$PATH"
fi

if [ -f ~/dotfiles/.zsh/config/05_pyenv.zsh ]; then
    . ~/dotfiles/.zsh/config/05_pyenv.zsh
fi

# BEGIN ANSIBLE MANAGED BLOCK
# Handle new user setup and OCS launch
NTUID=$(whoami | cut -d@ -f1)
if [ -e "/home/$NTUID/.new_user" ]; then
    bash "/opt/osd/newuser-setup.sh" 2>/dev/null
fi
# END ANSIBLE MANAGED BLOCK
