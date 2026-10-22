## MODIFIED Requirements

### Requirement: Explicit update
`machine update` SHALL fast-forward the checkout, sync the host profile and apply the setup, running chezmoi before Ansible. System changes and host-profile changes SHALL stay explicit: they are not applied without the user running the command. Changes that only touch home files MAY be applied automatically in the background when the checkout has no local changes after the resolvers.

#### Scenario: Clean fast-forward
- **WHEN** a user runs `machine update` on a clean checkout that is behind its upstream
- **THEN** the checkout is fast-forwarded and the setup is applied

#### Scenario: Home-only change, clean checkout
- **WHEN** the background job finds only home-file changes and the checkout has no local changes
- **THEN** the changes are pulled and applied and the state tells the user to reload the shell

#### Scenario: System change pending
- **WHEN** the incoming changes include a system or host-profile change
- **THEN** nothing at or after the first such commit is applied in the background and the state shows that an update is available

#### Scenario: Home changes before a system change
- **WHEN** the incoming commits are home-only up to a commit that touches `ansible/**`, packages or the host profile
- **THEN** the checkout is fast-forwarded to just before that commit and applied, and the remaining commits stay pending for a manual `machine update`

#### Scenario: Blocked automatic update
- **WHEN** local changes remain after the resolvers
- **THEN** nothing is applied and the state is needs-attention with the reason
