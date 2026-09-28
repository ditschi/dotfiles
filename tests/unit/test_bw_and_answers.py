from __future__ import annotations

import json
import os
from pathlib import Path


from package_sets import REPO

MACHINE = REPO / "home/dot_local/bin/executable_machine"


def test_fake_bw_publish_ssh_public_key(tmp_path: Path, fake_bw, monkeypatch):
    from importlib.machinery import SourceFileLoader

    bw, store = fake_bw
    repo = tmp_path / "dotfiles"
    (repo / "home").mkdir(parents=True)
    (repo / ".git").mkdir()
    home = tmp_path / "home"
    home.mkdir()
    (home / ".ssh").mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("DOTFILES_REPO", str(repo))
    monkeypatch.setenv("PATH", f"{bw.parent}:{os.environ.get('PATH', '')}")
    monkeypatch.setenv("BW_SESSION", "fake-session")
    monkeypatch.setenv(
        "MACHINE_PROFILE_FILE", str(home / ".config/machine/profile.yml")
    )
    monkeypatch.setenv("CHEZMOI_CONFIG", str(home / ".config/chezmoi/chezmoi.yaml"))
    monkeypatch.setenv("MACHINE_STATE_DIR", str(home / ".local/share/machine"))

    cli = SourceFileLoader("machine_cli", str(MACHINE)).load_module()
    machine = cli.Machine()
    machine.write_profile("home-laptop", ["zsh-full", "ssh-host-key"], [])
    # Pretend unlock already done
    assert machine.publish_ssh_key(store_private=False) == 0
    data = json.loads(store.read_text())
    items = data.get("items", {})
    # hostname from socket may vary; find ssh/home item
    matching = [k for k in items if k.startswith("ssh/home/hosts/")]
    assert matching
    fields = {f["name"]: f["value"] for f in items[matching[0]]["fields"]}
    assert "public_key" in fields
    assert "private_key" not in fields
    assert fields["public_key"].startswith("ssh-ed25519")


def test_setup_rerun_keeps_saved_features_as_defaults(tmp_path: Path, monkeypatch):
    from importlib.machinery import SourceFileLoader

    repo = tmp_path / "dotfiles"
    (repo / "home").mkdir(parents=True)
    (repo / "home" / "dot_zshrc").write_text("#z\n", encoding="utf-8")
    (repo / ".git").mkdir()
    home = tmp_path / "home"
    home.mkdir()
    profile = home / ".config/machine/profile.yml"
    profile.parent.mkdir(parents=True)
    profile.write_text(
        "---\nprofile: home-laptop\nfeatures:\n  - zsh-full\n  - monitoring\nssh_allow_from: []\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("DOTFILES_REPO", str(repo))
    monkeypatch.setenv("MACHINE_PROFILE_FILE", str(profile))
    monkeypatch.setenv("CHEZMOI_CONFIG", str(home / ".config/chezmoi/chezmoi.yaml"))
    monkeypatch.setenv("MACHINE_STATE_DIR", str(home / ".local/share/machine"))

    cli = SourceFileLoader("machine_cli", str(MACHINE)).load_module()
    machine = cli.Machine()
    assert machine.saved_features() == ["zsh-full", "monitoring"]
