#!/usr/bin/env bash
# Task 4.1: install the shell tools three ways as a non-root user in the spike image
# (the image's own tool links are removed first):
#   mise   - `mise use -g` + `mise activate zsh`
#   zinit  - zinit from"gh-r" as"program" (sheldon/antidote cannot install release binaries)
#   mix    - zinit gh-r for fzf (plugin-coupled), mise for the rest
# Per variant: install time, then (network off) start + `--version` of every tool, then the
# same with eza removed (and with eza and the download cache removed). Output: results/tools-install.txt
set -euo pipefail
cd "$(dirname "$0")"
tools="fzf eza fd zoxide starship atuin delta"
run() { # run <volume> <network>, script on stdin: as tester, home on a volume, tool links removed
  docker run --rm -i --network "$2" -v "$1:/home/tester" -u root \
    -e TOOLS="$tools" -e MISE_TOOLS="${mise_tools-}" shell-spike:local bash -c '
    cd /usr/local/bin && rm -f $TOOLS sheldon && chown tester: /home/tester &&
    exec runuser -u tester -- env HOME=/home/tester TERM=xterm-256color \
      MISE_DATA_DIR=/home/tester/.local/share/mise MISE_CONFIG_DIR=/home/tester/.config/mise \
      MISE_CACHE_DIR=/home/tester/.cache/mise TOOLS="$TOOLS" MISE_TOOLS="$MISE_TOOLS" bash -s'
}
zinit_head='ZINIT_HOME=~/.local/share/zinit/zinit.git
[[ -d $ZINIT_HOME ]] || git clone -q --depth 1 https://github.com/zdharma-continuum/zinit $ZINIT_HOME
source $ZINIT_HOME/zinit.zsh'
zinit_ghr() { # zinit gh-r lines for the given repos
  local r
  for r; do
    case $r in
      fzf) echo 'zinit lucid from"gh-r" as"program" pick"fzf" for junegunn/fzf' ;;
      eza) echo 'zinit lucid from"gh-r" as"program" bpick"*x86_64-unknown-linux-gnu.tar.gz" pick"eza" for eza-community/eza' ;;
      fd) echo 'zinit lucid from"gh-r" as"program" pick"*/fd" for @sharkdp/fd  # @: "sharkdp" would parse as the sh ice' ;;
      zoxide) echo 'zinit lucid from"gh-r" as"program" pick"zoxide" for ajeetdsouza/zoxide' ;;
      starship) echo 'zinit lucid from"gh-r" as"program" pick"starship" for starship/starship' ;;
      atuin) echo 'zinit lucid from"gh-r" as"program" pick"*/atuin" for atuinsh/atuin' ;;
      delta) echo 'zinit lucid from"gh-r" as"program" pick"*/delta" for dandavison/delta' ;;
    esac
  done
}
tool_init='(( $+commands[zoxide] )) && eval "$(zoxide init zsh)"
(( $+commands[fzf] )) && source <(fzf --zsh)
(( $+commands[atuin] )) && eval "$(atuin init zsh --disable-up-arrow)"
(( $+commands[starship] )) && eval "$(starship init zsh)"'
# check.zsh runs in an interactive zsh with a terminal (script): "tool=version" per tool,
# MISSING when it cannot run; any error output of the shell start is kept.
check_zsh='for t in $=TOOLS; do v=$($t --version 2>/dev/null | grep -oE "[0-9]+\.[0-9]+(\.[0-9]+)?" | head -1) || true; printf "%s=%s; " $t ${v:-MISSING}; done'
check='script -qfec "zsh -i ~/check.zsh" /dev/null </dev/null 2>&1 | sed "s/\x1b\[[0-9;?]*[a-zA-Z]//g" | tr -d "\r" | tr "\n" " " | cut -c1-600; echo'
ms='awk -v s=$s -v e=$EPOCHREALTIME "BEGIN { printf \"%.0f ms\n\", (e - s) * 1000 }"'


{
for v in mise zinit mix; do
  vol=spike-tools-$v
  docker volume rm -f "$vol" >/dev/null
  case $v in
    mise) mise_tools=$tools; zinit_tools= ;;
    zinit) mise_tools=; zinit_tools=$tools ;;
    mix) mise_tools=${tools#fzf }; zinit_tools=fzf ;;
  esac
  zshrc=
  [[ -n $zinit_tools ]] && zshrc+="$zinit_head"$'\n'"$(zinit_ghr $zinit_tools)"$'\n'
  [[ -n $mise_tools ]] && zshrc+='eval "$(mise activate zsh)"'$'\n'
  zshrc+=$tool_init
  echo "== $v (mise: ${mise_tools:-none}; zinit gh-r: ${zinit_tools:-none})"
  printf '%s\n' "$zshrc" | docker run --rm -i -v "$vol:/home/tester" shell-spike:local sh -c 'cat >~/.zshrc'
  printf '%s\n' "$check_zsh" | docker run --rm -i -v "$vol:/home/tester" shell-spike:local sh -c 'cat >~/check.zsh'
  # install: mise (if any), then the first shell start (zinit downloads on first start)
  printf 'install: '
  run "$vol" bridge <<IN
cd ~; s=\$EPOCHREALTIME
[ -n "\$MISE_TOOLS" ] && MISE_YES=1 mise use -g -q \$MISE_TOOLS >/tmp/mise.log 2>&1
script -qfec 'zsh -i -c exit' /dev/null </dev/null >/tmp/out 2>&1 || true
$ms
tail -3 /tmp/mise.log /tmp/out 2>/dev/null | sed 's/\x1b\[[0-9;?]*[a-zA-Z]//g' | grep -iE 'error|warn|fail' || true
printf 'online:  '; $check
IN
  printf 'offline: '; echo "s=\$EPOCHREALTIME; $check; printf '  start+check: '; $ms" | run "$vol" none
  # remove one tool (eza) and start offline: must start without errors
  echo 'rm -rf ~/.local/share/mise/installs/eza ~/.local/share/zinit/plugins/eza-community---eza' | run "$vol" none
  # mise reinstalls a missing tool on first use (auto_install) from its download cache, even offline
  inst='printf "  installed after check: "; ls ~/.local/share/mise/installs 2>/dev/null | tr "\n" " "; echo'
  printf 'no eza:  '; echo "s=\$EPOCHREALTIME; $check; printf '  start+check: '; $ms; $inst" | run "$vol" none
  echo 'rm -rf ~/.local/share/mise/installs/eza ~/.cache/mise ~/.local/share/zinit/plugins/eza-community---eza' | run "$vol" none
  printf 'no eza, no download cache:  '; echo "$check; $inst" | run "$vol" none
  docker volume rm -f "$vol" >/dev/null
done
} | tee results/tools-install.txt
