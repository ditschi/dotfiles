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


export DOCKER_SERVICE="dev-env"
# ---------------------------------------------------------------------------
# _sde_run: helper for sde/sdx that builds a single command string
#           joined with &&, so it can be passed as a quoted string to the container.
#           This supports the style where the command is wrapped in double quotes.
# Usage: _sde_run <shell> <setup_cmd> <extra_volumes...> -- [user command...]
#   shell:         "bash" or "zsh" (zsh falls back to bash if unavailable)
#   setup_cmd:     command to run inside container before post-start (empty string to skip)
#   extra_volumes: additional -v flags (terminated by --)
#   user command:  optional command args (quotes preserved)
# ---------------------------------------------------------------------------
_sde_run() {
    local shell="$1"; shift
    local setup_cmd="$1"; shift

    # Collect extra volume flags until we hit "--"
    local -a extra_vols=()
    while [[ $# -gt 0 && "$1" != "--" ]]; do
        extra_vols+=("$1"); shift
    done
    [[ "$1" == "--" ]] && shift
    # $@ now contains user command args with preserved quoting

    # --- Compose file check ---
    if [ ! -f docker-compose.yml ] && [ ! -f compose.yaml ]; then
        echo 'Error: No docker-compose.yml or compose.yaml found in this directory. Cannot start devcontainer.'
        return 1
    fi

    # --- Host-side: run initialize-command.sh if present ---
    if [ -f .devcontainer/initialize-command.sh ]; then
        ./.devcontainer/initialize-command.sh
    else
        echo 'Info: .devcontainer/initialize-command.sh not found, skipping initialization.'
    fi

    # --- Build ---
    docker compose build $DOCKER_SERVICE

    # --- Build the command string ---
    post_start_cmd='if [ -f ./.devcontainer/post-start-command.sh ]; then ./.devcontainer/post-start-command.sh; else echo "Info: .devcontainer/post-start-command.sh not found, skipping post-start setup."; fi'

    # --- Determine shell launch logic ---
    local cmd_str=""
    if [ $# -le 0 ]; then
        # interactive shell case, run setup (incl. shell setup), then start shell
        cmd_str="$setup_cmd && $post_start_cmd && "
        [[ "$shell" == "zsh" ]] && cmd_str+='exec zsh || exec bash' || cmd_str+='exec bash'
    else
        # user command case - run only post-start, then user command
        cmd_str="( $post_start_cmd ) && bash -c \"$@\""
    fi

    echo "[DEBUG] Running in container: $cmd_str"
    docker compose run --rm \
        "${extra_vols[@]}" \
        $DOCKER_SERVICE \
        "$cmd_str"
}

# ---------------------------------------------------------------------------
# sde: start devcontainer with bash (minimal, no dotfiles setup)
# ---------------------------------------------------------------------------
sde() {
    _sde_run bash "" \
        -v "${HOME}/:/mnt/host_home/" \
        -- "$@"
}

# ---------------------------------------------------------------------------
# sdx: start devcontainer with EXTENDED setup (zsh/bash + full dotfiles)
#
# Both zsh and bash get the better setup from host (all dotfiles, plugins, history).
#
# Volumes:
#   /mnt/host_home/           - host home (rw) for install.py + .gitconfig propagation
#   dotfiles-zinit-cache      - named volume for zinit (isolated from host)
#   dotfiles-apt-cache        - named volume caching .deb files across --rm runs
#   commandhistory.d/<repo>_zsh - per-repo persistent zsh history
#   /usr/share/autojump/      - autojump data from host (ro)
#
# Setup: install.py handles everything:
#   1. apt install zsh deps (idempotent, cached debs)
#   2. backup bind-mounted files to ~/.dotfiles-backup/<timestamp>/ (preserves company configs)
#   3. symlink dotfiles (full zsh/bash setup from repo)
#   4. seed zinit cache from host on first run
# ---------------------------------------------------------------------------
sdx() {
    local repo_name
    repo_name="$(basename "$(pwd)")"

    # Ensure zsh history file exists on host (prevent Docker creating it as a directory)
    mkdir -p "${HOME}/.docker-cache/zinit"
    mkdir -p "${HOME}/.docker-cache/apt"
    mkdir -p "${HOME}/.docker-cache/dotfiles-installer"
    mkdir -p "${HOME}/.docker-cache/commandhistory.d"
    touch "${HOME}/.docker-cache/commandhistory.d/${repo_name}_zsh"

    _sde_run zsh "python3 /mnt/host_home/dotfiles/install.py" \
        -v "${HOME}/:/mnt/host_home/" \
        -v "${HOME}/.docker-cache/zinit:${HOME}/.local/share/zinit/" \
        -v "${HOME}/.docker-cache/apt:/var/cache/apt/archives/" \
        -v "${HOME}/.docker-cache/dotfiles-installer:${HOME}/.local/share/dotfiles-installer" \
        -v "${HOME}/.docker-cache/commandhistory.d/${repo_name}_zsh:${HOME}/.zsh_history" \
        -v "/usr/share/autojump/:/usr/share/autojump/:ro" \
        -- "$@"
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
