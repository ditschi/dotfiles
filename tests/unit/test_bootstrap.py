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
