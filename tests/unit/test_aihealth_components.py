"""Component scores and the component check of scripts/aihealth_components.py."""

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "aihealth_components.py"
spec = importlib.util.spec_from_file_location("aihealth_components", SCRIPT)
components = importlib.util.module_from_spec(spec)
spec.loader.exec_module(components)


def scan(*files: tuple[str, int, float]) -> dict:
    return {
        "files": [
            {"language": lang, "loc": loc, "score": score} for lang, loc, score in files
        ]
    }


def test_component_scores_weight_by_lines():
    scans = {
        "code": scan(
            ("python", 100, 10.0),
            ("python", 300, 6.0),
            ("bash", 50, 9.0),
            ("make", 10, 1.0),
        ),
        "tests": scan(("python", 200, 8.0), ("bash", 20, 1.0)),
    }
    assert components.component_scores(scans) == {
        "python-cli": 7.0,
        "python-tests": 8.0,
        "shell": 9.0,
    }


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
