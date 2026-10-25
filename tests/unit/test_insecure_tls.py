from __future__ import annotations

import sys

import pytest

from package_sets import REPO

sys.path.insert(0, str(REPO / "tests/integration"))
from insecure_tls import insecure_tls  # noqa: E402


@pytest.mark.parametrize(
    "env, context, expected",
    [
        ({}, "work", True),
        ({}, "private", False),
        ({}, None, False),
        ({"DOTFILES_TEST_INSECURE_TLS": "0"}, "work", False),
        ({"DOTFILES_TEST_INSECURE_TLS": "1"}, "private", True),
    ],
)
def test_insecure_tls_default_and_override(env, context, expected):
    assert insecure_tls(env, lambda: context) is expected
