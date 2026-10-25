"""Feature table: stricter value wins, defaults, menu and dotfile groups."""

from __future__ import annotations

import sys

from package_sets import REPO

sys.path.insert(0, str(REPO))

from machine_cli import features  # noqa: E402


def test_stricter_value_wins_docker_on_work_desktop():
    assert features.levels("work", "desktop")["docker"] == features.OPTIONAL


def test_excluded_on_server_wins_thunderbird():
    assert features.levels("private", "server")["thunderbird"] == features.EXCLUDED


def test_new_private_desktop():
    defaults = features.defaults("private", "desktop")
    offered = features.allowed("private", "desktop")
    for name in ("monitoring", "sshd-home", "syncthing", "thunderbird", "docker"):
        assert name in defaults
    assert "claude-code" in defaults
    for name in ("copilot-cli", "tailscale", "opencode"):
        assert name in offered and name not in defaults
    assert "kerberos" not in offered and "azure-cli" not in offered


def test_new_work_desktop():
    defaults = features.defaults("work", "desktop")
    offered = features.allowed("work", "desktop")
    for name in ("copilot-cli", "kerberos", "azure-cli", "claude-code"):
        assert name in defaults
    assert "docker" in offered and "docker" not in defaults
    for name in ("unattended-upgrades", "monitoring", "sshd-home", "thunderbird"):
        assert name not in offered


def test_new_private_server():
    defaults = features.defaults("private", "server")
    offered = features.allowed("private", "server")
    assert "etckeeper" in defaults
    for name in ("gnome", "fonts", "thunderbird", "syncthing", "cosmic"):
        assert name not in offered
    assert "tailscale" in offered and "tailscale" not in defaults


def test_container_without_context():
    assert features.defaults("", "container") == ["zsh-full"]
    offered = features.allowed("", "container")
    assert set(offered) == {"zsh-full", "claude-code", "copilot-cli", "opencode"}


def test_split_drops_excluded_and_unknown():
    kept, dropped = features.split(
        ["zsh-full", "monitoring", "starship"], "work", "desktop"
    )
    assert kept == ["zsh-full"]
    assert dropped == ["monitoring", "starship"]


def test_dotfile_groups_from_table():
    groups = features.dotfile_groups(
        "private", "desktop", ["thunderbird", "claude-code", "copilot-cli"]
    )
    assert groups[:3] == ["core", "prompt", "systemd"]
    assert "work" not in groups
    assert groups.count("openspec") == 1
    assert {"thunderbird", "claude", "copilot"} <= set(groups)


def test_dotfile_groups_work_and_container():
    assert "work" in features.dotfile_groups("work", "desktop")
    container = features.dotfile_groups("", "container", ["claude-code"])
    assert "systemd" not in container and "claude" in container


def test_every_row_uses_known_keys_and_values():
    keys = {"help", "groups", *features.CONTEXTS, *features.DEVICES}
    values = {features.DEFAULT, features.OPTIONAL, features.EXCLUDED}
    for name, row in features.load_table().items():
        assert set(row) <= keys, name
        assert row.get("help"), name
        for key in (*features.CONTEXTS, *features.DEVICES):
            assert row.get(key, features.DEFAULT) in values, (name, key)


def test_groups_of_features_exist_in_mise_toml():
    text = (REPO / "mise.toml").read_text()
    for row in features.load_table().values():
        for group in row.get("groups") or []:
            assert f"[dotfile_groups.{group}]" in text, group


def _ansible_machine_features(context, device, names):
    """Render the `machine_features` group var the way Ansible templates it."""
    import ast

    import jinja2
    import yaml

    data = yaml.safe_load(features.TABLE_PATH.read_text())
    env = jinja2.Environment(extensions=["jinja2.ext.do"])
    text = env.from_string(data["machine_features"]).render(
        feature_table=data["feature_table"],
        context=context,
        device=device,
        features=names,
    )
    return ast.literal_eval(text.strip())


def test_ansible_filter_matches_resolver():
    names = list(features.load_table()) + ["starship"]
    for context in ["", *features.CONTEXTS]:
        for device in features.DEVICES:
            kept, _ = features.split(names, context, device)
            assert _ansible_machine_features(context, device, names) == kept, (
                context,
                device,
            )


def test_host_without_llm_features_gets_no_llm_group():
    groups = features.dotfile_groups("private", "server", ["zsh-full", "docker"])
    assert not {"claude", "copilot", "opencode", "openspec"} & set(groups)


def test_llm_tools_are_not_in_core():
    core = REPO / "home" / "core" / ".config" / "mise" / "conf.d"
    text = "".join(path.read_text() for path in core.glob("*.toml"))
    for tool in ("claude-code", "@github/copilot", "opencode", "openspec"):
        assert tool not in text


def test_laptop_and_swap_features():
    for context in features.CONTEXTS:
        defaults = features.defaults(context, "desktop")
        for name in (
            "lid-switch",
            "power-profile-switch",
            "battery-charge-limit",
            "zram-swap",
        ):
            assert name in defaults
        server = features.allowed(context, "server")
        assert "zram-swap" in features.defaults(context, "server")
        for name in ("lid-switch", "power-profile-switch", "battery-charge-limit"):
            assert name not in server
    container = features.allowed("", "container")
    assert "zram-swap" not in container and "lid-switch" not in container
    assert "thinkpad-tuning" not in features.load_table()
