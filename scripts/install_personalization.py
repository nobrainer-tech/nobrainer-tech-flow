#!/usr/bin/env python3
"""Install portable nobrainer-tech-flow instructions in a client profile.

The command is intentionally dry-run by default. It only writes a managed block
to a known global instruction file after an explicit ``--apply``.
"""

from __future__ import annotations

import argparse
import difflib
import os
import re
import shutil
import stat
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


START = "<!-- NOBRAINER-TECH-FLOW:START -->"
END = "<!-- NOBRAINER-TECH-FLOW:END -->"
LEGACY_FLOW_INSTRUCTIONS = re.compile(
    r"\bnobrainer-ultra\b|^\s*#{1,6}\s+NoBrainer(?:[ .]?Tech)?\s+Flow\b",
    re.IGNORECASE | re.MULTILINE,
)

def build_block(
    wiki_root: Path | None,
    auto_update: bool,
    auto_session_restart: bool,
    preferences: str | None = None,
) -> str:
    wiki_rule = (
        f"- Relevant project wiki: read `{wiki_root / 'WIKI.md'}`, locate relevant `index.md` entries with a targeted search, then read only the relevant pages. Do not scan the whole wiki by default."
        if wiki_root is not None
        else "- At project start, discover whether a relevant wiki exists. If one exists, read its `WIKI.md`, locate relevant `index.md` entries with a targeted search, then read only the relevant pages. Ask before creating a wiki unless project rules or prior authorization already settle it."
    )
    update_rule = (
        "- On the first `nobrainer-tech-flow` use each calendar day, check for a safe verified update when this client exposes a supported check. This setting grants standing authorization to apply a `nobrainer-tech-flow`-only update after verifying the canonical source/version, reviewing the exact changes, and making a recoverable backup. Never apply destructive, unrelated, or uncertain changes; ask the owner first. If the client is inactive or cannot check, do not claim a check occurred."
        if auto_update
        else "- On the first `nobrainer-tech-flow` use each calendar day, check for available updates when this client exposes a supported check and notify the owner; do not apply them automatically. If the client is inactive or cannot check, do not claim a check occurred."
    )
    session_rule = (
        "- This setting grants standing authorization for session rotation only when the host supports creating a fresh successor, context or checkpoint evidence warrants rotation, and no write is in flight. Create the successor, verify exact takeover by ID/readback, and archive the old session only after that readback. Do not create recursive visible workers or claim a restart when unsupported."
        if auto_session_restart
        else "- Assess context and checkpoint at appropriate milestones. Recommend session rotation when it would help; do not restart or archive automatically. When rotation is authorized, use the supported lifecycle, verify exact successor takeover by ID/readback, and archive the old session only after that readback. Do not create recursive visible workers or claim a restart when unsupported."
    )
    preference_rule = (
        f"- Owner-approved setup preference: {preferences.strip()}"
        if preferences and preferences.strip()
        else ""
    )
    return f"""<!-- NOBRAINER-TECH-FLOW:START -->
## nobrainer-tech-flow

- Use `nobrainer-tech-flow` (`$nobrainer-tech-flow`) as the task entrypoint when this client supports skill invocation. If unavailable, check the documented installation path and report that limitation honestly.
- On first setup, load `nobrainer-auto-fine-tune` for a read-only capability audit; preserve MAIN model and effort, and mark unverified runtime values `UNKNOWN`.
- Preserve the user's selected MAIN model and effort. Inspect the host's actual subagent models, capabilities, and concurrency; delegate independent work when it improves speed or quality, choosing the smallest capable available workers. Never assume a model is available or silently substitute one.
- Split substantial work into bounded tasks with clear outputs, exclusive write scope, dependencies, and verification. Keep integration and acceptance in MAIN; avoid duplicate or filler tasks.
- Derive short-term goals from the user's long-term direction (LDD) and define observable completion criteria. At project start, inspect the existing structure and layers, then recommend a fitting approach.
{wiki_rule}
{session_rule}
{update_rule}
{preference_rule}
- Use `nobrainer-ak` (`nbak`) for relevant marketing and sales content creation when available. For general writing use `nobrainer-writing` when available; make technical documentation concrete, source-backed, and technically verified. Preserve facts, use the user's language, and verify at the actual delivery layer.
<!-- NOBRAINER-TECH-FLOW:END -->"""


