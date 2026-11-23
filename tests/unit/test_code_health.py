"""Rules, scoring, output, gate and baseline of the code health checker."""

import json
import subprocess
import textwrap
from pathlib import Path

import pytest

from code_health import cli, config, scoring
from code_health.model import SourceFile

CONFIG = """
exclude = []

[gate]
min_file_score = 9.5
baseline = "code-health-baseline.json"

[parts.app]
language = "python"
files = ["app/**/*.py"]
rules = ["complex-method", "excess-arguments", "complex-conditional", "code-duplication"]

[parts.tests]
language = "python"
tests = true
files = ["tests/**/*.py"]
rules = ["complex-method", "duplicated-assertion-blocks"]

[parts.shell]
language = "shell"
files = ["bin/*"]
rules = ["nested-complexity"]

[parts.shell.overrides.nested-complexity]
min = 3

[rules.complex-method]
threshold = 2
base = 0.5
step = 0.25
max = 2.0

[rules.excess-arguments]
threshold = 4
base = 0.3

[rules.complex-conditional]
min = 2
base = 0.3

[rules.code-duplication]
min_loc = 3
similarity = 0.75
base = 0.5

[rules.nested-complexity]
min = 4
base = 0.5

[rules.duplicated-assertion-blocks]
block_size = 2
min = 1
base = 0.3
"""

