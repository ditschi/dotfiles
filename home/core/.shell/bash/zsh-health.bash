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
        "$HOME/.preferred-shell" "$HOME/.shell/zsh/plugins.txt" \
        "$HOME"/.shell/common/*.sh "$HOME"/.shell/zsh/*.zsh \
        "$HOME"/.shell/zsh/plugins.txt "$HOME"/.shell/work/common/*.sh \
        "$HOME"/.shell/work/zsh/*.zsh "$HOME/.shell" "$HOME/.shell/common" \
        "$HOME/.shell/zsh" "$HOME/.shell/work" "$HOME/.shell/work/common" \
        "$HOME/.shell/work/zsh"; do # directories also catch removed or renamed files
        [ "$f" -nt "$state" ] && return 0
    done
    return 1
}

# Prints the failure reason and returns 1 when a file zsh needs is missing.
_zhc_preflight() {
    [ -x "$1" ] || {
        echo "zsh is not executable"
        return 1
    }
    [ -r "$HOME/.zshrc" ] || {
        echo "$HOME/.zshrc is missing"
        return 1
    }
    [ -r "$HOME/.shell/zsh/init.zsh" ] || {
        echo "$HOME/.shell/zsh/init.zsh is missing"
        return 1
    }
}

# Sets the caller's `trial_term` to the TERM for the trial start.
_zhc_trial_term() {
    # Without a terminal (background update, ssh without -t) TERM is unset or dumb; a real login
    # has one, and tput or Starship in the startup files would otherwise report errors.
    trial_term="${TERM:-}"
    if [ ! -t 0 ] && _zhc_term_missing "$trial_term"; then
        trial_term=xterm-256color
    fi
}

_zhc_term_missing() {
    [ -z "$1" ] || [ "$1" = dumb ]
}

# Starts the trial zsh with output to $2 and $3 and returns its exit code. Sets the caller's
# `interrupted` on Ctrl-C.
_zhc_trial() {
    local zsh_bin="$1" out="$2" err="$3" timeout_cmd="" setsid_cmd="" trial_term trial old_int rc
    # Output goes to files, not a pipe, so a stuck child process cannot block us after the timeout.
    # Without --foreground, timeout signals the trial's whole process group, not only zsh.
    command -v timeout >/dev/null 2>&1 && timeout_cmd="timeout -k 1 ${DOTFILES_ZSH_CHECK_TIMEOUT:-60}"
    # Own session without the terminal: nothing the trial starts can read the user's keystrokes.
    command -v setsid >/dev/null 2>&1 && setsid_cmd="setsid -w"
    _zhc_trial_term
    # shellcheck disable=SC2016,SC2086  # expanded by the inner zsh; the command prefixes split on purpose
    # DOTFILES_ZSH_CHECK=1 makes the deferred plugins load during the start (see 02_plugins.zsh).
    DOTFILES_ZSH_CHECK=1 TERM="$trial_term" $setsid_cmd $timeout_cmd "$zsh_bin" -l -i -c 'print -r -- "DOTFILES_ZSH_LOADED=${DOTFILES_ZSH_LOADED:-0} DOTFILES_ZSH_DEFERRED_LOADED=${DOTFILES_ZSH_DEFERRED_LOADED:-0}"' >"$out" 2>"$err" </dev/null &
    trial=$!
    old_int=$(trap -p INT)
    trap 'interrupted=1' INT
    wait "$trial"
    rc=$?
    if [ -n "$interrupted" ]; then
        kill -KILL -- "-$trial" 2>/dev/null || kill -KILL "$trial" 2>/dev/null
        wait "$trial" 2>/dev/null
    fi
    eval "${old_int:-trap - INT}"
    return "$rc"
}

# Sets the caller's `reason` from the trial's result (exit code $1, output $2, errors $3).
_zhc_trial_reason() {
    local rc="$1" out="$2" err="$3"
    if [ -n "$interrupted" ]; then
        reason="zsh check interrupted"
    elif [ "$rc" -eq 124 ] || [ "$rc" -eq 137 ]; then
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
}

# Prints the failure reason and returns 1, or returns 0 when zsh is healthy.
_zhc_run_checks() {
    local zsh_bin="$1" tmp rc=0 reason="" interrupted=""
    _zhc_preflight "$zsh_bin" || return 1
    tmp=$(mktemp -d 2>/dev/null) || return 0
    _zhc_trial "$zsh_bin" "$tmp/out" "$tmp/err" || rc=$?
    _zhc_trial_reason "$rc" "$tmp/out" "$tmp/err"
    rm -rf "$tmp"
    [ -z "$reason" ] && return 0
    echo "$reason"
    return 1
}

# Sets the caller's `marker` to 1 when an update is pending (update state file key pending=1).
_zhc_pending_marker() {
    local ustate="${DOTFILES_UPDATE_STATE:-$HOME/.dotfiles-update-state}" ukey uvalue
    [ -r "$ustate" ] || return 0
    while IFS='=' read -r ukey uvalue || [ -n "$ukey" ]; do
        [ "$ukey" = pending ] && [ "$uvalue" = 1 ] && marker=1
    done <"$ustate"
    return 0
}

# Reads the cached result from state file $1 into the caller's c_* variables.
_zhc_read_cache() {
    local key value
    while IFS='=' read -r key value; do
        case "$key" in
            status) c_status="$value" ;;
            zsh) c_zsh="$value" ;;
            marker) c_marker="$value" ;;
            reason) c_reason="$value" ;;
        esac
    done <"$1"
}

# True if state file $1 holds a result for zsh $2 and marker $3 that is still current.
_zhc_cache_valid() {
    [ -f "$1" ] || return 1
    _zhc_read_cache "$1"
    [ "$c_zsh" = "$2" ] && [ "$c_marker" = "$3" ] && ! _zhc_stale "$1" "$2"
}

# Returns 0 for status ok, otherwise reports reason $2 and returns 1.
_zhc_result() {
    [ "$1" = ok ] && return 0
    _zhc_report "$2"
    return 1
}

# A timeout or Ctrl-C is inconclusive (slow first start after a new plugin, or a hang).
_zhc_inconclusive() {
    case "$1" in
        "zsh startup timed out" | "zsh check interrupted") return 0 ;;
    esac
    return 1
}

# Runs the checks for zsh $1 and sets the caller's c_status (ok or fail) and reason.
_zhc_check_now() {
    # Interactive bash would skip the rest of ~/.bashrc on Ctrl-C; the check handles it itself.
    local old_int
    old_int=$(trap -p INT)
    trap ':' INT
    c_status=ok
    reason=$(_zhc_run_checks "$1") || c_status=fail
    eval "${old_int:-trap - INT}"
    [ "$c_status" = ok ] && reason=""
    return 0
}

dotfiles_zsh_handoff_ok() {
    local zsh_bin state
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
    _zhc_pending_marker

    if _zhc_cache_valid "$state" "$zsh_bin" "$marker"; then
        _zhc_result "$c_status" "$c_reason"
        return
    fi

    _zhc_check_now "$zsh_bin"
    # Inconclusive: stay in bash this time, cache nothing, so the next start checks again.
    if [ "$c_status" = fail ] && _zhc_inconclusive "$reason"; then
        _zhc_report "$reason"
        return 1
    fi
    mkdir -p "${state%/*}" 2>/dev/null &&
        printf 'status=%s\nzsh=%s\nmarker=%s\nreason=%s\n' "$c_status" "$zsh_bin" "$marker" "$reason" >"$state" 2>/dev/null
    _zhc_result "$c_status" "$reason"
}

zsh-recheck() {
    rm -f "$(_zhc_state_file)"
    if dotfiles_zsh_handoff_ok; then
        echo "zsh handoff check passed"
    fi
}
