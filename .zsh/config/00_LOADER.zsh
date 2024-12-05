DEBUG=false

log() {
    if [ "$DEBUG" = "true" ]; then
        echo $1
    fi
}

if [[ $(whoami) =~ (^[a-zA-Z]{3}[0-9]{1,2}[a-zA-Z]{2,3}$) ]]; then
    export WORK_SETUP="true"
    echo "Loading work config as username '$(whoami)' is matching pattern"
else
    echo "Not loading work config as username '$(whoami)' is not matching pattern"

fi

for __file__ in $ZSH/config/*.zsh; do
    log "Running for  $__file__"
    if [ "$__file__" = "$0" ]; then # THIS file
        log "Skipping '$__file__'"
        continue
    fi
    log "Sourcing '$__file__'"
    source $__file__
done
unset __file__
