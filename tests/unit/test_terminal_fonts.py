"""Terminal font settings: only the font key changes."""

from __future__ import annotations

import subprocess
import sys

from package_sets import REPO

sys.path.insert(0, str(REPO))

from machine_cli import terminal_fonts as tf  # noqa: E402


def test_vscode_key_is_added_keeping_comments_and_keys():
    old = '{\n    // my theme\n    "workbench.colorTheme": "Dark",\n    "a": 1\n}\n'
    new = tf.with_vscode_font(old)
    assert '"terminal.integrated.fontFamily": "FiraCode Nerd Font Mono",' in new
    assert "// my theme" in new and '"a": 1' in new
    assert tf.with_vscode_font(new) == new


def test_vscode_key_is_replaced_and_empty_object_handled():
    old = '{"terminal.integrated.fontFamily": "Meslo", "a": 1}'
    assert tf.with_vscode_font(old) == (
        '{"terminal.integrated.fontFamily": "FiraCode Nerd Font Mono", "a": 1}'
    )
    assert tf.with_vscode_font("{}") == (
        '{\n    "terminal.integrated.fontFamily": "FiraCode Nerd Font Mono"\n}'
    )
    assert tf.with_vscode_font("").startswith("{")


def test_vscode_not_touched_without_user_dir(tmp_path):
    assert tf.set_vscode_font(tmp_path) is False
    assert not (tmp_path / ".config").exists()


def test_vscode_settings_file_is_created_in_existing_user_dir(tmp_path):
    user = tmp_path / ".config/Code/User"
    user.mkdir(parents=True)
    assert tf.set_vscode_font(tmp_path) is True
    assert "FiraCode Nerd Font Mono" in (user / "settings.json").read_text()


def test_ddterm_font_keeps_the_size():
    assert tf.ddterm_font("'Monospace Regular 12'") == "FiraCode Nerd Font Mono 12"
    assert tf.ddterm_font("") == "FiraCode Nerd Font Mono 10"


def _fake_gsettings(monkeypatch, values):
    commands: list[list[str]] = []

    def run(args, **_kw):
        commands.append(list(args))
        if args[3] == "get":
            return subprocess.CompletedProcess(
                args, 0, stdout=values[args[5]], stderr=""
            )
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(tf.system, "run", run)
    monkeypatch.setattr(tf.system, "have", lambda name: name == "gsettings")
    return commands


def test_ddterm_not_touched_without_its_schema(tmp_path, monkeypatch):
    commands = _fake_gsettings(monkeypatch, {})
    assert tf.set_ddterm_font(tmp_path) is False
    assert commands == []


def test_ddterm_font_is_set_with_the_extension_schema(tmp_path, monkeypatch):
    (tmp_path / tf.DDTERM_SCHEMA_DIR).mkdir(parents=True)
    commands = _fake_gsettings(
        monkeypatch,
        {"custom-font": "'Monospace Regular 12'\n", "use-system-font": "true\n"},
    )
    assert tf.set_ddterm_font(tmp_path) is True
    base = ["gsettings", "--schemadir", str(tmp_path / tf.DDTERM_SCHEMA_DIR)]
    assert [
        *base, "set", tf.DDTERM_SCHEMA, "custom-font", "FiraCode Nerd Font Mono 12"
    ] in commands  # fmt: skip
    assert [*base, "set", tf.DDTERM_SCHEMA, "use-system-font", "false"] in commands


def test_ddterm_font_already_set_writes_nothing(tmp_path, monkeypatch):
    (tmp_path / tf.DDTERM_SCHEMA_DIR).mkdir(parents=True)
    commands = _fake_gsettings(
        monkeypatch,
        {"custom-font": "'FiraCode Nerd Font Mono 12'\n", "use-system-font": "false\n"},
    )
    assert tf.set_ddterm_font(tmp_path) is False
    assert not any("set" in c for c in commands)
