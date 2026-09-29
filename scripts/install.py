#!/usr/bin/env python3
"""Install, preview or undo nobrainer-tech-flow for one client with one command.

Every run is a dry run until --apply. The skills are linked and the managed
instruction block is written by the same helpers as the manual and guided setups,
and --undo uses the guided setup's rollback state, so every path reverses the same
way. This command never grants a standing authorization.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import re
import shlex
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn


ROOT = Path(__file__).resolve().parents[1]
GUIDED = ROOT / "scripts" / "recommend_flow_setup.py"
INSTALL_SKILLS = ROOT / "scripts" / "install_skills.py"
PERSONALIZATION = ROOT / "scripts" / "install_personalization.py"
# The guided setup wants a repository link for context; this command reads none.
REPO_URL = "https://github.com/nobrainer-tech/nobrainer-tech-flow"
LABELS = {
    "claude": "Claude Code",
    "codex": "Codex",
    "opencode": "OpenCode",
    "copilot": "GitHub Copilot CLI",
}
# Lines of a helper's output that explain why it stopped or need the reader's eye.
PROBLEM = re.compile(
    r"^(ERROR|HINT|PRESERVED|WARNING|NOTE|CONFLICT\w*|LEGACY\w*|UNMAPPED_CONFLICT|"
    r"MIGRATE\w*|ROLLBACK\w*|BACKUP_PRESERVED|INPUT_REQUIRED): "
)
KEPT = re.compile(r"^(KEPT_OPTIONS|NOTE|WARNING|HINT|LEGACY_STATE_\w+|BACKUP_PRESERVED): ")
UNDO_NOTE = re.compile(r"^(PRESERVED|NOTE|WARNING|HINT): ")
SYMLINK_HELP = (
    "ERROR: this machine cannot create symbolic links, which this command needs.\n"
    "HINT: on Windows turn on Developer Mode (Settings > System > For developers) or run "
    "from an elevated shell, then rerun. To copy the skills instead, see docs/INSTALL.md "
    "(Windows)."
)


CONFLICT_HINT = (
    "a target above exists and is not a link to this checkout. Inspect it and move it away if "
    "it is yours to remove, or install the other skills one by one with "
    "scripts/install_skills.py --skill (docs/INSTALL.md)."
)
OVERRIDE_HINT = (
    "Codex reads AGENTS.override.md instead of AGENTS.md; remove or empty that file and rerun, "
    "or write to it on purpose with scripts/install_personalization.py --client codex "
    "--path <file>."
)


class Refused(Exception):
    """A helper refused; its reason is already printed and this is the exit code."""


@dataclass(frozen=True)
class Context:
    client: str
    apply: bool
    home: Path
    home_args: tuple[str, ...]
    skills: Path
    guided: object

    @property
    def label(self) -> str:
        return LABELS[self.client]

    def command(self, *flags: str) -> str:
        """The command that continues this run, keeping an explicit --home."""

        parts = ["python3", "scripts/install.py", "--client", self.client, *flags]
        if self.home_args:
            parts += ["--home", quote(self.home_args[1])]
        return " ".join(parts)


def quote(value: str) -> str:
    return subprocess.list2cmdline([value]) if os.name == "nt" else shlex.quote(value)


def load_guided():
    """The guided setup owns the client paths, the skill list and the rollback state."""

    spec = importlib.util.spec_from_file_location("_flow_guided_setup", GUIDED)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load {GUIDED}")
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolve string annotations through sys.modules.
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(spec.name, None)
        raise
    return module


def run(command: list[str]) -> tuple[int, str, str]:
    # The helpers write UTF-8 whatever the console code page is, and must never ask.
    result = subprocess.run(
        command,
        cwd=ROOT,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
        stdin=subprocess.DEVNULL,
    )
    return result.returncode, result.stdout, result.stderr


def refuse(code: int, out: str, err: str, hint: str | None = None) -> NoReturn:
    for line in out.splitlines():
        if PROBLEM.match(line):
            print(line, file=sys.stderr)
    if err.strip():
        print(err.rstrip(), file=sys.stderr)
    if hint:
        print(f"HINT: {hint}", file=sys.stderr)
    raise Refused(code)


def git(*arguments: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=ROOT,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def source_line() -> str:
    version = (ROOT / "skills" / "nobrainer-tech-flow" / "VERSION").read_text(encoding="utf-8").strip()
    commit = git("rev-parse", "--short", "HEAD")
    if not commit:
        return f"nobrainer-tech-flow {version}"
    changed = git("status", "--porcelain", "--untracked-files=no")
    return f"nobrainer-tech-flow {version} (commit {commit}{', local changes' if changed else ''})"


def symlinks_available() -> bool:
    """Whether this account can create directory links (Windows needs a privilege)."""

    try:
        with tempfile.TemporaryDirectory() as scratch:
            target = Path(scratch) / "target"
            target.mkdir()
            os.symlink(target, Path(scratch) / "link", target_is_directory=True)
    except (OSError, NotImplementedError):
        return False
    return True


def plan_skills(ctx: Context) -> tuple[int, int]:
    """Dry-run the skill install: (skills to link, skills already linked)."""

    code, out, err = run(
        [sys.executable, str(INSTALL_SKILLS), "--client", ctx.client, "--dest", str(ctx.skills)]
    )
    if code:
        refuse(
            code,
            out,
            err,
            CONFLICT_HINT if code == 3 else None,
        )
    actions = [line.split(":", 1)[0] for line in out.splitlines()]
    to_link = actions.count("SYMLINK")
    if to_link and not symlinks_available():
        print(SYMLINK_HELP, file=sys.stderr)
        raise Refused(2)
    return to_link, actions.count("KEEP")


def plan_instructions(ctx: Context) -> list[str]:
    code, out, err = run(
        [
            sys.executable,
            str(PERSONALIZATION),
            "--client",
            ctx.client,
            *ctx.home_args,
            "--keep-options",
        ]
    )
    if code:
        refuse(
            code,
            out,
            err,
            OVERRIDE_HINT if "takes precedence over" in out + err else None,
        )
    return [line for line in out.splitlines() if not line.startswith("DRY_RUN:")]


def guided_command(ctx: Context, *extra: str) -> list[str]:
    return [
        sys.executable,
        str(GUIDED),
        "--repo-url",
        REPO_URL,
        "--offline",
        "--client",
        ctx.client,
        *ctx.home_args,
        *extra,
    ]


def install(ctx: Context) -> int:
    to_link, kept = plan_skills(ctx)
    instructions = plan_instructions(ctx)
    if not ctx.apply:
        print(f"{source_line()} for {ctx.label}")
        print(f"SKILLS: {to_link} to link into {ctx.skills} ({kept} already linked)")
        for line in instructions:
            print(line)
        print(f"NO_CHANGES: preview only; install with: {ctx.command('--apply')}")
        return 0
    # Every skill is selected; the answers only feed the recommendations this run ignores.
    everything = ",".join(item.id for item in ctx.guided.ITEMS)
    code, out, err = run(
        guided_command(
            ctx,
            "--work-profile",
            "software-development",
            "--goal",
            "Install every nobrainer-tech-flow skill",
            "--tools",
            ctx.label,
            "--existing-setup",
            "not inspected",
            "--selection",
            everything,
            "--apply",
        )
    )
    if code:
        if os.name == "nt" and re.search(r"WinError 1314|privilege", err, re.IGNORECASE):
            print(SYMLINK_HELP, file=sys.stderr)
        refuse(code, out, err)
    readback = re.search(r"^READBACK: installed=([0-9,]*);", out, re.MULTILINE)
    linked = len([part for part in readback.group(1).split(",") if part]) if readback else to_link + kept
    written = re.search(r"^PREFERENCE_READBACK: (.+?); hash=", out, re.MULTILINE)
    backup = re.search(r"^BACKUP: (.+)$", out, re.MULTILINE)
    print(f"INSTALLED: {source_line()} for {ctx.label}")
    print(f"SKILLS: {linked} linked in {ctx.skills} ({to_link} new)")
    if written:
        print(f"INSTRUCTIONS: {written.group(1)}" + (f" (backup: {backup.group(1)})" if backup else ""))
    else:
        print("INSTRUCTIONS: inherited from the Codex global instructions; nothing written here")
    for line in out.splitlines():
        if KEPT.match(line):
            print(line)
    print(f"UNDO: {ctx.command('--undo', '--apply')}")
    print(
        f"NEXT: restart {ctx.label}, then give it one small task with a checkable result "
        "(docs/TRY_IT.md)."
    )
    return 0


def undo(ctx: Context) -> int:
    code, out, err = run(guided_command(ctx, "--rollback", *(("--apply",) if ctx.apply else ())))
    if code:
        print(out, end="")
        print(err, end="", file=sys.stderr)
        if "rollback state not found" in err:
            print(
                "HINT: undo reverses a setup that this command or the guided setup recorded; "
                f"none is recorded for {ctx.label}.",
                file=sys.stderr,
            )
        return code
    plan = re.search(r"^ROLLBACK_PLAN: remove=([^;]*); personalization=([^;]*); backup=(.*)$", out, re.MULTILINE)
    skills = [name for name in plan.group(1).split(",") if name != "none"] if plan else []
    target = plan.group(2) if plan and plan.group(2) != "none" else None
    backup = plan.group(3) if plan and plan.group(3) != "none" else None
    if not ctx.apply:
        print(f"UNDO_PLAN: unlink {len(skills)} skills from {ctx.skills}")
        if target:
            print(f"INSTRUCTIONS: {target}: " + (f"restore it from {backup}" if backup else "remove the managed block"))
        for line in out.splitlines():
            if UNDO_NOTE.match(line):
                print(line)
        print(f"NO_CHANGES: preview only; undo with: {ctx.command('--undo', '--apply')}")
        return 0
    print(f"UNDONE: nobrainer-tech-flow for {ctx.label}")
    print(f"SKILLS: {len(skills)} unlinked from {ctx.skills}")
    restored = re.search(r"^RESTORED: (.+?) from ", out, re.MULTILINE)
    removed = re.search(r"^REMOVED_MANAGED_BLOCK: (.+)$", out, re.MULTILINE)
    if restored:
        print(f"INSTRUCTIONS: {restored.group(1)} restored from {backup} (the backup file stays)")
    elif removed:
        print(f"INSTRUCTIONS: managed block removed from {removed.group(1)}")
    for line in out.splitlines():
        if UNDO_NOTE.match(line):
            print(line)
    print(f"NEXT: restart {ctx.label} to drop the skills.")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Link every nobrainer-tech-flow skill and add the managed instruction block for "
            "one client. Without --apply this only previews."
        ),
        epilog=(
            "Subsets, copy installs, the shared agents folder and other clients: docs/INSTALL.md."
        ),
    )
    parser.add_argument("--client", choices=tuple(LABELS), required=True)
    parser.add_argument(
        "--home",
        type=Path,
        help="profile home for the documented default locations; when omitted, "
        "CLAUDE_CONFIG_DIR, CODEX_HOME and XDG_CONFIG_HOME are honoured",
    )
    parser.add_argument("--apply", action="store_true", help="write the changes; the default is a preview")
    parser.add_argument(
        "--undo",
        action="store_true",
        help="reverse the setup this command or the guided setup recorded (add --apply to do it)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            # Piped output on Windows uses the ANSI code page, which cannot print every
            # character of a path.
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    args = parse_args(argv)
    try:
        guided = load_guided()
        # An explicit --home selects the documented defaults under it and ignores the
        # environment, exactly as the helpers do. They run from the checkout, so a
        # relative path would land inside it.
        if args.home is not None:
            home = Path(os.path.abspath(args.home.expanduser()))
            environ: object = {}
            home_args = ("--home", str(home))
        else:
            home, environ, home_args = Path.home(), os.environ, ()
            if not home.is_absolute():
                raise ValueError(f"the home directory must be an absolute path, not {str(home)!r}")
        skills = guided.skills_destination(args.client, home, environ).expanduser().resolve()
        ctx = Context(args.client, args.apply, home, home_args, skills, guided)
        return undo(ctx) if args.undo else install(ctx)
    except Refused as refused:
        return refused.args[0]
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
