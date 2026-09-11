#!/usr/bin/env python3
"""Read-only inspection of the project instructions Codex can load."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tomllib
from pathlib import Path
from typing import Any


DEFAULT_MAX_BYTES = 32 * 1024
DEFAULT_MARKERS = (".git",)
DEFAULT_FILENAMES = ("AGENTS.override.md", "AGENTS.md")


def _section(config: dict[str, Any], name: str) -> dict[str, Any]:
    value = config.get(name)
    return value if isinstance(value, dict) else {}


def load_config(path: Path) -> tuple[dict[str, Any], list[str]]:
    if not path.is_file():
        return {}, []
    try:
        return tomllib.loads(path.read_text(encoding="utf-8")), []
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return {}, [f"config unreadable: {exc}"]


def config_value(config: dict[str, Any], key: str, default: Any) -> Any:
    project = _section(config, "project")
    if key in project:
        return project[key]
    return config.get(key, default)


def find_root(cwd: Path, markers: tuple[str, ...]) -> tuple[Path | None, str | None]:
    if not markers:
        return cwd, "<cwd>"
    cursor = cwd
    while True:
        for marker in markers:
            if (cursor / marker).exists():
                return cursor, marker
        if cursor.parent == cursor:
            return None, None
        cursor = cursor.parent


def search_dirs(root: Path | None, cwd: Path) -> list[Path]:
    if root is None:
        return [cwd]
    dirs: list[Path] = []
    cursor = cwd
    while True:
        dirs.append(cursor)
        if cursor == root:
            return list(reversed(dirs))
        if cursor.parent == cursor:
            return list(reversed(dirs))
        cursor = cursor.parent


def unique_names(names: list[str]) -> list[str]:
    result: list[str] = []
    for name in names:
        if isinstance(name, str) and name and name not in result:
            result.append(name)
    return result


def inspect_context(cwd: Path, config_path: Path) -> dict[str, Any]:
    config, config_errors = load_config(config_path)
    raw_markers = config_value(config, "project_root_markers", list(DEFAULT_MARKERS))
    markers = (
        tuple(item for item in raw_markers if isinstance(item, str))
        if isinstance(raw_markers, list)
        else DEFAULT_MARKERS
    )
    raw_fallbacks = config_value(config, "project_doc_fallback_filenames", [])
    fallbacks = (
        [item for item in raw_fallbacks if isinstance(item, str)]
        if isinstance(raw_fallbacks, list)
        else []
    )
    raw_max = config_value(config, "project_doc_max_bytes", DEFAULT_MAX_BYTES)
    max_bytes = raw_max if isinstance(raw_max, int) and raw_max >= 0 else DEFAULT_MAX_BYTES
    names = unique_names([*DEFAULT_FILENAMES, *fallbacks])
    root, root_marker = find_root(cwd, markers)
    documents: list[dict[str, Any]] = []
    for directory in search_dirs(root, cwd):
        selected: Path | None = None
        for name in names:
            candidate = directory / name
            if candidate.is_file():
                selected = candidate
                break
        if selected is None:
            continue
        size = selected.stat().st_size
        documents.append({"path": str(selected), "bytes": size})

    loaded = 0
    for document in documents:
        remaining = max(max_bytes - loaded, 0)
        used = min(document["bytes"], remaining)
        document["loaded_bytes"] = used
        document["truncated"] = used < document["bytes"]
        loaded += used

    truncated = any(document["truncated"] for document in documents)
    if config_errors:
        status = "CONFIG_INVALID"
    elif not documents:
        status = "MISSING"
    elif truncated:
        status = "TRUNCATED"
    else:
        status = "CURRENT"
    return {
        "schema": 1,
        "status": status,
        "cwd": str(cwd),
        "project_root": str(root) if root else None,
        "root_marker": root_marker,
        "config_path": str(config_path),
        "config_errors": config_errors,
        "candidate_filenames": names,
        "project_doc_max_bytes": max_bytes,
        "loaded_bytes": loaded,
        "documents": documents,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path, help="Codex config.toml to inspect")
    parser.add_argument(
        "--json", action="store_true", help="print machine-readable JSON"
    )
    parser.add_argument(
        "--check", action="store_true", help="return non-zero unless context is CURRENT"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cwd = args.cwd.expanduser().resolve()
    config_path = (
        args.config.expanduser().resolve()
        if args.config
        else Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser().resolve()
        / "config.toml"
    )
    result = inspect_context(cwd, config_path)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"CODEX_CONTEXT: {result['status']}")
        print(f"PROJECT_ROOT: {result['project_root'] or 'UNKNOWN'}")
        print(f"DOCUMENTS: {', '.join(item['path'] for item in result['documents']) or 'NONE'}")
        print(f"BYTE_BUDGET: {result['project_doc_max_bytes']}")
        print(f"LOADED_BYTES: {result['loaded_bytes']}")
        print(f"TRUNCATED: {'YES' if result['status'] == 'TRUNCATED' else 'NO'}")
    return 0 if not args.check or result["status"] == "CURRENT" else 1


if __name__ == "__main__":
    sys.exit(main())
