#!/usr/bin/env bash
# Benchmark spike configs with zsh-bench.
#   bench.sh container <config>...   fresh container per config (needs shell-spike:local)
#   bench.sh host <config>...        on this host with a temporary HOME
# Env: ITERS (default 13; the first 3 are warm-ups), RESULTS (default spike/results),
#      TAG (suffix for result files, default container|host)
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
mode=$1
shift
iters=${ITERS:-13}
results=${RESULTS:-$here/results}
tag=${TAG:-$mode}
mkdir -p "$results"

run_container() {
    local cfg=$1
    docker run --rm -u root -v "$here/configs:/spike/configs:ro" shell-spike:local \
        timeout 1200 /opt/zsh-bench/zsh-bench --isolation user --config-dir /spike/configs \
        --iters "$iters" --raw "$cfg"
}

# Host runs use the image's tool binaries (same versions as in the container).
host_bin() {
    local bin=$here/.bin
    [[ -x $bin/sheldon ]] && return
    mkdir -p "$bin"
    docker run --rm -u root -v "$bin:/out" shell-spike:local sh -c \
        'for t in fzf eza fd zoxide starship atuin delta sheldon hyperfine; do cp -L /usr/local/bin/$t /out/; done; chown -R '"$(id -u):$(id -g)"' /out'
}

run_host() {
    local cfg=$1 home zb
    home=$(mktemp -d /tmp/spike-home.XXXXXX)
    zb=${ZSH_BENCH:-/tmp/zsh-bench}
    [[ -x $zb/zsh-bench ]] || git clone -q --depth 1 https://github.com/romkatv/zsh-bench "$zb"
    (
        cd "$home"
        # the baseline keeps the host tools (it is "the current state")
        [[ $cfg == baseline-current ]] || export PATH=$here/.bin:$PATH
        env -u ZDOTDIR -u XDG_DATA_HOME -u XDG_CACHE_HOME -u XDG_CONFIG_HOME HOME="$home" \
            "$here/configs/$cfg/setup"
        env -u ZDOTDIR -u XDG_DATA_HOME -u XDG_CACHE_HOME -u XDG_CONFIG_HOME HOME="$home" \
            timeout 1200 "$zb/zsh-bench" --iters "$iters" --raw
    )
    rm -rf -- "$home"
}

# The baseline is the current dotfiles setup from home/ (chezmoi source names).
stage_baseline() {
    local repo skel=$here/configs/baseline-current/skel
    repo=$(git -C "$here" rev-parse --show-toplevel)
    rm -rf -- "$skel" && mkdir -p "$skel"
    cp "$repo/home/dot_zshrc" "$skel/.zshrc"
    cp "$repo/home/dot_zprofile" "$skel/.zprofile"
    cp "$repo/home/dot_profile" "$skel/.profile"
    cp "$repo/home/dot_p10k.zsh" "$skel/.p10k.zsh"
    cp -r "$repo/home/dot_zsh" "$skel/.zsh"
    cp "$here/configs/baseline-current/zshrc-local" "$skel/.zshrc-local"
}

[[ $mode == host ]] && host_bin
for cfg in "$@"; do
    [[ $cfg == baseline-current ]] && stage_baseline
    echo "==> $cfg ($mode)" >&2
    out=$("run_$mode" "$cfg" 2>&1) || {
        echo "$out" >&2
        echo "FAILED: $cfg" >&2
        continue
    }
    printf '%s\n' "$out" >"$results/$cfg.$tag.raw"
    python3 "$here/summarize.py" "$results/$cfg.$tag.raw" >"$results/$cfg.$tag.json"
    python3 "$here/summarize.py" --line "$results/$cfg.$tag.raw"
done
