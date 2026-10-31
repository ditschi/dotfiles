from __future__ import annotations

import os
import subprocess
from pathlib import Path

from package_sets import REPO

BOOTSTRAP = REPO / "bootstrap"
STUB = '#!/usr/bin/env bash\necho "stub machine $*"\n'


def _git(*args: str, cwd: Path) -> None:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t",
    }
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, env=env)


def _stub_checkout(path: Path) -> Path:
    (path / "machine_cli").mkdir(parents=True)
    machine = path / "machine_cli" / "machine"
    machine.write_text(STUB)
    machine.chmod(0o755)
    return path


def _env(tmp_path: Path, **extra: str) -> dict[str, str]:
    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir(exist_ok=True)
    uv = bin_dir / "uv"
    uv.write_text("#!/usr/bin/env bash\n")
    uv.chmod(0o755)
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    env = {**os.environ, "HOME": str(home), "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    env.pop("DOTFILES_DIR", None)
    env.update(extra)
    return env


def test_checkout_run_links_machine_and_runs_setup(tmp_path):
    checkout = _stub_checkout(tmp_path / "checkout")
    (checkout / "bootstrap").write_text(BOOTSTRAP.read_text())
    (checkout / "bootstrap").chmod(0o755)
    env = _env(tmp_path)
    link = Path(env["HOME"]) / ".local/bin/machine"
    link.parent.mkdir(parents=True)
    link.write_text("old copied entry point\n")

    for _ in range(2):  # a re-run is idempotent
        result = subprocess.run(
            [str(checkout / "bootstrap"), "--yes"],
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert "stub machine setup --yes" in result.stdout
        assert link.is_symlink()
        assert link.resolve() == (checkout / "machine_cli/machine").resolve()


def test_piped_run_clones_once_and_does_not_pull(tmp_path):
    source = _stub_checkout(tmp_path / "source")
    _git("init", "-q", cwd=source)
    _git("add", ".", cwd=source)
    _git("commit", "-q", "-m", "init", cwd=source)
    target = tmp_path / "clone"
    env = _env(tmp_path, DOTFILES_REPO_URL=str(source), DOTFILES_DIR=str(target))

    def piped() -> subprocess.CompletedProcess:
        return subprocess.run(
            ["bash", "-s", "--", "--yes"],
            input=BOOTSTRAP.read_text(),
            env=env,
            capture_output=True,
            text=True,
        )

    first = piped()
    assert first.returncode == 0, first.stderr
    assert (target / "machine_cli/machine").is_file()
    assert "stub machine setup --yes" in first.stdout

    (source / "new.txt").write_text("x")
    _git("add", ".", cwd=source)
    _git("commit", "-q", "-m", "more", cwd=source)
    second = piped()
    assert second.returncode == 0, second.stderr
    assert "cloning" not in second.stdout
    assert not (target / "new.txt").exists()
    link = Path(env["HOME"]) / ".local/bin/machine"
    assert link.resolve() == (target / "machine_cli/machine").resolve()


def _installer(tmp_path: Path) -> Path:
    script = tmp_path / "install-mise.sh"
    script.write_text(
        'echo "$MISE_VERSION" > "$MISE_INSTALL_PATH.version"\n'
        'printf "#!/bin/sh\\n" > "$MISE_INSTALL_PATH"\n'
        'chmod +x "$MISE_INSTALL_PATH"\n'
    )
    return script


def _mise_env(tmp_path: Path, installer: Path) -> dict[str, str]:
    env = _env(tmp_path, MISE_INSTALL_URL=installer.as_uri())
    env["PATH"] = f"{tmp_path / 'fakebin'}:/usr/bin:/bin"
    return env


def test_bootstrap_installs_missing_mise_once(tmp_path):
    checkout = _stub_checkout(tmp_path / "checkout")
    (checkout / "bootstrap").write_text(BOOTSTRAP.read_text())
    (checkout / "bootstrap").chmod(0o755)
    env = _mise_env(tmp_path, _installer(tmp_path))
    if subprocess.run(["sh", "-c", "command -v mise"], env=env).returncode == 0:
        return  # a system mise would be kept, which the next test covers
    mise = Path(env["HOME"]) / ".local/bin/mise"

    result = subprocess.run(
        [str(checkout / "bootstrap")], env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert "stub machine setup" in result.stdout
    assert mise.is_file()
    assert Path(f"{mise}.version").read_text().strip() == "v2026.10.17"

    mise.write_text("#!/bin/sh\n# kept\n")
    subprocess.run([str(checkout / "bootstrap")], env=env, check=True)
    assert "# kept" in mise.read_text()


def test_bootstrap_keeps_installed_mise(tmp_path):
    checkout = _stub_checkout(tmp_path / "checkout")
    (checkout / "bootstrap").write_text(BOOTSTRAP.read_text())
    (checkout / "bootstrap").chmod(0o755)
    env = _mise_env(tmp_path, _installer(tmp_path))
    fake = tmp_path / "fakebin/mise"
    fake.write_text("#!/bin/sh\n")
    fake.chmod(0o755)
    result = subprocess.run(
        [str(checkout / "bootstrap")], env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert not (Path(env["HOME"]) / ".local/bin/mise").exists()
    assert "installing mise" not in result.stdout


def test_piped_run_gives_setup_the_terminal(tmp_path):
    import fcntl
    import pty
    import termios

    checkout = _stub_checkout(tmp_path / "checkout")
    (checkout / "machine_cli" / "machine").write_text(
        '#!/usr/bin/env bash\n[[ -t 0 ]] && echo "stdin tty" || echo "stdin pipe"\n'
    )
    env = _env(tmp_path, DOTFILES_DIR=str(checkout))
    master, slave = pty.openpty()

    def own_terminal() -> None:
        fcntl.ioctl(slave, termios.TIOCSCTTY, 0)

    try:
        result = subprocess.run(
            ["bash", "-s"],
            input=BOOTSTRAP.read_bytes(),
            stdout=subprocess.PIPE,
            stderr=slave,
            env=env,
            start_new_session=True,
            preexec_fn=own_terminal,
        )
    finally:
        os.close(slave)
        os.close(master)
    assert result.returncode == 0
    assert b"stdin tty" in result.stdout


def test_piped_run_without_terminal_keeps_stdin(tmp_path):
    checkout = _stub_checkout(tmp_path / "checkout")
    env = _env(tmp_path, DOTFILES_DIR=str(checkout))
    result = subprocess.run(
        ["bash", "-s", "--", "--yes"],
        input=BOOTSTRAP.read_text(),
        env=env,
        capture_output=True,
        text=True,
        start_new_session=True,
    )
    assert result.returncode == 0, result.stderr
    assert "stub machine setup --yes" in result.stdout
