"""cosmic_desktop: the pinned PPA signing key; the dotfile group cosmic."""

from __future__ import annotations

import configparser
import os
import subprocess

from package_sets import ANSIBLE, REPO

KEY = ANSIBLE / "roles/cosmic_desktop/files/cosmic-epoch.asc"
FINGERPRINT = "EB141BFC014828F92C2EF883210C6A47471454A0"  # pragma: allowlist secret
UNITS = REPO / "home/cosmic/.config/systemd/user"


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


def _unit(path):
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    parser.read(path)
    return parser


def test_dconf_profile_is_dropped_before_gnome_session():
    unit = _unit(UNITS / "drop-cosmic-dconf-profile.service")
    assert unit["Unit"]["DefaultDependencies"] == "no"
    assert unit["Unit"]["Before"] == "gnome-session-pre.target"
    assert unit["Service"]["Type"] == "oneshot"
    assert unit["Service"]["ExecStart"] == (
        "/usr/bin/systemctl --user unset-environment DCONF_PROFILE"
    )


def test_gnome_session_pre_target_wants_the_unit():
    dropin = _unit(UNITS / "gnome-session-pre.target.d/drop-cosmic-dconf-profile.conf")
    assert dropin["Unit"]["Wants"] == "drop-cosmic-dconf-profile.service"
