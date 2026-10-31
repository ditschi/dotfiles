"""Run the steps of setup and update one after another; report every failure at the end.

A failing step does not stop the steps that do not need it. Ctrl-C is never caught.
"""

from __future__ import annotations

import logging
import subprocess
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from .core import logger, warn

OK, FAILED, SKIPPED = "ok", "failed", "skipped"


class _ErrorCapture(logging.Handler):
    """Remember the last error `die` logged, as the reason of the failed step."""

    def __init__(self) -> None:
        super().__init__(logging.ERROR)
        self.last = ""

    def emit(self, record: logging.LogRecord) -> None:
        self.last = record.getMessage()


def _reason(exc: BaseException, logged: str) -> str:
    if isinstance(exc, subprocess.CalledProcessError):
        cmd = exc.cmd if isinstance(exc.cmd, str) else " ".join(map(str, exc.cmd))
        return f"`{cmd}` exited with {exc.returncode}"
    if isinstance(exc, SystemExit):
        return logged or f"stopped with exit code {exc.code}"
    return str(exc) or type(exc).__name__


class Steps:
    def __init__(self) -> None:
        self.results: Dict[str, Tuple[str, str]] = {}

    def run(
        self, name: str, func: Callable[[], object], needs: Iterable[str] = ()
    ) -> bool:
        """Run one step; False when it failed or was skipped because a step it needs did not succeed."""
        for need in needs:
            status = self.results.get(need, (OK, ""))[0]
            if status != OK:
                self.results[name] = (SKIPPED, f"needs {need}, which {status}")
                return False
        capture = _ErrorCapture()
        logger.addHandler(capture)
        try:
            result = func()
        except (subprocess.CalledProcessError, OSError, SystemExit) as exc:
            self.results[name] = (FAILED, _reason(exc, capture.last))
            return False
        finally:
            logger.removeHandler(capture)
        # cmd_env_pull and friends report failure through their return code.
        if result is False or (
            isinstance(result, int) and not isinstance(result, bool) and result != 0
        ):
            self.results[name] = (FAILED, capture.last or f"returned {result}")
            return False
        self.results[name] = (OK, "")
        return True

    def fail(self, name: str, reason: str) -> None:
        """Record a failure found by a check that is not run through `run`."""
        self.results[name] = (FAILED, reason)

    def ok(self, name: str) -> bool:
        return self.results.get(name, (OK, ""))[0] == OK

    def problems(self) -> List[Tuple[str, str, str]]:
        return [
            (name, status, reason)
            for name, (status, reason) in self.results.items()
            if status != OK
        ]

    def failed_names(self) -> List[str]:
        return [name for name, status, _ in self.problems() if status == FAILED]

    def summary(self) -> str:
        return "\n".join(
            f"{name} {status}: {reason}" for name, status, reason in self.problems()
        )

    def report(self, what: str) -> Optional[str]:
        """Print failed and skipped steps last; the summary text, or None when all succeeded."""
        problems = self.problems()
        if not problems:
            return None
        warn(f"{what} finished with problems:")
        for name, status, reason in problems:
            warn(f"  {name} {status}: {reason}")
        return self.summary()
