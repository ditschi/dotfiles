# shellcheck shell=bash
# Update state indicator, sourced by ~/.bashrc and by zsh (bash and zsh compatible).
# `dotfiles-update-check-job` and `machine update` write the state file (key=value lines):
#   state=none|available|updated|attention   reason=<text>   revision=<applied HEAD>
# Reading it uses only builtins (no fork), so it is cheap enough to run before every prompt.
# A shell remembers the revision it started with; a different revision means "reload".

# Exported so that the Starship env_var module can read the segment.
export DOTFILES_UPDATE_SEGMENT="" DOTFILES_UPDATE_SEGMENT_KIND=""
DOTFILES_UPDATE_STATE_FILE="${DOTFILES_UPDATE_STATE:-$HOME/.dotfiles-update-state}"

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

# Sets DOTFILES_UPDATE_SEGMENT (empty when nothing is to be shown) and DOTFILES_UPDATE_SEGMENT_KIND.
dotfiles_update_prompt() {
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
        echo "Dotfiles update needs attention: ${_dfu_reason:-see machine status} (run: machine status)"
    fi
}

reload() {
    if [ -n "${ZSH_VERSION:-}" ]; then
        exec zsh -l
    else
        exec bash -l
    fi
}
