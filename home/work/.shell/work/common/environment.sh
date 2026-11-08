# shellcheck shell=bash

if [[ ${WORK_SETUP} != "true" ]]; then # set by the shell startup loader
    return
fi

# shellcheck disable=SC2034
SCRIPTDIR=$(dirname -- "$0")

### MODIFIED BY OSD-PROXY-PACKAGE BEGIN ###

# Kerberos token check in bash prompt
PROMPT_COMMAND=__prompt_command

__prompt_command() {
    if klist -s; then
        export KRB_STATUS_MSG=""
    else
        export KRB_STATUS_MSG="(No Kerberos token, run kinit) "
    fi
}

RED="\[$(tput setaf 1)\]"
RESET="\[$(tput sgr0)\]"
PS1="${RED}\${KRB_STATUS_MSG}${RESET}${PS1}"

### MODIFIED BY OSD-PROXY-PACKAGE END ###

# proxy setup
export http_proxy=http://localhost:3128
export https_proxy=$http_proxy
export ftp_proxy=$http_proxy
export no_proxy='localhost,127.0.0.1,172.17.0.*,192.168.*,bosch.com,inside.bosch.cloud'
export HTTP_PROXY=$http_proxy
export HTTPS_PROXY=$http_proxy
export FTP_PROXY=$http_proxy
export NO_PROXY=$no_proxy

# dev-env setup
DOCKER_USER=$(whoami)
DOCKER_UID=$(id -u)
DOCKER_GID=$(id -g)
CONTAINER_USER=$(whoami)
CONTAINER_UID=$(id -u)
CONTAINER_GID=$(id -g)
export DOCKER_USER DOCKER_UID DOCKER_GID CONTAINER_USER CONTAINER_UID CONTAINER_GID
export CONAN_LOGIN_USERNAME=dci2lr

# aliases
alias fix-wifi='sudo systemctl restart NetworkManager.service'

# VPN through work-net: env password, failure guard; disconnect pauses the watcher.
alias vpn-pw='work-net vpn connect'
alias osd-vpn-connect-pw='vpn-pw'
alias osd-vpn-disconnect='work-net vpn disconnect'

alias TCCEdit="NODE_TLS_REJECT_UNAUTHORIZED=0 ~/tools/tccEdit/TCCEdit"
alias tccedit="TCCEdit"
alias cruft-sync='cruft update -c $(branch) -y && git add -u .'
alias cruft-fix-diff="cruft diff > patch.diff && git apply patch.diff && rm patch.diff"

alias chsh-bosch="echo 'https://inside-docupedia.bosch.com/confluence/display/BSC2OSD/Change+default+shell+from+bash+to+zsh \n \
    1. sudo nano /etc/sssd/sssd.conf \n \
        default_shell = /bin/bash \n \
        override_shell = /bin/zsh # <- add this \n \
    2. sudo rm /var/lib/sss/db/cache_de.bosch.com.ldb /var/lib/sss/db/ccache_DE.BOSCH.COM && sudo systemctl restart sssd \n \
    3. restart session'"

# ansible
alias ap="ansible-playbook"
alias ave="ansible-vault encrypt"
alias avd="ansible-vault decrypt"

# functions
setup-machine() {
    machine=$1
    ssh-copy-id "$machine"
    scp -r ~/.ssh "dci2lr@$machine:~/"
    scp -r ~/dotfiles "dci2lr@$machine:~/"
}

groups-list() {
    # usage:
    #   groups-list -> list groups for current user
    #   groups-list <user> -> list groups for specific user
    user=$1
    for group_id in $(id -G ${user:+"$user"}); do getent group "$group_id" | cut -d: -f1; done
}

export GHES_API_URL=https://github.boschdevcloud.com/api/v3/
export GHES_GRAPHQL_URL=https://github.boschdevcloud.com/api/graphql

export DOCKER_SERVICE="dev-env"
sde() {
    local script="./.devcontainer/sde.sh"
    if [[ -f $script ]]; then
        if [[ -x $script ]]; then
            "$script" "$@"
        else
            bash "$script" "$@"
        fi
        return $?
    fi
    command sde -- "$@"
}

sdx() {
    command sde --extended -- "$@"
}
