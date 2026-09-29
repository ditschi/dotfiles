DEBUG=false

log() {
    if [ "$DEBUG" = "true" ]; then
        echo "$1"
    fi
}

# Ensure ZSH variable is set
ZSH=${ZSH:-$HOME/.zsh}

# MACHINE_PROFILE / WORK_SETUP, shared with bash
source "$ZSH/machine-profile.sh"

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
