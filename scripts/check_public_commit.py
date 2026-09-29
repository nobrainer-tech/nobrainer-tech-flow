#!/usr/bin/env python3
"""Fail closed before a public-repository commit uses automation or backup state."""

from __future__ import annotations

import re
import subprocess
import sys


AUTOMATED_IDENTITY_RE = re.compile(
    r"\b(?:auto|automated|automation|backup|bot)\b",
    re.IGNORECASE,
)
BACKUP_PATH_RE = re.compile(
    r"(?:^|/)(?:\.git-backups|backup|backups)(?:/|$)"
    r"|(?:^|/)[^/]*\.(?:bak|backup)(?:[-.]|$)",
    re.IGNORECASE,
)


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", *args],
            # Git emits UTF-8 names and paths whatever the console code page is.
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise RuntimeError(f"git is unavailable: {exc}") from None


def _identity(variable: str) -> tuple[str, str]:
    result = _git("var", variable)
    if result.returncode != 0:
        detail = result.stderr.strip() or "git var failed"
        raise RuntimeError(f"{variable}: {detail}")
    match = re.match(r"^(?P<name>.+) <(?P<email>[^>]+)>", result.stdout.strip())
    if match is None:
        raise RuntimeError(f"{variable}: unparseable identity")
    return match.group("name"), match.group("email")


def _staged_paths() -> tuple[str, ...]:
    result = _git("diff", "--cached", "--name-only", "-z")
    if result.returncode != 0:
        detail = result.stderr.strip() or "git diff failed"
        raise RuntimeError(f"staged paths: {detail}")
    return tuple(path for path in result.stdout.split("\0") if path)


def main() -> int:
    violations: list[str] = []
    try:
        for variable in ("GIT_AUTHOR_IDENT", "GIT_COMMITTER_IDENT"):
            name, email = _identity(variable)
            if AUTOMATED_IDENTITY_RE.search(f"{name} <{email}>"):
                violations.append(f"{variable}={name} <{email}>")

        for path in _staged_paths():
            if BACKUP_PATH_RE.search(path):
                violations.append(f"staged backup path={path}")
    except RuntimeError as exc:
        print(f"PUBLIC_COMMIT_GUARD: ERROR: {exc}", file=sys.stderr)
        return 2

    if violations:
        print("PUBLIC_COMMIT_GUARD: BLOCKED", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        print(
            "Use a human repository identity and keep backup state in the "
            "private repository.",
            file=sys.stderr,
        )
        return 1

    print("PUBLIC_COMMIT_GUARD: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
