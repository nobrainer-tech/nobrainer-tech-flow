from __future__ import annotations

import importlib.util
import json
import unittest
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_release_channels", ROOT / "scripts" / "check_release_channels.py")
channels = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(channels)


def fake(version: str, *, mcp: str | None = None, changelog: str | None = None, npm: str | None = None, prs=(),
         registry: tuple[str, str] | None = (channels.REGISTRY_NAME, "")):
    def get(url: str, body, headers) -> str:
        if url.startswith(channels.REGISTRY_API):
            # The probe must ask for this exact version; a search result page would not do.
            assert url == channels.registry_url(version), url
            if registry is None:
                raise urllib.error.HTTPError(url, 404, "Not Found", None, None)
            name, listed_version = registry
            return json.dumps({"server": {"name": name, "version": listed_version or version}})
        if url.endswith(f"nobrainer-tech-flow/releases/tags/v{version}"):
            names = [f"nobrainer-tech-flow-{version}-plugin.zip", f"nobrainer-tech-flow-{version}.tgz"]
            return json.dumps({"draft": False, "assets": [{"name": n} for n in names]})
        if url.endswith(f"nobrainer-tech-flow-plugin/releases/tags/v{version}"):
            return json.dumps({"draft": False, "assets": [{"name": f"nobrainer-tech-flow-{version}-native.zip"}]})
        if "registry.npmjs.org" in url:
            return json.dumps({"dist-tags": {"latest": npm or version}})
        if url == channels.MCP_URL:
            return json.dumps({"result": {"serverInfo": {"version": mcp or f"1.0.0+flow.{version}"}}})
        if "/pulls?state=open" in url:
            return json.dumps([pr for pr in prs if pr["repo"] in url])
        if url == channels.CHANGELOG_URL:
            return changelog if changelog is not None else f"<h2>v{version}</h2>"
        raise AssertionError(url)
    return get


NOW = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)


class ReleaseChannelTests(unittest.TestCase):
    def failures(self, **kwargs) -> dict[str, str]:
        return {name: problem for name, problem in channels.check("2.9.0", fake("2.9.0", **kwargs), NOW) if problem}

    def test_every_channel_passes_when_it_carries_the_version(self) -> None:
        self.assertEqual({}, self.failures())

    def test_stale_mcp_cards_fail(self) -> None:
        self.assertIn("MCP server", self.failures(mcp="1.0.0+flow.2.7.3"))

    def test_missing_website_changelog_entry_fails(self) -> None:
        self.assertIn("Website changelog", self.failures(changelog="<h2>v2.6.0</h2><p>2.9.01</p>"))

    def test_stale_npm_latest_fails(self) -> None:
        self.assertIn("npm", self.failures(npm="2.8.0"))

    def test_a_registry_without_this_version_fails(self) -> None:
        self.assertIn("2.9.0 is not listed", self.failures(registry=None)["MCP Registry"])
        # An answer for another version or another publisher's server never counts as ours.
        self.assertIn("2.8.0", self.failures(registry=(channels.REGISTRY_NAME, "2.8.0"))["MCP Registry"])
        other = self.failures(registry=("io.github.someone/nobrainer-tech-flow", "2.9.0"))
        self.assertIn("io.github.someone", other["MCP Registry"])

    def test_the_registry_probe_asks_for_the_exact_version(self) -> None:
        # Searching would page through every historical version and miss a release on page two.
        self.assertEqual(
            "https://registry.modelcontextprotocol.io/v0.1/servers/"
            "io.github.nobrainer-tech%2Fnobrainer-tech-flow/versions/2.9.0",
            channels.registry_url("2.9.0"),
        )

    def test_the_registry_entry_names_the_live_server_and_fits_the_registry_limits(self) -> None:
        entry = json.loads((ROOT / "mcp" / "server.json").read_text(encoding="utf-8"))
        self.assertEqual(channels.REGISTRY_NAME, entry["name"])
        self.assertEqual([{"type": "streamable-http", "url": channels.MCP_URL}], entry["remotes"])
        self.assertLessEqual(len(entry["description"]), 100)
        self.assertNotIn("packages", entry)

    def test_a_pull_request_left_open_for_a_day_fails(self) -> None:
        stale = {"repo": "nobrainer-tech-flow/", "number": 126, "created_at": "2026-10-30T08:23:01Z"}
        fresh = {"repo": "nobrainer-tech-flow-plugin/", "number": 22, "created_at": "2026-10-31T11:00:00Z"}
        problem = self.failures(prs=[stale, fresh]).get("Open pull requests", "")
        self.assertIn("nobrainer-tech-flow#126", problem)
        self.assertNotIn("#22", problem)

    def test_an_unreadable_channel_is_a_failure(self) -> None:
        def broken(url, body, headers):
            raise OSError("offline")
        results = channels.check("2.9.0", broken, NOW)
        self.assertTrue(all(problem and "read failed" in problem for _, problem in results))


if __name__ == "__main__":
    unittest.main()
