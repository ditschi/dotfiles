# shellcheck shell=sh
# Which machine profile is this shell on, and is it a work setup?
# Sourced by ~/.zsh/config/00_LOADER.zsh and ~/.bashrc; POSIX sh so both can use it.
# Exports MACHINE_PROFILE and WORK_SETUP (set to "true" or unset).

_machine_profile=""
if [ -f "$HOME/.config/machine/profile.yml" ]; then
    _machine_profile="$(awk '$1=="profile:" {print $2; exit}' "$HOME/.config/machine/profile.yml")"
fi

# Work laptops, plus dev containers running as a Bosch user id (e.g. abc1de).
if [ "$_machine_profile" = "work-laptop" ] ||
    printf '%s\n' "${USER:-$(id -un)}" | grep -Eq '^[a-zA-Z]{3}[0-9]{1,2}[a-zA-Z]{2,3}$'; then
    export WORK_SETUP="true"
    export MACHINE_PROFILE="${_machine_profile:-work-laptop}"
else
    unset WORK_SETUP
    export MACHINE_PROFILE="${_machine_profile:-home-laptop}"
fi
unset _machine_profile
