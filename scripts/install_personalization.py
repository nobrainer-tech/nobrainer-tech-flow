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
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


START = "<!-- NOBRAINER-TECH-FLOW:START -->"
END = "<!-- NOBRAINER-TECH-FLOW:END -->"
LEGACY_FLOW_INSTRUCTIONS = re.compile(
    r"\bnobrainer-ultra\b|^\s*#{1,6}\s+NoBrainer(?:[ .]?Tech)?\s+Flow\b",
    re.IGNORECASE | re.MULTILINE,
)
# The two lines that carry a standing authorization. --keep-options recognises a grant
# only as one of these exact lines, never as a phrase somewhere in the block, so free
# text in a preference cannot forge one.
AUTO_UPDATE_RULE = "- On the first `nobrainer-tech-flow` use each calendar day, check for a safe verified update when this client exposes a supported check. This setting grants standing authorization to apply a `nobrainer-tech-flow`-only update after verifying the canonical source/version, reviewing the exact changes, and making a recoverable backup. Never apply destructive, unrelated, or uncertain changes; ask the owner first. If the client is inactive or cannot check, do not claim a check occurred."
AUTO_SESSION_RULE = "- This setting grants standing authorization for session rotation only when the host supports creating a fresh successor, context or checkpoint evidence warrants rotation, and no write is in flight. Create the successor, verify exact takeover by ID/readback, and archive the old session only after that readback. Do not create recursive visible workers or claim a restart when unsupported."


def has_rule_line(text: str, rule: str) -> bool:
    """True when ``rule`` is a whole line of ``text``.

    Only ``\\n`` and ``\\r\\n`` end a line here. ``str.splitlines`` would also split on
    U+2028, U+0085 and other separators, which a path or a preference could carry.
    """

    return re.search(r"(?m)^" + re.escape(rule) + r"\r?$", text) is not None


def earlier_grant(existing: str, rule: str, phrase: str, label: str, flag: str) -> bool:
    """Whether the block already holds this exact grant line; says so when one was edited."""

    if has_rule_line(existing, rule):
        return True
    if phrase in existing:
        print(
            f"NOTE: an earlier {label} authorization was not kept because its line no longer "
            f"matches what this installer writes; pass {flag} to grant it again"
        )
    return False


def unsafe_line(value: str) -> bool:
    """True when ``value`` cannot be one plain Markdown line (or could split into two)."""

    return "`" in value or not value.isprintable()


def preference_problem(value: str) -> str | None:
    if len(value) > 240 or "<" in value or ">" in value or unsafe_line(value):
        return "preferences must be a single line of at most 240 safe characters"
    return None