@dataclass(frozen=True)
class Client:
    path: Path
    display: str


def known_client_path(client: str, home: Path) -> Client | None:
    """Return a global instruction path only where the client defines one."""

    paths = {
        "codex": home / ".codex" / "AGENTS.md",
        "claude": home / ".claude" / "CLAUDE.md",
        "opencode": home / ".config" / "opencode" / "AGENTS.md",
        "copilot": home / ".copilot" / "copilot-instructions.md",
    }
    if client == "agents":
        return None
    return Client(paths[client], client)


def managed_block_status(content: str, block: str) -> tuple[str, str | None]:
    """Return (status, updated_content), rejecting malformed/duplicated markers."""

    starts = [match.start() for match in re.finditer(re.escape(START), content)]
    ends = [match.start() for match in re.finditer(re.escape(END), content)]
    if not starts and not ends:
        if LEGACY_FLOW_INSTRUCTIONS.search(content):
            raise ValueError(
                "unmarked existing nobrainer-tech-flow instructions detected; "
                "explicit migration is required before installing a managed block"
            )
        separator = "" if not content or content.endswith(("\n", "\r")) else "\n"
        return "MISSING", content + separator + block
    if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
        raise ValueError("malformed or duplicated nobrainer-tech-flow managed markers")

    block_start = starts[0]
    block_end = ends[0] + len(END)
    old_block = content[block_start:block_end]
    if old_block == block:
        return "UNCHANGED", content
    return "UPDATE", content[:block_start] + block + content[block_end:]


def imports_codex_global(content: str, codex_path: Path) -> bool:
    """Detect Claude instructions that already import the Codex global file."""

    codex_spellings = {
        str(codex_path),
        str(codex_path).replace(str(Path.home()), "~", 1),
        "~/.codex/AGENTS.md",
        "${HOME}/.codex/AGENTS.md",
    }
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") and not stripped.startswith("# "):
            continue
        if any(spelling in stripped for spelling in codex_spellings):
            if re.search(r"(?:^\s*@|\b(?:import|include|read|source)\b|\]\()", stripped, re.I):
                return True
    return False


def inspect_target(path: Path, block: str) -> tuple[str, str, int | None]:
    """Read the target without following links and prepare its managed block."""

    try:
        metadata = path.lstat()
    except FileNotFoundError:
        status, updated = managed_block_status("", block)
        assert updated is not None
        return status, updated, None
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise ValueError(f"target must be a regular non-symlink file: {path}")
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            content = handle.read()
    except UnicodeDecodeError as exc:
        raise ValueError(f"target is not UTF-8 text: {path}") from exc
    status, updated = managed_block_status(content, block)
    return status, updated or content, stat.S_IMODE(metadata.st_mode)


