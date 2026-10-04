from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from package_sets import REPO

SHARED = REPO / "home/dot_gitconfig"
HOST_ONLY = (
    r"^(user\.(name|email|signingkey)|gpg\.|commit\.gpgsign|tag\.gpgsign"
    r"|safe\.|credential\.|https?\.|core\.sshcommand)"
)


def _git(
    *args: str, env: dict | None = None, cwd: Path | None = None
) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], env=env, cwd=cwd, capture_output=True, text=True
    )


def test_shared_gitconfig_has_no_host_only_settings():
    res = _git("config", "-f", str(SHARED), "--no-includes", "--get-regexp", HOST_ONLY)
    assert res.stdout == "", f"move to ~/.gitconfig.local:\n{res.stdout}"


def test_local_include_is_last_so_it_wins():
    res = _git("config", "-f", str(SHARED), "--no-includes", "--list")
    assert res.stdout.strip().splitlines()[-1] == "include.path=~/.gitconfig.local"


def test_gitconfig_relocation_preserves_local_overrides_and_multivalues(tmp_path):
    shared = tmp_path / "shared"
    shared.write_text(
        "[user]\n email = shared@example.com\n useConfigOnly = true\n"
        "[credential]\n helper = first\n helper = second\n"
        "[commit]\n gpgSign\n"
        "[alias]\n st = status\n[include]\n path = ~/.gitconfig.local\n"
    )
    local = tmp_path / ".gitconfig.local"
    local.write_text("[user]\n email = local@example.com\n")
    env = {**os.environ, "HOME": str(tmp_path)}
    env.pop("CI", None)
    command = [
        "python3",
        str(REPO / "machine/gitconfig.py"),
        "--shared",
        str(shared),
        "--local",
        str(local),
    ]
    rejected = subprocess.run(
        [*command, "--check"], env=env, capture_output=True, text=True
    )
    assert rejected.returncode == 1
    assert "shared@example.com" not in rejected.stdout
    assert "email = shared@example.com" in shared.read_text()
    subprocess.run(command, env=env, check=True)
    assert _git(
        "config", "-f", str(local), "--get-all", "credential.helper"
    ).stdout.splitlines() == ["first", "second"]
    assert (
        _git("config", "-f", str(local), "user.email").stdout.strip()
        == "local@example.com"
    )
    assert (
        _git("config", "-f", str(local), "--bool", "commit.gpgSign").stdout.strip()
        == "true"
    )
    assert (
        _git("config", "-f", str(shared), "user.useConfigOnly").stdout.strip() == "true"
    )
    assert _git("config", "-f", str(shared), "alias.st").stdout.strip() == "status"
    assert local.stat().st_mode & 0o777 == 0o600
    backups = list(
        (tmp_path / ".local/share/machine/gitconfig-backup").glob("*/gitconfig")
    )
    assert len(backups) == 1
    assert backups[0].stat().st_mode & 0o777 == 0o600
    subprocess.run([*command, "--check"], env=env, check=True)
    subprocess.run(command, env=env, check=True)
    assert len(list(backups[0].parent.parent.iterdir())) == 1


