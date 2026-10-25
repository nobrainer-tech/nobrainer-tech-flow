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
        self.assertEqual(1, names.count(".mcp.json"))
        self.assertEqual({"mcpServers": {"nobrainer-tech-flow": {"url": "https://mcp.nobrainer.tech/mcp"}}}, config)
        self.assertEqual("./.mcp.json", codex["mcpServers"])
        self.assertNotIn("mcpServers", claude)
        self.assertNotIn("mcpServers", portable)
        self.assertEqual("https://nobrainer.tech/flow/privacy/", codex["interface"]["privacyPolicyURL"])


if __name__ == "__main__":
    unittest.main()
