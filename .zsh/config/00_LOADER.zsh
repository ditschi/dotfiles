

DEBUG=false

log() {
    if [ "$DEBUG" = true ]
    then
        echo $1
    fi
}


for __file__ in $ZSH/config/*.zsh; do
    log "Running for  $__file__"
    if [ "$__file__" = "$0" ] # THIS file
    then
        log "Skipping"
        continue
    fi
    log "Sourcing '$__file__'"
    source $__file__
done
unset __file__
