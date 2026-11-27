#!/bin/sh
# Reverse SSH tunnel to the jump host for a device without dotfiles (spec ssh-tunnel).
# POSIX sh (BusyBox) and OpenSSH 7.4 options only; see README.md next to this file.
#
#   device-tunnel.sh start    start the tunnel loop unless it already runs (boot task
#                             and watchdog both call this)
#   device-tunnel.sh stop     end the loop and its ssh
#   device-tunnel.sh status   exit 0 when the loop runs
#   device-tunnel.sh run      the loop in the foreground (used by start)
#
# Settings come from a file on the device (TUNNEL_CONF, default
# /root/.ssh/tunnel.conf), so no address is in the repository:
#   JUMP_HOST=<address of the jump host>   PORT=<port of the jump route>
#   KEY=/root/.ssh/tunnel_oracle           KNOWN_HOSTS=/root/.ssh/tunnel_known_hosts
# Optional: JUMP_PORT=22  JUMP_USER=tunnel  HOST_KEY_ALIAS=oracle  LOCAL_PORT=22
#           PIDFILE=/var/run/ssh-tunnel.pid  RETRY=30  SSH=ssh
# TUNNEL_SHELL (environment, default /bin/sh) runs the loop.

CONF=${TUNNEL_CONF:-/root/.ssh/tunnel.conf}

log() {
    if command -v logger >/dev/null 2>&1; then
        logger -t ssh-tunnel "$*"
    else
        echo "ssh-tunnel: $*" >&2
    fi
}

load_config() {
    if [ ! -r "$CONF" ]; then
        log "missing $CONF"
        exit 78
    fi
    # shellcheck disable=SC1090
    . "$CONF"
    JUMP_HOST=${JUMP_HOST:-} PORT=${PORT:-} KEY=${KEY:-} KNOWN_HOSTS=${KNOWN_HOSTS:-}
    for name in JUMP_HOST PORT KEY KNOWN_HOSTS; do
        eval "value=\${$name:-}"
        if [ -z "$value" ]; then
            log "$CONF: $name is not set"
            exit 78
        fi
    done
    JUMP_PORT=${JUMP_PORT:-22}
    JUMP_USER=${JUMP_USER:-tunnel}
    HOST_KEY_ALIAS=${HOST_KEY_ALIAS:-oracle}
    LOCAL_PORT=${LOCAL_PORT:-22}
    PIDFILE=${PIDFILE:-/var/run/ssh-tunnel.pid}
    RETRY=${RETRY:-30}
    SSH=${SSH:-ssh}
}

running() {
    [ -r "$PIDFILE" ] || return 1
    pid=$(cat "$PIDFILE" 2>/dev/null)
    [ -n "$pid" ] && [ "$pid" != "$$" ] && kill -0 "$pid" 2>/dev/null || return 1
    # A reused PID belongs to another program: only this script's loop counts.
    tr '\0' ' ' <"/proc/$pid/cmdline" 2>/dev/null | grep -q "$(basename "$0") run"
}

# Ends a child of the loop. A TERM in the first instant after the fork is lost: the
# child still runs the shell's signal handler. So it is sent until the child is gone.
end_child() {
    n=0
    while [ "$n" -lt 1000 ] && read -r stat <"/proc/$1/stat" 2>/dev/null; do
        stat=${stat##*) }
        [ "${stat%% *}" = Z ] && break
        kill "$1" 2>/dev/null
        n=$((n + 1))
    done
}

end_loop() {
    # The trap can run between the fork and child=$!; $! is then the new child.
    if [ "$child" = starting ] && [ "$!" != "$last" ]; then
        child=$!
    fi
    case $child in
        '' | starting) ;;
        *) end_child "$child" ;;
    esac
    rm -f "$PIDFILE"
    exit 0
}

# Runs "$@" in the background as $child, so the trap does not wait for it.
run_child() {
    last=$! child=starting
    "$@" &
    child=$!
    wait "$child"
    status=$?
    child=
}

run_loop() {
    child=
    trap end_loop TERM INT
    while :; do
        # -F /dev/null: none of the device's own ssh settings (no connection sharing).
        run_child "$SSH" -F /dev/null -N \
            -o ControlMaster=no -o ControlPath=none \
            -o ExitOnForwardFailure=yes \
            -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
            -o BatchMode=yes -o ConnectTimeout=20 \
            -o IdentitiesOnly=yes -i "$KEY" \
            -o StrictHostKeyChecking=yes -o UserKnownHostsFile="$KNOWN_HOSTS" \
            -o HostKeyAlias="$HOST_KEY_ALIAS" \
            -p "$JUMP_PORT" \
            -R "127.0.0.1:$PORT:localhost:$LOCAL_PORT" \
            "$JUMP_USER@$JUMP_HOST"
        log "ssh ended with status $status; next attempt in ${RETRY}s"
        run_child sleep "$RETRY"
    done
}

start_tunnel() {
    # Boot task and watchdog may start at the same moment: one wins the lock.
    lock="$PIDFILE.lock"
    if ! mkdir "$lock" 2>/dev/null; then
        # A lock older than a minute was left by a killed start.
        if [ -n "$(find "$lock" -maxdepth 0 -mmin +1 2>/dev/null)" ]; then
            rmdir "$lock" 2>/dev/null
        fi
        return 0
    fi
    if running; then
        rmdir "$lock"
        return 0
    fi
    # The loop removes the lock once it runs, so a start in between does not
    # take the not yet recognisable PID for a stale one and start a second loop.
    nohup "${TUNNEL_SHELL:-/bin/sh}" "$0" run >/dev/null 2>&1 &
    echo $! >"$PIDFILE"
    log "started (127.0.0.1:$PORT on $JUMP_HOST -> localhost:$LOCAL_PORT)"
}

stop_tunnel() {
    # A loop that start has just launched is recognisable once it removed the lock.
    waited=0
    while [ -d "$PIDFILE.lock" ] && [ "$waited" -lt 10 ]; do
        sleep 1
        waited=$((waited + 1))
    done
    if ! running; then
        rm -f "$PIDFILE"
        return 0
    fi
    # The loop removes the PID file itself; removing it here too can fail
    # (BusyBox rm -f) when both remove it at the same moment.
    kill "$(cat "$PIDFILE")"
    log "stopped"
}

show_status() {
    if ! running; then
        echo "not running"
        return 1
    fi
    echo "running (pid $(cat "$PIDFILE"))"
}

loop_process() {
    # Only now is this PID recognisable as the loop (during its exec chain
    # /proc/PID/cmdline is the start script's or empty), so start's lock ends here.
    echo $$ >"$PIDFILE"
    rmdir "$PIDFILE.lock" 2>/dev/null
    run_loop
}

case "${1:-}" in
    start) load_config && start_tunnel ;;
    stop) load_config && stop_tunnel ;;
    status) load_config && show_status ;;
    run) load_config && loop_process ;;
    *)
        echo "usage: $0 start|stop|status|run" >&2
        exit 2
        ;;
esac
