#!/usr/bin/env python3
"""Optional Claude Code guards for nobrainer-tech-flow.

``pre-tool`` reads a PreToolUse payload and asks the person before a common risky
shell command; it never denies. ``stop`` reads a Stop or SubagentStop payload and
blocks the stop once when a turn that edited files or ran commands ends without a
proof line. Both fail open: input they cannot read is allowed, with a note on stderr.
``session`` reads a SessionStart payload and, when the project has active Flow goal
files, tells the agent to re-read them. It prints only their paths and a known STATUS
word, never other goal-file text, and prints nothing at all on any error.

This is a seatbelt, not a security boundary. It reads the command text, so a
command hidden behind ``sh -c``, a variable or an alias can pass unnoticed, and a
risky phrase inside a quoted string can ask without need.

Install with ``scripts/install_guards.py``; the field names follow
https://code.claude.com/docs/en/hooks.
"""

from __future__ import annotations

import itertools
import json
import os
import re
import shlex
import stat
import sys
import tempfile
from pathlib import Path


# One shell command: the text up to the next separator.
ARGS = r"[^;&|\n]*?"
# Global options between a tool and its subcommand, each "-x", "--name=value" or an
# option and one value word, as in "npm -w pkg publish" or "gh -R owner/repo release".
# Narrower than ARGS, so "npm run publish" or "gh issue create --title release" pass.
OPTIONS = r"(?:\s+-[^\s;&|]+(?:\s+[^\s;&|-][^\s;&|]*)?)*"
END = r"(?=\s|$|[;&|)])"
RISKY = (
    # --force-with-lease and a "+branch" refspec ask too: they still rewrite the remote.
    (re.compile(rf"\bgit\b{ARGS}\spush\b{ARGS}\s(?:--force\S*|-[a-zA-Z]*f[a-zA-Z]*|\+[A-Za-z]\S*){END}"),
     "git push --force rewrites the remote branch"),
    (re.compile(rf"\bgit\b{ARGS}\sreset\b{ARGS}\s--hard\b"), "git reset --hard discards uncommitted work"),
    (re.compile(rf"\bgit\b{ARGS}\sclean\b{ARGS}\s(?:--force\b|-[a-zA-Z]*f)"),
     "git clean -f deletes untracked files"),
    (re.compile(rf"\bvercel\b{ARGS}\s--prod\b"), "vercel --prod deploys to production"),
    (re.compile(rf"\bnpm\b{OPTIONS}\s+publish{END}"), "npm publish releases a package"),
    (re.compile(rf"\bterraform\b{ARGS}\s(?:apply|destroy)\b"), "terraform apply or destroy changes infrastructure"),
    (re.compile(rf"\bkubectl\b{ARGS}\sdelete\b"), "kubectl delete removes cluster resources"),
    (re.compile(rf"\bgh\b{OPTIONS}\s+release\s+create{END}"), "gh release create publishes a release"),
)
# An rm, also path-qualified as /bin/rm or quoted as "rm", that is not part of "git rm";
# its arguments run to the next separator.
RM = re.compile(r"(?<![\w./-])[\"']?(?:[\w.-]*/)*rm[\"']?(?=\s)([^;&|\n)]*)")
# Commands are matched one segment at a time. A segment this long that names a risky
# tool is asked about whole, because the patterns slow down sharply on long lines.
SEPARATOR = re.compile(r"[;&|\n]")
LONGEST_SEGMENT = 2000
RISKY_TOOL = re.compile(r"\b(?:git|vercel|npm|terraform|kubectl|gh)\b")
# A directory change before an rm means the hook's cwd no longer says where a relative
# target is, so the temporary-folder exemption cannot apply to it.
CHANGE_DIRECTORY = re.compile(r"(?<![\w./-])(?:cd|pushd|popd)(?=\s|$|[;&|)])")
RECURSIVE = re.compile(r"^(?:-[a-zA-Z]*[rR][a-zA-Z]*|--recursive)$")
TEMP_ROOTS = ("/tmp", "/private/tmp", "/var/folders", "/private/var/folders")
TMPDIR_REFERENCE = re.compile(r"^(?:\$TMPDIR|\$\{TMPDIR\})(?=/|$)")
EDITING_TOOLS = {"Edit", "MultiEdit", "Write", "NotebookEdit", "Bash"}
# A proof line may sit in a bulleted or numbered list item, with the label in bold.
PROOF_LINE = re.compile(r"^[\s>*_\-]*(?:\d+[.)]\s*)?(?:\*\*|__)?(?:Proof|Checked)(?:\*\*|__)?:", re.MULTILINE)
STOP_REASON = (
    "Flow guard: this turn changed files or ran commands, but the final message has no "
    "proof. Add a line starting with 'Proof:' or 'Checked:' that names the command, test "
    "or readback showing the result, or say UNVERIFIED and what is missing."
)
# A goal file as nobrainer-context's context_inventory.goal_state finds it: Markdown with a
# GOAL_ID line whose first STATUS is not COMPLETE, in the project root or one or two levels
# into tasks/, docs/ or .nobrainer/. tests/test_flow_guard.py checks that both agree.
GOAL_ID = re.compile(r"^GOAL_ID:\s*\S", re.MULTILINE)
GOAL_STATUS = re.compile(r"^STATUS:\s*([A-Z_]+)", re.MULTILINE)
GOAL_DIRS = ("", "tasks", "docs", ".nobrainer")
GOAL_MAX_BYTES = 256 * 1024
# Bounds that keep the hook fast in a large repository; goal_state has no such limit.
GOAL_MATCHES_PER_PATTERN = 500
# The goal file is repository content, so none of its text reaches the context: only a
# STATUS from references/long-run-state.md, and only a path made of these characters.
KNOWN_STATUSES = ("ACTIVE", "BLOCKED", "OWNER_DECISION_REQUIRED")
PATH_PART = re.compile(r"[A-Za-z0-9._-]+")
MAX_PATH_CHARS = 200
MAX_GOALS_SHOWN = 3
SESSION_INTRO = (
    "Flow guard: the context was compacted, resumed or cleared. Before continuing, re-read "
    "these active Flow goal files from disk and check GOAL_ID, STATUS, CHECKPOINT and "
    "NEXT_SAFE_ACTION against the repository. Only paths and known STATUS words are shown here."
)