def backup_path(path: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    candidate = path.with_name(f"{path.name}.bak.{stamp}")
    index = 1
    while candidate.exists():
        candidate = path.with_name(f"{path.name}.bak.{stamp}.{index}")
        index += 1
    return candidate


def write_atomically(path: Path, content: str, mode: int | None) -> Path | None:
    """Back up an existing target, then atomically replace it with preserved mode."""

    path.parent.mkdir(parents=True, exist_ok=True)
    backup: Path | None = None
    if path.exists():
        backup = backup_path(path)
        # Copy bytes and mode before replacing; exclusive destination avoids clobbering.
        source_stat = path.lstat()
        if stat.S_ISLNK(source_stat.st_mode) or not stat.S_ISREG(source_stat.st_mode):
            raise ValueError(f"target changed and is no longer a regular file: {path}")
        with path.open("rb") as source, backup.open("xb") as destination:
            shutil.copyfileobj(source, destination)
        os.chmod(backup, stat.S_IMODE(source_stat.st_mode))

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if mode is not None:
            os.chmod(temporary, mode)
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return backup


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--client",
        required=True,
        choices=("codex", "claude", "opencode", "agents", "copilot"),
        help="client whose global personalization file should be inspected",
    )
    parser.add_argument(
        "--home",
        type=Path,
        default=Path.home(),
        help="profile home used to resolve the documented global instruction path",
    )
    parser.add_argument(
        "--path",
        type=Path,
        help="explicit instruction-file path (useful for isolated tests or custom profiles)",
    )
    parser.add_argument(
        "--wiki-root",
        type=Path,
        help="project wiki root containing WIKI.md; its resolved path is added to the managed instructions",
    )
    parser.add_argument(
        "--auto-update",
        action="store_true",
        help="authorize safe, verified nobrainer-tech-flow-only updates; default is check and notify",
    )
    parser.add_argument(
        "--auto-session-restart",
        action="store_true",
        help="authorize evidence-gated session rotation; default is assess, checkpoint, and recommend",
    )
    parser.add_argument(
        "--preferences",
        help="short owner-approved setup preferences to include in the managed block",
    )
    parser.add_argument(
        "--apply", action="store_true", help="write changes; without this flag, only preview"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    home = args.home.expanduser()
    resolved = known_client_path(args.client, home)
    if resolved is None and args.path is None:
        print(
            f"UNSUPPORTED: no single documented global instruction path is defined for {args.client}; use --path only when the owner supplies the exact target",
            file=sys.stderr,
        )
        return 2

    path = (args.path or resolved.path).expanduser()
    try:
        wiki_root: Path | None = None
        if args.wiki_root is not None:
            # Persist the caller's canonical alias path, while normalizing relative
            # segments. Path.resolve() would silently replace user-facing symlinks.
            wiki_root = Path(os.path.abspath(args.wiki_root.expanduser()))
            if any(char in str(wiki_root) for char in ("\n", "\r", "`")):
                raise ValueError("wiki root path contains characters unsafe for Markdown")
            if not (wiki_root / "WIKI.md").is_file():
                raise ValueError(f"wiki root must contain WIKI.md: {wiki_root}")
        if args.preferences and (
            len(args.preferences) > 240
            or any(char in args.preferences for char in ("\n", "\r", "`", "<", ">"))
        ):
            raise ValueError("preferences must be a single line of at most 240 safe characters")
        preferences = args.preferences
        if preferences is None:
            try:
                metadata = path.lstat()
            except FileNotFoundError:
                metadata = None
            if metadata is not None and stat.S_ISREG(metadata.st_mode):
                existing_content = path.read_text(encoding="utf-8")
                managed = re.search(
                    re.escape(START) + r"(.*?)" + re.escape(END),
                    existing_content,
                    re.DOTALL,
                )
                if managed:
                    saved = re.search(
                        r"^- Owner-approved setup preference: ([^\r\n]+)$",
                        managed.group(1),
                        re.MULTILINE,
                    )
                    if saved:
                        preferences = saved.group(1)
        block = build_block(
            wiki_root, args.auto_update, args.auto_session_restart, preferences
        )
        if args.client == "claude":
            codex_global = home / ".codex" / "AGENTS.md"
            try:
                metadata = path.lstat()
            except FileNotFoundError:
                metadata = None
            if metadata is not None and stat.S_ISREG(metadata.st_mode):
                with path.open("r", encoding="utf-8", newline="") as handle:
                    if imports_codex_global(handle.read(), codex_global):
                        print(f"INHERITS_CODEX: {path} imports {codex_global}; no duplicate block added")
                        return 0
        status, updated, mode = inspect_target(path, block)
        print(f"TARGET: {path}")
        if status == "UNCHANGED":
            print("UNCHANGED: managed block is current")
            return 0
        print(f"{status}: nobrainer-tech-flow personalization block")
        if wiki_root is not None:
            print(f"WIKI_ROOT: {wiki_root}")
        print(f"AUTO_UPDATE: {'AUTHORIZED_SAFE_VERIFIED_ONLY' if args.auto_update else 'CHECK_AND_NOTIFY'}")
        print(f"AUTO_SESSION_RESTART: {'AUTHORIZED_EVIDENCE_GATED' if args.auto_session_restart else 'ASSESS_CHECKPOINT_RECOMMEND'}")
        if status == "UPDATE":
            print("PRESERVED: content outside the managed block")
        try:
            old_content = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            old_content = ""
        diff = difflib.unified_diff(
            old_content.splitlines(),
            updated.splitlines(),
            fromfile=f"{path} (current)",
            tofile=f"{path} (planned)",
            lineterm="",
        )
        diff_lines = list(diff)
        if diff_lines:
            print("DIFF:")
            print("\n".join(diff_lines))
        if not args.apply:
            print("DRY_RUN: pass --apply to write; no files changed")
            return 0
        backup = write_atomically(path, updated, mode)
        if backup:
            print(f"BACKUP: {backup}")
        print(f"APPLIED: {path}")
        return 0
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
