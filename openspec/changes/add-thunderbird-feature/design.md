# Design

## Context

`thunderbird-cli` (npm, binary `tb`) is an HTTP client for a local bridge daemon (`thunderbird-cli-bridge`, binary `tb-bridge`, `127.0.0.1:7700` for HTTP and `:7701` for WebSocket). A Thunderbird WebExtension (`thunderbird-ai@extension`, Thunderbird 128+) connects to the bridge. Upstream publishes the extension signed by addons.thunderbird.net as a release asset (`thunderbird_ai_bridge-<version>-tb.xpi`). Locally built XPIs do not install permanently. On Ubuntu, `thunderbird` is a transitional deb for the snap. The snap has a `system-files` plug that reads `/etc/thunderbird` (checked on Ubuntu 26.04, Thunderbird snap 158). See proposal.md for the motivation.

## Decisions

- **Feature only on private laptops by default (owner request).** `home-laptop` gets `thunderbird` in `ansible/profiles/home-laptop.yml`. Other profiles can still select it.
- **Bridge started by hand (owner decision).** No systemd user service; the user starts `tb-bridge` when needed.
- **Bridge only with the extension (owner request).** The CLI and the bridge come from a dotfile group that only the feature selects. The same feature installs the extension, so the bridge never exists without it.
- **`normal_installed`, not `force_installed` (owner decision).** The extension is installed automatically, and the user can still disable it in Thunderbird. `force_installed` would prevent disabling.
- **CLI as mise `npm:` tools (owner decision).** Same as the LLM CLIs: pinned in `mise.lock`, no root, no `npm install -g`.

## Assumptions (to be confirmed by the owner)

- **Extension through a system policy, not the profile directory.** `ExtensionSettings` in `/etc/thunderbird/policies/policies.json` works for the snap and for a deb, does not depend on a Thunderbird profile existing yet, and survives profile changes. Copying the XPI into `<profile>/extensions/` was rejected because the profile path differs between snap and deb, and a profile may not exist before the first start.
- **Pinned release URL.** The policy points to the release asset of a fixed version (`v1.1.0`, extension 2.1.0). Thunderbird updates the add-on as usual. A new version is a reviewed commit, like the mise lockfile.
- **Policy merge.** The role reads an existing policy file and merges the entry into `ExtensionSettings`, so other policies stay.

## Risks / Trade-offs

- [Release URL moves or disappears] → Thunderbird cannot install the extension; the rest of the feature still works. The URL is pinned in `ansible/roles/thunderbird/defaults/main.yml`.
- [Extension has wide mail permissions (read, send, delete)] → it only listens to the local bridge on `127.0.0.1`. The feature is opt-in outside `home-laptop`.