def note(message: str) -> None:
    print(f"flow_guard: {message}", file=sys.stderr)


def temp_roots() -> list[str]:
    roots = list(TEMP_ROOTS)
    for value in (os.environ.get("TMPDIR"), tempfile.gettempdir()):
        if value and os.path.isabs(value):
            roots.append(os.path.normpath(value))
    # Compared with real paths below, so each root counts in its real form as well
    # (/tmp is /private/tmp on macOS).
    return sorted({form for root in roots for form in (root, os.path.realpath(root))})


def inside_temp(argument: str, cwd: str | None, roots: list[str]) -> bool:
    """Whether ARGUMENT names a path strictly inside a temporary folder."""

    tmpdir = os.environ.get("TMPDIR") or tempfile.gettempdir()
    argument = TMPDIR_REFERENCE.sub(lambda _: tmpdir, argument)
    if "$" in argument or "`" in argument or argument.startswith("~"):
        return False
    if not os.path.isabs(argument):
        if not cwd or not os.path.isabs(cwd):
            return False
        argument = os.path.join(cwd, argument)
    # Links on the way are followed before any "..", as the shell does: a folder under
    # /tmp that links to a project is the project, and its real place decides.
    path = os.path.realpath(argument)
    return any(path.startswith(root.rstrip("/") + "/") for root in roots)


