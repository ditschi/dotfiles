"""tailscale: the pinned repository key, the apt source and the feature wiring."""

from __future__ import annotations

import os
import subprocess

import jinja2
import yaml

from package_sets import ANSIBLE

ROLE = ANSIBLE / "roles/tailscale"
KEY = ROLE / "files/tailscale.asc"
FINGERPRINT = "2596A99EAAB33821893C0A79458CA832957F5868"  # pragma: allowlist secret


def test_pinned_key_has_the_repository_fingerprint(tmp_path):
    result = subprocess.run(
        ["gpg", "--show-keys", "--with-colons", str(KEY)],
        env={**os.environ, "GNUPGHOME": str(tmp_path)},
        capture_output=True,
        text=True,
        check=True,
    )
    lines = result.stdout.splitlines()
    primary = [
        lines[i + 1].split(":")[9]
        for i, line in enumerate(lines)
        if line.startswith("pub:") and lines[i + 1].startswith("fpr:")
    ]
    assert primary == [FINGERPRINT]


def _defaults():
    return yaml.safe_load((ROLE / "defaults/main.yml").read_text())


def _render_source(distro: str, codename: str) -> dict:
    template = jinja2.Template((ROLE / "templates/tailscale.sources.j2").read_text())
    text = template.render(
        **_defaults(),
        tailscale_distro=distro,
        ansible_facts={"distribution_release": codename},
    )
    fields = {}
    for line in text.splitlines():
        if line and not line.startswith("#"):
            key, _, value = line.partition(":")
            fields[key] = value.strip()
    return fields


def test_source_per_distribution():
    defaults = _defaults()
    assert defaults["tailscale_keyring"] == "/etc/apt/keyrings/tailscale.asc"
    assert defaults["tailscale_source"] == ("/etc/apt/sources.list.d/tailscale.sources")
    for distro, codename in (("ubuntu", "resolute"), ("debian", "trixie")):
        fields = _render_source(distro, codename)
        assert fields == {
            "Types": "deb",
            "URIs": f"https://pkgs.tailscale.com/stable/{distro}/",
            "Suites": codename,
            "Components": "main",
            "Signed-By": "/etc/apt/keyrings/tailscale.asc",
        }


def test_role_runs_only_with_the_feature():
    plays = yaml.safe_load((ANSIBLE / "workstation.yml").read_text())
    entries = [
        (play, role)
        for play in plays
        for role in play.get("roles", [])
        if isinstance(role, dict) and role.get("role") == "tailscale"
    ]
    assert len(entries) == 1
    play, role = entries[0]
    assert role["when"] == "'tailscale' in machine_features"
    assert "tailscale" in play["tags"]
    assert play["become"] is True


def test_snap_host_gets_no_package():
    tasks = yaml.safe_load((ROLE / "tasks/main.yml").read_text())
    names = [t["name"] for t in tasks]
    install = next(
        t for t in tasks if t.get("block") and "Install Tailscale" in t["name"]
    )
    assert "tailscale_snap.rc | default(1) != 0" in install["when"]
    assert names.index("Check for the Tailscale snap") < names.index(install["name"])
    text = (ROLE / "tasks/main.yml").read_text()
    assert "snap remove" not in text and "snap stop" not in text