def test_gitconfig_check_rejects_malformed_config(tmp_path):
    shared = tmp_path / "shared"
    shared.write_text("[broken\n")
    result = subprocess.run(
        [
            "python3",
            str(REPO / "machine/gitconfig.py"),
            "--check",
            "--shared",
            str(shared),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1


def test_gitconfig_hook_in_ci_checks_without_moving_settings(tmp_path):
    shared = tmp_path / "shared"
    original = "[credential]\n helper = store\n"
    shared.write_text(original)
    local = tmp_path / ".gitconfig.local"
    result = subprocess.run(
        [
            "python3",
            str(REPO / "machine/gitconfig.py"),
            "--shared",
            str(shared),
            "--local",
            str(local),
        ],
        env={**os.environ, "HOME": str(tmp_path), "CI": "true"},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert shared.read_text() == original
    assert not local.exists()


@pytest.mark.parametrize("operation", ["update", "commit"])
def test_machine_commands_move_shared_host_settings_before_git(
    tmp_path, monkeypatch, operation
):
    from test_bw_and_answers import isolated_machine
    from types import SimpleNamespace

    cli, machine = isolated_machine(tmp_path, monkeypatch)
    monkeypatch.delenv("CI", raising=False)
    repo = tmp_path / "repo"
    (repo / "home").mkdir(parents=True)
    (repo / "machine").mkdir()
    shutil.copy2(REPO / "machine/gitconfig.py", repo / "machine/gitconfig.py")
    shared = repo / "home/dot_gitconfig"
    shared.write_text("[user]\n email = work@example.com\n")
    machine.repo = repo
    machine.chezmoi_source = repo / "home"
    real_run = cli.system.run
    calls = []

    def fake_git(args, **kwargs):
        if args[0] != "git":
            return real_run(args, **kwargs)
        assert "email" not in shared.read_text()
        assert "work@example.com" in (tmp_path / ".gitconfig.local").read_text()
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(cli.system, "run", fake_git)
    monkeypatch.setattr(machine, "handle_layout_gate", lambda **kwargs: None)
    monkeypatch.setattr(machine, "git_dirty", lambda: False)
    monkeypatch.setattr(machine, "sync_host_profile_from_repo", lambda: False)
    monkeypatch.setattr(machine, "cmd_env_pull", lambda: 0)
    monkeypatch.setattr(machine, "run_chezmoi_apply", lambda: None)
    if operation == "update":
        assert machine.cmd_update(SimpleNamespace(force=False, system=False)) == 0
        assert any("pull" in args for args in calls)
    else:
        assert machine.cmd_commit(SimpleNamespace(message="test")) == 0
        assert any("commit" in args for args in calls)


@pytest.mark.skipif(shutil.which("chezmoi") is None, reason="chezmoi not installed")
@pytest.mark.parametrize(
    "profile, email",
    [
        ("work-laptop", "christian.ditscher@de.bosch.com"),
        ("home-laptop", "chris@ditscher.me"),
        ("container", "chris@ditscher.me"),
    ],
)
def test_default_identity_per_profile(tmp_path: Path, profile: str, email: str):
    home = tmp_path / "home"
    home.mkdir()
    cfg = tmp_path / "chezmoi.yaml"
    cfg.write_text(
        f"sourceDir: {REPO / 'home'}\nmode: symlink\ndata:\n  profile: {profile}\n"
    )
    targets = [str(home / ".gitconfig"), str(home / ".gitconfig.local")]
    subprocess.run(
        [
            "chezmoi",
            "--config",
            str(cfg),
            "--persistent-state",
            str(tmp_path / "state.boltdb"),
            "-D",
            str(home),
            "apply",
            "--force",
            *targets,
        ],
        check=True,
    )
    assert (home / ".gitconfig").is_symlink()
    assert not (home / ".gitconfig.local").is_symlink()

    env = {**os.environ, "HOME": str(home), "XDG_CONFIG_HOME": str(home / ".config")}
    env.pop("GIT_CONFIG_GLOBAL", None)
    repo = tmp_path / "repo"
    _git("init", "-q", str(repo), env=env)
    assert _git("config", "user.email", env=env, cwd=repo).stdout.strip() == email
    assert (
        _git("commit", "-q", "--allow-empty", "-m", "t", env=env, cwd=repo).returncode
        == 0
    )

    # create_: later applies keep local edits
    local = home / ".gitconfig.local"
    local.write_text(local.read_text() + "# edited\n")
    subprocess.run(
        [
            "chezmoi",
            "--config",
            str(cfg),
            "--persistent-state",
            str(tmp_path / "state.boltdb"),
            "-D",
            str(home),
            "apply",
            "--force",
            *targets,
        ],
        check=True,
    )
    assert local.read_text().endswith("# edited\n")


def _aliases() -> dict[str, str]:
    out = _git(
        "config", "-f", str(SHARED), "--no-includes", "-z", "--get-regexp", r"^alias\."
    ).stdout
    pairs = (entry.split("\n", 1) for entry in out.split("\0") if entry)
    return {key.removeprefix("alias."): value for key, value in pairs}


def test_shell_aliases_have_valid_syntax():
    bad = {}
    for name, value in _aliases().items():
        if value.startswith("!"):
            res = subprocess.run(
                ["sh", "-n", "-c", value[1:]], capture_output=True, text=True
            )
            if res.returncode != 0:
                bad[name] = res.stderr.strip()
    assert bad == {}


def _unquoted_comment_char(raw: str) -> str | None:
    """Return ';' or '#' if it appears outside double quotes (git: comment start)."""
    in_quotes = escaped = False
    for ch in raw:
        if escaped:
            escaped = False
        elif ch == "\\":
            escaped = True
        elif ch == '"':
            in_quotes = not in_quotes
        elif ch in ";#" and not in_quotes:
            return ch
    return None


def test_alias_values_are_not_cut_off_by_comment_chars():
    # An unquoted ; or # silently truncates the alias (see 25ea465 regression).
    in_alias = False
    bad = []
    for line in SHARED.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            in_alias = stripped == "[alias]"
            continue
        if not in_alias or not stripped or stripped.startswith(("#", ";")):
            continue
        name, _, raw = stripped.partition("=")
        if _unquoted_comment_char(raw):
            bad.append(name.strip())
    assert bad == [], f"wrap these alias values in double quotes: {bad}"


def test_plain_aliases_resolve_to_git_command_or_alias():
    aliases = _aliases()
    commands = set(_git("--list-cmds=main,others").stdout.split())
    unknown = [
        f"{name} -> {value.split()[0]}"
        for name, value in aliases.items()
        if not value.startswith("!")
        and value.split()[0] not in commands
        and value.split()[0] not in aliases
    ]
    assert unknown == []


@pytest.fixture
def git_home(tmp_path: Path):
    home = tmp_path / "home"
    home.mkdir()
    (home / ".gitconfig").symlink_to(SHARED)
    (home / ".gitconfig.local").write_text(
        "[user]\n    name = Host Default\n    email = host@example.com\n"
    )
    env = {
        **os.environ,
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    env.pop("GIT_CONFIG_GLOBAL", None)
    repo = tmp_path / "repo"
    _git("init", "-q", str(repo), env=env)
    (repo / "a.txt").write_text("a\n")
    _git("add", "a.txt", env=env, cwd=repo)
    assert _git("commit", "-q", "-m", "init", env=env, cwd=repo).returncode == 0
    return home, repo, env


def test_harmless_aliases_run(git_home):
    home, repo, env = git_home
    (repo / "a.txt").write_text("b\n")
    _git("add", "a.txt", env=env, cwd=repo)
    for alias in ["st", "cdiff", "ls", "ll", "lf", "le", "lol", "l", "root", "la"]:
        res = _git(alias, env=env, cwd=repo)
        assert res.returncode == 0, f"git {alias}: {res.stderr}"
    assert _git("ca", env=env, cwd=repo).returncode == 0
    assert _git("log", "-1", "--format=%s", env=env, cwd=repo).stdout.strip() == "init"


def test_user_aliases(git_home):
    _home, repo, env = git_home
    show = _git("user-show", env=env, cwd=repo)
    assert show.returncode == 0, show.stderr
    assert "host  : Host Default <host@example.com>" in show.stdout
    assert "active: Host Default <host@example.com>" in show.stdout

    assert _git("user-private", env=env, cwd=repo).returncode == 0
    show = _git("user-show", env=env, cwd=repo).stdout
    assert "repo  : Christian Ditscher <chris@ditscher.me>" in show
    assert "active: Christian Ditscher <chris@ditscher.me>" in show

    assert _git("user-unset-local", env=env, cwd=repo).returncode == 0
    assert _git("config", "user.email", env=env, cwd=repo).stdout.strip() == (
        "host@example.com"
    )


def test_store_alias_writes_host_local_file_not_shared(git_home):
    home, repo, env = git_home
    before = SHARED.read_text()
    assert _git("store", env=env, cwd=repo).returncode == 0
    assert SHARED.read_text() == before
    local = _git("config", "-f", str(home / ".gitconfig.local"), "credential.helper")
    assert local.stdout.strip() == "store"


@pytest.fixture
def git_remote(git_home, tmp_path: Path):
    home, repo, env = git_home
    origin = tmp_path / "origin.git"
    _git("init", "-q", "--bare", str(origin), env=env)
    _git("remote", "add", "origin", str(origin), env=env, cwd=repo)
    _git("branch", "-M", "develop", env=env, cwd=repo)
    _git("push", "-q", "-u", "origin", "develop", env=env, cwd=repo)
    return home, repo, env


def _run(env, repo, *args):
    res = _git(*args, env=env, cwd=repo)
    assert res.returncode == 0, f"git {' '.join(args)}:\n{res.stdout}{res.stderr}"
    return res.stdout


def test_caa_amends_with_files_of_head(git_home):
    _home, repo, env = git_home
    (repo / "a.txt").write_text("changed\n")
    _run(env, repo, "caa")
    assert _run(env, repo, "status", "--porcelain") == ""
    assert _run(env, repo, "rev-list", "--count", "HEAD").strip() == "1"


def test_tidy_and_fresh_run_all_steps(git_home):
    _home, repo, env = git_home
    (repo / "a.txt").write_text("dirty\n")
    (repo / "untracked.txt").write_text("x\n")
    _run(env, repo, "tidy")
    assert _run(env, repo, "status", "--porcelain") == ""
    (repo / "a.txt").write_text("dirty\n")
    (repo / "untracked.txt").write_text("x\n")
    _run(env, repo, "fresh")
    assert _run(env, repo, "status", "--porcelain") == ""


def test_reset_to_origin_resets(git_remote):
    _home, repo, env = git_remote
    _run(env, repo, "commit", "-q", "--allow-empty", "-m", "local only")
    _run(env, repo, "reset-to-origin")
    assert _run(env, repo, "status", "-sb").startswith("## develop...origin/develop\n")
    assert "ahead" not in _run(env, repo, "status", "-sb")


def test_clean_branches_deletes_gone_branches(git_remote):
    _home, repo, env = git_remote
    _run(env, repo, "checkout", "-q", "-b", "feature")
    _run(env, repo, "push", "-q", "-u", "origin", "feature")
    _run(env, repo, "push", "-q", "origin", "--delete", "feature")
    _run(env, repo, "clb")
    assert "feature" not in _run(env, repo, "branch", "--list")


def test_bclean_deletes_merged_branches(git_remote):
    _home, repo, env = git_remote
    _run(env, repo, "branch", "merged-one")
    _run(env, repo, "bclean")
    assert _run(env, repo, "branch", "--list").split() == ["*", "develop"]


def test_clean_tags_refetches_only_remote_tags(git_remote):
    _home, repo, env = git_remote
    _run(env, repo, "tag", "v1")
    _run(env, repo, "push", "-q", "origin", "v1")
    _run(env, repo, "tag", "local-only")
    _run(env, repo, "clt")
    assert _run(env, repo, "tag", "-l").split() == ["v1"]


def test_branch_change_issue_id(git_home):
    _home, repo, env = git_home
    _run(env, repo, "checkout", "-q", "-b", "feat/ABC-1-thing")
    _run(env, repo, "branch-change-issue-id", "XYZ-42")
    assert _run(env, repo, "branch", "--show-current").strip() == "feat/XYZ-42-thing"
