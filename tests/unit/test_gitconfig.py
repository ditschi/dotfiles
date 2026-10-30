from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

import sys

from package_sets import REPO

sys.path.insert(0, str(REPO))

from machine_cli.dotfiles import render_github_token_config  # noqa: E402

SHARED = REPO / "home/core/.gitconfig"
HELPER = REPO / "home/core/.local/bin/git-credential-env"
TOKEN_VARS = ("GITHUB_TOKEN", "BDC_GITHUB_TOKEN", "GITHUB_PRIVATE_TOKEN")
WORK = "christian.ditscher@de.bosch.com"
PRIVATE = "chris@ditscher.me"
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
    lines = _git("config", "-f", str(SHARED), "--no-includes", "--list").stdout
    lines = lines.strip().splitlines()
    local = lines.index("include.path=~/.gitconfig.local")
    after = lines[local:][1:]
    assert after, "owner rules expected after the host-local include"
    assert all(line.startswith("includeif.hasconfig:remote.*.url:") for line in after)


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
        "-m",
        "machine_cli.local_overrides",
        "--shared",
        str(shared),
        "--local",
        str(local),
    ]
    rejected = subprocess.run(
        [*command, "--check"], env=env, capture_output=True, text=True, cwd=REPO
    )
    assert rejected.returncode == 1
    assert "shared@example.com" not in rejected.stdout
    assert "email = shared@example.com" in shared.read_text()
    moved = subprocess.run(command, env=env, cwd=REPO, capture_output=True, text=True)
    assert moved.returncode == 1 and "user.email" in moved.stdout
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
        (tmp_path / ".local/share/machine/local-overrides-backup").glob("*/shared")
    )
    assert len(backups) == 1
    assert backups[0].stat().st_mode & 0o777 == 0o600
    _git("config", "-f", str(shared), "--unset", "user.email")
    subprocess.run([*command, "--check"], env=env, check=True, cwd=REPO)
    subprocess.run(command, env=env, check=True, cwd=REPO)
    assert len(list(backups[0].parent.parent.iterdir())) == 1


def test_gitconfig_check_rejects_malformed_config(tmp_path):
    shared = tmp_path / "shared"
    shared.write_text("[broken\n")
    result = subprocess.run(
        [
            "python3",
            "-m",
            "machine_cli.local_overrides",
            "--check",
            "--shared",
            str(shared),
        ],
        capture_output=True,
        text=True,
        cwd=REPO,
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
            "-m",
            "machine_cli.local_overrides",
            "--shared",
            str(shared),
            "--local",
            str(local),
        ],
        env={**os.environ, "HOME": str(tmp_path), "CI": "true"},
        capture_output=True,
        text=True,
        cwd=REPO,
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
    (repo / "home/core").mkdir(parents=True)
    shared = repo / "home/core/.gitconfig"
    shared.write_text("[user]\n email = work@example.com\n")
    machine.repo = repo
    machine.core_source = repo / "home/core"
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
    monkeypatch.setattr(machine, "sync_host_config_from_repo", lambda: False)
    monkeypatch.setattr(machine, "cmd_env_pull", lambda: 0)
    monkeypatch.setattr(machine, "run_dotfiles_apply", lambda: None)
    if operation == "update":
        assert machine.cmd_update(SimpleNamespace(force=False, system=False)) == 0
        assert any("fetch" in args for args in calls)
    else:
        assert machine.cmd_commit(SimpleNamespace(message="test")) == 0
        assert any("commit" in args for args in calls)


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
        "[credential]\n    helper = store\n"
    )
    (home / ".config/git").mkdir(parents=True)
    for snippet in (REPO / "home/core/.config/git").iterdir():
        (home / ".config/git" / snippet.name).symlink_to(snippet)
    # Written by `machine` per host type; these tests use the work variable.
    (home / ".config/git/github-token.gitconfig").write_text(
        render_github_token_config("work")
    )
    (home / ".local/bin").mkdir(parents=True)
    (home / ".local/bin/git-credential-env").symlink_to(HELPER)
    env = {
        **os.environ,
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
    }
    for var in ("GIT_CONFIG_GLOBAL", "GIT_ASKPASS", "SSH_ASKPASS", *TOKEN_VARS):
        env.pop(var, None)
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


def _identity(env, repo) -> tuple[str, str]:
    email = _git("config", "user.email", env=env, cwd=repo).stdout.strip()
    user = _git(
        "config",
        "--get-urlmatch",
        "credential.username",
        "https://github.com",
        env=env,
        cwd=repo,
    ).stdout.strip()
    return email, user


