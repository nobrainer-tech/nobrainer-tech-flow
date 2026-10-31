#!/usr/bin/env python3
"""Read back every public release channel for one version (docs/RELEASING.md).

Usage: python3 scripts/check_release_channels.py 2.9.0

Prints one PASS or FAIL line per channel and exits 1 when any channel does not carry
the version, or when a pull request in the Flow repositories has been open for more
than a day. A release is finished only when this prints no FAIL; a FAIL that cannot
be fixed yet is reported as a gap, never as done. Read-only: it changes nothing.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Callable

CANONICAL = "nobrainer-tech/nobrainer-tech-flow"
NATIVE = "nobrainer-tech/nobrainer-tech-flow-plugin"
MCP_URL = "https://mcp.nobrainer.tech/mcp"
CHANGELOG_URL = "https://nobrainer.tech/flow/changelog/"
STALE_PR_AGE = timedelta(days=1)

Fetch = Callable[[str, bytes | None, dict[str, str]], str]


def fetch(url: str, body: bytes | None = None, headers: dict[str, str] | None = None) -> str:
    request = urllib.request.Request(url, data=body, headers={"user-agent": "flow-release-readback", **(headers or {})})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def github_release(get: Fetch, repo: str, version: str, assets: tuple[str, ...]) -> str | None:
    release = json.loads(get(f"https://api.github.com/repos/{repo}/releases/tags/v{version}", None, {}))
    if release.get("draft"):
        return "release is a draft"
    names = {asset["name"] for asset in release.get("assets", [])}
    missing = [name for name in assets if name not in names]
    return f"missing assets {missing}" if missing else None


def npm_latest(get: Fetch, version: str) -> str | None:
    latest = json.loads(get("https://registry.npmjs.org/nobrainer-tech-flow", None, {}))["dist-tags"]["latest"]
    return None if latest == version else f"npm latest is {latest}"


def mcp_server(get: Fetch, version: str) -> str | None:
    body = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                   "clientInfo": {"name": "flow-release-readback", "version": "1"}},
    }).encode()
    headers = {"content-type": "application/json", "accept": "application/json, text/event-stream",
               "mcp-protocol-version": "2025-06-18"}
    served = json.loads(get(MCP_URL, body, headers))["result"]["serverInfo"]["version"]
    return None if served.endswith(f"+flow.{version}") else f"server reports {served}"


def website_changelog(get: Fetch, version: str) -> str | None:
    text = get(CHANGELOG_URL, None, {})
    pattern = r"(?<![\d.])v?" + re.escape(version) + r"(?![\d.])"
    return None if re.search(pattern, text) else f"{CHANGELOG_URL} has no {version} entry"


def open_pull_requests(get: Fetch, now: datetime) -> str | None:
    stale = []
    for repo in (CANONICAL, NATIVE):
        for pr in json.loads(get(f"https://api.github.com/repos/{repo}/pulls?state=open&per_page=100", None, {})):
            created = datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00"))
            if now - created > STALE_PR_AGE:
                stale.append(f"{repo}#{pr['number']}")
    return f"open for more than a day: {', '.join(stale)}" if stale else None


def check(version: str, get: Fetch = lambda u, b, h: fetch(u, b, h),
          now: datetime | None = None) -> list[tuple[str, str | None]]:
    now = now or datetime.now(timezone.utc)
    channels = [
        ("GitHub release", lambda: github_release(get, CANONICAL, version, (
            f"nobrainer-tech-flow-{version}-plugin.zip", f"nobrainer-tech-flow-{version}.tgz"))),
        ("npm", lambda: npm_latest(get, version)),
        ("Native plugin release", lambda: github_release(get, NATIVE, version, (
            f"nobrainer-tech-flow-{version}-native.zip",))),
        ("MCP server", lambda: mcp_server(get, version)),
        ("Website changelog", lambda: website_changelog(get, version)),
        ("Open pull requests", lambda: open_pull_requests(get, now)),
    ]
    results = []
    for name, probe in channels:
        try:
            results.append((name, probe()))
        except Exception as error:  # a failed read is a FAIL, never a pass
            results.append((name, f"read failed: {error}"))
    return results


def main(argv: list[str]) -> int:
    if len(argv) != 1 or not re.fullmatch(r"\d+\.\d+\.\d+", argv[0]):
        print("usage: check_release_channels.py X.Y.Z", file=sys.stderr)
        return 2
    results = check(argv[0])
    for name, problem in results:
        print(f"{'FAIL' if problem else 'PASS'} {name}" + (f": {problem}" if problem else ""))
    return 1 if any(problem for _, problem in results) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
