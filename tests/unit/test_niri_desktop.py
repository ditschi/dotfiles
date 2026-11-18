"""niri_desktop: the pinned PPA signing key, the deb822 sources, the wiring; the dotfile group niri."""

from __future__ import annotations

import os
import subprocess

import jinja2
import yaml

from package_sets import ANSIBLE, REPO

ROLE = ANSIBLE / "roles/niri_desktop"
KEY = ROLE / "files/duxlabs.asc"
FINGERPRINT = "6354D7C7146C2DD8F98892895ABFA2A5F21E824E"  # pragma: allowlist secret
GROUP = REPO / "home/niri"


def test_pinned_key_has_the_ppa_fingerprint(tmp_path):
    result = subprocess.run(
        ["gpg", "--show-keys", "--with-colons", str(KEY)],
        env={**os.environ, "GNUPGHOME": str(tmp_path)},
        capture_output=True,
        text=True,
        check=True,
    )
    fingerprints = [
        line.split(":")[9]
        for line in result.stdout.splitlines()
        if line.startswith("fpr:")
    ]
    assert fingerprints == [FINGERPRINT]


def _defaults():
    return yaml.safe_load((ROLE / "defaults/main.yml").read_text())


def test_both_ppas_and_the_packages():
    defaults = _defaults()
    assert {ppa["name"]: ppa["url"] for ppa in defaults["niri_desktop_ppas"]} == {
        "dux-repo": "https://ppa.launchpadcontent.net/duxlabs/dux-repo/ubuntu",
        "dms": "https://ppa.launchpadcontent.net/duxlabs/dms/ubuntu",
    }
    assert defaults["niri_desktop_keyring"] == "/etc/apt/keyrings/duxlabs.asc"
    assert defaults["niri_desktop_packages"] == ["niri", "dms", "ghostty"]


def test_sources_are_signed_by_the_pinned_key():
    defaults = _defaults()
    template = jinja2.Template((ROLE / "templates/duxlabs.sources.j2").read_text())
    for ppa in defaults["niri_desktop_ppas"]:
        text = template.render(
            item=ppa,
            niri_desktop_keyring=defaults["niri_desktop_keyring"],
            ansible_facts={"distribution_release": "resolute"},
        )
        fields = dict(line.split(": ", 1) for line in text.splitlines() if ": " in line)
        assert fields == {
            "Types": "deb",
            "URIs": ppa["url"] + "/",
            "Suites": "resolute",
            "Components": "main",
            "Signed-By": "/etc/apt/keyrings/duxlabs.asc",
        }


def test_role_replaces_the_add_apt_repository_files():
    tasks = (ROLE / "tasks/main.yml").read_text()
    assert (
        "duxlabs-ubuntu-{{ item.name }}-{{ ansible_facts.distribution_release }}.sources"
        in tasks
    )
    assert "duxlabs-{{ item.name }}.sources" in tasks


def test_role_runs_only_with_the_feature():
    plays = yaml.safe_load((ANSIBLE / "workstation.yml").read_text())
    play = next(
        p
        for p in plays
        if any(r.get("role") == "niri_desktop" for r in p.get("roles", []))
    )
    assert play["tags"] == ["niri"]
    assert play["become"] is True
    (role,) = play["roles"]
    assert role["when"] == "'niri' in machine_features"


def test_dotfile_group_binds_f12_and_mod_e():
    text = (GROUP / ".config/niri/dotfiles.kdl").read_text()
    assert (
        'F12 hotkey-overlay-title="Drop-down terminal" { spawn "ghostty" "+toggle-quick-terminal"; }'
        in text
    )
    assert (
        'Mod+E hotkey-overlay-title="File manager" { spawn-sh "xdg-open ~"; }' in text
    )


def test_quick_terminal_settings():
    lines = [
        line
        for line in (GROUP / ".config/ghostty/quick-terminal.conf")
        .read_text()
        .splitlines()
        if line and not line.startswith("#")
    ]
    assert lines == [
        "quick-terminal-position = top",
        "quick-terminal-size = 45%, 85%",
        "quick-terminal-autohide = true",
    ]
