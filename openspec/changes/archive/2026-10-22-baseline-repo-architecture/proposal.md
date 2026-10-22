# Proposal

## Why

The repository architecture is the third area moved from the temporary decision log into OpenSpec, so that later changes build on a written baseline.

Motivation confirmed by the owner:

- One shared repository keeps shell, Git and tool configuration in sync across work and private machines.
- Editing a file in the home directory should edit the checkout, so changes are committed and reach other hosts with `machine update`.
- Machine setup and tool installation should be easy to read and repeat: new hosts are guided through setup, existing hosts get a clear and safe update path.
- Bootstrap should be self-contained: it installs `uv` when missing so nothing else needs to be prepared by hand.

## What Changes

- Describe the confirmed architecture as baseline requirements: files in the home directory are symlinks into the repository, the layering of host state, `machine` CLI, chezmoi and Ansible, guided setup for new hosts and safe updates for existing ones, and a self-contained bootstrap.
- Points the owner marked unclear (the `install.py` wrapper, the migrate and rollback code) and goals that are not current behaviour (bootstrap through `curl | bash`, all Python versions up to the latest) stay out of the specs. They are investigations in design.md.
- Features only: no fixes or improvements are added to the baseline.

## Capabilities

### New Capabilities

Boundaries are a proposal and are settled together with the owner:

- `repo-layout`: how the dotfiles live in the home directory and how host state, CLI, chezmoi and Ansible divide the work.
- `bootstrap`: how a new host gets from nothing to a set up machine.

### Modified Capabilities

None.

## Open Questions

See design.md for the investigations.

## Impact

- Decision records: 0001-repo-architecture (to be retired once its content lives in specs and design).
- Profiles: all.
- Code: none. This change only adds planning artifacts.
