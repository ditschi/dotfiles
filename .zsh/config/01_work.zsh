alias zshwork="nano $0"

if [[ "${WORK_SETUP}" != "true" ]]; then # set in 00_LOADER.zsh
    return
fi

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
export no_proxy=localhost,127.0.0.1,127.*,172.*,10.*,de.bosch.com,apac.bosch.com,emea.bosch.com,us.bosch.com,bosch.cloud,rb-artifactory.bosch.com,sourcecode01.de.bosch.com,sourcecode.socialcoding.bosch.com,sourcecode06.dev.bosch.com
export HTTP_PROXY=$http_proxy
export HTTPS_PROXY=$http_proxy
export FTP_PROXY=$http_proxy
export NO_PROXY=$no_proxy

# dev-env setup
export DOCKER_USER=$(whoami) && export DOCKER_UID=$(id -u) && export DOCKER_GID=$(id -g)
export CONTAINER_USER=$(whoami) && export CONTAINER_UID=$(id -u) && export CONTAINER_GID=$(id -g)
export CONAN_LOGIN_USERNAME=dci2lr

# aliases
alias fix-wifi='sudo systemctl restart NetworkManager.service'

alias kinit-pw='echo $(get-password 3>/dev/null) | kinit'
alias vpn-pw='get-password 3>/dev/null | osd-vpn-connect -k'
alias osd-vpn-connect-pw='vpn-pw'

alias ldap-userdetails="ldapsearch-bosch -cn" # <USER-ID>
alias ldap-usergroups="ldap-groups"           # <USER-ID>
alias TCCEdit="NODE_TLS_REJECT_UNAUTHORIZED=0 ~/tools/tccEdit/TCCEdit"
alias tccedit="TCCEdit"
alias branch='git branch --no-color --show-current'
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
alias ldapsearch-bosch="ldapsearch -D dc=bosch,dc=com -Z -H rb-gc-12.de.bosch.com:3268"

ldap-user-info-full() {
    nt_user=$1

    # Check if username is provided
    if [[ -z "$nt_user" ]]; then
        echo "Usage: ldap-user-info <username>"
        return 1
    fi
    ldapsearch -H ldaps://rb-gc-lb.bosch.com:3269 \
        -b "OU=LR,DC=de,DC=bosch,DC=com" \
        -D "de\\dci2lr" \
        -x "(|(displayName=*${nt_user}*)(samAccountname=*${nt_user}*))" \
        -w "$PASSWORD"
}

ldap-user-info() {
    nt_user=$1

    # Check if username is provided
    if [[ -z "$nt_user" ]]; then
        echo "Usage: ldap-user-info <username>"
        return 1
    fi

    # Execute ldapsearch with specific fields in logical order, limit to first result with -z 1
    # Fields: names first, then identity, location, and organization info
    ldapsearch -H ldaps://rb-gc-lb.bosch.com:3269 \
        -b "OU=LR,DC=de,DC=bosch,DC=com" \
        -D "de\\dci2lr" \
        -x -z 1 \
        "(|(displayName=*${nt_user}*)(samAccountname=*${nt_user}*))" \
        cn givenName sn displayName uid mail c co l physicalDeliveryOfficeName department company \
        -w "$PASSWORD"
}

ldap-groups() {
    username=$1
    ldapsearch-bosch -cn "$username" memberOf
}

setup-machine() {
    machine=$1
    ssh-copy-id $machine
    scp -r ~/.ssh dci2lr@$machine:~/
    scp -r ~/dotfiles dci2lr@$machine:~/
}

groups_list() {
    # usage:
    #   groups_list -> list groups for current user
    #   groups_list <user> -> list groups for specific user
    user=$1
    for i in $(id -G $user); do echo "$(getent group $i | cut -d: -f1)"; done
}


