alias zshalias="nano $0"

export DOTFILES_REPO="${DOTFILES_REPO:-$HOME/dotfiles}"
export DOTFILES_REPO_URL="${DOTFILES_REPO_URL:-https://github.com/ditschi/dotfiles.git}"
export DOTFILES_UPDATE_STATE="${DOTFILES_UPDATE_STATE:-$HOME/.dotfiles-update-state}"
export DOTFILES_UPDATE_LAST_CHECK="${DOTFILES_UPDATE_LAST_CHECK:-$HOME/.dotfiles-update-last-check}"

dotfiles-setup() {
    if ! command -v git >/dev/null 2>&1; then
        echo "git not found; cannot clone dotfiles repository."
        return 1
    fi
    if ! command -v python3 >/dev/null 2>&1; then
        echo "python3 not found; cannot run machine setup"
        return 1
    fi

    if [ ! -d "$DOTFILES_REPO/.git" ]; then
        echo "Dotfiles repository missing. Cloning from $DOTFILES_REPO_URL"
        if ! git clone "$DOTFILES_REPO_URL" "$DOTFILES_REPO"; then
            echo "Failed to clone dotfiles repository."
            return 1
        fi
    fi
    "$DOTFILES_REPO/bootstrap" "$@"
}

dotfiles-update-check() {
    if command -v machine >/dev/null 2>&1; then
        machine update --check
    else
        echo "machine helper not found; run $DOTFILES_REPO/bootstrap"
        return 1
    fi
}

dotfiles-update-status() {
    if grep -qs '^pending=1$' "$DOTFILES_UPDATE_STATE"; then
        echo "Dotfiles update is pending."
    else
        echo "No dotfiles update pending."
    fi

    if [ -f "$DOTFILES_UPDATE_LAST_CHECK" ]; then
        echo "Last update check: $(cat "$DOTFILES_UPDATE_LAST_CHECK")"
    else
        echo "Last update check: never"
    fi
}

dotfiles-update() {
    if command -v machine >/dev/null 2>&1; then
        machine update "$@"
    elif [ -x "$DOTFILES_REPO/machine_cli/machine" ]; then
        "$DOTFILES_REPO/machine_cli/machine" update "$@"
    else
        echo "machine helper not found; run $DOTFILES_REPO/bootstrap"
        return 1
    fi
}

alias update-dotfiles="dotfiles-update"
alias machine-setup="dotfiles-setup"
alias update-system="get-password | sudo -S apt update && sudo apt upgrade -y"

alias docker-compose='docker compose'
alias dc='docker compose'

#alias cursor='~/Applications/cursor.AppImage --no-sandbox > /dev/null 2>&1 &'
alias cursor-setup='mkdir -p ~/Applications/ && curl -L -o ~/Applications/cursor.AppImage https://downloader.cursor.sh/linux/appImage/x64 && chmod +x ~/Applications/cursor.AppImage && command -v fusermount >/dev/null || echo "Warning: requires libfuse which is not installed. Please install it using your package manager."'

# enable color support of ls and other tools
alias ls='ls --color=auto'
alias ll='ls -alF --color=auto'
alias la='ls -a --color=auto'
alias grep='grep --color=auto'
alias fgrep='fgrep --color=auto'
alias egrep='egrep --color=auto'


alias branch='git branch --show-current'
alias issue='git rev-parse --abbrev-ref HEAD | grep -Eo "[A-Z]+-[0-9]+"'
alias g='git'

alias ipv6-disable='sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1 && sudo sysctl -w net.ipv6.conf.default.disable_ipv6=1 && sudo sysctl -w net.ipv6.conf.lo.disable_ipv6=1'
alias ipv6-enable='sudo sysctl -w net.ipv6.conf.all.disable_ipv6=0 && sudo sysctl -w net.ipv6.conf.default.disable_ipv6=0 && sudo sysctl -w net.ipv6.conf.lo.disable_ipv6=0'


store-password() {
    local user="${1:-$(whoami)}"
    secret-tool store --label "User Credentials" password "$user"
}

clone_org_repos() {
  local OWNER=$1
  for repo in $(gh repo list $OWNER --limit 1000 --json name --jq '.[].name'); do
    gh repo clone $OWNER/$repo
  done
}

get-ipv4() {
    dig  "$1" A +short
}

get-ipv6() {
    dig "$1" AAAA +short
}

if command -v yazi >/dev/null 2>&1; then
    y() {
        local tmp cwd
        tmp="$(mktemp -t "yazi-cwd.XXXXXX")"
        yazi "$@" --cwd-file="$tmp"
        if cwd="$(command cat -- "$tmp")" && [ -n "$cwd" ] && [ "$cwd" != "$PWD" ]; then
            builtin cd -- "$cwd" || return
        fi
        rm -f -- "$tmp"
    }
fi
