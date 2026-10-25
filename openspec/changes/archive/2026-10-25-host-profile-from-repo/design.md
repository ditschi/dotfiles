# Design

## Context

`sync_host_profile_from_repo` already copies the repository file over the local copy on every update and apply, and logs only "synced local profile". `maybe_persist_host_profile` in `machine setup` shows a diff and asks before writing the repository file; with `--yes` an existing file is left alone. See proposal.md for the motivation.

## Decisions

- **The repository file is the only source (owner decision).** A profile can then be changed from any host, and an update brings the change to the machine. Two editable files were rejected: they diverge silently and need a merge question.
- **Applied with a notice, without a question (owner decision).** Update and apply print what changed in the profile and go on; the background update applies it too, as for any other incoming commit.
- **The local copy stays, written only by `machine`.** It is the applied state a failed apply reverts to, and it holds the profile where no repository file exists (containers, a fresh host before the first commit). Edits by hand are overwritten on the next update, and the notice shows them.
- **Setup writes the repository file directly.** No "Update versioned host profile?" question; the existing commit offer stays, so committing and pushing remain explicit.
