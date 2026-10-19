#!/usr/bin/env python3
"""Preview, add or remove the optional nobrainer-tech-flow guards for Claude Code.

The guards are three hooks in the Claude Code user settings.json: a PreToolUse hook
that asks before common risky shell commands, and Stop and SubagentStop hooks that
ask for a proof line once. Every run is a preview until --apply. The hooks point at
flow_guard.py through the skill link that scripts/install.py created, so they keep
working when the checkout is updated. Our entries are the hooks whose command is
exactly one this script generates; --undo --apply removes those and nothing else.
The preview names only those hooks and the settings path, never other settings,
which can hold tokens.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shlex
import shutil
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALL_SKILLS = ROOT / "scripts" / "install_skills.py"
GUARD = Path("nobrainer-tech-flow") / "scripts" / "flow_guard.py"
EVENTS = (("PreToolUse", "Bash", "pre-tool"), ("Stop", None, "stop"), ("SubagentStop", None, "stop"))
TIMEOUT = 10
DISCLAIMER = (
    "NOTE: a seatbelt: it asks before common risky commands; it is not a security "
    "boundary, and sh -c or variables bypass it."
)


class Refused(Exception):
    """The run stopped; the reason is the message and nothing was written."""


def client_destinations():
    spec = importlib.util.spec_from_file_location("_flow_install_skills", INSTALL_SKILLS)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {INSTALL_SKILLS}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.client_destinations


def locations(home: Path | None) -> tuple[Path, Path]:
    """(settings.json, flow_guard.py through the skill link) for Claude Code.

    An explicit home selects ~/.claude under it and ignores CLAUDE_CONFIG_DIR, as
    scripts/install.py does.
    """

    environ = {} if home is not None else os.environ
    skills = client_destinations()(environ, home or Path.home(), "claude")["claude"]
    return skills.parent / "settings.json", skills / GUARD


def command(guard: Path, mode: str) -> str:
    # A missing or failing guard (the skills were unlinked, no python3) must stay silent:
    # exit 2 from a hook would block every shell command or every stop.
    path = shlex.quote(str(guard))
    return f"if [ -f {path} ]; then python3 {path} {mode} || true; fi"


def ours(hook: object, guard: Path) -> bool:
    # The exact generated text, not a path substring: the path may be shell-quoted, and
    # another hook that merely mentions the path is not ours.
    return isinstance(hook, dict) and hook.get("command") in {command(guard, mode) for _, _, mode in EVENTS}


def read_settings(path: Path) -> tuple[str | None, dict]:
    if not path.exists():
        return None, {}
    text = path.read_text(encoding="utf-8")
    try:
        settings = json.loads(text)
    except ValueError as exc:
        raise Refused(f"{path} is not valid JSON ({exc}); fix it first") from exc
    if not isinstance(settings, dict):
        raise Refused(f"{path} does not hold a JSON object")
    hooks = settings.get("hooks", {})
    if not isinstance(hooks, dict):
        raise Refused(f"{path}: \"hooks\" is not an object")
    for event, groups in hooks.items():
        if not isinstance(groups, list) or not all(
            isinstance(group, dict) and isinstance(group.get("hooks", []), list) for group in groups
        ):
            raise Refused(f"{path}: hooks.{event} is not a list of matcher groups")
    return text, settings


def without_ours(settings: dict, guard: Path) -> dict:
    """SETTINGS with our hooks removed, and the groups and events they leave empty."""

    result = json.loads(json.dumps(settings))
    hooks = result.get("hooks")
    if not isinstance(hooks, dict):
        return result
    for event in list(hooks):
        groups = []
        for group in hooks[event]:
            kept = [hook for hook in group.get("hooks", []) if not ours(hook, guard)]
            if kept or not group.get("hooks"):
                groups.append({**group, "hooks": kept} if "hooks" in group else group)
        if groups or not hooks[event]:
            hooks[event] = groups
        else:
            del hooks[event]
    if not hooks and "hooks" in settings and settings["hooks"]:
        del result["hooks"]
    return result


def with_ours(settings: dict, guard: Path) -> dict:
    result = without_ours(settings, guard)
    hooks = result.setdefault("hooks", {})
    for event, matcher, mode in EVENTS:
        group: dict = {"matcher": matcher} if matcher else {}
        group["hooks"] = [{"type": "command", "command": command(guard, mode), "timeout": TIMEOUT}]
        hooks.setdefault(event, []).append(group)
    return result


def render(settings: dict) -> str:
    return json.dumps(settings, indent=2) + "\n"


def listed(settings: dict, guard: Path) -> list[str]:
    """One line per hook of ours in SETTINGS: its event, matcher and command."""

    lines = []
    for event, groups in settings.get("hooks", {}).items():
        for group in groups:
            matcher = f" (matcher {group['matcher']})" if group.get("matcher") else ""
            lines.extend(f"  {event}{matcher}: {hook['command']}" for hook in group.get("hooks", []) if ours(hook, guard))
    return lines


def backup_copy(target: Path) -> Path:
    """Copy TARGET to a new backup file; an existing file of that name is never replaced."""

    stamp = time.strftime("%Y%m%d-%H%M%S")
    for counter in range(1000):
        suffix = f"-{counter}" if counter else ""
        backup = target.with_name(f"{target.name}.flow-guards-{stamp}{suffix}.bak")
        try:
            # Exclusive creation also refuses a symlink planted at the name. The settings can
            # hold tokens, so the copy is private from its first byte whatever the umask is.
            descriptor = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            continue
        try:
            with os.fdopen(descriptor, "wb") as handle, target.open("rb") as source:
                shutil.copyfileobj(source, handle)
            shutil.copystat(target, backup)
        except BaseException:
            backup.unlink(missing_ok=True)
            raise
        return backup
    raise RuntimeError(f"no free backup name for {target}")


def write(path: Path, before: str | None, after: str) -> Path | None:
    """Write AFTER atomically, keeping a backup of BEFORE; the backup path or None."""

    target = path.resolve() if path.is_symlink() else path
    target.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    if before is not None:
        backup = backup_copy(target)
    descriptor, staged = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(after)
            handle.flush()
            os.fsync(handle.fileno())
        if before is not None:
            shutil.copymode(target, staged)
        os.replace(staged, target)
    except BaseException:
        Path(staged).unlink(missing_ok=True)
        raise
    if target.read_text(encoding="utf-8") != after:
        raise RuntimeError(f"readback of {target} does not match what was written")
    return backup


def installed(settings_path: Path, guard: Path) -> bool:
    """Whether SETTINGS_PATH holds any of our hooks; unreadable settings count as no."""

    try:
        _, settings = read_settings(settings_path)
    except (OSError, Refused):
        return False
    return without_ours(settings, guard) != settings


def run(apply: bool, undo: bool, home: Path | None, rerun: str = "python3 scripts/install_guards.py {flags}") -> int:
    """RERUN is the command that continues this run, with {flags} where --apply goes."""

    settings_path, guard = locations(home)
    if not undo and not guard.is_file():
        print(
            f"UNSUPPORTED: no linked nobrainer-tech-flow skill at {guard.parent.parent}. The guards "
            "point at the skill that scripts/install.py --client claude links; a plugin-only "
            "install is not supported in this version. Install the skills first, then rerun."
        )
        return 3
    before, settings = read_settings(settings_path)
    updated = without_ours(settings, guard) if undo else with_ours(settings, guard)
    if updated == settings:
        if undo:
            print(f"NOTHING TO UNDO: no Flow guards in {settings_path}; nothing was changed")
        else:
            print(f"UP TO DATE: the Flow guards are already in {settings_path}; nothing changed")
        return 0
    after = render(updated)
    if not apply:
        hooks = listed(settings if undo else updated, guard)
        verb = f"remove {len(hooks)} hooks from" if undo else f"add {len(hooks)} hooks to"
        print(f"PREVIEW: would {verb} {settings_path}; other settings keep their values:")
        print("\n".join(hooks))
        if not undo:
            print(DISCLAIMER)
        flags = "--undo --apply" if undo else "--apply"
        print(f"NO_CHANGES: preview only; {'remove' if undo else 'add'} them with: {rerun.replace('{flags}', flags)}")
        return 0
    backup = write(settings_path, before, after)
    print(f"{'REMOVED' if undo else 'INSTALLED'}: Flow guards in {settings_path}")
    if backup:
        print(f"BACKUP: {backup}")
    if not undo:
        print(DISCLAIMER)
        print(f"UNDO: {rerun.replace('{flags}', '--undo --apply')}")
    print("NEXT: restart Claude Code so it loads the changed hooks.")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add the optional Flow guards to the Claude Code settings.json. Without --apply this only previews."
    )
    parser.add_argument("--apply", action="store_true", help="write the change; the default is a preview")
    parser.add_argument("--undo", action="store_true", help="remove the Flow guards (add --apply to do it)")
    parser.add_argument(
        "--home",
        type=Path,
        help="profile home for ~/.claude; when omitted, CLAUDE_CONFIG_DIR is honoured",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if os.name == "nt":
        print("UNSUPPORTED: the Flow guards are POSIX-only in this version.")
        return 3
    home = Path(os.path.abspath(args.home.expanduser())) if args.home else None
    rerun = "python3 scripts/install_guards.py {flags}" + (f" --home {shlex.quote(str(home))}" if home else "")
    try:
        return run(args.apply, args.undo, home, rerun)
    except Refused as refused:
        print(f"REFUSED: {refused}; nothing was changed", file=sys.stderr)
        return 3
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