@pytest.mark.parametrize(
    "url, email, github_user",
    [
        ("https://github.com/ditschi/dotfiles.git", PRIVATE, "ditschi"),
        ("git@github.com:ditschi/dotfiles.git", PRIVATE, "ditschi"),
        ("https://github.com/someone/bosch-tool.git", PRIVATE, "ditschi"),
        ("https://github.com/bosch-foo/x.git", WORK, "dci2lr_bosch"),
        ("https://github.com/bosch_rbadas/x.git", WORK, "dci2lr_bosch"),
        ("git@github.com:bosch-foo/x.git", WORK, "dci2lr_bosch"),
        ("https://github.boschdevcloud.com/DCI2LR/x.git", WORK, "dci2lr_bosch"),
        (
            "ssh://git@sourcecode.socialcoding.bosch.com:7999/p/x.git",
            WORK,
            "dci2lr_bosch",
        ),
        ("https://gitlab.com/me/x.git", "host@example.com", ""),
    ],
)
def test_owner_rules_pick_identity_and_github_user(git_home, url, email, github_user):
    _home, repo, env = git_home
    _run(env, repo, "remote", "add", "origin", url)
    assert _identity(env, repo) == (email, github_user)


def test_user_alias_overrides_owner_rule(git_home):
    _home, repo, env = git_home
    _run(env, repo, "remote", "add", "origin", "https://github.com/ditschi/x.git")
    _run(env, repo, "user-work")
    assert _identity(env, repo) == (WORK, "dci2lr_bosch")
    _run(env, repo, "user-private")
    assert (
        _run(env, repo, "config", "--local", "--get-all", "include.path").count("\n")
        == 1
    )
    _run(env, repo, "user-unset-local")
    assert _identity(env, repo) == (PRIVATE, "ditschi")


def _fill(env, repo, host="github.com"):
    return subprocess.run(
        ["git", "credential", "fill"],
        input=f"protocol=https\nhost={host}\n\n",
        env=env,
        cwd=repo,
        capture_output=True,
        text=True,
    )


def test_credentials_come_from_env_and_are_never_stored(git_home):
    home, repo, env = git_home
    _run(env, repo, "remote", "add", "origin", "https://github.com/ditschi/x.git")
    filled = _fill({**env, "GITHUB_PRIVATE_TOKEN": "private-secret"}, repo)
    assert filled.returncode == 0, filled.stderr
    assert "username=ditschi\npassword=private-secret\n" in filled.stdout
    approve = subprocess.run(
        ["git", "credential", "approve"],
        input=filled.stdout,
        env=env,
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert approve.returncode == 0
    assert not (home / ".git-credentials").exists()

    _run(env, repo, "remote", "set-url", "origin", "https://github.com/bosch-x/y.git")
    filled = _fill({**env, "GITHUB_TOKEN": "work-secret"}, repo)
    assert "username=dci2lr_bosch\npassword=work-secret\n" in filled.stdout


def test_credential_helper_reads_dotenv_when_env_is_empty(git_home):
    home, repo, env = git_home
    (home / ".shell/common").mkdir(parents=True)
    (home / ".shell/common/environment.sh").symlink_to(
        REPO / "home/core/.shell/common/environment.sh"
    )
    dotenv = home / ".env"
    dotenv.write_text(
        "BDC_GITHUB_TOKEN=a$b;c d\nGITHUB_PRIVATE_TOKEN=${BDC_GITHUB_TOKEN}\n"
    )
    dotenv.chmod(0o600)
    _run(env, repo, "remote", "add", "origin", "https://github.com/ditschi/x.git")
    assert "password=a$b;c d\n" in _fill(env, repo).stdout
    _run(
        env,
        repo,
        "remote",
        "set-url",
        "origin",
        "https://github.boschdevcloud.com/o/x.git",
    )
    filled = _fill(env, repo, "github.boschdevcloud.com")
    assert "username=x-access-token\npassword=a$b;c d\n" in filled.stdout


def test_credential_helper_without_token_returns_nothing(tmp_path):
    env = {"PATH": os.environ["PATH"], "HOME": str(tmp_path)}
    run = lambda *args: subprocess.run(  # noqa: E731
        [str(HELPER), *args],
        input="protocol=https\nhost=github.com\n\n",
        env=env,
        capture_output=True,
        text=True,
    )
    missing = run("GITHUB_PRIVATE_TOKEN", "get")
    assert (missing.returncode, missing.stdout) == (0, "")
    assert "GITHUB_PRIVATE_TOKEN is not set" in missing.stderr
    assert run("GITHUB_PRIVATE_TOKEN", "store").stdout == ""
    assert run("BAD-NAME", "get").returncode == 1


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


def test_private_host_serves_github_token(git_home):
    home, repo, env = git_home
    (home / ".config/git/github-token.gitconfig").write_text(
        render_github_token_config("private")
    )
    _run(env, repo, "remote", "add", "origin", "https://github.com/ditschi/x.git")
    filled = _fill(
        {**env, "GITHUB_TOKEN": "private-token", "GITHUB_PRIVATE_TOKEN": "unused"}, repo
    )
    assert filled.returncode == 0, filled.stderr
    assert "password=private-token\n" in filled.stdout
