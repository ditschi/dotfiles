# Investigation: sensitive work and host data in the shared repository

Related specs: `work-private-separation`. Status: recommendations only, not owner-confirmed policy.

- Scope: tracked configuration and documentation relevant to work identity, inventory, host topology, and repository sharing.

## Findings

- work.gitconfig contains real personal and corporate identity details, organization/account identifiers, and credential account names.
- 01_work.zsh contains company-specific proxy settings, internal domains and documentation links, work tool names, and a work account identifier.
- hosts.example.yml is described as an example but contains real private-network addresses, SSH ports, and usernames. It should not be treated as a sanitized template.
- machine/hosts/README.md maps hostnames to device roles and describes parts of the home network/service topology. Versioned host profile filenames also expose host labels and profile/feature choices.
- machine/ssh_keys/ contains public keys with identifying comments. Public keys are not private credentials, but their comments and reuse can associate a person with specific devices.
- .pre-commit-config.yaml enables private-key and secret scanning. Those checks help detect credential material but do not identify personal names, internal URLs, hostnames, IPs, public-key comments, or topology as sensitive context.

## Recommended rules

1. Never commit passwords, tokens, session material, private keys, unencrypted inventories, or vault credentials. Keep real inventories encrypted or local.
2. Keep real work identity and account identifiers, internal domains/URLs, proxy configuration, company-specific hostnames, and work network details in an approved private/work-specific store or local configuration. Share generic logic, not the identifying values.
3. Treat real hostnames, IPs, ports, usernames, device mappings, and homelab topology as private metadata. Example inventories should use clearly fictional names and documentation-only IP ranges.
4. Public keys are not secrets, but commit them only when their device/user association is intentionally public. Never commit corresponding private keys.
5. Keep secret scanners, but require contextual review for metadata and identity exposure; a clean scanner result is not proof that a repository is safe to share.

## Recommendation

Do not share or publish the current repository unchanged beyond its intended private audience. First move or replace the real work identity/configuration and sanitize the inventory example and host/topology details. Keep generic profiles, reusable Ansible logic, and CI fixtures. Decide separately whether public-key comments and homelab mappings are acceptable disclosures.

These are agent recommendations for owner review, not owner-confirmed policy.
