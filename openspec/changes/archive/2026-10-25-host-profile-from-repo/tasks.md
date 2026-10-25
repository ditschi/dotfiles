# Tasks

## 1. Repository file as the only source

- [x] 1.1 `machine setup` writes `machine/hosts/<hostname>.yml` without a question (also with `--yes`) when the selection differs, except in containers, then offers the commit as before. Verify unit tests for a changed selection with and without `--yes` and for the container profile.
- [x] 1.2 When update or apply copies the repository file over a different local copy, print the profile change, added and removed features and `ssh_allow_from` changes. Verify unit tests for an added feature and for a hand-edited local copy.
- [x] 1.3 `machine update --check` lists the profile changes of an incoming commit to this host's file. Verify a unit test with an upstream change.

## 2. Docs and checks

- [x] 2.1 Update the Readme profile section. Verify the text matches the behaviour.
- [x] 2.2 Run `pre-commit run --all-files`, `pytest tests/unit -q` and `openspec validate host-profile-from-repo --strict`. Verify all pass.
