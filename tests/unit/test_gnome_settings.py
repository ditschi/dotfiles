"""Shared GNOME extension settings must not carry host-specific or runtime-state keys."""

from __future__ import annotations

import re

from package_sets import REPO

SETTINGS = REPO / "home/gnome/.config/machine/dconf"
FORBIDDEN = re.compile(
    r"^(available-.*|excluded-.*|storage-main|overridden-settings|last-version-installed)=",
    re.M,
)


def test_settings_files_exist_for_the_extensions():
    names = {p.stem for p in SETTINGS.glob("*.ini")}
    assert {
        "astra-monitor",
        "clipboard-indicator",
        "gtile",
        "tiling-assistant",
    } <= names


def test_no_host_specific_keys_are_shipped():
    for ini in SETTINGS.glob("*.ini"):
        assert not FORBIDDEN.search(ini.read_text()), ini.name


def test_clipboard_history_is_150():
    assert "history-size=150" in (SETTINGS / "clipboard-indicator.ini").read_text()
