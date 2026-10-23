"""Terminal font settings: only the font key changes."""

from __future__ import annotations

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


def test_guake_font_keeps_the_size():
    assert tf.guake_font("'Monospace 12'") == "FiraCode Nerd Font Mono 12"
    assert tf.guake_font("") == "FiraCode Nerd Font Mono 10"
