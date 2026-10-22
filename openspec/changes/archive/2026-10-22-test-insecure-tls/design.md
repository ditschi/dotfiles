## Decisions

- Opt-in via environment variable, off by default, so CI and normal hosts keep verification.
- Covers `curl` and `ansible-galaxy` at build time; `git`, `uv`, Python and Ansible Galaxy in the running containers. The tool list is an implementation detail and not in the spec.
- Never applies to the real machine setup, only to test images and containers.