def risky_rm(command: str, cwd: str | None) -> str | None:
    roots = temp_roots()
    for match in RM.finditer(command):
        before = SEPARATOR.split(command[: match.start()])[-1].split()
        if before and os.path.basename(before[-1]) == "git":
            continue
        base = None if CHANGE_DIRECTORY.search(command, 0, match.start()) else cwd
        try:
            words = shlex.split(match.group(1))
        except ValueError:
            # An open quote means a separator inside it cut the arguments short, or the
            # "rm" is only a word in quoted text. Only a recursive rm is asked about.
            rest = command[match.start(1):].split("\n")[0].split()
            if any(RECURSIVE.match(word.strip("\"'")) for word in rest):
                return "rm -r with arguments the guard cannot read deletes files for good"
            continue
        if not any(RECURSIVE.match(word) for word in words):
            continue
        paths = [word for word in words if not word.startswith("-")]
        if not paths or not all(inside_temp(path, base, roots) for path in paths):
            return "rm -r outside a temporary folder deletes files for good"
    return None


def pre_tool(payload: dict) -> dict | None:
    if payload.get("tool_name") != "Bash":
        return None
    tool_input = payload.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(command, str):
        return None
    cwd = payload.get("cwd") if isinstance(payload.get("cwd"), str) else None
    # A backslash line continuation is one command, so join it before splitting.
    command = command.replace("\\\n", " ")
    reasons = []
    for segment in SEPARATOR.split(command):
        if len(segment) > LONGEST_SEGMENT and RISKY_TOOL.search(segment):
            reasons.append("a long command names a risky tool and is too long to check")
            continue
        reasons += [reason for pattern, reason in RISKY if pattern.search(segment) and reason not in reasons]
    rm = risky_rm(command, cwd)
    if rm:
        reasons.insert(0, rm)
    if not reasons:
        return None
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": (
                f"Flow guard: {'; '.join(reasons)}. Confirm only if this is intended "
                "(a seatbelt check, not a security boundary)."
            ),
        }
    }


def blocks(entry: dict) -> list:
    message = entry.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return [block for block in content if isinstance(block, dict)] if isinstance(content, list) else []


def read_turn(path: Path, skip_sidechain: bool) -> tuple[set[str], str]:
    """The tools the last turn used and its final assistant text.

    A turn starts at the last user entry that is a prompt rather than tool results.
    Lines that are not JSON (a line still being written) are skipped.
    """

    entries = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if not isinstance(entry, dict) or entry.get("type") not in ("user", "assistant"):
                continue
            if skip_sidechain and entry.get("isSidechain"):
                continue
            entries.append(entry)
    if not entries:
        raise ValueError(f"no transcript entries in {path}")
    start = 0
    for index, entry in enumerate(entries):
        if entry["type"] == "user" and not any(block.get("type") == "tool_result" for block in blocks(entry)):
            start = index
    tools: set[str] = set()
    final = ""
    for entry in entries[start:]:
        if entry["type"] != "assistant":
            continue
        for block in blocks(entry):
            if block.get("type") == "tool_use" and isinstance(block.get("name"), str):
                tools.add(block["name"])
        text = "\n".join(
            block["text"] for block in blocks(entry) if block.get("type") == "text" and isinstance(block.get("text"), str)
        )
        if text.strip():
            final = text
    return tools, final


def stop(payload: dict) -> dict | None:
    if payload.get("stop_hook_active") is True:
        return None
    event = payload.get("hook_event_name")
    transcript = payload.get("agent_transcript_path") if event == "SubagentStop" else None
    transcript = transcript or payload.get("transcript_path")
    if not isinstance(transcript, str) or not transcript:
        note("no transcript path in the payload; allowing the stop")
        return None
    try:
        tools, final = read_turn(Path(transcript).expanduser(), skip_sidechain=event != "SubagentStop")
    except (OSError, ValueError) as exc:
        note(f"cannot read the transcript ({exc}); allowing the stop")
        return None
    if not tools & EDITING_TOOLS:
        return None
    message = payload.get("last_assistant_message")
    text = message if isinstance(message, str) else final
    if PROOF_LINE.search(text) or "UNVERIFIED" in text:
        return None
    return {"decision": "block", "reason": STOP_REASON}


