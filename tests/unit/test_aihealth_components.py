"""Component scores and the component check of scripts/aihealth_components.py."""

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "aihealth_components.py"
spec = importlib.util.spec_from_file_location("aihealth_components", SCRIPT)
components = importlib.util.module_from_spec(spec)
spec.loader.exec_module(components)


def scan(*files: tuple[str, str, int, float]) -> dict:
    return {
        "files": [
            {"path": path, "language": lang, "loc": loc, "score": score}
            for path, lang, loc, score in files
        ]
    }


SCANS = {
    "code": scan(
        ("a.py", "python", 100, 10.0),
        ("b.py", "python", 300, 6.0),
        ("c.sh", "bash", 50, 9.0),
        ("Makefile", "make", 10, 1.0),
    ),
    "tests": scan(("unit/test_a.py", "python", 200, 8.0), ("run.sh", "bash", 20, 1.0)),
}


def test_component_scores_weight_by_lines():
    files = components.component_files(SCANS)
    assert sorted(files) == ["a.py", "b.py", "c.sh", "tests/unit/test_a.py"]
    assert components.component_scores(files) == {
        "python-cli": 7.0,
        "python-tests": 8.0,
        "shell": 9.0,
    }


def test_deleting_a_healthy_file_is_not_a_drop():
    base = components.component_files(SCANS)
    head = {path: entry for path, entry in base.items() if path != "a.py"}
    before = components.component_scores(components.common(base, head))
    after = components.component_scores(components.common(head, base))
    assert components.regressions(before, after) == []


@pytest.mark.parametrize(
    "head, expected",
    [
        ({"shell": 8.995, "python-cli": 7.0}, []),
        ({"shell": 8.99, "python-cli": 6.99}, []),
        ({"shell": 8.9, "python-cli": 7.5}, ["shell: 9.00 -> 8.90"]),
        ({"shell": 9.0, "python-cli": 7.0, "python-tests": 1.0}, []),
    ],
)
def test_regressions_allow_a_small_tolerance_and_new_components(head, expected):
    assert components.regressions({"shell": 9.0, "python-cli": 7.0}, head) == expected


def test_a_drop_of_exactly_the_tolerance_passes_for_every_score():
    hundredths = [value / 100 for value in range(101, 1001)]
    assert not [
        s
        for s in hundredths
        if components.regressions({"x": s}, {"x": round(s - 0.01, 2)})
    ]


def test_scan_calls_the_pinned_ai_health_with_the_component_configs(
    monkeypatch, tmp_path
):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return type("Result", (), {"stdout": '{"files": []}'})()

    monkeypatch.setattr(components.subprocess, "run", fake_run)
    components.scan(tmp_path)
    root = components.ROOT
    assert calls == [
        [
            str(components.WRAPPER),
            "scan",
            str(tmp_path),
            "--config",
            str(root / ".aihealth.toml"),
            "--format",
            "json",
        ],
        [
            str(components.WRAPPER),
            "scan",
            str(tmp_path / "tests"),
            "--config",
            str(root / ".aihealth-tests.toml"),
            "--format",
            "json",
        ],
    ]
