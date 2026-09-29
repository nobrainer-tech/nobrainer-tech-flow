"""Helpers shared by the test modules."""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def find_bash() -> str | None:
    """A bash the hook scripts can run under, or None.

    On Windows that is Git Bash, found at its default locations or next to the git on
    PATH. Never a bare `bash`: Windows searches System32 first, where `bash.exe` is the
    WSL launcher, which fails without an installed distribution.
    """

    if os.name != "nt":
        return shutil.which("bash")
    candidates = [
        Path(r"C:\Program Files\Git\bin\bash.exe"),
        Path(r"C:\Program Files (x86)\Git\bin\bash.exe"),
    ]
    git = shutil.which("git")
    if git:
        # ...\Git\cmd\git.exe or ...\Git\bin\git.exe
        candidates.append(Path(git).resolve().parent.parent / "bin" / "bash.exe")
    return next((str(path) for path in candidates if path.is_file()), None)
