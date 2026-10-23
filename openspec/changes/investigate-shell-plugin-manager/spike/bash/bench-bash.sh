#!/usr/bin/env bash
# Time bash -i to the first prompt for each variant (none, fallback, full; each optionally with atuin) in the spike image.
# Usage: ./bench-bash.sh [iterations]   -> ../results/bash.txt
set -euo pipefail
cd "$(dirname "$0")"
iters=${1:-13}
docker run --rm -i -e ITERS="$iters" -v "$PWD/..:/spike:ro" shell-spike:local bash -s <<'IN' | tee ../results/bash.txt
set -euo pipefail
cd ~
cp -r /spike/configs/_common/skel/.config ~/
mkdir -p ~/.bash && cp /spike/bash/common.bash ~/.bash/
# LS_COLORS checkout as the zsh plugin manager (sheldon) leaves it
d=~/.local/share/sheldon/repos/github.com/trapd00r/LS_COLORS
mkdir -p "$d" && git clone -q --depth 1 https://github.com/trapd00r/LS_COLORS "$d"
for v in none fallback fallback+atuin full full+atuin; do
  atuin=; [[ $v == *+atuin ]] && atuin=1
  if [[ $v == none ]]; then
    printf '%s\n' '[[ $- == *i* ]] || return' 'spike_bash_features() { echo -; }' \
      "$(sed -n '/^spike_bash_prompt()/,/^}/p' ~/.bash/common.bash)" 'PROMPT_COMMAND+=(spike_bash_prompt)' >~/.bashrc
  else
    cp "/spike/bash/${v%+atuin}.bashrc" ~/.bashrc
  fi
  rm -rf ~/.cache/spike-bash ~/.cache/blesh ~/.local/share/atuin ~/.config/atuin
  report=$(mktemp)
  for i in $(seq 0 "$ITERS"); do   # run 0 = cold caches
    SPIKE_ATUIN=$atuin SPIKE_T0=$EPOCHREALTIME SPIKE_REPORT=$report SPIKE_EXIT_AT_PROMPT=1 TERM=xterm-256color \
      timeout 20 script -qfec 'bash -i' /dev/null </dev/null >/dev/null 2>&1 || true
  done
  awk -v v="$v" '/^prompt_ms=/ { split($1, a, "="); ms[n++] = a[2]; $1 = ""; feat = $0 }
    END {
      m = 0; for (i = 4; i < n; i++) w[m++] = ms[i]   # drop cold run + 3 warm-up
      asort(w)
      med = m ? (m % 2 ? w[(m + 1) / 2] : (w[m / 2] + w[m / 2 + 1]) / 2) : -1
      k = int(0.9 * m); if (k < 0.9 * m) k++
      p90 = m ? w[k] : -1
      printf "bash-%-15s cold %7.1f  prompt %6.1f/%6.1f  n=%d %s\n", v, (n ? ms[0] : -1), med, p90, m, feat
    }' "$report"
done
IN
