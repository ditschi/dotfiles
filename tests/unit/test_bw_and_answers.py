from __future__ import annotations

import getpass
import json
import os
import subprocess
from pathlib import Path

import pytest

from package_sets import REPO

MACHINE = REPO / "machine_cli/machine"


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
    monkeypatch.setenv(
        "MISE_LOCAL_CONFIG", str(home / ".config/mise/config.local.toml")
    )
    monkeypatch.setenv("MACHINE_STATE_DIR", str(home / ".local/share/machine"))

    cli = SourceFileLoader("machine_entry", str(MACHINE)).load_module()
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
    (repo / "home" / "core").mkdir(parents=True)
    (repo / "home" / "core" / ".zshrc").write_text("#z\n", encoding="utf-8")
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
    monkeypatch.setenv(
        "MISE_LOCAL_CONFIG", str(home / ".config/mise/config.local.toml")
    )
    monkeypatch.setenv("MACHINE_STATE_DIR", str(home / ".local/share/machine"))

    cli = SourceFileLoader("machine_entry", str(MACHINE)).load_module()
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
    monkeypatch.setattr(cli.system, "in_docker", lambda: False)
    monkeypatch.setattr(cli.system, "is_tty", lambda: False)
    # No versioned host file may match, whatever machine the tests run on.
    monkeypatch.setattr(cli.system, "hostname_short", lambda: "unit-test-host")
    return cli, cli.Machine()


