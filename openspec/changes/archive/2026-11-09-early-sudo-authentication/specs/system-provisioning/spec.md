# Spec Delta

## ADDED Requirements

### Requirement: Sudo authentication before the slow steps
When `machine update` or `machine apply` will run local Ansible, `machine` SHALL authenticate sudo and check that sudo allows `ansible-playbook` as root before any step that is slow or asks a question, so that no sudo prompt appears later in the run. It SHALL NOT authenticate when Ansible will not run.

#### Scenario: Update with a system change
- **WHEN** `machine update` in a terminal finds that the host config changed or a relevant system file changed
- **THEN** the sudo prompt comes first, before the environment pull, the dotfile apply and the tool install, and Ansible later starts without a prompt while the ticket is valid

#### Scenario: Home-only update
- **WHEN** `machine update` finds no host-config change and no relevant system file change, and `--system` is not given
- **THEN** no sudo prompt appears

#### Scenario: Apply
- **WHEN** `machine apply` runs local Ansible in a terminal
- **THEN** the sudo prompt comes before the bootstrap tool install

#### Scenario: Ansible is skipped
- **WHEN** the host config has `ansible: false` or `--skip-ansible` is given
- **THEN** no sudo prompt appears

#### Scenario: Automatic update
- **WHEN** the background update runs
- **THEN** it never prompts for sudo and never runs Ansible

### Requirement: Renewed sudo check right before Ansible
Right before it starts local Ansible, `machine` SHALL check the sudo ticket again and SHALL prompt again only when it has expired meanwhile.

#### Scenario: Ticket still valid
- **WHEN** the steps between the early authentication and Ansible took less than the ticket lasts
- **THEN** Ansible starts without a prompt

#### Scenario: Ticket expired
- **WHEN** the steps took longer than the ticket lasts
- **THEN** the sudo prompt appears again right before Ansible and the run continues after authentication

### Requirement: Without sudo, everything that needs no root still runs
When the early sudo authentication fails, or sudo refuses `ansible-playbook` as root, `machine` SHALL report the reason at that point and SHALL NOT start Ansible. `machine update` SHALL still run every step that needs no root and report the Ansible step as failed at the end; `machine apply` SHALL restore the host config as for a failed Ansible run.

#### Scenario: Wrong password in update
- **WHEN** sudo gives up at the start of `machine update` because the password was wrong in every try
- **THEN** the dotfile and tool steps still run, Ansible does not run, and the summary names the failed Ansible step

#### Scenario: Changed host config without sudo
- **WHEN** `machine update` brings a changed host config and sudo gives up at the start
- **THEN** the steps that need no root use the new host config, the host config is restored at the end, and the next update applies it again

#### Scenario: Typo
- **WHEN** the user mistypes the password once and then enters it correctly
- **THEN** sudo asks again, the authentication succeeds and the run continues as usual

#### Scenario: Restricted sudo
- **WHEN** sudo refuses `ansible-playbook` as root
- **THEN** the message of the permission check appears before any slow step

#### Scenario: Without a terminal or with `--no-become`
- **WHEN** sudo would need authentication and there is no terminal or `--no-become` is given
- **THEN** the existing message appears at the start and no prompt is attempted

### Requirement: The failure names its cause
When the sudo authentication fails, the message SHALL say whether the password was wrong or the user has no permission to use sudo, and otherwise SHALL keep a generic text.

#### Scenario: Wrong password
- **WHEN** sudo gives up after incorrect password attempts
- **THEN** the message says the password was wrong and that the command can be run again

#### Scenario: No sudo permission
- **WHEN** sudo reports that the user may not run sudo
- **THEN** the message says the user has no sudo permission and names the administrator as the one to ask
