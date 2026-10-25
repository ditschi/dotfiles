from __future__ import annotations

import sys
import textwrap

from package_sets import REPO

sys.path.insert(0, str(REPO))

from machine_cli import mise_check  # noqa: E402


def _repo(tmp_path, fragments, packages):
    for name, body in fragments.items():
        path = tmp_path / "home" / "core" / ".config" / "mise" / "conf.d" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(body))
    group_vars = tmp_path / "ansible" / "group_vars" / "all"
    group_vars.mkdir(parents=True)
    lines = "\n".join(f"  - {p}" for p in packages)
    (group_vars / "packages.yml").write_text(
        f"packages_base:\n{lines}\npackages_by_feature:\n  x:\n  - curl\n"
    )
    return tmp_path


def test_repository_fragments_pass():
    assert mise_check.check() == []


def test_tool_in_two_fragments_fails(tmp_path):
    repo = _repo(
        tmp_path,
        {"10.toml": '[tools]\nfzf = "latest"\n', "20.toml": '[tools]\n"fzf" = "0.5"\n'},
        ["curl"],
    )
    errors = mise_check.check(repo)
    assert len(errors) == 1
    assert "fzf" in errors[0] and "10.toml" in errors[0] and "20.toml" in errors[0]


def test_tool_that_is_also_an_apt_package_fails(tmp_path):
    repo = _repo(
        tmp_path,
        {
            "10.toml": '[tools]\nfd = "latest"\n"conda:git" = "latest"\n\n[settings]\njq = 1\n'
        },
        ["fd-find", "git", "jq"],
    )
    errors = mise_check.check(repo)
    assert sorted(e.split("'")[1] for e in errors) == ["fd", "git"]
