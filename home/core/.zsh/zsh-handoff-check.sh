# shellcheck shell=bash
# Health check for the bash -> zsh handoff. Sourced by ~/.bashrc only (bash-specific).
# The result is cached in a state file and re-used until a watched file, the zsh
# binary or the pending-update flag changes; `zsh-recheck` clears the cache.

_zhc_state_file() {
    printf '%s' "${XDG_STATE_HOME:-$HOME/.local/state}/dotfiles/zsh-handoff"
}

_zhc_report() {
    printf 'zsh handoff skipped: %s (fix it, then run: zsh-recheck)\n' "$1" >&2
}

# True if anything that influences zsh startup is newer than the state file.
_zhc_stale() {
    local state="$1" zsh_bin="$2" f
    for f in "$zsh_bin" \
        "${BASH_SOURCE[0]}" \
        "$HOME/.zshenv" "$HOME/.zprofile" "$HOME/.zshrc" "$HOME/.zshrc-local" \
        "$HOME/.preferred-shell" "$HOME/.zsh/plugins.txt" \
        "$HOME/.zsh/machine-profile.sh" "$HOME"/.zsh/*.sh "$HOME"/.zsh/config/*.zsh \
        "$HOME/.zsh" "$HOME/.zsh/config"; do # directories: a removed or renamed file changes their mtime
        [ "$f" -nt "$state" ] && return 0
    done
    return 1
}

# Prints the failure reason and returns 1, or returns 0 when zsh is healthy.
_zhc_run_checks() {
    local zsh_bin="$1" tmp out err rc reason="" timeout_cmd=""
    [ -x "$zsh_bin" ] || {
        echo "zsh is not executable"
        return 1
    }
    [ -r "$HOME/.zshrc" ] || {
        echo "$HOME/.zshrc is missing"
        return 1
    }
    [ -r "$HOME/.zsh/config/00_LOADER.zsh" ] || {
        echo "$HOME/.zsh/config/00_LOADER.zsh is missing"
        return 1
    }

    # Output goes to files, not a pipe, so a stuck child process cannot block us after the timeout.
    command -v timeout >/dev/null 2>&1 && timeout_cmd="timeout --foreground -k 1 ${DOTFILES_ZSH_CHECK_TIMEOUT:-60}"
    tmp=$(mktemp -d 2>/dev/null) || return 0
    out="$tmp/out" err="$tmp/err"
    # An interactive zsh without a terminal prints benign errors (zle, monitor, gitstatus), so a
    # real terminal on stdin is kept; only without one stdin comes from /dev/null.
    local stdin_src=/dev/null
    [ -t 0 ] && stdin_src=/dev/tty
    # shellcheck disable=SC2016  # expanded by the inner zsh
    # DOTFILES_ZSH_CHECK=1 makes the deferred plugins load during the start (see 02_plugins.zsh).
    DOTFILES_ZSH_CHECK=1 $timeout_cmd "$zsh_bin" -l -i -c 'print -r -- "DOTFILES_ZSH_LOADED=${DOTFILES_ZSH_LOADED:-0} DOTFILES_ZSH_DEFERRED_LOADED=${DOTFILES_ZSH_DEFERRED_LOADED:-0}"' >"$out" 2>"$err" <"$stdin_src"
    rc=$?
    if [ "$rc" -eq 124 ] || [ "$rc" -eq 137 ]; then
        reason="zsh startup timed out"
    elif [ "$rc" -ne 0 ]; then
        reason="zsh failed to start (exit $rc)"
    elif [ -s "$err" ]; then
        reason="zsh printed errors on startup: $(head -n 1 "$err")"
    elif ! grep -q 'DOTFILES_ZSH_LOADED=1' "$out"; then
        reason="zsh config did not load completely"
    elif ! grep -q 'DOTFILES_ZSH_DEFERRED_LOADED=1' "$out"; then
        reason="zsh plugins did not load completely"
    fi
    rm -rf "$tmp"
    [ -z "$reason" ] && return 0
    echo "$reason"
    return 1
}

dotfiles_zsh_handoff_ok() {
    local zsh_bin state key value
    local c_status="" c_zsh="" c_marker="" c_reason="" marker=0 reason
    zsh_bin=$(command -v zsh 2>/dev/null) || {
        _zhc_report "zsh is not installed"
        return 1
    }
    # First start on a fresh machine: zsh clones antidote and the plugins itself, which is
    # slow and must not be mistaken for a failure. Hand over and check next time.
    # Old zinit data alone does not count: the host is fresh for antidote.
    [ -d "${XDG_DATA_HOME:-$HOME/.local/share}/antidote/mattmc3/antidote" ] || return 0
    [ -s "${XDG_CACHE_HOME:-$HOME/.cache}/zsh/plugins.zsh" ] || return 0
    state=$(_zhc_state_file)
    # A pending update (state file key pending=1) changes the check cache key.
    local ustate="${DOTFILES_UPDATE_STATE:-$HOME/.dotfiles-update-state}" ukey uvalue
    if [ -r "$ustate" ]; then
        while IFS='=' read -r ukey uvalue || [ -n "$ukey" ]; do
            [ "$ukey" = pending ] && [ "$uvalue" = 1 ] && marker=1
        done <"$ustate"
    fi

    if [ -f "$state" ]; then
        while IFS='=' read -r key value; do
            case "$key" in
                status) c_status="$value" ;;
                zsh) c_zsh="$value" ;;
                marker) c_marker="$value" ;;
                reason) c_reason="$value" ;;
            esac
        done <"$state"
        if [ "$c_zsh" = "$zsh_bin" ] && [ "$c_marker" = "$marker" ] && ! _zhc_stale "$state" "$zsh_bin"; then
            [ "$c_status" = ok ] && return 0
            _zhc_report "$c_reason"
            return 1
        fi
    fi

    if reason=$(_zhc_run_checks "$zsh_bin"); then
        c_status=ok
        reason=""
    else
        c_status=fail
        # A timeout is inconclusive (slow first start after a new plugin, or a hang): stay in
        # bash this time, cache nothing, so the next start checks again.
        if [ "$reason" = "zsh startup timed out" ]; then
            _zhc_report "$reason"
            return 1
        fi
    fi
    mkdir -p "${state%/*}" 2>/dev/null &&
        printf 'status=%s\nzsh=%s\nmarker=%s\nreason=%s\n' "$c_status" "$zsh_bin" "$marker" "$reason" >"$state" 2>/dev/null
    [ "$c_status" = ok ] && return 0
    _zhc_report "$reason"
    return 1
}

zsh-recheck() {
    rm -f "$(_zhc_state_file)"
    if dotfiles_zsh_handoff_ok; then
        echo "zsh handoff check passed"
    fi
}
