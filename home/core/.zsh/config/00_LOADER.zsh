DEBUG=false

log() {
    if [ "$DEBUG" = "true" ]; then
        echo "$1"
    fi
}

# Ensure ZSH variable is set
ZSH=${ZSH:-$HOME/.zsh}

# MACHINE_CONTEXT / MACHINE_DEVICE / WORK_SETUP, shared with bash
source "$ZSH/machine-profile.sh"

# Update state indicator (prompt segment, see 03_theme.zsh)
source "$ZSH/update-state.sh"

# dotfiles_cache_eval: cached tool init output (fzf, zoxide, starship), shared with bash
source "$ZSH/cache-eval.sh"

for __file__ in "$ZSH"/config/*.zsh; do
    log "Running for $__file__"
    if [[ "$__file__" == "$ZSH/config/00_LOADER.zsh" ]]; then
        log "Skipping '$__file__'"
        continue
    fi
    log "Sourcing '$__file__'"
    source "$__file__"
done
unset __file__

# Health check mode only (DOTFILES_ZSH_CHECK=1): run the queued deferred plugin steps now.
(( ! $+functions[dotfiles_run_deferred] )) || dotfiles_run_deferred

# Lets the bash handoff check (zsh-handoff-check.sh) see that the config loaded completely.
typeset -g DOTFILES_ZSH_LOADED=1
