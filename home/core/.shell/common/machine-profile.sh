# shellcheck shell=sh
# Context and device of this host, and is it a work setup?
# Sourced by the Bash and zsh startup loaders; POSIX sh so both can use it.
# Exports MACHINE_CONTEXT (private, work; unset without context), MACHINE_DEVICE
# (desktop, server, container) and WORK_SETUP ("true" or unset).
# Same order as the machine CLI: in Docker the device is "container" without context
# unless MACHINE_DEVICE_OVERRIDE / MACHINE_CONTEXT_OVERRIDE name others; otherwise the
# applied host config wins.

_machine_file="${MACHINE_APPLIED_HOST_FILE:-${MACHINE_STATE_DIR:-$HOME/.local/share/machine}/applied-host.yml}"
# Before `machine` took over the former local file.
[ -f "$_machine_file" ] || _machine_file="$HOME/.config/machine/profile.yml"
_machine_user="${USER:-$(id -un)}"
_machine_context=""
_machine_device=""
if [ -f /.dockerenv ] || [ "${MACHINE_IN_DOCKER:-}" = "1" ]; then
    case "${MACHINE_DEVICE_OVERRIDE:-}" in
        desktop | server) _machine_device="$MACHINE_DEVICE_OVERRIDE" ;;
        *) _machine_device="container" ;;
    esac
    case "${MACHINE_CONTEXT_OVERRIDE:-}" in
        private | work) _machine_context="$MACHINE_CONTEXT_OVERRIDE" ;;
    esac
else
    if [ -f "$_machine_file" ]; then
        _machine_context="$(awk '$1=="context:" {print $2; exit}' "$_machine_file")"
        _machine_device="$(awk '$1=="device:" {print $2; exit}' "$_machine_file")"
        if [ -z "$_machine_device" ]; then
            case "$(awk '$1=="profile:" {print $2; exit}' "$_machine_file")" in
                work-machine) _machine_context="work" _machine_device="desktop" ;;
                home-laptop) _machine_context="private" _machine_device="desktop" ;;
                home-server | rpi | rpi-zero) _machine_context="private" _machine_device="server" ;;
                container) _machine_device="container" ;;
            esac
        fi
    fi
    if [ -z "$_machine_context" ] && [ "$_machine_device" != "container" ]; then
        if printf '%s\n' "$_machine_user" | grep -Eq '^[a-zA-Z]{3}[0-9]{1,2}[a-zA-Z]{2,3}$'; then
            _machine_context="work"
        else
            _machine_context="private"
        fi
    fi
fi
export MACHINE_DEVICE="${_machine_device:-desktop}"
if [ -n "$_machine_context" ]; then
    export MACHINE_CONTEXT="$_machine_context"
else
    unset MACHINE_CONTEXT
fi

# Work hosts, plus company user IDs (e.g. abc1de) outside containers.
if [ "$_machine_context" = "work" ] ||
    { [ "$MACHINE_DEVICE" != "container" ] &&
        printf '%s\n' "$_machine_user" | grep -Eq '^[a-zA-Z]{3}[0-9]{1,2}[a-zA-Z]{2,3}$'; }; then
    export WORK_SETUP="true"
else
    unset WORK_SETUP
fi
unset _machine_file _machine_user _machine_context _machine_device