SIMPLE = "def f(a):\n    return a\n"
BRANCHY = "def f(a, b):\n    if a:\n        return 1\n    if b:\n        return 2\n    return 3\n"


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def write(root: Path, path: str, text: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(textwrap.dedent(text))


@pytest.fixture
def repo(tmp_path, monkeypatch):
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "t@example.com")
    git(tmp_path, "config", "user.name", "t")
    write(tmp_path, "code-health.toml", CONFIG)
    write(tmp_path, "app/a.py", SIMPLE)
    write(tmp_path, "notes.yml", "a: 1\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "init")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def run_json(*args: str, capsys) -> tuple[int, dict]:
    code = cli.main(["--json", *args])
    return code, json.loads(capsys.readouterr().out)


def part(name: str, root: Path):
    return next(found for found in config.load(root).parts if found.name == name)


def score(root: Path, part_name: str, path: str, source: str):
    found = part(part_name, root)
    return scoring.score_source(
        SourceFile(path, textwrap.dedent(source), found.tests), found
    )


def test_deduction_grows_with_the_value_up_to_the_maximum(repo):
    rule = part("app", repo).rule("complex-method")
    assert [rule.penalty(value) for value in (3, 4, 20)] == [0.5, 0.75, 2.0]


def test_rule_not_enabled_for_the_part_is_not_reported(repo):
    report = score(
        repo, "tests", "tests/test_a.py", "def test_a(a, b, c, d, e, f):\n    pass\n"
    )
    assert report.smells == [] and report.score == 10.0


def test_file_score_subtracts_each_smell(repo):
    report = score(repo, "app", "app/b.py", "def g(a, b, c, d, e):\n" + BRANCHY[13:])
    assert sorted(smell.rule for smell in report.smells) == [
        "complex-method",
        "excess-arguments",
    ]
    assert report.score == 9.2


def test_duplicated_functions(repo):
    source = BRANCHY + "\n\n" + BRANCHY.replace("def f", "def g").replace("1", "5")
    smells = score(repo, "app", "app/b.py", source).smells
    assert [(s.rule, s.target) for s in smells if s.rule == "code-duplication"] == [
        ("code-duplication", "g")
    ]


def test_duplicated_assertion_blocks(repo):
    source = """
    def test_one(x):
        assert x
        assert not x.y

    def test_two(x):
        assert x
        assert not x.y
    """
    (smell,) = score(repo, "tests", "tests/test_a.py", source).smells
    assert (smell.rule, smell.target) == ("duplicated-assertion-blocks", "test_two")


def test_part_override_replaces_the_default(repo):
    source = """
    f() {
        if a; then
            for b in c; do
                e
            done
        fi
    }
    """
    (smell,) = score(repo, "shell", "bin/x", source).smells
    assert (smell.rule, smell.detail) == ("nested-complexity", "nesting depth 3")


def test_suppression_with_reason_removes_the_smell(repo):
    source = (
        "# code-health: ignore[complex-method] mirrors the protocol table\n" + BRANCHY
    )
    report = score(repo, "app", "app/b.py", source)
    assert (report.smells, report.errors, report.score) == ([], [], 10.0)


@pytest.mark.parametrize(
    "comment, error",
    [
        ("# code-health: ignore[complex-method]", "needs a reason"),
        ("# code-health: ignore[large-file] no such smell here", "matches no smell"),
    ],
)
def test_invalid_suppressions_are_errors(repo, comment, error):
    report = score(repo, "app", "app/b.py", comment + "\n" + BRANCHY)
    assert any(error in message for message in report.errors)


def test_unparsable_file_scores_minimum(repo):
    report = score(repo, "app", "app/b.py", "def f(:\n")
    assert report.score == 1.0 and report.errors


def test_json_lists_parts_and_files(repo, capsys):
    write(repo, "app/b.py", BRANCHY)
    write(repo, "bin/tool", "#!/bin/sh\nalias x=y\n")
    code, data = run_json(capsys=capsys)
    assert code == 0
    assert set(data["files"][0]) >= {"path", "part", "loc", "score", "smells", "errors"}
    assert data["worst_file"]["path"] == "app/b.py"
    assert data["parts"]["shell"] == 10.0
    assert data["parts"]["app"] < 10.0


def test_changed_lists_only_changed_files(repo, capsys):
    write(repo, "app/b.py", SIMPLE)
    _, data = run_json("--changed", "HEAD", capsys=capsys)
    assert [entry["path"] for entry in data["files"]] == ["app/b.py"]


def test_table_output(repo, capsys):
    write(repo, "app/b.py", BRANCHY)
    assert cli.main([]) == 0
    out = capsys.readouterr().out
    assert "app/b.py" in out and "complex-method" in out and "part app" in out


def test_gate_fails_when_a_changed_file_gets_worse(repo, capsys):
    write(repo, "app/a.py", BRANCHY)
    code, data = run_json("--gate", "--base", "HEAD", "app/a.py", capsys=capsys)
    assert code == 1
    assert any("fell from 10.00" in failure for failure in data["gate"]["failures"])


def test_gate_passes_for_healthy_changes(repo, capsys):
    write(repo, "app/b.py", SIMPLE)
    code, data = run_json("--gate", "--changed", "HEAD", capsys=capsys)
    assert code == 0 and data["gate"]["passed"]


def test_baseline_allows_known_debt_but_not_more(repo, capsys):
    many = "".join(f"\n\ndef g{i}(a, b):\n" + BRANCHY[13:] for i in range(4))
    write(repo, "app/a.py", many)
    assert cli.main(["--update-baseline"]) == 0
    capsys.readouterr()
    baseline = json.loads((repo / "code-health-baseline.json").read_text())
    assert "app/a.py" in baseline["files"] and "app" in baseline["parts"]
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "debt")
    write(repo, "app/a.py", many + "\n\ndef h(a, b):\n" + BRANCHY[13:])
    code, data = run_json("--gate", "--base", "HEAD", "app/a.py", capsys=capsys)
    assert code == 1


def test_baseline_only_tightens(repo, capsys):
    two = BRANCHY + "\n\n" + BRANCHY.replace("def f", "def g")
    write(repo, "app/a.py", two)
    cli.main(["--update-baseline"])
    before = json.loads((repo / "code-health-baseline.json").read_text())
    assert before["files"]["app/a.py"] < 9.5
    write(repo, "app/a.py", two + "\n\n" + BRANCHY.replace("def f", "def h"))
    write(repo, "app/new.py", two)
    cli.main(["--update-baseline"])
    after = json.loads((repo / "code-health-baseline.json").read_text())
    assert after["files"] == before["files"]
    write(repo, "app/a.py", SIMPLE)
    write(repo, "app/new.py", SIMPLE)
    cli.main(["--update-baseline"])
    assert json.loads((repo / "code-health-baseline.json").read_text()) == {
        "parts": {},
        "files": {},
    }
