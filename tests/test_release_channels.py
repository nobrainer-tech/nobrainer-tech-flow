from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_release_channels", ROOT / "scripts" / "check_release_channels.py")
channels = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(channels)


def fake(version: str, *, mcp: str | None = None, changelog: str | None = None, npm: str | None = None):
    def get(url: str, body, headers) -> str:
        if url.endswith(f"nobrainer-tech-flow/releases/tags/v{version}"):
            names = [f"nobrainer-tech-flow-{version}-plugin.zip", f"nobrainer-tech-flow-{version}.tgz"]
            return json.dumps({"draft": False, "assets": [{"name": n} for n in names]})
        if url.endswith(f"nobrainer-tech-flow-plugin/releases/tags/v{version}"):
            return json.dumps({"draft": False, "assets": [{"name": f"nobrainer-tech-flow-{version}-native.zip"}]})
        if "registry.npmjs.org" in url:
            return json.dumps({"dist-tags": {"latest": npm or version}})
        if url == channels.MCP_URL:
            return json.dumps({"result": {"serverInfo": {"version": mcp or f"1.0.0+flow.{version}"}}})
        if url == channels.CHANGELOG_URL:
            return changelog if changelog is not None else f"<h2>v{version}</h2>"
        raise AssertionError(url)
    return get


class ReleaseChannelTests(unittest.TestCase):
    def failures(self, **kwargs) -> dict[str, str]:
        return {name: problem for name, problem in channels.check("2.9.0", fake("2.9.0", **kwargs)) if problem}

    def test_every_channel_passes_when_it_carries_the_version(self) -> None:
        self.assertEqual({}, self.failures())

    def test_stale_mcp_cards_fail(self) -> None:
        self.assertIn("MCP server", self.failures(mcp="1.0.0+flow.2.7.3"))

    def test_missing_website_changelog_entry_fails(self) -> None:
        self.assertIn("Website changelog", self.failures(changelog="<h2>v2.6.0</h2><p>2.9.01</p>"))

    def test_stale_npm_latest_fails(self) -> None:
        self.assertIn("npm", self.failures(npm="2.8.0"))

    def test_an_unreadable_channel_is_a_failure(self) -> None:
        def broken(url, body, headers):
            raise OSError("offline")
        results = channels.check("2.9.0", broken)
        self.assertTrue(all(problem and "read failed" in problem for _, problem in results))


if __name__ == "__main__":
    unittest.main()
