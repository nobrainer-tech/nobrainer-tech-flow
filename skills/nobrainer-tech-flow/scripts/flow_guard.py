#!/usr/bin/env python3
"""Optional Claude Code guards for nobrainer-tech-flow.

``pre-tool`` reads a PreToolUse payload and asks the person before a common risky
shell command; it never denies. ``stop`` reads a Stop or SubagentStop payload and
blocks the stop once when a turn that edited files or ran commands ends without a
proof line. Both fail open: input they cannot read is allowed, with a note on stderr.

This is a seatbelt, not a security boundary. It reads the command text, so a
command hidden behind ``sh -c``, a variable or an alias can pass unnoticed, and a
risky phrase inside a quoted string can ask without need.

Install with ``scripts/install_guards.py``; the field names follow
https://code.claude.com/docs/en/hooks.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
import tempfile
from pathlib import Path


# One shell command: the text up to the next separator.
ARGS = r"[^;&|\n]*?"
RISKY = (
    (re.compile(rf"\bgit\b{ARGS}\spush\b{ARGS}\s(?:--force\S*|-[a-zA-Z]*f[a-zA-Z]*)(?=\s|$|[;&|])"),
     "git push --force rewrites the remote branch"),
    (re.compile(rf"\bgit\b{ARGS}\sreset\b{ARGS}\s--hard\b"), "git reset --hard discards uncommitted work"),
    (re.compile(rf"\bgit\b{ARGS}\sclean\b{ARGS}\s(?:--force\b|-[a-zA-Z]*f)"),
     "git clean -f deletes untracked files"),
    (re.compile(rf"\bvercel\b{ARGS}\s--prod\b"), "vercel --prod deploys to production"),
    (re.compile(r"\bnpm\s+publish\b"), "npm publish releases a package"),
    (re.compile(rf"\bterraform\b{ARGS}\s(?:apply|destroy)\b"), "terraform apply or destroy changes infrastructure"),
    (re.compile(rf"\bkubectl\b{ARGS}\sdelete\b"), "kubectl delete removes cluster resources"),
    (re.compile(r"\bgh\s+release\s+create\b"), "gh release create publishes a release"),
)
# An rm that is not part of "git rm"; its arguments run to the next separator.
RM = re.compile(r"(?<![\w./-])rm(?=\s)([^;&|\n)]*)")
RECURSIVE = re.compile(r"^(?:-[a-zA-Z]*[rR][a-zA-Z]*|--recursive)$")
TEMP_ROOTS = ("/tmp", "/private/tmp", "/var/folders", "/private/var/folders")
TMPDIR_REFERENCE = re.compile(r"^(?:\$TMPDIR|\$\{TMPDIR\})(?=/|$)")
EDITING_TOOLS = {"Edit", "MultiEdit", "Write", "NotebookEdit", "Bash"}
# A proof line may sit in a list item or in bold.
PROOF_LINE = re.compile(r"^[\s>*_-]*(?:Proof|Checked):", re.MULTILINE)
STOP_REASON = (
    "Flow guard: this turn changed files or ran commands, but the final message has no "
    "proof. Add a line starting with 'Proof:' or 'Checked:' that names the command, test "
    "or readback showing the result, or say UNVERIFIED and what is missing."
)


def note(message: str) -> None:
    print(f"flow_guard: {message}", file=sys.stderr)


def temp_roots() -> list[str]:
    roots = list(TEMP_ROOTS)
    for value in (os.environ.get("TMPDIR"), tempfile.gettempdir()):
        if value and os.path.isabs(value):
            roots.append(os.path.normpath(value))
    return roots


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
    path = os.path.normpath(argument)
    return any(path.startswith(root.rstrip("/") + "/") for root in roots)


def risky_rm(command: str, cwd: str | None) -> str | None:
    roots = temp_roots()
    for match in RM.finditer(command):
        before = command[: match.start()].split()
        if before and before[-1] == "git":
            continue
        try:
            words = shlex.split(match.group(1))
        except ValueError:
            words = match.group(1).split()
        if not any(RECURSIVE.match(word) for word in words):
            continue
        paths = [word for word in words if not word.startswith("-")]
        if not paths or not all(inside_temp(path, cwd, roots) for path in paths):
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
    reasons = [reason for pattern, reason in RISKY if pattern.search(command)]
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


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1 or argv[0] not in ("pre-tool", "stop"):
        print("usage: flow_guard.py pre-tool|stop  (reads the hook payload on stdin)", file=sys.stderr)
        return 1
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
