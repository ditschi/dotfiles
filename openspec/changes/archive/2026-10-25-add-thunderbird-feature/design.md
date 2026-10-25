# Design

## Context

`thunderbird-cli` (npm, binary `tb`) is an HTTP client for a local bridge daemon (`thunderbird-cli-bridge`, binary `tb-bridge`, `127.0.0.1:7700` for HTTP and `:7701` for WebSocket). A Thunderbird WebExtension (`thunderbird-ai@extension`, Thunderbird 128+) connects to the bridge; its address is fixed in the source (`ws://127.0.0.1:7701`) and the WebSocket side has no authentication. The bridge can require a token for HTTP (`TB_AUTH_TOKEN`). Upstream calls the release XPI signed, but the v1.1.0 assets contain no `META-INF/` signature; Thunderbird does not require signed add-ons by default (`xpinstall.signatures.required = false`, checked in the Thunderbird snap 158). On Ubuntu, `thunderbird` is a transitional deb for the snap. See proposal.md for the motivation.

## Decisions

- **Feature only on private laptops by default (owner request).** `home-laptop` gets `thunderbird` in `ansible/profiles/home-laptop.yml`. Other profiles can still select it.
- **CLI as mise `npm:` tools (owner decision).** Same as the LLM CLIs: pinned in `mise.lock`, no root, no `npm install -g`.
- **No automatic extension (owner decision).** Any Thunderbird with the extension connects to any bridge on `127.0.0.1:7701`, also one started by another local user, so its agent could read, send and delete that Thunderbird's mail. A system policy (`ExtensionSettings` in `/etc/thunderbird/policies`) was rejected because it installs the extension for every user of the host; an automatic copy into the profile directory was rejected for the same reason on shared hosts and because the profile path differs between snap and deb. The owner installs the extension by hand in their own profile.
- **XPI downloaded into the checkout, gitignored (owner decision).** `machine` stores the pinned release asset in `downloads/` so the manual install needs no search; ignored files do not count as local changes for the update.
- **Pinned release, verified by SHA-256 (owner decision).** URL and checksum are constants in `machine_cli/mise_tools.py`; a new version is a reviewed commit, like the mise lockfile.
- **Bridge started by hand (owner decision).** No systemd user service; the user starts `tb-bridge` when needed.

## Risks / Trade-offs

- [Another local user starts a bridge first] → the owner's Thunderbird with the extension connects to it. Accepted for hosts whose other accounts are trusted; only the owner's profile has the extension.
- [Release URL moves or disappears] → the download warns; the CLI and the bridge still work.
- [Extension has wide mail permissions (read, send, delete)] → installed only by the owner, only in their profile.