def test_save_bitwarden_settings_preserves_other_local_exports(tmp_path, monkeypatch):
    _, machine = isolated_machine(tmp_path, monkeypatch)
    path = tmp_path / ".env.local"
    path.write_text(
        "# local settings\nexport OTHER='keep me'\n"
        "export BW_SESSION=old\nBW_SESSION=duplicate\n"
        "export NODE_USE_ENV_PROXY=0\n"
    )
    monkeypatch.setenv("BW_SESSION", "new-session")
    monkeypatch.setenv("NODE_EXTRA_CA_CERTS", "/tmp/CA bundle.pem")
    monkeypatch.setenv("NODE_USE_ENV_PROXY", "1")
    machine.save_bitwarden_local_settings()
    first = path.read_bytes()
    machine.save_bitwarden_local_settings()
    assert path.read_bytes() == first
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.read_text().count("BW_SESSION=") == 1
    result = subprocess.run(
        [
            "bash",
            "-c",
            '. "$1"; printf "%s\\n" "$BW_SESSION" "$OTHER" '
            '"$NODE_EXTRA_CA_CERTS" "$NODE_USE_ENV_PROXY"',
            "_",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.splitlines() == [
        "new-session",
        "keep me",
        "/tmp/CA bundle.pem",
        "1",
    ]


@pytest.mark.parametrize("unattended,tty", [(True, True), (False, False)])
def test_bitwarden_setup_never_prompts_unattended(
    tmp_path, monkeypatch, unattended, tty
):
    cli, machine = isolated_machine(tmp_path, monkeypatch)
    machine.unattended = unattended
    monkeypatch.setattr(cli.system, "is_tty", lambda: tty)
    monkeypatch.setattr("builtins.input", lambda *_: pytest.fail("must not prompt"))
    assert not machine.setup_bitwarden()
    assert not (tmp_path / ".env.local").exists()


@pytest.mark.parametrize("save", [False, True])
def test_bitwarden_setup_configures_server_and_saves_only_with_consent(
    tmp_path, monkeypatch, save
):
    cli, machine = isolated_machine(tmp_path, monkeypatch)
    monkeypatch.setattr(cli.system, "is_tty", lambda: True)
    monkeypatch.setattr(cli.system, "have", lambda _: True)
    answers = iter([True, save])
    monkeypatch.setattr(cli.system, "prompt_yes_no", lambda *_: next(answers))
    monkeypatch.setattr("builtins.input", lambda *_: "https://vault.example.test")
    commands = []

    def run(args, **kwargs):
        commands.append(args)
        output = (
            json.dumps(
                {"status": "unauthenticated", "serverUrl": "https://bitwarden.com"}
            )
            if args == ["bw", "status"]
            else ""
        )
        return subprocess.CompletedProcess(args, 0, output, "")

    def unlock(**kwargs):
        assert kwargs == {"allow_login": True}
        monkeypatch.setenv("BW_SESSION", "test-unlock-token")
        return True

    monkeypatch.setattr(cli.system, "run", run)
    monkeypatch.setattr(machine, "unlock_bitwarden", unlock)
    assert machine.setup_bitwarden()
    assert ["bw", "config", "server", "https://vault.example.test"] in commands
    path = tmp_path / ".env.local"
    assert path.exists() == save
    if save:
        assert "BW_SESSION=test-unlock-token" in path.read_text()
        assert path.stat().st_mode & 0o777 == 0o600


def test_bitwarden_setup_keeps_local_file_when_unlock_fails(tmp_path, monkeypatch):
    cli, machine = isolated_machine(tmp_path, monkeypatch)
    path = tmp_path / ".env.local"
    original = "export BW_SESSION=existing\nexport OTHER=keep\n"
    path.write_text(original)
    monkeypatch.setattr(cli.system, "is_tty", lambda: True)
    monkeypatch.setattr(cli.system, "have", lambda _: True)
    monkeypatch.setattr(cli.system, "prompt_yes_no", lambda *_: True)
    monkeypatch.setattr(
        cli.system,
        "run",
        lambda args, **kwargs: subprocess.CompletedProcess(
            args, 0, '{"status":"locked","serverUrl":"https://vault.example.test"}', ""
        ),
    )
    monkeypatch.setattr(machine, "unlock_bitwarden", lambda **_: False)
    assert not machine.setup_bitwarden()
    assert path.read_text() == original


def test_bitwarden_setup_refreshes_expired_local_session(tmp_path, monkeypatch):
    cli, machine = isolated_machine(tmp_path, monkeypatch)
    path = tmp_path / ".env.local"
    path.write_text("export BW_SESSION=expired\n")
    monkeypatch.setattr(cli.system, "is_tty", lambda: True)
    monkeypatch.setattr(cli.system, "have", lambda _: True)
    monkeypatch.setattr(cli.system, "prompt_yes_no", lambda *_: True)
    commands = []

    def run(args, **kwargs):
        commands.append(args)
        if args == ["bw", "status"]:
            output = '{"status":"locked","serverUrl":"https://vault.example.test"}'
        elif args == ["bw", "unlock", "--raw"]:
            assert "BW_SESSION" not in os.environ
            output = "refreshed-session"
        else:
            output = ""
        return subprocess.CompletedProcess(args, 0, output, "")

    monkeypatch.setattr(cli.system, "run", run)
    assert machine.setup_bitwarden()
    assert ["bw", "unlock", "--raw"] in commands
    assert "BW_SESSION=refreshed-session" in path.read_text()


def test_bitwarden_status_keeps_working_network_settings(tmp_path, monkeypatch):
    cli, machine = isolated_machine(tmp_path, monkeypatch)
    monkeypatch.delenv("NODE_EXTRA_CA_CERTS", raising=False)
    monkeypatch.delenv("NODE_USE_ENV_PROXY", raising=False)
    monkeypatch.setenv("HTTPS_PROXY", "http://localhost:3128")
    monkeypatch.setattr(
        cli.system,
        "run",
        lambda args, **kwargs: subprocess.CompletedProcess(
            args, 0, '{"status":"locked"}', ""
        ),
    )
    monkeypatch.setattr(
        cli.system, "prompt_yes_no", lambda *_: pytest.fail("no workaround needed")
    )
    assert machine.bitwarden_setup_status()["status"] == "locked"
    assert "NODE_EXTRA_CA_CERTS" not in os.environ
    assert "NODE_USE_ENV_PROXY" not in os.environ


@pytest.mark.parametrize(
    "error,key,value",
    [
        ("getaddrinfo ENOTFOUND vault.example.test", "NODE_USE_ENV_PROXY", "1"),
        (
            "unable to get local issuer certificate",
            "NODE_EXTRA_CA_CERTS",
            "/etc/ssl/certs/ca-certificates.crt",
        ),
    ],
)
@pytest.mark.parametrize("consent", [True, False])
def test_bitwarden_status_offers_only_matching_workaround(
    tmp_path, monkeypatch, error, key, value, consent
):
    cli, machine = isolated_machine(tmp_path, monkeypatch)
    if key == "NODE_EXTRA_CA_CERTS" and not Path(value).is_file():
        pytest.skip("Ubuntu CA bundle not installed")
    monkeypatch.delenv("NODE_EXTRA_CA_CERTS", raising=False)
    monkeypatch.delenv("NODE_USE_ENV_PROXY", raising=False)
    monkeypatch.setenv("HTTPS_PROXY", "http://localhost:3128")
    calls = []
    prompts = []

    def run(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(
            args, 0, '{"status":"locked"}', error if len(calls) == 1 else ""
        )

    def prompt(question, default):
        prompts.append(question)
        assert not default
        return consent

    monkeypatch.setattr(cli.system, "run", run)
    monkeypatch.setattr(cli.system, "prompt_yes_no", prompt)
    if consent:
        assert machine.bitwarden_setup_status()["status"] == "locked"
        assert os.environ[key] == value
        assert len(calls) == 2
    else:
        with pytest.raises(SystemExit):
            machine.bitwarden_setup_status()
        assert key not in os.environ
        assert len(calls) == 1
    assert len(prompts) == 1
    assert not (tmp_path / ".env.local").exists()


@pytest.mark.parametrize("fail_login", [False, True])
def test_bitwarden_login_captures_token_without_printing(
    tmp_path, monkeypatch, capsys, fail_login
):
    cli, machine = isolated_machine(tmp_path, monkeypatch)
    monkeypatch.setattr(cli.system, "is_tty", lambda: True)
    monkeypatch.setattr(cli.system, "have", lambda _: True)
    monkeypatch.setattr("builtins.input", lambda _: "")
    commands = []
    login = ["bw", "login", "chris@ditschers.de", "--raw"]

    def run(args, **kwargs):
        commands.append(args)
        assert kwargs.get("capture") or kwargs.get("interactive_stdout")
        if args == ["bw", "status"]:
            output = '{"status":"unauthenticated"}'
        elif args == login:
            return subprocess.CompletedProcess(
                args, 1 if fail_login else 0, "never-print-this-token", ""
            )
        else:
            output = ""
        return subprocess.CompletedProcess(args, 0, output, "")

    monkeypatch.setattr(cli.system, "run", run)
    assert machine.unlock_bitwarden(allow_login=True) == (not fail_login)
    assert login in commands
    if not fail_login:
        assert os.environ["BW_SESSION"] == "never-print-this-token"
    output = capsys.readouterr()
    assert "never-print-this-token" not in output.out + output.err


@pytest.mark.parametrize(
    "user,expected",
    [
        ("dci2lr", "work-machine"),
        ("abc12def", "work-machine"),
        ("ditschi", "home-laptop"),
    ],
)
def test_profile_default_matches_work_account(tmp_path, monkeypatch, user, expected):
    cli, machine = isolated_machine(tmp_path, monkeypatch)
    monkeypatch.setattr(getpass, "getuser", lambda: user)
    assert machine.default_profile() == expected
    machine.write_profile("home-server", ["zsh-full"], [])
    monkeypatch.setenv("MACHINE_PROFILE", "work-machine")
    assert machine.default_profile() == "home-server"


def test_container_default_beats_work_username(tmp_path, monkeypatch):
    cli, machine = isolated_machine(tmp_path, monkeypatch)
    monkeypatch.setattr(cli.system, "in_docker", lambda: True)
    monkeypatch.setattr(getpass, "getuser", lambda: "dci2lr")
    assert machine.default_profile() == "container"


def test_container_ignores_saved_profile_unless_overridden(tmp_path, monkeypatch):
    cli, machine = isolated_machine(tmp_path, monkeypatch)
    machine.write_profile("work-machine", ["zsh-full"], [])
    monkeypatch.setattr(cli.system, "in_docker", lambda: True)
    assert machine.default_profile() == "container"
    monkeypatch.setenv("MACHINE_PROFILE_OVERRIDE", "home-server")
    assert machine.default_profile() == "home-server"


def test_company_user_regex_is_identical_in_cli_and_shell():
    pattern = "[a-zA-Z]{3}[0-9]{1,2}[a-zA-Z]{2,3}"
    assert pattern in (REPO / "home/core/.zsh/machine-profile.sh").read_text()
    assert pattern in (REPO / "machine_cli/profile.py").read_text()


@pytest.mark.parametrize(
    "saved,env,user,expected",
    [
        ("work-machine", {}, "tester", "work-machine|true"),
        ("home-laptop", {}, "abc1de", "home-laptop|true"),
        ("work-machine", {"MACHINE_IN_DOCKER": "1"}, "tester", "container|"),
        ("home-laptop", {"MACHINE_IN_DOCKER": "1"}, "abc1de", "container|"),
        (
            "home-laptop",
            {"MACHINE_IN_DOCKER": "1", "MACHINE_PROFILE_OVERRIDE": "work-machine"},
            "tester",
            "work-machine|true",
        ),
    ],
)
def test_shell_profile_follows_docker_rule(tmp_path, saved, env, user, expected):
    profile = tmp_path / ".config/machine/profile.yml"
    profile.parent.mkdir(parents=True)
    profile.write_text(f"---\nprofile: {saved}\n")
    script = REPO / "home/core/.zsh/machine-profile.sh"
    result = subprocess.run(
        [
            "sh",
            "-c",
            '. "$1"; echo "$MACHINE_PROFILE|${WORK_SETUP:-}"',
            "_",
            str(script),
        ],
        env={"PATH": os.environ["PATH"], "HOME": str(tmp_path), "USER": user, **env},
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == expected


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
        cli.system, "run", lambda *_args, **_kwargs: pytest.fail("must not run keygen")
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
        cli.system, "run", lambda *_args, **_kwargs: pytest.fail("must not run keygen")
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

    monkeypatch.setattr(cli.system, "run", locked_key)
    assert machine.ensure_host_ssh_key() is None
    assert len(calls) == 1 and "-y" in calls[0] and "-P" in calls[0]
    assert key.read_bytes() == original


@pytest.mark.parametrize("valid", [True, False])
def test_unlock_reuses_a_saved_session_unless_expired(tmp_path, monkeypatch, valid):
    cli, machine = isolated_machine(tmp_path, monkeypatch)
    (tmp_path / ".env.local").write_text("export BW_SESSION=saved\n")
    monkeypatch.setattr(cli.system, "is_tty", lambda: True)
    monkeypatch.setattr(cli.system, "have", lambda _: True)
    commands = []

    def run(args, **kwargs):
        commands.append(args)
        if args == ["bw", "status"]:
            unlocked = valid or os.environ.get("BW_SESSION") == "fresh"
            output = json.dumps({"status": "unlocked" if unlocked else "locked"})
        elif args == ["bw", "unlock", "--raw"]:
            output = "fresh"
        else:
            output = ""
        return subprocess.CompletedProcess(args, 0, output, "")

    monkeypatch.setattr(cli.system, "run", run)
    assert machine.unlock_bitwarden()
    assert (["bw", "unlock", "--raw"] in commands) == (not valid)
    assert os.environ["BW_SESSION"] == ("saved" if valid else "fresh")


@pytest.mark.parametrize("answer", [True, False])
def test_fresh_unlock_offers_to_save_the_session_once(tmp_path, monkeypatch, answer):
    cli, machine = isolated_machine(tmp_path, monkeypatch)
    monkeypatch.delenv("BW_SESSION", raising=False)
    monkeypatch.setattr(cli.system, "is_tty", lambda: True)
    monkeypatch.setattr(cli.system, "have", lambda _: True)
    questions = []
    monkeypatch.setattr(
        cli.system, "prompt_yes_no", lambda q, d: questions.append(d) or answer
    )

    def run(args, **kwargs):
        output = "fresh" if args == ["bw", "unlock", "--raw"] else '{"status":"locked"}'
        return subprocess.CompletedProcess(args, 0, output, "")

    monkeypatch.setattr(cli.system, "run", run)
    assert machine.unlock_bitwarden()
    machine.offer_saving_bitwarden_session()
    machine.offer_saving_bitwarden_session()  # asked once per run

    assert questions == [False]  # default: no
    saved = (tmp_path / ".env.local").read_text() if answer else ""
    assert ("BW_SESSION=fresh" in saved) == answer


def test_no_save_offer_without_a_fresh_unlock(tmp_path, monkeypatch):
    cli, machine = isolated_machine(tmp_path, monkeypatch)
    monkeypatch.setattr(cli.system, "is_tty", lambda: True)
    monkeypatch.setattr(
        cli.system, "prompt_yes_no", lambda *_a: pytest.fail("must not ask")
    )
    machine.offer_saving_bitwarden_session()
