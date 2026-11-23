"""Raw metrics of shell scripts (sh, bash, zsh) from a line-based parser.

The repository formats shell code with shfmt, so control keywords start commands and
blocks close on their own lines. The parser relies on that layout instead of a full grammar.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from .model import FileMetrics, FunctionMetrics, SourceFile
from .suppressions import parse_suppression

FUNCTION_DEF = re.compile(
    r"^(?:function\s+([\w:.@+-]+)\s*(?:\(\))?|([\w:.@+-]+)\s*\(\))\s*(\{)?\s*$"
)
HEREDOC = re.compile(r"(?<!<)<<-?\s*['\"]?([A-Za-z_]\w*)['\"]?")
SEPARATORS = re.compile(r"(&&|\|\||;;|;&|;|\|&|\||&)")
TOKEN = re.compile(
    r"""(?P<escape>\\.)
    |(?P<single>'[^']*(?P<single_end>')?)
    |(?P<double>"(?:\\.|[^"\\])*(?P<double_end>")?)
    |(?P<comment>(?:^|(?<=[\s;(|&]))\#.*)
    |(?P<other>.)""",
    re.VERBOSE,
)
CLOSING_QUOTE = {"'": re.compile(r"[^']*'"), '"': re.compile(r'(?:\\.|[^"\\])*"')}
LEADING_KEYWORDS = {"then", "do", "else", "!", "time"}
CONDITION_KEYWORDS = {"if", "elif", "while", "until"}


class Block(Enum):
    IF = "if"
    LOOP = "loop"
    CASE = "case"
    GROUP = "group"


OPENERS = {
    "if": Block.IF,
    "for": Block.LOOP,
    "while": Block.LOOP,
    "until": Block.LOOP,
    "select": Block.LOOP,
    "case": Block.CASE,
}
CLOSERS = {"fi": Block.IF, "done": Block.LOOP, "esac": Block.CASE}


@dataclass(frozen=True)
class Line:
    """A logical line: its first physical line number and its code."""

    number: int
    code: str


def analyse(source: SourceFile) -> FileMetrics:
    lexer = _Lexer()
    parser = _Parser()
    for line in lexer.lines(source.text):
        parser.line(line)
    return parser.finish(source, lexer.suppressions)


class _Lexer:
    """Removes comments, string contents (kept as `S`) and heredocs; joins continued lines."""

    def __init__(self):
        self.suppressions: dict[int, dict[str, str]] = {}
        self.quote: str | None = None
        self.heredoc: str | None = None
        self.pending = ""
        self.number = 0

    def lines(self, text: str):
        for number, raw in enumerate(text.splitlines(), start=1):
            line = self._line(Line(number, raw))
            if line:
                yield line

    def _line(self, raw: Line) -> Line | None:
        if self.heredoc:
            self.heredoc = None if raw.code.strip() == self.heredoc else self.heredoc
            return None
        code = self._strip(raw)
        match = HEREDOC.search(raw.code) if "<<" in code else None
        self.heredoc = match.group(1) if match else None
        return self._join(Line(raw.number, code))

    def _join(self, line: Line) -> Line | None:
        code = line.code.rstrip()
        if code.endswith("\\"):
            self.pending += code[:-1] + " "
            return None
        code, self.pending = (self.pending + code).strip(), ""
        return Line(line.number, code) if code else None

    def _strip(self, raw: Line) -> str:
        self.number = raw.number
        rest = self._close_quote(raw.code)
        return "".join(map(self._token, TOKEN.finditer(rest)))

    def _close_quote(self, text: str) -> str:
        """The part of the line after a string that started on an earlier line."""
        if not self.quote:
            return text
        match = CLOSING_QUOTE[self.quote].match(text)
        if not match:
            return ""
        self.quote = None
        end = match.end()
        return "S" + text[end:]

    def _token(self, match: re.Match) -> str:
        kind = match.lastgroup
        if kind in ("single", "double"):
            return self._string(match)
        if kind == "comment":
            self.suppressions.update(_suppression(Line(self.number, match.group(0))))
            return ""
        return match.group(0)

    def _string(self, match: re.Match) -> str:
        if match.group(f"{match.lastgroup}_end") is None:
            self.quote = match.group(0)[0]
            return ""
        return "S"


def _suppression(comment: Line) -> dict[int, dict[str, str]]:
    parsed = parse_suppression(comment.code)
    return {comment.number: parsed} if parsed else {}


@dataclass
class _Function:
    metrics: FunctionMetrics
    lines: set[int] = field(default_factory=set)
    chunk_depth: int = 0


@dataclass
class _Frame:
    block: Block
    function: _Function | None = None
    start_depth: int = 0


class _Parser:
    def __init__(self):
        top = FunctionMetrics(name="<top-level>", line=1, loc=0, top_level=True)
        self.top = _Function(top)
        self.functions: list[_Function] = []
        self.stack: list[_Frame] = []
        self.pending: _Function | None = None
        self.code_lines: set[int] = set()
        self.has_control = False

    @property
    def current(self) -> _Function:
        owners = [frame.function for frame in self.stack if frame.function]
        return owners[-1] if owners else self.top

    def depth(self) -> int:
        """Control nesting inside the current function."""
        depth = 0
        for frame in reversed(self.stack):
            if frame.function:
                break
            depth += frame.block is not Block.GROUP
        return depth

    def line(self, line: Line) -> None:
        self.code_lines.add(line.number)
        function = self.current
        function.lines.add(line.number)
        function.metrics.tokens.extend(_normalise(line.code))
        function.metrics.cyclomatic += line.code.count("&&") + line.code.count("||")
        segments = [segment.strip() for segment in SEPARATORS.split(line.code)]
        self._condition(line, segments)
        for segment in segments:
            self._segment(Line(line.number, segment))

    def _condition(self, line: Line, segments: list[str]) -> None:
        if _first_word(segments[0]) not in CONDITION_KEYWORDS:
            return
        operators = line.code.count("&&") + line.code.count("||")
        operators += len(re.findall(r"\s-[ao]\s", line.code))
        if operators:
            self.current.metrics.conditionals.append((line.number, operators))

    def _segment(self, segment: Line) -> None:
        if segment.code in (";;", ";&"):
            self.current.metrics.cyclomatic += 1
            return
        definition = FUNCTION_DEF.match(segment.code)
        if definition:
            self._define(segment, definition)
            return
        words = segment.code.split()
        while words and words[0] in LEADING_KEYWORDS:
            self._keyword(words.pop(0))
        keywords = words[:1] + [word for word in words[1:] if word in ("{", "}")]
        for word in keywords:
            self._keyword(word)

    def _define(self, segment: Line, match: re.Match) -> None:
        name, number = match.group(1) or match.group(2), segment.number
        self.pending = _Function(
            FunctionMetrics(name=name, line=number, loc=0), {number}
        )
        self.current.lines.discard(number)
        if match.group(3):
            self._open_brace()

    def _keyword(self, word: str) -> None:
        if word in OPENERS:
            self._open(OPENERS[word])
        elif word in CLOSERS or word.startswith("}"):
            self._close()
        elif word in ("elif", "else"):
            self.current.metrics.cognitive += 1
            self.current.metrics.cyclomatic += word == "elif"
        elif word == "{":
            self._open_brace()

    def _open(self, block: Block) -> None:
        self.has_control = True
        function, depth = self.current, self.depth()
        metrics = function.metrics
        metrics.cognitive += 1 + depth
        metrics.cyclomatic += block is not Block.CASE
        metrics.nesting = max(metrics.nesting, depth + 1)
        function.chunk_depth = max(function.chunk_depth if depth else 0, depth + 1)
        self.stack.append(_Frame(block, start_depth=depth))

    def _close(self) -> None:
        frame = self.stack.pop() if self.stack else None
        if frame and frame.function:
            self.functions.append(frame.function)
        elif frame and frame.block is not Block.GROUP:
            self._end_chunk(frame)

    def _end_chunk(self, frame: _Frame) -> None:
        function = self.current
        if frame.start_depth == 0 and function.chunk_depth >= 2:
            function.metrics.bumps.append(function.chunk_depth)

    def _open_brace(self) -> None:
        function, self.pending = self.pending, None
        self.stack.append(_Frame(Block.GROUP, function=function))

    def finish(
        self, source: SourceFile, suppressions: dict[int, dict[str, str]]
    ) -> FileMetrics:
        unclosed = [frame.function for frame in self.stack if frame.function]
        functions = [self.top, *self.functions, *unclosed]
        for function in functions:
            function.metrics.loc = len(function.lines)
        return FileMetrics(
            path=source.path,
            language="shell",
            loc=len(self.code_lines),
            functions=[function.metrics for function in functions],
            suppressions=suppressions,
            is_test=source.is_test,
            has_logic=len(functions) > 1 or self.has_control,
        )


def _first_word(segment: str) -> str:
    words = [word for word in segment.split() if word not in LEADING_KEYWORDS]
    return words[0] if words else ""


def _normalise(code: str) -> list[str]:
    return ["<num>" if word.isdigit() else word for word in code.split()]
