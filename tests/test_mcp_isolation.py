"""The remote MCP server in mcp/ must never ship inside the npm package or the plugin ZIP.

The plugin ZIP only declares the hosted server in .mcp.json (see test_plugin_zip_declares_one_remote_server);
the server's source code stays out of every package.
"""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NPM = shutil.which("npm")


class McpIsolationTests(unittest.TestCase):
    def test_mcp_folder_exists_with_its_own_package(self):
        package = json.loads((ROOT / "mcp" / "package.json").read_text(encoding="utf-8"))
        self.assertTrue(package["private"])
        self.assertEqual("nobrainer-tech-flow-mcp", package["name"])
        root = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        self.assertFalse(any(entry.lstrip("./").startswith("mcp") for entry in root["files"]))

    @unittest.skipUnless(NPM, "npm is needed for the packed-file list")
    def test_npm_package_contains_no_mcp_files(self):
        result = subprocess.run([NPM, "pack", "--dry-run", "--json"], cwd=ROOT,
                                capture_output=True, text=True, check=True)
        files = [entry["path"] for entry in json.loads(result.stdout)[0]["files"]]
        self.assertGreater(len(files), 50)
        self.assertEqual([], [path for path in files if path == "mcp" or path.startswith("mcp/")])

    def test_plugin_zip_is_byte_identical_across_builds(self):
        with tempfile.TemporaryDirectory() as tmp:
            digests = []
            for name in ("first.zip", "second.zip"):
                output = Path(tmp) / name
                subprocess.run([sys.executable, str(ROOT / "scripts" / "build_plugin.py"), "--output", str(output)],
                               check=True, capture_output=True, text=True)
                digests.append(output.read_bytes())
            self.assertEqual(digests[0], digests[1])

    def test_plugin_zip_contains_no_mcp_files(self):
        with tempfile.TemporaryDirectory(prefix="flow-mcp-isolation-") as folder:
            output = Path(folder) / "plugin.zip"
            subprocess.run([sys.executable, str(ROOT / "scripts" / "build_plugin.py"), "--output", str(output)],
                           cwd=ROOT, capture_output=True, text=True, check=True)
            with zipfile.ZipFile(output) as archive:
                names = archive.namelist()
        self.assertTrue(any(name.startswith("skills/") for name in names))
        self.assertEqual([], [name for name in names if name.startswith("mcp/") or "/mcp/" in name])

    def test_plugin_zip_declares_one_remote_server(self):
        # OpenAI's plugin directory rejects skills-only submissions; its Codex package format
        # is exactly {"mcpServers": {name: {"url": ...}}} with no type, $schema or headers.
        with tempfile.TemporaryDirectory(prefix="flow-mcp-declared-") as folder:
            output = Path(folder) / "plugin.zip"
            subprocess.run([sys.executable, str(ROOT / "scripts" / "build_plugin.py"), "--output", str(output)],
                           cwd=ROOT, capture_output=True, text=True, check=True)
            with zipfile.ZipFile(output) as archive:
                names = archive.namelist()
                config = json.loads(archive.read(".mcp.json"))
                codex = json.loads(archive.read(".codex-plugin/plugin.json"))
                claude = json.loads(archive.read(".claude-plugin/plugin.json"))
                portable = json.loads(archive.read("plugin.json"))
                portable_mcp = json.loads(archive.read("mcp.json"))
        self.assertEqual(1, names.count(".mcp.json"))
        # The root plugin.json carries extensions.com.openai, so OpenAI reads the package as
        # portable, ignores .codex-plugin/plugin.json and discovers the root mcp.json instead.
        self.assertIn("com.openai", portable["extensions"])
        self.assertEqual(1, names.count("mcp.json"))
        self.assertEqual({
            "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
            "mcpServers": {"nobrainer-tech-flow": {"type": "streamable-http", "url": "https://mcp.nobrainer.tech/mcp"}},
        }, portable_mcp)
        self.assertFalse((ROOT / "mcp.json").exists())
        review = portable["extensions"]["com.openai"]["review"]
        self.assertEqual(5, len(review["test_cases"]["positive"]))
        self.assertEqual(3, len(review["test_cases"]["negative"]))
        for case in review["test_cases"]["positive"]:
            self.assertTrue(all(case.get(key) for key in ("description", "prompt", "tools_triggered", "expected_behavior")))
        tools = {"start_flow_task", "get_flow_step", "check_flow_evidence", "check_flow_done",
                 "draft_flow_handoff", "recommend_flow_model"}
        named = {name.strip() for case in review["test_cases"]["positive"] for name in case["tools_triggered"].split(",")}
        self.assertEqual(tools, named)
        self.assertTrue(review["demo_recording_url"].startswith("https://"))
        self.assertNotIn("test_credentials", review)
        self.assertNotIn("reviewer_instructions", review)
        self.assertEqual({"mcpServers": {"nobrainer-tech-flow": {"url": "https://mcp.nobrainer.tech/mcp"}}}, config)
        self.assertEqual("./.mcp.json", codex["mcpServers"])
        self.assertNotIn("mcpServers", claude)
        self.assertNotIn("mcpServers", portable)
        self.assertEqual("https://nobrainer.tech/flow/privacy/", codex["interface"]["privacyPolicyURL"])


if __name__ == "__main__":
    unittest.main()
