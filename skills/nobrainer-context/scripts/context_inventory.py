#!/usr/bin/env python3
"""Read-only inventory of the project instruction files coding agents load.

Lists, per client, the instruction files it reads in one project, their size
against documented limits, lines repeated across files, which file imports
which, and whether instructions point to the current Flow goal file. It never
writes. Client rules and sources: ../references/clients.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import codex_context  # noqa: E402

CLIENTS = ("codex", "claude", "gemini", "cursor", "copilot", "opencode")
# Documented guidance, not hard limits (see references/clients.md).
LINE_GUIDANCE = {"claude": 200, "cursor": 500}
CLAUDE_HARD_BYTES = 4 * 1024 * 1024
IMPORT_DEPTH = {"claude": 4, "gemini": 5}
# Modes that put a file in context at session start (Copilot: agent surfaces only).
LOADED = ("launch", "import", "global", "agent_surfaces")
MIN_DUPLICATE_CHARS = 40
MAX_READ_BYTES = 4 * 1024 * 1024
IMPORT_RE = re.compile(r"(?:^|\s)@((?:\.{0,2}/)?[\w.\-/]*\w)")
GOAL_ID_RE = re.compile(r"^GOAL_ID:\s*\S", re.MULTILINE)
GOAL_STATUS_RE = re.compile(r"^STATUS:\s*([A-Z_]+)", re.MULTILINE)
GOAL_DIRS = ("", "tasks", "docs", ".nobrainer")
GLOBAL_FILES = {
    "codex": ("~/.codex/AGENTS.override.md", "~/.codex/AGENTS.md"),
    "claude": ("~/.claude/CLAUDE.md",),
    "gemini": ("~/.gemini/GEMINI.md",),
    "copilot": ("~/.copilot/copilot-instructions.md",),
    "opencode": ("~/.config/opencode/AGENTS.md",),
}


def read_text(path: Path) -> str:
    try:
        with path.open("rb") as handle:
            return handle.read(MAX_READ_BYTES).decode("utf-8", errors="replace")
    except OSError:
        return ""


def chain(root: Path, cwd: Path) -> list[Path]:
    return codex_context.search_dirs(root, cwd)


def prose(text: str) -> str:
    """Text outside fenced code blocks and inline code spans."""

    text = re.sub(r"^(```|~~~).*?^\1", "", text, flags=re.MULTILINE | re.DOTALL)
    return re.sub(r"`[^`\n]*`", "", text)


def imports(path: Path, depth: int, seen: set[Path] | None = None) -> list[Path]:
    seen = seen if seen is not None else {path.resolve()}
    found: list[Path] = []
    if depth <= 0:
        return found
    for match in IMPORT_RE.finditer(prose(read_text(path))):
        target = (path.parent / match.group(1)).resolve()
        if target.is_file() and target not in seen:
            seen.add(target)
            found.append(target)
            found.extend(imports(target, depth - 1, seen))
    return found


def frontmatter(path: Path) -> str:
    text = read_text(path)
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    return text[3:end] if end > 0 else ""


def present(*paths: Path) -> list[Path]:
    return [path for path in paths if path.is_file()]


def project_settings(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(read_text(path)) if path.is_file() else {}
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def client_files(client: str, root: Path, cwd: Path, codex_config: Path) -> list[tuple[Path, str]]:
    """Return (file, load mode) pairs one client reads for this project."""

    dirs = chain(root, cwd)
    files: list[tuple[Path, str]] = []
    if client == "codex":
        result = codex_context.inspect_context(cwd, codex_config)
        return [(Path(doc["path"]), "launch") for doc in result["documents"]]
    if client == "claude":
        claude = [p for d in dirs for p in present(d / "CLAUDE.md", d / ".claude" / "CLAUDE.md", d / "CLAUDE.local.md")]
        agents = [p for d in dirs for p in present(d / "AGENTS.md", d / ".claude" / "AGENTS.md")]
        files = [(p, "launch") for p in (claude or agents)]
        for rule in sorted((root / ".claude" / "rules").rglob("*.md")):
            scoped = re.search(r"^paths\s*:", frontmatter(rule), re.MULTILINE)
            files.append((rule, "on_demand" if scoped else "launch"))
    elif client == "gemini":
        names = project_settings(root / ".gemini" / "settings.json").get("context", {})
        names = names.get("fileName", "GEMINI.md") if isinstance(names, dict) else "GEMINI.md"
        names = [names] if isinstance(names, str) else [n for n in names if isinstance(n, str)] or ["GEMINI.md"]
        files = [(p, "launch") for d in dirs for p in present(*(d / n for n in names))]
    elif client == "cursor":
        for rule in sorted((root / ".cursor" / "rules").rglob("*.mdc")):
            always = re.search(r"^alwaysApply\s*:\s*true", frontmatter(rule), re.MULTILINE)
            files.append((rule, "launch" if always else "conditional"))
        files += [(p, "launch") for d in dirs for p in present(d / "AGENTS.md")]
        files += [(p, "legacy") for p in present(root / ".cursorrules")]
    elif client == "copilot":
        files = [(p, "launch") for p in present(root / ".github" / "copilot-instructions.md")]
        files += [(p, "conditional") for p in sorted((root / ".github" / "instructions").rglob("*.instructions.md"))]
        nearest = [p for d in reversed(dirs) for p in present(d / "AGENTS.md")][:1]
        files += [(p, "agent_surfaces") for p in nearest + present(root / "CLAUDE.md", root / "GEMINI.md")]
    elif client == "opencode":
        up = list(reversed(dirs))
        agents = [p for d in up for p in present(d / "AGENTS.md")][:1]
        files = [(p, "launch") for p in agents or [p for d in up for p in present(d / "CLAUDE.md")][:1]]
        entries = project_settings(root / "opencode.json").get("instructions", [])
        for entry in entries if isinstance(entries, list) else []:
            if isinstance(entry, str) and not entry.startswith(("http://", "https://")):
                files += [(p, "launch") for p in sorted(root.glob(entry)) if p.is_file()]
    depth = IMPORT_DEPTH.get(client, 0)
    expanded: list[tuple[Path, str]] = []
    for path, mode in files:
        expanded.append((path, mode))
        expanded += [(extra, "import") for extra in imports(path, depth)]
    unique: dict[Path, tuple[Path, str]] = {}
    for path, mode in expanded:
        unique.setdefault(path.resolve(), (path, mode))
    return list(unique.values())


def normalize(line: str) -> str:
    line = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", line.strip())
    return re.sub(r"\s+", " ", line).lower()


def duplicates(paths: list[Path], root: Path) -> list[dict[str, Any]]:
    seen: dict[str, list[str]] = {}
    for path in paths:
        for number, line in enumerate(prose(read_text(path)).splitlines(), 1):
            key = normalize(line)
            if len(key) >= MIN_DUPLICATE_CHARS and not key.startswith(("#", "<!--", "|")):
                where = f"{label(path, root)}:{number}"
                if not any(item.startswith(label(path, root) + ":") for item in seen.setdefault(key, [])):
                    seen[key].append(where)
    return [{"text": key[:100], "locations": spots} for key, spots in seen.items() if len(spots) > 1]


def label(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        home = Path.home().resolve()
        resolved = path.resolve()
        return "~/" + resolved.relative_to(home).as_posix() if resolved.is_relative_to(home) else str(resolved)


def describe(path: Path, root: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    return {
        "path": label(path, root),
        "bytes": len(raw),
        "lines": text.count("\n") + (0 if text.endswith("\n") or not text else 1),
        "words": len(text.split()),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "imports": [label(p, root) for p in imports(path, 1)],
    }


def goal_state(root: Path, texts: dict[str, str], explicit: Path | None) -> dict[str, Any]:
    candidates = [explicit] if explicit else [
        path for sub in GOAL_DIRS for pattern in ("*.md", "*/*.md")
        for path in sorted((root / sub).glob(pattern)) if sub or pattern == "*.md"
    ]
    goals = []
    for path in candidates:
        text = read_text(path) if path and path.is_file() and path.stat().st_size <= 256 * 1024 else ""
        if GOAL_ID_RE.search(text):
            status = GOAL_STATUS_RE.search(text)
            goals.append({"path": label(path, root), "status": status.group(1) if status else "UNKNOWN"})
    active = [g for g in goals if g["status"] not in ("COMPLETE",)]
    mentioned = {g["path"] for g in goals for t in texts.values() if g["path"] in t}
    dangling = sorted({m for t in texts.values() for m in re.findall(r"[\w./-]*goal[\w./-]*\.md", t, re.I)
                       if not (root / m).is_file()})
    if not goals:
        status = "STALE_POINTER" if dangling else "NONE"
    elif any(g["path"] in mentioned for g in active):
        status = "POINTED"
    else:
        status = "STALE_POINTER" if mentioned or dangling else "NOT_POINTED"
    return {"status": status, "goal_files": goals, "mentioned": sorted(mentioned), "missing_paths": dangling}


def inventory(cwd: Path, codex_config: Path, clients: tuple[str, ...], include_global: bool,
              goal_file: Path | None) -> dict[str, Any]:
    root, _ = codex_context.find_root(cwd, codex_context.DEFAULT_MARKERS)
    root = root or cwd
    report: dict[str, Any] = {"schema": 1, "project_root": str(root), "clients": {}}
    all_files: dict[Path, Path] = {}
    findings: list[str] = []
    for client in clients:
        loaded = client_files(client, root, cwd, codex_config)
        if include_global:
            loaded += [(Path(p).expanduser(), "global") for p in GLOBAL_FILES.get(client, ())
                       if Path(p).expanduser().is_file()][:1]
        entries = []
        for path, mode in loaded:
            all_files.setdefault(path.resolve(), path)
            entry = describe(path, root) | {"mode": mode}
            guidance = LINE_GUIDANCE.get(client)
            entry["over_guidance"] = bool(guidance and mode != "import" and entry["lines"] > guidance)
            if entry["over_guidance"]:
                findings.append(f"{client}: {entry['path']} has {entry['lines']} lines (guidance {guidance})")
            if client == "claude" and entry["bytes"] > CLAUDE_HARD_BYTES:
                findings.append(f"claude: {entry['path']} is over 4 MiB and is skipped")
            entries.append(entry)
        doubled = duplicates([p for p, m in loaded if m in LOADED], root)
        if doubled:
            findings.append(f"{client}: {len(doubled)} line(s) loaded more than once")
        info: dict[str, Any] = {"files": entries, "launch_bytes": sum(
            e["bytes"] for e in entries if e["mode"] in LOADED), "repeated_lines": len(doubled)}
        if client == "codex":
            probe = codex_context.inspect_context(cwd, codex_config)
            info |= {"byte_budget": probe["project_doc_max_bytes"], "truncated": probe["status"] == "TRUNCATED"}
            if info["truncated"]:
                findings.append("codex: project instructions exceed project_doc_max_bytes and are truncated")
        report["clients"][client] = info
    paths = list(all_files.values())
    report["files"] = sorted({label(p, root) for p in paths})
    digests: dict[str, list[str]] = {}
    for path in paths:
        digests.setdefault(hashlib.sha256(path.read_bytes()).hexdigest(), []).append(label(path, root))
    report["identical_copies"] = [sorted(group) for group in digests.values() if len(group) > 1]
    report["duplicates"] = duplicates(paths, root)
    report["goal"] = goal_state(root, {label(p, root): read_text(p) for p in paths}, goal_file)
    if report["identical_copies"]:
        findings.append(f"{len(report['identical_copies'])} set(s) of byte-identical instruction files")
    if report["goal"]["status"] in ("NOT_POINTED", "STALE_POINTER"):
        findings.append(f"goal: {report['goal']['status']}")
    source = root / "AGENTS.md"
    report["source_of_truth_candidate"] = "AGENTS.md" if source.is_file() else None
    report["findings"] = findings
    report["status"] = "MISSING" if not paths else "ATTENTION" if findings else "CURRENT"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--codex-config", type=Path, help="Codex config.toml (default: CODEX_HOME or ~/.codex)")
    parser.add_argument("--client", action="append", choices=CLIENTS, help="limit to a client; repeatable")
    parser.add_argument("--include-global", action="store_true", help="also size each client's user-level file")
    parser.add_argument("--goal-file", type=Path, help="Flow goal file to check instead of searching")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    parser.add_argument("--check", action="store_true", help="exit 1 unless the status is CURRENT")
    args = parser.parse_args()
    cwd = args.cwd.expanduser().resolve()
    config = (args.codex_config or Path(os.environ.get("CODEX_HOME", "~/.codex")) / "config.toml").expanduser()
    goal = args.goal_file.expanduser().resolve() if args.goal_file else None
    report = inventory(cwd, config.resolve(), tuple(args.client or CLIENTS), args.include_global, goal)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"CONTEXT: {report['status']}")
        print(f"PROJECT_ROOT: {report['project_root']}")
        for client, info in report["clients"].items():
            names = ", ".join(f"{e['path']} ({e['mode']}, {e['bytes']} B)" for e in info["files"]) or "NONE"
            print(f"{client.upper()}: {names}")
        print(f"IDENTICAL_COPIES: {report['identical_copies'] or 'NONE'}")
        print(f"REPEATED_LINES: {len(report['duplicates'])}")
        print(f"GOAL: {report['goal']['status']}")
        for finding in report["findings"]:
            print(f"FINDING: {finding}")
    return 1 if args.check and report["status"] != "CURRENT" else 0


if __name__ == "__main__":
    sys.exit(main())