export DOCKER_SERVICE="dev-env"
sde() {
    COMMAND="$@"
    if [ -f .devcontainer/initialize-command.sh ]; then
        ./.devcontainer/initialize-command.sh
    else
        echo '.devcontainer/initialize-command.sh not found, skipping execution'
    fi

    docker compose build --pull $DOCKER_SERVICE
    docker compose run --rm \
           -v "${HOME}/:${HOME}/mnt/home/" \
           $DOCKER_SERVICE \
        "
            if [ -f ./.devcontainer/post-start-command.sh ]; then
                ./.devcontainer/post-start-command.sh
            else
                echo '.devcontainer/post-start-command.sh not found, skipping execution'
            fi \
            && if [ -z \"$COMMAND\" ]; then
                exec bash
            else
                bash -c \"$COMMAND\"
            fi
        "
}

sdx() {
    COMMAND="$@"
    if [ -f .devcontainer/initialize-command.sh ]; then
        ./.devcontainer/initialize-command.sh
    else
        echo '.devcontainer/initialize-command.sh not found, skipping execution'
    fi

    mkdir -p "${HOME}/.docker-cache/.zsh"
    mkdir -p "${HOME}/.docker-cache/.local_share_zinit"

    docker compose build --pull $DOCKER_SERVICE
    docker compose run --rm \
        -v "${HOME}/:/mnt/host_home/" \
        -v "/usr/share/autojump/:/usr/share/autojump/" \
        -v "${HOME}/.docker-cache/.zsh:${HOME}/.zsh/" \
        -v "${HOME}/.docker-cache/.local_share_zinit:${HOME}/.local/share/zinit/" \
        $DOCKER_SERVICE \
        "
            if [ -f /mnt/host_home/dotfiles/install.py ]; then
                python3 /mnt/host_home/dotfiles/install.py
            else
                echo '/mnt/host_home/dotfiles/install.py not found, skipping execution'
            fi \
            && if [ -f ./.devcontainer/post-start-command.sh ]; then
                ./.devcontainer/post-start-command.sh
            else
                echo '.devcontainer/post-start-command.sh not found, skipping execution'
            fi \
            && if [ -z \"$COMMAND\" ]; then
                exec zsh || exec bash
            else
                zsh -c \"$COMMAND\" || bash -c \"$COMMAND\"
            fi
        "
}

sdz() {
    COMMAND="$@"
    if [ -f .devcontainer/initialize-command.sh ]; then
        ./.devcontainer/initialize-command.sh
    else
        echo '.devcontainer/initialize-command.sh not found, skipping execution'
    fi

    docker-compose build $DOCKER_SERVICE
    docker-compose run --rm \
        -v "${HOME}/.zshrc:${HOME}/.zshrc" \
        -v "${HOME}/.zsh/:${HOME}/.zsh/" \
        -v "${HOME}/.env:${HOME}/.env" \
        -v "${HOME}/.netrc:${HOME}/.netrc" \
        -v "${HOME}/.p10k.zsh:${HOME}/.p10k.zsh" \
        -v "${HOME}/.shared_history:${HOME}/.shared_history" \
        -v "${HOME}/.local/share/:${HOME}/.local/share/" \
        -v "/usr/share/autojump/:/usr/share/autojump/" \
        -v "${HOME}/.cache/:${HOME}/.cache/" \
        $DOCKER_SERVICE \
        "
            if [ -f ./.devcontainer/post-start-command.sh ]; then
                ./.devcontainer/post-start-command.sh
            else
                echo '.devcontainer/post-start-command.sh not found, skipping execution'
            fi \
            && if [ -z \"$COMMAND\" ]; then
                exec zsh || exec bash
            else
                zsh -c \"$COMMAND\" || bash -c \"$COMMAND\"
            fi
        "
}

function ra6-setup-variant() {
    variant=${1:-$variant}
    ./tools/jenkins/shared/scripts/conan-install.sh . $variant $variant $(basename -s .git $(git config --get remote.origin.url))
    ./tools/jenkins/shared/scripts/setup_and_configure.sh . $variant
}
function ra6-build-variant() {
    variant=${1:-$variant}
    command="./tools/jenkins/shared/scripts/build-cmake.sh . $variant $variant"
    eval $command || ra6-setup-variant $variant && eval $command $variant
}
function ra6-clean-variant() {
    variant=${1:-$variant}
    rm -rf ./build/$variant
}
function ra6-helix-gui() {
    variant=${1:-$variant}
    command="cmake --build  --preset=$variant --target qac_daad_gui -- -dkeepdepfile"
    eval $command || echo "\n\n\n\n\n[WARNING] Retrying with setup" && ra6-setup-variant $variant && eval $command
}

kinit-pw
