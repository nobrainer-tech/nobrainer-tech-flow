"""The remote MCP server in mcp/ must never ship inside the npm package or the plugin ZIP."""
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


if __name__ == "__main__":
    unittest.main()
