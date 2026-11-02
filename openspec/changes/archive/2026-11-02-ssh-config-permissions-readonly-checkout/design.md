# Design

## Context

See proposal.md - Why. Dotfile apply sets the managed SSH config to mode `0600` and the SSH client apply removes group/other write access from the versioned base config. Both fail with `Read-only file system` when the checkout is mounted read-only (Docker profile tests, `sdx`).

## Decisions

### Tolerate only a read-only file system
When changing the mode fails with `EROFS`, dotfile apply and the SSH client apply report that the mode could not be set, naming the file and its current mode, and continue. Any other error from changing the mode, for example `EPERM` when the user does not own the file, still fails the apply as before. When the target already has the wanted mode, the mode is not changed at all.

This keeps the guarantee that a writable checkout gets owner-only permissions and that real permission problems stay visible, while a read-only mount, where nothing can be changed, no longer breaks setup.

Alternative considered: copying the checkout into the test containers instead of mounting it read-only. It would fix only the tests, not `sdx`, which runs bootstrap from a read-only mount.

## Risks / Trade-offs

- [On a read-only mount the linked SSH config keeps a group- or world-readable mode, and ssh may refuse a group-writable file] → The output names the file and its mode; the mount's source decides the mode.
