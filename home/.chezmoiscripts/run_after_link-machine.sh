#!/usr/bin/env bash
# Links ~/.local/bin/machine to the CLI in this checkout. Migrates hosts that
# still have the copy chezmoi used to deploy; bootstrap does the same.
set -euo pipefail

target="$(cd "$CHEZMOI_SOURCE_DIR/.." && pwd)/machine_cli/machine"
link="$HOME/.local/bin/machine"

mkdir -p "$(dirname "$link")"
if [ "$(readlink "$link" 2>/dev/null || true)" != "$target" ]; then
    ln -sfn "$target" "$link"
fi
