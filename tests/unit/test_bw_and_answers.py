from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

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


def isolated_machine(tmp_path, monkeypatch):
    from importlib.machinery import SourceFileLoader

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("DOTFILES_REPO", str(REPO))
    monkeypatch.delenv("MACHINE_SSH_KEY", raising=False)
    monkeypatch.delenv("MACHINE_PROFILE", raising=False)
    monkeypatch.delenv("SUDO_USER", raising=False)
    cli = SourceFileLoader("machine_keys", str(MACHINE)).load_module()
    monkeypatch.setattr(cli, "in_docker", lambda: False)
    monkeypatch.setattr(cli, "is_tty", lambda: False)
    return cli, cli.Machine()


@pytest.mark.parametrize(
    "user,expected",
    [
        ("dci2lr", "work-laptop"),
        ("abc12def", "work-laptop"),
        ("ditschi", "home-laptop"),
    ],
)
def test_profile_default_matches_work_account(tmp_path, monkeypatch, user, expected):
    cli, machine = isolated_machine(tmp_path, monkeypatch)
    monkeypatch.setattr(cli.getpass, "getuser", lambda: user)
    assert machine.default_profile() == expected
    machine.write_profile("home-server", ["zsh-full"], [])
    monkeypatch.setenv("MACHINE_PROFILE", "work-laptop")
    assert machine.default_profile() == "home-server"


def test_container_default_beats_work_username(tmp_path, monkeypatch):
    cli, machine = isolated_machine(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "in_docker", lambda: True)
    monkeypatch.setattr(cli.getpass, "getuser", lambda: "dci2lr")
    assert machine.default_profile() == "container"


def generate_test_key(path, passphrase=""):
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", passphrase, "-f", str(path)],
        check=True,
        capture_output=True,
    )


def test_existing_ssh_key_is_reused_without_generation(tmp_path, monkeypatch):
    cli, machine = isolated_machine(tmp_path, monkeypatch)
    key = tmp_path / ".ssh/id_ed25519"
    key.parent.mkdir()
    generate_test_key(key)
    original = key.read_bytes()
    public = Path(str(key) + ".pub")
    monkeypatch.setattr(
        cli, "run", lambda *_args, **_kwargs: pytest.fail("must not run keygen")
    )
    assert machine.ensure_host_ssh_key() == public
    assert key.read_bytes() == original
    assert not machine.host_key_paths()[0].exists()


def test_ambiguous_existing_ssh_keys_skip_generation(tmp_path, monkeypatch):
    cli, machine = isolated_machine(tmp_path, monkeypatch)
    (tmp_path / ".ssh").mkdir()
    for name in ("custom-one", "custom-two"):
        generate_test_key(tmp_path / ".ssh" / name)
    monkeypatch.setattr(
        cli, "run", lambda *_args, **_kwargs: pytest.fail("must not run keygen")
    )
    assert machine.ensure_host_ssh_key() is None


def test_encrypted_key_without_public_file_is_kept(tmp_path, monkeypatch):
    cli, machine = isolated_machine(tmp_path, monkeypatch)
    key = tmp_path / ".ssh/id_ed25519"
    key.parent.mkdir()
    generate_test_key(key, "test-only passphrase")
    original = key.read_bytes()
    Path(str(key) + ".pub").unlink()
    calls = []

    def locked_key(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 1, "", "locked")

    monkeypatch.setattr(cli, "run", locked_key)
    assert machine.ensure_host_ssh_key() is None
    assert len(calls) == 1 and "-y" in calls[0] and "-P" in calls[0]
    assert key.read_bytes() == original
