# Project containers

`sde` and `sdx` start the current project's dev container.

`sde` runs the current project's `.devcontainer/sde.sh` when present, forwarding
arguments and its exit status. Non-executable scripts run through Bash. Without
that file, the shared Bash launcher is used. `sdx` calls that launcher in extended
mode, mounting the selected dotfiles checkout, plugin/apt caches, host HOME and
per-project history. Set `SDE_CONTAINER_HOME` if the container HOME differs from
the host HOME. Initialization runs before Compose; extended setup runs before
post-start and the shell or supplied command. Interactive sessions prefer zsh,
falling back to Bash.

Existing images can be reused or rebuilt, and interactive callers can attach to
existing project containers. `sdx` only offers containers created in extended
mode. Rebuilding starts a new container rather than attaching to one using the
old image. One-off commands reuse the image but always run in a fresh container,
without prompts or forced TTY allocation. To force a rebuild, invoke
`command sde --extended --rebuild -- <cmd> [args...]` (omit `--extended` for minimal
mode). The shell wrappers pass arguments as commands; shell expressions should
be explicit, e.g. `sdx bash -lc 'echo ready && make test'`.
