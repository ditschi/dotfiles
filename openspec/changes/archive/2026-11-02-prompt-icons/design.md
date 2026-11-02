# Design

## Context

See proposal.md for the motivation and specs/shell-prompt/spec.md for the required behaviour. The terminals use "FiraCode Nerd Font Mono" (set by `machine` for Ddterm and the VS Code terminal). Starship renders colour emoji with the emoji font's own colours; text colours and the `dimmed` attribute only make them darker.

## Decisions

1. **One meaning per colour.** Cyan for the location, green for good or in sync (staged, ✓, branch name, zsh `❯`), yellow for things that need attention (changed, new, renamed, dotfiles update, Bitwarden), red for problems (failed command, conflicts, deletions, diverged, low disk), purple for the distance to the upstream and the stash, blue `#5f87ff` for the remote context, lilac for the Python virtualenv, and grey for background information (time, command duration, the fill line). The git icon keeps the orange of the git logo. Warnings stand out because no decorative element uses yellow or red.
2. **Emoji for markers, Nerd Font icons for inline symbols.** The Mono variant of the Nerd Font fits every icon into one cell, so a Font Awesome globe as SSH marker was too small to notice. Markers on the second line are colour emoji like the existing 🐳 (`💻` for SSH), followed by a text label `ssh` in the remote blue. The git branch uses the Font Awesome code-fork icon, which takes the text colour.
3. **SSH marker from `SSH_CONNECTION`.** An `env_var` module on `SSH_CONNECTION` draws the marker on the second line, separately from `user@hostname`, which stays directly in front of the time.
4. **Python only with an active virtualenv.** Project-file detection is turned off, so 🐍 appears only when `VIRTUAL_ENV` is set; the Python version is not shown.
5. **The bash prompt character stays blue.** The spec text that called it purple was wrong; the owner confirmed the existing colours (zsh green/red, bash blue/orange).

Alternatives the owner rejected while previewing: the 🌿 emoji for the branch (a plant, not a git branch), a Font Awesome globe in light blue (too small, too close to the directory colour), and a badge with a coloured background.

## Risks / Trade-offs

- [A terminal without a Nerd Font shows a replacement character for the git icon] → `machine` sets the Nerd Font for the supported terminals; the branch name stays readable.
