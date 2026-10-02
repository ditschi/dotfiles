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
export no_proxy=localhost,127.0.0.1,172.17.0.*,192.168.*,bosch.com,inside.bosch.cloud
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

alias vpn-pw='get-password 2>/dev/null | osd-vpn-connect -k'
alias osd-vpn-connect-pw='vpn-pw'

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
    ssh-copy-id $machine
    scp -r ~/.ssh dci2lr@$machine:~/
    scp -r ~/dotfiles dci2lr@$machine:~/
}

groups-list() {
    # usage:
    #   groups-list -> list groups for current user
    #   groups-list <user> -> list groups for specific user
    user=$1
    for i in $(id -G $user); do echo "$(getent group $i | cut -d: -f1)"; done
}


export GHES_API_URL=https://github.boschdevcloud.com/api/v3/
export GHES_GRAPHQL_URL=https://github.boschdevcloud.com/api/graphql

export DOCKER_SERVICE="dev-env"
sde() {
    local script="./.devcontainer/sde.sh"
    if [[ -f "$script" ]]; then
        if [[ -x "$script" ]]; then
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


### Kerberos token auto-refresh: call external refresher and hint about cron.

# Path to expected refresher script
KERB_SCRIPT="$HOME/.local/bin/ensure-kerberos-token"

ensure_kerberos_token() {
    if [[ -x "$KERB_SCRIPT" ]]; then
        # Run external refresher; ignore non-zero so shell startup isn't disrupted
        "$KERB_SCRIPT" || true
    else
        echo "Warning: Kerberos refresher not found at $KERB_SCRIPT." >&2
        echo "Please update your dotfiles to include the refresher script." >&2
    fi
}

# Check whether a user cron job was installed; if not, give a hint how to install it.
# To avoid running 'crontab -l' on every shell startup, only perform this check at most once per day.
if command -v crontab >/dev/null 2>&1; then
    _kerb_cron_hint_cache_dir="${HOME}/.cache"
    _kerb_cron_hint_cache_file="${_kerb_cron_hint_cache_dir}/kerberos_cron_hint_last_check"

    # Best-effort creation of cache directory; ignore failure to avoid impacting shell startup.
    mkdir -p "${_kerb_cron_hint_cache_dir}" 2>/dev/null || true

    _kerb_today="$(date +%Y-%m-%d 2>/dev/null || printf '')"
    _kerb_last_check=""
    if [[ -f "${_kerb_cron_hint_cache_file}" ]]; then
        _kerb_last_check="$(<"${_kerb_cron_hint_cache_file}")"
    fi

    if [[ "${_kerb_today}" != "${_kerb_last_check}" ]]; then
        if ! crontab -l 2>/dev/null | grep -q "BEGIN ensure-kerberos-token"; then
            echo "Tip: No ensure-kerberos-token cron job found. Install with:" >&2
            echo "  $HOME/.local/bin/setup-ensure-kerberos-cron --install --freq 15" >&2
        fi
        # Record that we've performed today's check; ignore errors writing the file.
        echo "${_kerb_today}" > "${_kerb_cron_hint_cache_file}" 2>/dev/null || true
    fi

    unset _kerb_cron_hint_cache_dir _kerb_cron_hint_cache_file _kerb_today _kerb_last_check
fi

# Run the refresher once at shell startup
ensure_kerberos_token
