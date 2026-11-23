"""The two ai-health profiles must stay the same profile (docs/code-health.md)."""

import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SHARED_SECTIONS = ("thresholds", "score", "delta")


def profile(name: str) -> dict:
    return tomllib.loads((ROOT / name).read_text())


@pytest.mark.parametrize("section", SHARED_SECTIONS)
def test_tests_profile_repeats_the_shared_section(section):
    assert (
        profile(".aihealth-tests.toml")[section] == profile(".aihealth.toml")[section]
    )


def test_tests_profile_switches_off_fixture_and_class_smells():
    weights = profile(".aihealth-tests.toml")["weights"]
    assert weights == {
        "excess_arguments": 0,
        "primitive_obsession": 0,
        "low_cohesion": 0,
    }


def test_strict_profile_values():
    strict = profile(".aihealth.toml")
    assert strict["score"] == {"decay": 8, "symbol_cap": 4, "density_loc": 100000}
    assert strict["delta"] == {"tolerance": 0.0}
    assert strict["thresholds"] == {"large_file": 600, "primitive_obsession": 0.3}
