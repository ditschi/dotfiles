"""Shell metrics of the code health checker."""

import textwrap

from code_health import shell_metrics
from code_health.model import SourceFile


def analyse(source: str):
    return shell_metrics.analyse(SourceFile("x.sh", textwrap.dedent(source).lstrip()))


def functions(source: str) -> dict:
    return {function.name: function for function in analyse(source).functions}


def test_three_definition_styles():
    source = """
    one() {
        echo 1
    }
    function two {
        echo 2
    }
    function three() {
        echo 3
    }
    """
    found = functions(source)
    assert list(found) == ["<top-level>", "one", "two", "three"]
    assert [found[name].loc for name in ("one", "two", "three")] == [3, 3, 3]


def test_nesting_complexity_and_bumps():
    source = """
    f() {
        if [[ -n $1 ]]; then
            for x in "$@"; do
                while read -r line; do
                    echo "$line"
                done <"$x"
            done
        elif [[ -z $2 ]]; then
            echo none
        else
            echo other
        fi
        if [[ -n $3 ]]; then
            if [[ -n $4 ]]; then
                echo deep
            fi
        fi
    }
    """
    function = functions(source)["f"]
    assert function.nesting == 3
    assert function.cyclomatic == 7
    assert function.cognitive == 1 + 2 + 3 + 1 + 1 + 1 + 2
    assert function.bumps == [3, 2]


def test_case_items_count_as_branches():
    source = """
    f() {
        case "$1" in
            a) echo a ;;
            b)
                echo b
                ;;
            *) echo other ;;
        esac
    }
    """
    assert functions(source)["f"].cyclomatic == 4


def test_conditions_with_several_operators():
    source = """
    f() {
        if [[ -n $1 && -n $2 ]] || [ -z "$3" -a -z "$4" ]; then
            echo yes
        fi
        [[ -n $1 ]] && echo chained
    }
    """
    function = functions(source)["f"]
    assert function.conditionals == [(2, 3)]
    assert function.cyclomatic == 5


def test_keywords_in_strings_comments_and_heredocs_are_ignored():
    source = """
    f() {
        echo "if this fi { done"  # if not a block {
        cat <<'EOF'
    if [ x ]; then
    }
    EOF
        echo 'while case esac'
    }
    g() {
        echo after
    }
    """
    found = functions(source)
    assert (found["f"].nesting, found["f"].cyclomatic) == (0, 1)
    assert list(found) == ["<top-level>", "f", "g"]


def test_top_level_code_is_a_pseudo_function():
    source = """
    set -eu
    if [ -n "$1" ]; then
        echo arg
    fi
    """
    top = functions(source)["<top-level>"]
    assert top.top_level and top.cyclomatic == 2


def test_file_without_logic():
    metrics = analyse("alias ll='ls -l'\nexport EDITOR=vim\n")
    assert not metrics.has_logic
    assert metrics.loc == 2


def test_line_continuation_and_multiline_strings():
    source = """
    f() {
        printf '%s\\n' \\
            "one" \\
            "two"
        echo "multi
    line if"
    }
    """
    function = functions(source)["f"]
    assert (function.nesting, function.cyclomatic) == (0, 1)


def test_suppression_comment():
    metrics = analyse(
        "f() { # code-health: ignore[large-method] generated\n    echo\n}\n"
    )
    assert metrics.suppressions == {1: {"large-method": "generated"}}
