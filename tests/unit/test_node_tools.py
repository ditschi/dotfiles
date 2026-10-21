from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "profile",
    ["home-laptop", "home-server", "rpi", "rpi-zero", "container", "work-machine"],
)
def test_llm_profile_defaults(profile):
    data = yaml.safe_load((ROOT / f"ansible/profiles/{profile}.yml").read_text())
    assert ("claude-code" in data["features"]) == (profile != "container")
    assert ("copilot-cli" in data["features"]) == (profile == "work-machine")


def test_node_role_runs_for_all_profiles():
    plays = yaml.safe_load((ROOT / "ansible/workstation.yml").read_text())
    play = next(p for p in plays if "node_tools" in p.get("tags", []))
    assert play["become"] is False
    assert play["roles"] == [{"role": "node_tools"}]


@pytest.mark.skipif(
    shutil.which("ansible-playbook") is None, reason="Ansible unavailable"
)
@pytest.mark.parametrize(
    "features,existing,version,expected",
    [
        (
            ["claude-code"],
            [],
            None,
            ["@anthropic-ai/claude-code", "@fission-ai/openspec"],
        ),
        (
            ["claude-code", "copilot-cli"],
            [],
            24,
            ["@anthropic-ai/claude-code", "@github/copilot", "@fission-ai/openspec"],
        ),
        (
            ["copilot-cli"],
            [],
            24,
            ["@github/copilot", "@fission-ai/openspec"],
        ),
        ([], [], 24, []),
        ([], ["codex"], 24, ["@fission-ai/openspec"]),
        (["claude-code"], ["claude"], 24, ["@fission-ai/openspec"]),
        (["claude-code"], ["claude", "openspec"], 24, []),
        (
            ["claude-code", "copilot-cli"],
            ["claude", "copilot"],
            24,
            ["@fission-ai/openspec"],
        ),
        ([], [], 20, []),
    ],
)
def test_node_role_install_policy_and_idempotence(
    tmp_path, features, existing, version, expected
):
    home = tmp_path / "home"
    nvm = home / ".nvm"
    templates = nvm / "templates"
    templates.mkdir(parents=True)
    log = home / "npm-installs"
    runtime_log = home / "runtime-installs"
    (templates / "node").write_text(
        """#!/bin/bash
major="$(cat "$NVM_DIR/major")"
if [ "$1" = --version ]; then echo "v$major.0.0"; else test "$major" -ge 22; fi
"""
    )
    (templates / "npm").write_text(
        """#!/bin/bash
set -eu
if [ "$1" = --version ]; then echo 11.0.0; exit 0; fi
test "$1" = install
test "$2" = --global
echo "$3" >> "$NVM_DIR/../npm-installs"
case "$3" in
  @anthropic-ai/claude-code) tool=claude ;;
  @github/copilot) tool=copilot ;;
  @fission-ai/openspec) tool=openspec ;;
  *) exit 1 ;;
esac
printf '#!/bin/bash\\nexit 0\\n' > "$NVM_DIR/bin/$tool"
chmod +x "$NVM_DIR/bin/$tool"
"""
    )
    for tool in templates.iterdir():
        tool.chmod(0o755)
    (nvm / "nvm.sh").write_text(
        """test "$1" = --no-use || return 1
nvm() {
  case "$1" in
    version)
      if [ -x "$NVM_DIR/bin/node" ]; then
        echo "v$(cat "$NVM_DIR/major").0.0"
      else
        echo N/A
        return 3
      fi ;;
    use)
      export PATH="$NVM_DIR/bin:$PATH"
      test -x "$NVM_DIR/bin/node" ;;
    install)
      echo "$*" >> "$NVM_DIR/../runtime-installs"
      mkdir -p "$NVM_DIR/bin"
      cp "$NVM_DIR/templates/node" "$NVM_DIR/templates/npm" "$NVM_DIR/bin/"
      echo 24 > "$NVM_DIR/major" ;;
    alias) : ;;
    *) return 1 ;;
  esac
}
"""
    )
    if version is not None:
        shutil.copytree(templates, nvm / "bin")
        (nvm / "major").write_text(str(version))
    local_bin = home / ".local/bin"
    local_bin.mkdir(parents=True)
    for tool in existing:
        binary = local_bin / tool
        binary.write_text("#!/bin/sh\nexit 0\n")
        binary.chmod(0o755)
    playbook = tmp_path / "play.yml"
    playbook.write_text(
        yaml.safe_dump(
            [
                {
                    "name": "Test Node tools",
                    "hosts": "localhost",
                    "connection": "local",
                    "gather_facts": False,
                    "vars": {
                        "ansible_facts": {
                            "env": {"HOME": str(home), "PATH": "/usr/bin:/bin"}
                        },
                        "features": features,
                    },
                    "roles": [{"role": str(ROOT / "ansible/roles/node_tools")}],
                }
            ]
        )
    )
    for iteration in range(3):
        arguments = ["--check"] if iteration == 0 else []
        result = subprocess.run(
            ["ansible-playbook", "-i", "localhost,", str(playbook), *arguments],
            capture_output=True,
            text=True,
            env={**os.environ, "ANSIBLE_NOCOLOR": "1"},
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert (log.read_text().splitlines() if log.exists() else []) == (
            [] if iteration == 0 else expected
        )
        if iteration == 0:
            assert not runtime_log.exists()
        if iteration == 2:
            assert "changed=0" in result.stdout
    installs = runtime_log.read_text().splitlines() if runtime_log.exists() else []
    if version is None:
        assert installs == ["install --lts"]
    elif version < 22:
        assert installs == [f"install --lts --reinstall-packages-from=v{version}.0.0"]
    else:
        assert installs == []
