#!/usr/bin/env python3
"""Read-only daily check for a newer nobrainer-tech-flow GitHub release."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit


RELEASE_API = "https://api.github.com/repos/nobrainer-tech/nobrainer-tech-flow/releases/latest"
TIMEOUT_SECONDS = 5
MAX_RESPONSE_BYTES = 256 * 1024
SUPPORTED_CLIENTS = ("agents", "claude", "codex", "copilot", "opencode")
VERSION_RE = re.compile(
    r"^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+[0-9A-Za-z.-]+)?$"
)


class UpdateCheckError(Exception):
    """A bounded API or local-state failure suitable for a short CLI report."""


def parse_version(value: str) -> tuple[int, int, int, tuple[tuple[int, Any], ...] | None]:
    """Parse SemVer without guessing from arbitrary version strings."""
    match = VERSION_RE.fullmatch(value.strip())
    if not match:
        raise UpdateCheckError(f"unsupported version format: {value!r}")
    core = tuple(int(match.group(index)) for index in (1, 2, 3))
    prerelease = match.group(4)
    if prerelease is None:
        return core[0], core[1], core[2], None
    parts: list[tuple[int, Any]] = []
    for item in prerelease.split("."):
        if item.isdigit():
            if len(item) > 1 and item.startswith("0"):
                raise UpdateCheckError(f"invalid numeric prerelease identifier: {item!r}")
            parts.append((0, int(item)))
        else:
            parts.append((1, item))
    return core[0], core[1], core[2], tuple(parts)


def is_newer(latest: str, installed: str) -> bool:
    """Return whether latest is strictly newer according to SemVer precedence."""
    left = parse_version(latest)
    right = parse_version(installed)
    if left[:3] != right[:3]:
        return left[:3] > right[:3]
    left_pre, right_pre = left[3], right[3]
    if left_pre is None:
        return right_pre is not None
    if right_pre is None:
        return False
    for left_item, right_item in zip(left_pre, right_pre):
        if left_item != right_item:
            # Numeric identifiers have lower precedence than non-numeric ones.
            if left_item[0] != right_item[0]:
                return left_item[0] < right_item[0]
            return left_item[1] > right_item[1]
    return len(left_pre) > len(right_pre)


def fetch_latest_release(timeout: float = TIMEOUT_SECONDS) -> tuple[str, str]:
    """Fetch only the public latest-release metadata; never execute remote data."""
    request = urllib.request.Request(
        RELEASE_API,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "NoBrainer-Tech-Flow-update-check",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise UpdateCheckError(f"GitHub release check failed: {type(exc).__name__}") from None
    if len(raw) > MAX_RESPONSE_BYTES:
        raise UpdateCheckError("GitHub release metadata exceeded the size limit")
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise UpdateCheckError("GitHub returned invalid release metadata") from None
    if not isinstance(data, dict) or data.get("draft") is not False or data.get("prerelease") is not False:
        raise UpdateCheckError("GitHub response is not a published stable release")
    tag = data.get("tag_name")
    url = data.get("html_url")
    if not isinstance(tag, str) or not isinstance(url, str):
        raise UpdateCheckError("GitHub release metadata is missing a valid tag or release URL")
    parse_version(tag)
    parsed_url = urlsplit(url)
    expected_path = "/nobrainer-tech/nobrainer-tech-flow/releases/tag/" + quote(tag, safe="")
    if (
        parsed_url.scheme != "https"
        or parsed_url.netloc != "github.com"
        or parsed_url.path != expected_path
        or parsed_url.query
        or parsed_url.fragment
    ):
        raise UpdateCheckError("GitHub release URL does not match the official repository and tag")
    return tag, url


def state_root() -> Path:
    """Return a portable per-user state directory outside the source checkout."""
    override = os.environ.get("NOBRAINER_TECH_FLOW_STATE_HOME")
    if override:
        return Path(override).expanduser() / "update-checks"
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return base / "nobrainer-tech-flow" / "update-checks"


def _read_state(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"schema_version": 1, "checks": {}, "latest_verified": None}
    except (OSError, json.JSONDecodeError):
        return {"schema_version": 1, "checks": {}, "latest_verified": None}
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        return {"schema_version": 1, "checks": {}, "latest_verified": None}
    if not isinstance(value.get("checks"), dict):
        value["checks"] = {}
    return value


def _write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        pass
    temp = path.with_suffix(f".{os.getpid()}.tmp")
    try:
        temp.write_text(json.dumps(state, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        try:
            os.chmod(temp, 0o600)
        except OSError:
            pass
        temp.replace(path)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def read_installed_version(path: Path | None = None) -> str:
    version_file = path or Path(__file__).resolve().parents[1] / "VERSION"
    try:
        version = version_file.read_text(encoding="utf-8").strip()
    except OSError:
        raise UpdateCheckError(
            "installed skill version is unavailable; include its VERSION file or pass --installed-version"
        ) from None
    if not version:
        raise UpdateCheckError("installed skill VERSION file is empty; pass --installed-version")
    parse_version(version)
    return version


def check_update(
    client: str,
    installed: str,
    *,
    force: bool = False,
    unattended: bool = False,
    now: dt.datetime | None = None,
    root: Path | None = None,
    fetcher=fetch_latest_release,
) -> dict[str, Any]:
    """Check/cached-read one client and installed ref for the local calendar day."""
    if client not in SUPPORTED_CLIENTS:
        raise UpdateCheckError(f"unsupported client: {client!r}")
    parse_version(installed)
    today = (now or dt.datetime.now().astimezone()).date().isoformat()
    client_root = (root or state_root()) / client
    path = client_root / "state.json"
    state = _read_state(path)
    key = f"{today}|{installed}"
    cached = state["checks"].get(key)
    if isinstance(cached, dict) and not force:
        return {**cached, "cached": True, "unattended": unattended}

    checked_at = (now or dt.datetime.now().astimezone()).isoformat(timespec="seconds")
    try:
        latest, release_url = fetcher()
        parse_version(latest)
        result: dict[str, Any] = {
            "date": today,
            "checked_at": checked_at,
            "client": client,
            "installed_ref": installed,
            "latest_ref": latest,
            "release_url": release_url,
            "status": "UPDATE_AVAILABLE" if is_newer(latest, installed) else "CURRENT",
            "stale": False,
        }
        state["latest_verified"] = {
            "latest_ref": latest,
            "release_url": release_url,
            "checked_at": checked_at,
            "date": today,
        }
    except UpdateCheckError as exc:
        previous = state.get("latest_verified")
        result = {
            "date": today,
            "checked_at": checked_at,
            "client": client,
            "installed_ref": installed,
            "latest_ref": previous.get("latest_ref") if isinstance(previous, dict) else None,
            "release_url": previous.get("release_url") if isinstance(previous, dict) else None,
            "status": "CHECK_FAILED",
            "error": str(exc),
            "stale": isinstance(previous, dict),
            "previously_checked_at": previous.get("checked_at") if isinstance(previous, dict) else None,
        }
    result["cached"] = False
    result["unattended"] = unattended
    state["checks"][key] = result
    # Bound local state while retaining the latest known successful release.
    if len(state["checks"]) > 90:
        ordered = sorted(state["checks"].items(), key=lambda item: item[1].get("checked_at", ""))
        for old_key, _ in ordered[: len(state["checks"]) - 90]:
            del state["checks"][old_key]
    try:
        _write_state(path, state)
    except OSError as exc:
        raise UpdateCheckError(f"could not save update-check state: {type(exc).__name__}") from None
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", required=True, choices=SUPPORTED_CLIENTS)
    parser.add_argument(
        "--installed-version",
        help="Override the version in the installed skill's adjacent VERSION file",
    )
    parser.add_argument("--force", action="store_true", help="Fetch again even if already checked today")
    parser.add_argument("--unattended", action="store_true", help="Emit a stable machine-readable line for schedulers")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        installed = args.installed_version or read_installed_version()
        result = check_update(args.client, installed, force=args.force, unattended=args.unattended)
    except UpdateCheckError as exc:
        print(f"UPDATE_CHECK: ERROR: {exc}", file=sys.stderr)
        return 2

    status = result["status"]
    if args.unattended:
        fields = [
            f"status={status}",
            f"client={result['client']}",
            f"installed_ref={result['installed_ref']}",
            f"latest_ref={result.get('latest_ref') or 'unknown'}",
            f"cached={str(result['cached']).lower()}",
            f"stale={str(result.get('stale', False)).lower()}",
        ]
        print("UPDATE_CHECK: " + " ".join(fields))
    else:
        print(f"UPDATE_CHECK: {status} client={result['client']} installed={result['installed_ref']} latest={result.get('latest_ref') or 'unknown'}")
        if status == "UPDATE_AVAILABLE":
            print(f"Release: {result['release_url']}")
            print(
                f"Next: obtain and review release tag {result['latest_ref']} from the official repository; "
                "verify its source and release evidence, then run the installer dry-run, apply "
                "the reviewed update, and read back the installed files and version."
            )
        elif status == "CHECK_FAILED":
            print(f"Details: {result['error']}")
            if result.get("stale"):
                print(f"Last verified release: {result['latest_ref']} at {result['previously_checked_at']} (stale; verify online before acting)")
    return 0 if status in ("CURRENT", "UPDATE_AVAILABLE") else 1


if __name__ == "__main__":
    raise SystemExit(main())
