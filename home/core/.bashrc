# ~/.bashrc: executed by bash(1) for non-login shells.
# see /usr/share/doc/bash/examples/startup-files (in the package bash-doc)
# for examples
# shellcheck shell=bash

# If not running interactively, don't do anything
case $- in
    *i*) ;;
    *) return ;;
esac

. "$HOME/.shell/bash/handoff.bash"
. "$HOME/.shell/bash/init.bash"
[[ ! -f ~/.bashrc-local ]] || source ~/.bashrc-local
