DEBUG=false

log() {
    if [ "$DEBUG" = "true" ]; then
        echo "$1"
    fi
}

# Ensure ZSH variable is set
ZSH=${ZSH:-$HOME/.zsh}

if [[ $(whoami) =~ (^[a-zA-Z]{3}[0-9]{1,2}[a-zA-Z]{2,3}$) ]]; then
    export WORK_SETUP="true"
else
    unset WORK_SETUP
fi

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
