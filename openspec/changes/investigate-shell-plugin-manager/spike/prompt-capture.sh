#!/usr/bin/env bash
# Render the shared Starship prompt for zsh and bash (status 0 and 1), on the host and in the
# spike container. Escape sequences are shown with cat -v; colours: 1;32 green, 1;35 purple.
set -euo pipefail
cd "$(dirname "$0")"
cap='cd /tmp; for sh in zsh bash; do for st in 0 1; do
  printf "%s status=%s: " $sh $st
  STARSHIP_CONFIG=$CFG STARSHIP_SHELL=$sh starship prompt --status=$st --terminal-width=60 | cat -v | tr "\n" "|"
  echo; done; done'
{
  echo "== host"
  CFG=$PWD/configs/_common/skel/.config/starship.toml PATH=$PWD/.bin:$PATH bash -c "$cap"
  echo "== container"
  docker run --rm -e CFG=/s.toml -v "$PWD/configs/_common/skel/.config/starship.toml:/s.toml:ro" \
    shell-spike:local bash -c "$cap"
} | tee results/prompt-capture.txt
