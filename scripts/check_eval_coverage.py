#!/usr/bin/env python3
"""Require a scenario record in docs/evals/ when a skill, hook or instruction file changes.

Deterministic coverage check: it reads `git diff --name-only base...head` and the
text of the changed `docs/evals/` files. It runs no model, makes no network call
and does not judge whether a scenario is good, only that the change names one.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

EVALS_DIR = "docs/evals/"
INSTRUCTION_FILES = {"AGENTS.md", "CLAUDE.md"}
INSTRUCTION_DIRS = ("hooks/", "adapters/")


class GitError(RuntimeError):
    pass


def _git(repo: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        raise GitError(f"git is unavailable: {exc}") from None
    if result.returncode != 0:
        raise GitError(result.stderr.strip() or f"git {args[0]} failed")
    return result.stdout


def changed_paths(repo: Path, base: str, head: str, *, diff_filter: str = "") -> list[str]:
    args = ["diff", "--name-only", "-z"]
    if diff_filter:
        args.append(f"--diff-filter={diff_filter}")
    args.append(f"{base}...{head}")
    return [path for path in _git(repo, *args).split("\0") if path]


def skill_of(path: str) -> str | None:
    """Skill directory name when the path is a skill's SKILL.md or one of its references."""
    parts = PurePosixPath(path).parts
    if len(parts) >= 3 and parts[0] == "skills":
        if parts[2] == "SKILL.md" and len(parts) == 3:
            return parts[1]
        if parts[2] == "references":
            return parts[1]
    return None


def is_instruction_path(path: str) -> bool:
    return path in INSTRUCTION_FILES or path.startswith(INSTRUCTION_DIRS)


def evaluate(repo: Path, base: str, head: str) -> tuple[list[str], list[str]]:
    """Return (uncovered skills, uncovered instruction paths); both empty means covered."""
    changed = changed_paths(repo, base, head)
    skills = sorted({name for path in changed if (name := skill_of(path))})
    instruction = sorted(path for path in changed if is_instruction_path(path))
    if not skills and not instruction:
        return [], []

    eval_paths = [
        path
        for path in changed_paths(repo, base, head, diff_filter="AM")
        if path.startswith(EVALS_DIR)
    ]
    texts = [_git(repo, "show", f"{head}:{path}") for path in eval_paths]
    uncovered_skills = [
        name
        for name in skills
        if not any(re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", text) for text in texts)
    ]
    uncovered_instruction = [] if eval_paths else instruction
    return uncovered_skills, uncovered_instruction


def default_base() -> str:
    ref = os.environ.get("GITHUB_BASE_REF", "").strip()
    return f"origin/{ref}" if ref else "origin/main"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Fail when a diff changes skills/*/SKILL.md, skills/*/references/, hooks/, "
            "adapters/, AGENTS.md or CLAUDE.md without adding or modifying a scenario "
            "record under docs/evals/ that names each changed skill. For hooks, adapters "
            "and the instruction files any docs/evals/ change in the diff suffices. "
            "Docs-only and scripts-only changes pass. Reads git only; no model, no network."
        ),
    )
    parser.add_argument(
        "base",
        nargs="?",
        help="base ref (default: origin/$GITHUB_BASE_REF when set, else origin/main)",
    )
    parser.add_argument("head", nargs="?", default="HEAD", help="head ref (default: HEAD)")
    parser.add_argument("--repo", default=".", help="repository directory (default: current)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    base = args.base or default_base()
    try:
        skills, instruction = evaluate(Path(args.repo), base, args.head)
    except GitError as exc:
        print(f"EVAL_COVERAGE_ERROR: {exc}", file=sys.stderr)
        return 2
    if not skills and not instruction:
        print(f"EVAL_COVERAGE_OK: {base}...{args.head}")
        return 0
    print(f"EVAL_COVERAGE_FAIL: {base}...{args.head}", file=sys.stderr)
    for name in skills:
        print(f"  uncovered skill: {name}", file=sys.stderr)
    for path in instruction:
        print(f"  uncovered path: {path}", file=sys.stderr)
    print(
        "Fix: add or update a scenario record under docs/evals/ in this change"
        " (name each changed skill directory in its text), or revert the change.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