SAVED_WIKI = re.compile(r"^- Relevant project wiki: read `([^`\r\n]+)`", re.MULTILINE)
SAVED_PREFERENCE = re.compile(
    r"^- Owner-approved setup preference: ([^\r\n]+)$", re.MULTILINE
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
        AUTO_UPDATE_RULE
        if auto_update
        else "- On the first `nobrainer-tech-flow` use each calendar day, check for available updates when this client exposes a supported check and notify the owner; do not apply them automatically. If the client is inactive or cannot check, do not claim a check occurred."
    )
    session_rule = (
        AUTO_SESSION_RULE
        if auto_session_restart
        else "- Assess context and checkpoint at appropriate milestones. Recommend session rotation when it would help; do not restart or archive automatically. When rotation is authorized, use the supported lifecycle, verify exact successor takeover by ID/readback, and archive the old session only after that readback. Do not create recursive visible workers or claim a restart when unsupported."
    )
    preference_rule = (
        f"- Owner-approved setup preference: {preferences.strip()}\n"
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
{preference_rule}- Use `nobrainer-ak` (`nbak`) for relevant marketing and sales content creation when available. For general writing use `nobrainer-writing` when available; make technical documentation concrete, source-backed, and technically verified. Preserve facts, use the user's language, and verify at the actual delivery layer.
<!-- NOBRAINER-TECH-FLOW:END -->"""


@dataclass(frozen=True)
class Client:
    path: Path
    display: str


# The variable each client reads to locate its own configuration directory.
CLIENT_CONFIG_VARIABLE = {
    "claude": "CLAUDE_CONFIG_DIR",
    "codex": "CODEX_HOME",
    "opencode": "XDG_CONFIG_HOME",
}


def config_directory(environ: Mapping[str, str], name: str) -> str:
    """The directory a client variable names, or "" when it is unset.

    A blank value counts as unset and any other value is used exactly as written. A
    relative path is an error: the client resolves it against its own directory, the
    script runs from the checkout, and neither can know where the other means.
    """

    value = environ.get(name) or ""
    if not value.strip():
        return ""
    if not Path(value).is_absolute():
        raise ValueError(f"{name} must be an absolute path, not {value!r}")
    return value


def known_client_path(
    client: str, home: Path | None = None, environ: Mapping[str, str] | None = None
) -> Client | None:
    """Return a global instruction path only where the client defines one.

    An explicit ``home`` selects the documented default locations under it. Without
    one, the variable the client reads itself applies: CLAUDE_CONFIG_DIR for Claude
    Code, CODEX_HOME for Codex and XDG_CONFIG_HOME for OpenCode. Variables of other
    clients are none of this client's business, so they are never checked.
    """

    if client == "agents":
        return None
    if environ is None:
        environ = os.environ if home is None else {}
    home = Path.home() if home is None else home
    variable = CLIENT_CONFIG_VARIABLE.get(client)
    base = config_directory(environ, variable) if variable else ""
    paths = {
        "codex": (Path(base) if base else home / ".codex") / "AGENTS.md",
        "claude": (Path(base) if base else home / ".claude") / "CLAUDE.md",
        "opencode": (Path(base) if base else home / ".config") / "opencode" / "AGENTS.md",
        "copilot": home / ".copilot" / "copilot-instructions.md",
    }
    return Client(paths[client], client)


def codex_override_problem(path: Path) -> str | None:
    """Explain why Codex would never read a block written to its global AGENTS.md."""

    override = path.with_name("AGENTS.override.md")
    try:
        if override.is_file() and override.read_bytes().strip():
            return (
                f"{override} takes precedence over {path.name} in Codex, so a block "
                f"written to {path.name} would not load; move or empty the override, "
                "or pass --path to target it deliberately"
            )
    except OSError:
        return None
    return None


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


# Raw HTML blocks that end at a marker instead of at the next blank line.
HTML_TYPE_ONE = re.compile(r"^ {0,3}<(pre|script|style|textarea)(?:[\s>]|$)", re.IGNORECASE)
HTML_END_MARKERS = (
    (re.compile(r"^ {0,3}<\?"), re.compile(r"\?>")),
    (re.compile(r"^ {0,3}<!\[CDATA\["), re.compile(r"\]\]>")),
    (re.compile(r"^ {0,3}<![A-Za-z]"), re.compile(r">")),
)
LINK_DEFINITION = re.compile(r"^ {0,3}\[[^\]\n]+\]:")
FENCE_OPEN = re.compile(r"^[ \t>]*(?:(?:[-*+]|\d{1,9}[.)])[ \t]+)?(`{3,}|~{3,})(.*)$")
FENCE_CLOSE = re.compile(r"^[ \t>]*(`{3,}|~{3,})[ \t]*$")
BLANK_LINE = re.compile(r"\n[ \t]*\n")


def html_block_end(line: str) -> tuple[re.Pattern[str], bool] | None:
    """How the raw HTML block starting on this line ends, and whether it ends a paragraph.

    ``<pre>``, ``<script>``, ``<style>`` and ``<textarea>`` end at their own closing tag
    only: an unclosed one runs to the end of the file, and so does a comment.
    """

    tag = HTML_TYPE_ONE.match(line)
    if tag:
        return re.compile(f"</{tag.group(1)}>", re.IGNORECASE), True
    end = next((end for start, end in HTML_END_MARKERS if start.match(line)), None)
    return (end, False) if end else None


def prose_lines(content: str) -> list[str]:
    """The lines Claude Code may scan for ``@`` imports, with blank lines where code was.

    Fenced code, indented code, HTML comments, raw HTML blocks and link definitions are
    not scanned. The rules are deliberately wide: a line that might be code is treated as
    code, because a missed import only writes a second copy of the block while an import
    that is not one would leave Claude without the block. An unclosed fence or comment
    runs to the end of the file, and only ``\n``, ``\r\n`` and ``\r`` end a line.
    """

    kept: list[str] = []
    fence: tuple[str, int] | None = None
    html_end: tuple[re.Pattern[str], bool] | None = None
    comment = False
    comment_splits = False
    in_html = False

    def hide(splits: bool) -> None:
        # Fenced code and block-level HTML end the paragraph before them, so they must
        # not join two paragraphs. Where that is unsure the paragraphs stay joined.
        if splits and kept and kept[-1]:
            kept.append("")

    for line in content.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if fence:
            closing = FENCE_CLOSE.match(line)
            if closing and closing.group(1)[0] == fence[0] and len(closing.group(1)) >= fence[1]:
                fence = None
            hide(True)
            continue
        if comment:
            comment = "-->" not in line
            hide(comment_splits)
            continue
        if html_end:
            if html_end[0].search(line):
                in_html = True
                hide(html_end[1])
                html_end = None
            else:
                hide(html_end[1])
            continue
        # From here on a start marker wins over the state of a surrounding HTML block:
        # hiding more is always the safe error.
        opening = FENCE_OPEN.match(line)
        if opening and not (opening.group(1)[0] == "`" and "`" in opening.group(2)):
            fence = (opening.group(1)[0], len(opening.group(1)))
            hide(True)
            continue
        if "<!--" in line:
            comment = line.rfind("-->") < line.rfind("<!--")
            comment_splits = line.lstrip(" ").startswith("<!--")
            hide(comment_splits)
            continue
        block = html_block_end(line)
        if block:
            # Whatever follows stays hidden to the next blank line: the surrounding markup
            # may make this block part of a longer one.
            if block[0].search(line):
                in_html = True
            else:
                html_end = block
            hide(block[1])
            continue
        if in_html:
            in_html = bool(line.strip())
            hide(False)
            continue
        if line.startswith(("    ", "\t")) or LINK_DEFINITION.match(line):
            continue
        if line.lstrip(" ").startswith("<"):
            in_html = True
            continue
        kept.append(line)
    return kept


def without_code_spans(text: str) -> str:
    """Drop inline code: a run of backticks up to the next run of the same length."""

    pieces: list[str] = []
    position = 0
    while position < len(text):
        if text[position] == "\\" and position + 1 < len(text):
            # A backslash escapes the next character, so an escaped backtick opens nothing.
            pieces.append(text[position : position + 2])
            position += 2
            continue
        if text[position] != "`":
            pieces.append(text[position])
            position += 1
            continue
        opening_end = position
        while opening_end < len(text) and text[opening_end] == "`":
            opening_end += 1
        length = opening_end - position
        paragraph_end = BLANK_LINE.search(text, opening_end)
        limit = paragraph_end.start() if paragraph_end else len(text)
        close = None
        scan = opening_end
        while scan < limit:
            if text[scan] != "`":
                scan += 1
                continue
            run_end = scan
            while run_end < limit and text[run_end] == "`":
                run_end += 1
            if run_end - scan == length:
                close = run_end
                break
            scan = run_end
        if close is None:
            pieces.append(text[position:opening_end])
            position = opening_end
        else:
            pieces.append(" ")
            position = close
    return "".join(pieces)


def imports_codex_global(content: str, codex_path: Path, home: Path) -> bool:
    """Detect a Claude ``@`` import of the Codex global file.

    Claude Code follows ``@path`` in prose and ignores it in code and raw HTML. A prose
    mention such as "read ~/.codex/AGENTS.md" is a request to the model, not an import,
    and so is ``@path.`` with punctuation stuck to it: the path ends at whitespace and
    stops at a backslash, so a backslash spelling never matches. See ``prose_lines`` for
    why every doubt resolves to "not an import".
    """

    spellings = {codex_path.as_posix()}
    try:
        spellings.add("~/" + codex_path.relative_to(home).as_posix())
    except ValueError:
        pass
    # A paragraph left with a lone backtick may pair it with a line this scan cannot see,
    # so nothing in it counts.
    paragraphs = BLANK_LINE.split("\n".join(prose_lines(content)))
    prose = "\n\n".join(
        text for text in map(without_code_spans, paragraphs) if "`" not in text
    )
    return any(
        re.search(r"(?<!\S)@" + re.escape(spelling) + r"(?!\S)", prose)
        for spelling in spellings
        if "\\" not in spelling
    )


def has_managed_block(path: Path) -> bool:
    """True when the file, read through any symlink, carries a complete block."""

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    return START in text and END in text


def existing_managed_block(path: Path) -> str | None:
    """Return the managed block already in a regular target file, without markers."""

    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(metadata.st_mode):
        return None
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"target is not UTF-8 text: {path}") from exc
    managed = re.search(
        re.escape(START) + r"(.*?)" + re.escape(END), content, re.DOTALL
    )
    return managed.group(1) if managed else None


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
        help=(
            "profile home used to resolve the documented default global instruction path; "
            "when omitted, CLAUDE_CONFIG_DIR, CODEX_HOME and XDG_CONFIG_HOME are honoured"
        ),
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
        "--keep-options",
        action="store_true",
        help=(
            "keep the auto-update, session-restart and wiki-root settings already in the "
            "managed block; flags given on this run are added to them, never removed"
        ),
    )
    parser.add_argument(
        "--apply", action="store_true", help="write changes; without this flag, only preview"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            # Piped output on Windows uses the ANSI code page, which cannot print every
            # character of the instruction files this preview echoes.
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    args = parse_args(argv)
    home = args.home.expanduser() if args.home is not None else None
    try:
        resolved = known_client_path(args.client, home)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3
    if resolved is None and args.path is None:
        print(
            f"UNSUPPORTED: no single documented global instruction path is defined for {args.client}; use --path only when the owner supplies the exact target",
            file=sys.stderr,
        )
        return 2

    path = (args.path or resolved.path).expanduser()
    try:
        if args.client == "codex" and args.path is None:
            problem = codex_override_problem(path)
            if problem:
                raise ValueError(problem)
        wiki_root: Path | None = None
        if args.wiki_root is not None:
            # Persist the caller's canonical alias path, while normalizing relative
            # segments. Path.resolve() would silently replace user-facing symlinks.
            wiki_root = Path(os.path.abspath(args.wiki_root.expanduser()))
            if unsafe_line(str(wiki_root)):
                raise ValueError("wiki root path contains characters unsafe for Markdown")
            if not (wiki_root / "WIKI.md").is_file():
                raise ValueError(f"wiki root must contain WIKI.md: {wiki_root}")
        if args.preferences and preference_problem(args.preferences):
            raise ValueError(preference_problem(args.preferences))
        existing = existing_managed_block(path)
        preferences = args.preferences
        if preferences is None and existing:
            saved = SAVED_PREFERENCE.search(existing)
            if saved:
                preferences = saved.group(1)
        auto_update = args.auto_update
        auto_session_restart = args.auto_session_restart
        if args.keep_options and existing:
            kept: list[str] = []
            if not auto_update and earlier_grant(
                existing, AUTO_UPDATE_RULE, "grants standing authorization to apply", "auto-update", "--auto-update"
            ):
                auto_update = True
                kept.append("auto-update")
            if not auto_session_restart and earlier_grant(
                existing,
                AUTO_SESSION_RULE,
                "grants standing authorization for session rotation",
                "session-restart",
                "--auto-session-restart",
            ):
                auto_session_restart = True
                kept.append("session-restart")
            saved_wiki = SAVED_WIKI.search(existing)
            if wiki_root is None and saved_wiki:
                candidate = Path(saved_wiki.group(1)).parent
                if unsafe_line(str(candidate)):
                    print("NOTE: saved wiki root is not a plain path and was not kept")
                elif (candidate / "WIKI.md").is_file():
                    wiki_root = candidate
                    kept.append("wiki-root")
                else:
                    print(f"NOTE: saved wiki root no longer contains WIKI.md and was not kept: {candidate}")
            if kept:
                print(f"KEPT_OPTIONS: {', '.join(kept)}")
        block = build_block(wiki_root, auto_update, auto_session_restart, preferences)
        if args.client == "claude":
            try:
                codex_global = known_client_path("codex", home).path
            except ValueError:
                # Without a usable Codex path there is nothing to inherit from.
                codex_global = None
            try:
                metadata = path.lstat()
            except FileNotFoundError:
                metadata = None
            if codex_global is not None and metadata is not None and stat.S_ISREG(metadata.st_mode):
                with path.open("r", encoding="utf-8", newline="") as handle:
                    imported = imports_codex_global(
                        handle.read(), codex_global, home or Path.home()
                    )
                if imported and has_managed_block(codex_global):
                    print(f"INHERITS_CODEX: {path} imports {codex_global}; no duplicate block added")
                    return 0
                if imported:
                    print(
                        f"NOTE: {path} imports {codex_global}, which has no nobrainer-tech-flow "
                        "block; the block is written here so the instructions are not lost"
                    )
        status, updated, mode = inspect_target(path, block)
        print(f"TARGET: {path}")
        if status == "UNCHANGED":
            print("UNCHANGED: managed block is current")
            return 0
        print(f"{status}: nobrainer-tech-flow personalization block")
        if wiki_root is not None:
            print(f"WIKI_ROOT: {wiki_root}")
        print(f"AUTO_UPDATE: {'AUTHORIZED_SAFE_VERIFIED_ONLY' if auto_update else 'CHECK_AND_NOTIFY'}")
        print(f"AUTO_SESSION_RESTART: {'AUTHORIZED_EVIDENCE_GATED' if auto_session_restart else 'ASSESS_CHECKPOINT_RECOMMEND'}")
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
