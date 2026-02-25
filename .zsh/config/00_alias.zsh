alias zshalias="nano $0"

export DOTFILES_REPO="${DOTFILES_REPO:-$HOME/dotfiles}"
export DOTFILES_REPO_URL="${DOTFILES_REPO_URL:-https://github.com/ditschi/dotfiles.git}"
export DOTFILES_UPDATE_MARKER="${DOTFILES_UPDATE_MARKER:-$HOME/.dotfiles-update-available}"
export DOTFILES_UPDATE_LAST_CHECK="${DOTFILES_UPDATE_LAST_CHECK:-$HOME/.dotfiles-update-last-check}"

dotfiles-setup() {
    if ! command -v git >/dev/null 2>&1; then
        echo "git not found; cannot clone dotfiles repository."
        return 1
    fi
    if ! command -v python3 >/dev/null 2>&1; then
        echo "python3 not found; cannot run install.py"
        return 1
    fi

    if [ ! -d "$DOTFILES_REPO/.git" ]; then
        echo "Dotfiles repository missing. Cloning from $DOTFILES_REPO_URL"
        if ! git clone "$DOTFILES_REPO_URL" "$DOTFILES_REPO"; then
            echo "Failed to clone dotfiles repository."
            return 1
        fi
    fi

    python3 "$DOTFILES_REPO/install.py" --new-host "$@"
}

dotfiles-update-check() {
    if [ ! -d "$DOTFILES_REPO/.git" ]; then
        echo "Dotfiles repo not found at: $DOTFILES_REPO"
        return 1
    fi

    if ! git -C "$DOTFILES_REPO" fetch --quiet; then
        echo "Dotfiles update check failed (git fetch)."
        return 1
    fi

    current_branch=$(git -C "$DOTFILES_REPO" rev-parse --abbrev-ref HEAD 2>/dev/null) || return 1
    upstream_ref="origin/$current_branch"
    if ! git -C "$DOTFILES_REPO" rev-parse --verify "$upstream_ref" >/dev/null 2>&1; then
        echo "No upstream branch found for '$current_branch'."
        return 1
    fi

    pending_count=$(git -C "$DOTFILES_REPO" rev-list --count "HEAD..$upstream_ref" 2>/dev/null || echo 0)
    if [ "${pending_count:-0}" -gt 0 ]; then
        : > "$DOTFILES_UPDATE_MARKER"
        echo "Dotfiles update available ($pending_count commits)."
        return 0
    fi

    rm -f "$DOTFILES_UPDATE_MARKER"
    echo "Dotfiles are up to date."
    return 0
}

dotfiles-update-status() {
    if [ -f "$DOTFILES_UPDATE_MARKER" ]; then
        echo "Dotfiles update marker is set."
    else
        echo "No dotfiles update marker set."
    fi

    if [ -f "$DOTFILES_UPDATE_LAST_CHECK" ]; then
        echo "Last update check: $(cat "$DOTFILES_UPDATE_LAST_CHECK")"
    else
        echo "Last update check: never"
    fi
}

dotfiles-update-apply() {
    if [ ! -d "$DOTFILES_REPO/.git" ]; then
        echo "Dotfiles repo not found at: $DOTFILES_REPO"
        return 1
    fi

    if ! git -C "$DOTFILES_REPO" pull --ff-only; then
        echo "Dotfiles pull failed."
        return 1
    fi

    if ! command -v python3 >/dev/null 2>&1; then
        echo "python3 not found; cannot run install.py"
        return 1
    fi

    if python3 "$DOTFILES_REPO/install.py" --update --non-interactive; then
        rm -f "$DOTFILES_UPDATE_MARKER"
        echo "Dotfiles updated and re-linked successfully."
        return 0
    fi

    echo "Dotfiles install step failed."
    return 1
}

alias update-dotfiles="dotfiles-update-apply"

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


alias branch='git rev-parse --abbrev-ref HEAD'
alias issue='git rev-parse --abbrev-ref HEAD | grep -Eo "[A-Z]+-[0-9]+"'
alias g='git'

alias ipv6-disable='sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1 && sudo sysctl -w net.ipv6.conf.default.disable_ipv6=1 && sudo sysctl -w net.ipv6.conf.lo.disable_ipv6=1'
alias ipv6-enable='sudo sysctl -w net.ipv6.conf.all.disable_ipv6=0 && sudo sysctl -w net.ipv6.conf.default.disable_ipv6=0 && sudo sysctl -w net.ipv6.conf.lo.disable_ipv6=0'


store-password() {
    if [ -n "$1" ]; then
        user="$1"
    else
        user="$(whoami)"
    fi

    secret-tool store --label "User Credentials" password "$user"
}

get-password() {
    if [ -n "$1" ]; then
        user="$1"
    else
        user="$(whoami)"
    fi

    result=$(secret-tool lookup password "$user")
    if [ -z "$result" ]; then
        echo "$PASSWORD"
    else
        echo "$result"
    fi
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
