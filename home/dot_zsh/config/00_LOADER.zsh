DEBUG=false

log() {
    if [ "$DEBUG" = "true" ]; then
        echo "$1"
    fi
}

# Ensure ZSH variable is set
ZSH=${ZSH:-$HOME/.zsh}

_machine_profile=""
if [[ -f "${HOME}/.config/machine/profile.yml" ]]; then
    _machine_profile="$(awk '$1=="profile:" {print $2; exit}' "${HOME}/.config/machine/profile.yml")"
fi

if [[ "${_machine_profile}" == "work-laptop" ]] || [[ $(whoami) =~ (^[a-zA-Z]{3}[0-9]{1,2}[a-zA-Z]{2,3}$) ]]; then
    export WORK_SETUP="true"
    export MACHINE_PROFILE="${_machine_profile:-work-laptop}"
else
    unset WORK_SETUP
    export MACHINE_PROFILE="${_machine_profile:-home-laptop}"
fi
unset _machine_profile

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
