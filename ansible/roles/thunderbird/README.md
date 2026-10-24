# thunderbird

Feature `thunderbird`: adds the signed "Thunderbird AI Bridge" extension of
[thunderbird-cli](https://github.com/vitalio-sh/thunderbird-cli) to
`/etc/thunderbird/policies/policies.json` (`ExtensionSettings`, `normal_installed`).
Thunderbird installs it on its next start. The package itself comes from
`packages_by_feature`, `tb` and `tb-bridge` from the mise group `home/thunderbird`.
