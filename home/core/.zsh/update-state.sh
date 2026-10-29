# shellcheck shell=bash
# Update state indicator, sourced by ~/.bashrc and by zsh (bash and zsh compatible).
# `dotfiles-update-check-job` and `machine update` write the state file (key=value lines):
#   state=none|available|updated|attention   reason=<text>   revision=<applied HEAD>
# Reading it uses only builtins (no fork), so it is cheap enough to run before every prompt.
# A shell remembers the revision it started with; a different revision means "reload".

# Exported so that the Starship env_var module can read the segment.
export DOTFILES_UPDATE_SEGMENT="" DOTFILES_UPDATE_SEGMENT_KIND="" DOTFILES_DISK_SEGMENT=""
DOTFILES_UPDATE_STATE_FILE="${DOTFILES_UPDATE_STATE:-$HOME/.dotfiles-update-state}"
# Low filesystems, recorded by `machine` and its 15-minute timer (segment=<text>).
DOTFILES_DISK_STATE_FILE="${MACHINE_DISK_STATE:-${MACHINE_STATE_DIR:-$HOME/.local/share/machine}/disk-state}"

_dfu_read() {
    local key value
    _dfu_state="" _dfu_reason="" _dfu_rev=""
    [ -r "$DOTFILES_UPDATE_STATE_FILE" ] || return 0
    while IFS='=' read -r key value || [ -n "$key" ]; do
        case "$key" in
            state) _dfu_state="$value" ;;
            reason) _dfu_reason="$value" ;;
            revision) _dfu_rev="$value" ;;
        esac
    done <"$DOTFILES_UPDATE_STATE_FILE"
}

_dfu_read_disk() {
    local key value
    DOTFILES_DISK_SEGMENT=""
    [ -r "$DOTFILES_DISK_STATE_FILE" ] || return 0
    while IFS='=' read -r key value || [ -n "$key" ]; do
        [ "$key" = segment ] && DOTFILES_DISK_SEGMENT="$value"
    done <"$DOTFILES_DISK_STATE_FILE"
}

# Sets DOTFILES_UPDATE_SEGMENT (empty when nothing is to be shown), DOTFILES_UPDATE_SEGMENT_KIND
# and DOTFILES_DISK_SEGMENT (low filesystems; separate from the update state).
dotfiles_update_prompt() {
    _dfu_read_disk
    _dfu_read
    DOTFILES_UPDATE_SEGMENT="" DOTFILES_UPDATE_SEGMENT_KIND=""
    if [ "$_dfu_state" = attention ]; then
        DOTFILES_UPDATE_SEGMENT="⚠ dotfiles: check (machine status)" DOTFILES_UPDATE_SEGMENT_KIND=attention
    elif [ "$_dfu_state" = available ]; then
        DOTFILES_UPDATE_SEGMENT="⬆ dotfiles update" DOTFILES_UPDATE_SEGMENT_KIND=available
    elif [ "$_dfu_rev" != "$_DFU_LOADED_REV" ]; then
        DOTFILES_UPDATE_SEGMENT="↻ reload shell" DOTFILES_UPDATE_SEGMENT_KIND=reload
    fi
}

# Shell start: remember the loaded revision; print a line only for needs-attention.
dotfiles_update_startup() {
    _dfu_read
    _DFU_LOADED_REV="$_dfu_rev"
    if [ "$_dfu_state" = attention ]; then
        echo "Dotfiles update needs attention: ${_dfu_reason:-see machine attention} (run: machine)"
    fi
}

reload() {
    if [ -n "${ZSH_VERSION:-}" ]; then
        exec zsh -l
    else
        exec bash -l
    fi
}

# A child process cannot reload its parent shell: after a successful `machine update`
# in an interactive shell, replace the shell so the result is live. Failures leave it alone.
machine() {
    command machine "$@"
    local rc=$?
    if [ "$rc" -eq 0 ] && [ "${1:-}" = update ] && [ -t 0 ] && [ -t 1 ]; then
        local arg
        for arg in "$@"; do
            case "$arg" in
                --check | --auto | --json | -h | --help) return 0 ;;
            esac
        done
        reload
    fi
    return "$rc"
}
