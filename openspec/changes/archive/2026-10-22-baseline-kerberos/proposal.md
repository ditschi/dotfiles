# Proposal

## Why

The Kerberos token and password helpers are the ninth area moved from the temporary decision log into OpenSpec.

Motivation confirmed by the owner:

- Cron was the simplest choice for the refresher at the time; there is no known reason to move to a systemd user timer unless it has a practical benefit.
- Keyring lookup is preferred for passwords, with an environment-variable fallback because keyring access is not reliable in every context.
- Work networking needs the configured HTTP(S) proxy for some external destinations.

## What Changes

- Describe the confirmed behaviour as baseline requirements: the password helper, non-interactive `kinit`, the ticket refresher, the cron installer and the work shell start behaviour.
- Points the owner marked unclear or open stay out of the specs and become investigations in design.md: the name and content of the `kerberos` feature (LDAP tools are not Kerberos), which aliases use the helpers, managing the refresher through Ansible, password fallback across contexts, and LDAP region selection.
- Features only: no fixes or improvements are added to the baseline.

## Capabilities

### New Capabilities

- `kerberos-tokens`: how a work machine gets and keeps a Kerberos ticket and finds the password for it.

### Modified Capabilities

None.

## Open Questions

See design.md for the investigations.

## Impact

- Decision records: 0009-kerberos (to be retired once its content lives in specs and design).
- Code: none. This change only adds planning artifacts.
