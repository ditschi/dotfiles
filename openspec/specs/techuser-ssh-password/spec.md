# techuser-ssh-password Specification

## Purpose
Lets `ssh` log in as a technical user without typing its password, by reading the password live from Azure Key Vault when key authentication does not succeed, and only for those users.

## Requirements

### Requirement: Technical users are configured in the work env group
The technical users SHALL be configured by the variable `AZKV_TECHUSERS`, a space-separated list of `<user>=<vault>/<secret>` entries, set in the Bitwarden item `env/groups/work` and loaded through `~/.env`. The repository SHALL NOT contain vault names, secret names or user names.

#### Scenario: Two technical users
- **WHEN** `AZKV_TECHUSERS` is `ci-user-a=vault-a/technical-user-password ci-user-b=vault-b/technical-user-password`
- **THEN** the password of `ci-user-a` is read from the secret `technical-user-password` in `vault-a`, and that of `ci-user-b` from `vault-b`

#### Scenario: Variable not set
- **WHEN** `AZKV_TECHUSERS` is not set or empty
- **THEN** every `ssh` connection behaves exactly as without this capability

#### Scenario: Quoted value
- **WHEN** a plain env file sets the value in double quotes and the shell loads the quotes literally
- **THEN** the wrapper and the helper still match every entry

### Requirement: Wrapper scoped to technical users
The `work` dotfile group SHALL provide an `ssh` command that runs the real `ssh` unchanged. Only when `ssh -G` resolves the target to a user listed in `AZKV_TECHUSERS` SHALL it set `SSH_ASKPASS` to the Key Vault helper, `SSH_ASKPASS_REQUIRE=prefer` and the variable naming that user; otherwise it SHALL remove that variable and leave the askpass settings alone.

#### Scenario: CI agent
- **WHEN** a user runs `ssh ci-agent` and the SSH config resolves `User ci-user-a`
- **THEN** the real `ssh` is started with the Key Vault helper as askpass program for `ci-user-a`

#### Scenario: Other host
- **WHEN** a user runs `ssh homeserver` and the resolved user is not in `AZKV_TECHUSERS`
- **THEN** the real `ssh` starts without askpass settings from the wrapper and prompts in the terminal as before

#### Scenario: Wrapper not in the work group
- **WHEN** the host has the context `private`
- **THEN** no `ssh` wrapper and no helper is linked

### Requirement: Other tools use the same behavior
`scp`, `rsync`, `git` and `ssh-copy-id` call `ssh` through `PATH`, so connections they make as a technical user SHALL use the same password source without any change to those tools.

#### Scenario: Copying the key
- **WHEN** a user runs `ssh-copy-id -i ~/.ssh/id_ed25519_ci-user-a.pub ci-user-a@ci-agent` and the key is not yet authorized
- **THEN** the password comes from Key Vault, and the key is appended to `authorized_keys` of `ci-user-a`

#### Scenario: Key already authorized
- **WHEN** the key is already authorized on the agent
- **THEN** no password is requested and `az` is not called

### Requirement: Password only after key authentication fails
The helper SHALL be called only when ssh asks for a password, so a host that accepts the SSH key SHALL NOT cause an `az` call.

#### Scenario: Key accepted
- **WHEN** `ssh ci-agent` authenticates with the key
- **THEN** `az` is not run

### Requirement: One password attempt per connection
For a technical user, the wrapper SHALL set `NumberOfPasswordPrompts=1` when it sets the helper, so that a wrong Key Vault password is not sent repeatedly.

#### Scenario: Wrong password in Key Vault
- **WHEN** the server rejects the password from Key Vault
- **THEN** ssh fails after one attempt

### Requirement: Helper answers password prompts of the configured user only
The helper SHALL answer only a prompt that asks for a password (not for a passphrase, a confirmation or a password change) and names the account the wrapper resolved. It SHALL print the password on stdout only, and SHALL NOT write it to a file, a log or a command line.

#### Scenario: Password prompt
- **WHEN** ssh asks `ci-user-a@ci-agent's password:` or the keyboard-interactive prompt `(ci-user-a@ci-agent) Password:`
- **THEN** the helper prints the Key Vault password of `ci-user-a` and nothing else

#### Scenario: Another account
- **WHEN** a jump host asks `other@jump's password:`
- **THEN** the helper does not call `az` and asks in the terminal

#### Scenario: Password change
- **WHEN** the server asks for a new or current password
- **THEN** the helper does not call `az` and asks in the terminal

#### Scenario: Host key confirmation
- **WHEN** ssh asks `Are you sure you want to continue connecting (yes/no)?`
- **THEN** the helper reads the answer from the terminal, reports it through its exit status and does not call `az`

#### Scenario: Informational message
- **WHEN** ssh passes an informational message
- **THEN** the helper shows it on stderr, exits successfully and does not call `az`

### Requirement: Fallback to the terminal
When the Key Vault password cannot be read (not logged in to `az`, vault unreachable, no access, no such secret), the helper SHALL say why on stderr in one line, without the password, and SHALL ask for the password in the terminal. Without a terminal it SHALL fail.

#### Scenario: az not logged in
- **WHEN** ssh asks for the password and `az` has no valid login
- **THEN** one line says to run `az login`, and the password is read from the terminal

#### Scenario: No terminal
- **WHEN** the same happens in a run without a terminal
- **THEN** the helper exits non-zero, so the connection fails instead of waiting

### Requirement: An existing askpass program wins
When `SSH_ASKPASS` is already set in the environment, the wrapper SHALL NOT replace it.

#### Scenario: Editor sets its own askpass
- **WHEN** a remote-editing tool starts `ssh` with its own `SSH_ASKPASS`
- **THEN** the wrapper leaves it unchanged
