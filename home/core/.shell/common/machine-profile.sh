# shellcheck shell=sh
# Context and device of this host, and is it a work setup?
# Sourced by the Bash and zsh startup loaders; POSIX sh so both can use it.
# Exports MACHINE_CONTEXT (private, work; unset without context), MACHINE_DEVICE
# (desktop, server, container) and WORK_SETUP ("true" or unset).
# Same order as the machine CLI: in Docker the device is "container" without context
# unless MACHINE_DEVICE_OVERRIDE / MACHINE_CONTEXT_OVERRIDE name others; otherwise the
# applied host config wins.

# The helpers work on the _machine_* variables; all are removed again at the end.

_machine_in_docker() {
    [ -f /.dockerenv ] || [ "${MACHINE_IN_DOCKER:-}" = "1" ]
}

_machine_from_overrides() {
    case "${MACHINE_DEVICE_OVERRIDE:-}" in
        desktop | server) _machine_device="$MACHINE_DEVICE_OVERRIDE" ;;
        *) _machine_device="container" ;;
    esac
    case "${MACHINE_CONTEXT_OVERRIDE:-}" in
        private | work) _machine_context="$MACHINE_CONTEXT_OVERRIDE" ;;
    esac
}

# Old profile names, from files without a device key.
_machine_from_profile() {
    case "$(awk '$1=="profile:" {print $2; exit}' "$_machine_file")" in
        work-machine) _machine_context="work" _machine_device="desktop" ;;
        home-laptop) _machine_context="private" _machine_device="desktop" ;;
        home-server | rpi | rpi-zero) _machine_context="private" _machine_device="server" ;;
        container) _machine_device="container" ;;
    esac
}

_machine_from_file() {
    [ -f "$_machine_file" ] || return 0
    _machine_context="$(awk '$1=="context:" {print $2; exit}' "$_machine_file")"
    _machine_device="$(awk '$1=="device:" {print $2; exit}' "$_machine_file")"
    [ -n "$_machine_device" ] || _machine_from_profile
}

# Company user IDs, e.g. abc1de.
_machine_company_user() {
    printf '%s\n' "$_machine_user" | grep -Eq '^[a-zA-Z]{3}[0-9]{1,2}[a-zA-Z]{2,3}$'
}

# Without a saved context (and outside containers) the user ID decides.
_machine_default_context() {
    [ -z "$_machine_context" ] && [ "$_machine_device" != "container" ] || return 0
    if _machine_company_user; then
        _machine_context="work"
    else
        _machine_context="private"
    fi
}

# Work hosts, plus company user IDs (e.g. abc1de) outside containers.
_machine_work_setup() {
    [ "$_machine_context" = "work" ] && return 0
    [ "$MACHINE_DEVICE" != "container" ] && _machine_company_user
}

_machine_file="${MACHINE_APPLIED_HOST_FILE:-${MACHINE_STATE_DIR:-$HOME/.local/share/machine}/applied-host.yml}"
# Before `machine` took over the former local file.
[ -f "$_machine_file" ] || _machine_file="$HOME/.config/machine/profile.yml"
_machine_user="${USER:-$(id -un)}"
_machine_context=""
_machine_device=""
if _machine_in_docker; then
    _machine_from_overrides
else
    _machine_from_file
    _machine_default_context
fi
export MACHINE_DEVICE="${_machine_device:-desktop}"
if [ -n "$_machine_context" ]; then
    export MACHINE_CONTEXT="$_machine_context"
else
    unset MACHINE_CONTEXT
fi

if _machine_work_setup; then
    export WORK_SETUP="true"
else
    unset WORK_SETUP
fi
unset _machine_file _machine_user _machine_context _machine_device
unset -f _machine_in_docker _machine_from_overrides _machine_from_profile _machine_from_file \
    _machine_company_user _machine_default_context _machine_work_setup
