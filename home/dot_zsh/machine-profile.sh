# shellcheck shell=sh
# Which machine profile is this shell on, and is it a work setup?
# Sourced by ~/.zsh/config/00_LOADER.zsh and ~/.bashrc; POSIX sh so both can use it.
# Exports MACHINE_PROFILE and WORK_SETUP (set to "true" or unset).
# Same order as the machine CLI: in Docker the profile is "container" unless
# MACHINE_PROFILE_OVERRIDE names another one; otherwise the saved profile wins.

_machine_profile=""
if [ -f /.dockerenv ] || [ "${MACHINE_IN_DOCKER:-}" = "1" ]; then
    _machine_profile="${MACHINE_PROFILE_OVERRIDE:-container}"
elif [ -f "$HOME/.config/machine/profile.yml" ]; then
    _machine_profile="$(awk '$1=="profile:" {print $2; exit}' "$HOME/.config/machine/profile.yml")"
fi

# Work laptops, plus company user IDs (e.g. abc1de) outside containers.
if [ "$_machine_profile" = "work-machine" ] ||
    { [ "$_machine_profile" != "container" ] &&
        printf '%s\n' "${USER:-$(id -un)}" | grep -Eq '^[a-zA-Z]{3}[0-9]{1,2}[a-zA-Z]{2,3}$'; }; then
    export WORK_SETUP="true"
    export MACHINE_PROFILE="${_machine_profile:-work-machine}"
else
    unset WORK_SETUP
    export MACHINE_PROFILE="${_machine_profile:-home-laptop}"
fi
unset _machine_profile