def project_root(cwd: Path) -> Path:
    """The nearest folder holding .git, where context_inventory looks too; else CWD."""

    return next((folder for folder in (cwd, *cwd.parents) if (folder / ".git").exists()), cwd)


def goal_text(path: Path) -> str | None:
    """The text of a regular file up to GOAL_MAX_BYTES, or None for anything else."""

    try:
        # A device or FIFO is never opened; one swapped in after this check cannot block
        # the non-blocking open and fails the second check.
        if not stat.S_ISREG(os.stat(path).st_mode):
            return None
        with os.fdopen(os.open(path, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)), "rb") as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                return None
            data = handle.read(GOAL_MAX_BYTES + 1)
    except OSError:
        return None
    return data.decode("utf-8", errors="replace") if len(data) <= GOAL_MAX_BYTES else None


def active_goals(root: Path) -> list[tuple[Path, str]]:
    """(path, STATUS) of each active goal file, in goal_state order."""

    goals = []
    for sub in GOAL_DIRS:
        for pattern in ("*.md", "*/*.md") if sub else ("*.md",):
            for path in sorted(itertools.islice((root / sub).glob(pattern), GOAL_MATCHES_PER_PATTERN)):
                text = goal_text(path)
                if text is None or not GOAL_ID.search(text):
                    continue
                status = GOAL_STATUS.search(text)
                status = status.group(1) if status else "UNKNOWN"
                if status != "COMPLETE":
                    goals.append((path, status))
    return goals


def shown_path(path: Path, cwd: Path) -> str | None:
    """PATH relative to CWD when every part is plain and the whole is short, else None."""

    relative = os.path.relpath(path, cwd)
    parts = relative.split(os.sep)
    named = list(itertools.dropwhile(lambda part: part == "..", parts))
    if len(relative) > MAX_PATH_CHARS or not named:
        return None
    if not all(PATH_PART.fullmatch(part) and part not in (".", "..") for part in named):
        return None
    return "/".join(parts)


def session(payload: dict) -> dict | None:
    cwd = payload.get("cwd")
    folder = Path(cwd) if isinstance(cwd, str) and os.path.isabs(cwd) else Path.cwd()
    goals = active_goals(project_root(folder))
    if not goals:
        return None
    lines = []
    for path, status in goals:
        name = shown_path(path, folder)
        if name is None or len(lines) == MAX_GOALS_SHOWN:
            continue
        lines.append(f"- {name} (STATUS: {status})" if status in KNOWN_STATUSES else f"- {name} (STATUS not shown)")
    if len(goals) > len(lines):
        lines.append(f"- {len(goals) - len(lines)} more active goal file(s) not listed")
    context = "\n".join((SESSION_INTRO, *lines))
    return {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1 or argv[0] not in ("pre-tool", "stop", "session"):
        print("usage: flow_guard.py pre-tool|stop|session  (reads the hook payload on stdin)", file=sys.stderr)
        return 1
    if argv[0] == "session":
        # Whatever goes wrong, a session must start with no guard text and no error notice.
        try:
            payload = json.loads(sys.stdin.read())
            result = session(payload) if isinstance(payload, dict) else None
            if result is not None:
                print(json.dumps(result))
        except Exception:
            pass
        return 0
    try:
        payload = json.loads(sys.stdin.read())
    except ValueError as exc:
        note(f"cannot parse the hook input ({exc}); allowing")
        return 0
    if not isinstance(payload, dict):
        note("the hook input is not a JSON object; allowing")
        return 0
    result = pre_tool(payload) if argv[0] == "pre-tool" else stop(payload)
    if result is not None:
        print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
