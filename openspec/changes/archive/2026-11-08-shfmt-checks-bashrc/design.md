# Design

## Context

See proposal.md - Why. `~/.bashrc` is a symlink into the checkout, so a block that the work Ansible setup (`blockinfile`) adds to `~/.bashrc` lands in the working tree of `home/core/.bashrc`. `machine update` moves added text into `~/.bashrc-local`, keyed by its first line (`machine_cli/local_overrides.py`); identical text is later removed silently, different text under the same key is a conflict. During `git commit`, pre-commit stashes unstaged changes, so hooks see only staged content; `pre-commit run --files`/`--all-files` see the working tree.

## Decisions

### Check `.bashrc`, never rewrite it
A second `shfmt` hook runs on `home/core/.bashrc` with `--diff` (same indent options) and without `--write`. A formatting difference fails the hook and shows the diff; the file stays as it is. If `shfmt --write` reformatted a block that Ansible added and that was not moved yet, `machine update` would move the reformatted text, Ansible would add the original block again, and every later update would report a conflict for that key. The check keeps the stub formatted without that risk.

Alternative considered: formatting `.bashrc` and `~/.bashrc-local` together. Ansible would still write its own formatting on its next run, so the conflict would come back.

### Reject managed blocks in the shared `.bashrc`
The local hook `bashrc-no-managed-blocks` (`pygrep`, the pattern `machine_cli/local_overrides.py` uses for managed blocks) fails when `home/core/.bashrc` contains a `# BEGIN ... MANAGED BLOCK` line. Host additions belong in `~/.bashrc-local` (spec `bash-shared-config`), and once a block is committed `machine update` no longer sees it as added and never moves it.

## Risks / Trade-offs

- [`pre-commit run --all-files` on a work host fails while an Ansible block is still in `~/.bashrc`] → intended; the hook message names `machine update`, which moves the block.
