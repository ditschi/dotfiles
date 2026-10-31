# Spec Delta

## MODIFIED Requirements

### Requirement: Work and private stay separate
The separation SHALL also cover the Git default identity (`~/.gitconfig.local`, from the context), the Bitwarden environment group (`work` or `private`, one per context, none in a container without context), the SSH key class (`work` or `home`), the SSH host list (`ssh/home/config` or `ssh/work/config`), the managed SSH host keys and `ssh-route` host blocks (private only), and the features of the private infrastructure (`monitoring`, `sshd-home`, `syncthing`, `tailscale`, `thunderbird`), which are excluded for work.

#### Scenario: Private host
- **WHEN** a private host loads secrets
- **THEN** only `env/groups/private` and its host item are queried, never the work group

#### Scenario: Work host
- **WHEN** a work host is set up
- **THEN** none of the private infrastructure features is offered or applied

#### Scenario: SSH host list on a work host
- **WHEN** a work host writes its SSH host list
- **THEN** only `ssh/work/config` is read, never `ssh/home/config`, and no managed home host keys are installed
