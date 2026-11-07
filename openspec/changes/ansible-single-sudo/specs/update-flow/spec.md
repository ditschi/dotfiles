# Spec Delta

## MODIFIED Requirements

### Requirement: Apply failure names the failing step
When a local `machine apply` or the apply step of `machine update` fails, the message SHALL name the step that failed (Ansible or the post-apply health check) with its reason. Hints about Ansible or sudo restrictions SHALL appear only when Ansible failed.

#### Scenario: Health check names itself
- **WHEN** Ansible succeeds and the post-apply health check fails because zsh prints an error on startup
- **THEN** the output says that the health check failed, shows the zsh output and does not mention Ansible's error or sudo restrictions

#### Scenario: Ansible failure keeps its hint
- **WHEN** the Ansible run of `machine apply` fails and the host config did not change
- **THEN** the output says to review Ansible's error and that running `ansible-playbook` as root through sudo needs administrator approval where sudo is restricted
