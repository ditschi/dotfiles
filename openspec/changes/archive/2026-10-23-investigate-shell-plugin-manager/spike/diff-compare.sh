#!/usr/bin/env bash
# diff-so-fancy vs delta (task 3.3): runtime on a large sample diff (hyperfine) and a rendered
# small diff for reading by eye. Output: results/diff-compare.txt
set -euo pipefail
cd "$(dirname "$0")"
docker run --rm -i shell-spike:local bash -s <<'IN' | tee results/diff-compare.txt
set -euo pipefail
cd ~
export TERM=xterm-256color COLUMNS=100
git clone -q --depth 1 https://github.com/so-fancy/diff-so-fancy dsf
git clone -q --depth 300 https://github.com/zsh-users/zsh-autosuggestions repo
git -C repo log -p --color=always -300 >big.diff
git -C repo show --color=always "$(git -C repo log --no-merges -1 --format=%h -- src)" >small.diff
echo "sample: $(wc -l <big.diff) lines (git log -p -300 of zsh-autosuggestions)"
echo "diff-so-fancy $(git -C dsf describe --tags --always), delta $(delta --version | cut -d' ' -f2)"
hyperfine -N -w 3 -r 15 --export-markdown /tmp/h.md \
  -n diff-so-fancy "$HOME/dsf/diff-so-fancy" -n delta 'delta --paging=never --width=120' \
  --input big.diff 2>&1 | sed 's/\x1b\[[0-9;]*m//g'
cat /tmp/h.md
echo "== diff-so-fancy (small diff, colours stripped)"
"$HOME/dsf/diff-so-fancy" <small.diff | sed 's/\x1b\[[0-9;]*m//g' | head -30
echo "== delta (small diff, colours stripped)"
delta --paging=never --width=100 <small.diff | sed 's/\x1b\[[0-9;]*m//g' | head -30
IN
