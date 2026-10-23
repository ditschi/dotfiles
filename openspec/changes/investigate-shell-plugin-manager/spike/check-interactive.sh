#!/usr/bin/env bash
# Interactive feature check in the container, driven by tmux key presses.
#   check-interactive.sh <config>...   prints PASS/FAIL per feature (results/<config>.interactive.txt)
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)

check() {
    local cfg=$1
    docker run --rm -i -v "$here/configs:/spike/configs:ro" shell-spike:local bash -s "$cfg" <<'EOF'
cfg=$1
cp -r /spike/configs/_common/skel/. ~/ && cp -r /spike/configs/$cfg/skel/. ~/
cd ~ || exit 1
export TERM=xterm-256color
tmux new-session -d -s t -x 160 -y 40 "zsh -li"
wait_for() { for _ in $(seq 1 300); do tmux capture-pane -pt t | grep -q -- "$1" && return 0; sleep 0.2; done; return 1; }
run() { tmux send-keys -t t "$@"; sleep 0.6; }
screen() { tmux capture-pane -pt t; }
result() { if [ "$2" = 0 ]; then echo "PASS $1"; else echo "FAIL $1"; screen | grep -v '^\s*$' | tail -5 | sed 's/^/    /'; fi; }
clear_line() { run C-c; run 'clear' Enter; }

# wait until fully loaded (plugins installed on first start); a blocking loop would stall zsh-defer
loaded=1
for _ in $(seq 1 120); do
  sleep 1; run 'echo L=${SPIKE_LOADED:-0}' Enter
  screen | grep -q '^L=1' && { loaded=0; break; }
done
[ $loaded = 0 ] || { echo "FAIL loaded (timeout)"; screen | tail -5; exit 1; }

clear_line; run 'echo $LS_COLORS | wc -c' Enter
n=$(screen | grep -Eo '^[0-9]+' | tail -1); [ "${n:-0}" -gt 1000 ]; result "ls_colors (LS_COLORS has ${n:-0} chars)" $?

clear_line; run '$ echo undollar-ok' Enter; screen | grep -q '^undollar-ok'; result 'paste "$ cmd"' $?
clear_line; run '❯ echo prompt-char-ok' Enter; screen | grep -q '^prompt-char-ok'; result 'paste "❯ cmd"' $?

clear_line; run 'ls -d /tmp'; run Escape; run Escape; screen | grep -q 'sudo ls -d /tmp'; result 'Esc Esc prepends sudo' $?

clear_line; run 'echo autosuggest-target-xyz' Enter; clear_line
run 'echo autosug'; run C-Space; run Enter; screen | grep -q '^autosuggest-target-xyz'; result 'autosuggestion + Ctrl+Space accept' $?

clear_line; run 'echo hss-target-abc' Enter; run 'echo other' Enter; clear_line
run 'hss-t'; run Up; screen | grep -q 'echo hss-target-abc'; result 'Up = history substring search' $?

clear_line; run 'cd /usr/share/doc' Enter; run 'cd ~' Enter; run 'z doc && echo "Z=$PWD"' Enter
screen | grep -q '^Z=/usr/share/doc'; result 'z jumps to a visited dir' $?

clear_line; run 'cd /usr/'; run Tab; sleep 1
screen | grep -Eq '^\s*>|[0-9]+/[0-9]+'; result 'Tab opens fzf-tab list (cd /usr/)' $?
screen | grep -q '│' ; result 'fzf-tab preview pane (eza)' $?
run Escape; clear_line

run C-r; sleep 1; screen | grep -Eq '[0-9]+/[0-9]+'; result 'Ctrl+R opens fzf/atuin history' $?
run Escape; run C-c; clear_line

run 'sl' Enter; sleep 0.5; screen | grep -qi 'correct'; result 'correction prompt for typo (sl)' $?
run n Enter; clear_line
tmux kill-server
EOF
}

mkdir -p "$here/results"
for cfg in "$@"; do
    echo "==> $cfg"
    check "$cfg" | tee "$here/results/$cfg.interactive.txt"
done
