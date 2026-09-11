from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "nobrainer-codex-context" / "scripts" / "codex_context.py"


class CodexContextProbeTests(unittest.TestCase):
    def run_probe(self, cwd: Path, config: Path, *extra: str) -> tuple[int, dict]:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--cwd",
                str(cwd),
                "--config",
                str(config),
                "--json",
                *extra,
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode, json.loads(result.stdout)

    def test_discovers_root_to_cwd_and_reports_order(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = (Path(raw) / "repo").resolve()
            nested = (root / "packages" / "app").resolve()
            nested.mkdir(parents=True)
            (root / ".git").mkdir()
            (root / "AGENTS.md").write_text("root rules\n", encoding="utf-8")
            (nested / "AGENTS.override.md").write_text("app rules\n", encoding="utf-8")
            config = Path(raw) / "config.toml"
            config.write_text("[project]\nproject_doc_max_bytes = 1024\n", encoding="utf-8")

            code, payload = self.run_probe(nested, config)

        self.assertEqual(0, code)
        self.assertEqual("CURRENT", payload["status"])
        self.assertEqual(str(root), payload["project_root"])
        self.assertEqual(
            [str(root / "AGENTS.md"), str(nested / "AGENTS.override.md")],
            [item["path"] for item in payload["documents"]],
        )
        self.assertEqual(21, payload["loaded_bytes"])

    def test_fallback_and_truncation_are_visible(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = (Path(raw) / "repo").resolve()
            root.mkdir()
            (root / ".git").mkdir()
            (root / "CODEX_CONTEXT.md").write_text("1234567890", encoding="utf-8")
            config = Path(raw) / "config.toml"
            config.write_text(
                "[project]\nproject_doc_fallback_filenames = [\"CODEX_CONTEXT.md\"]\n"
                "project_doc_max_bytes = 5\n",
                encoding="utf-8",
            )

            code, payload = self.run_probe(root, config, "--check")

        self.assertEqual(1, code)
        self.assertEqual("TRUNCATED", payload["status"])
        self.assertEqual(["AGENTS.override.md", "AGENTS.md", "CODEX_CONTEXT.md"], payload["candidate_filenames"])
        self.assertTrue(payload["documents"][0]["truncated"])
        self.assertEqual(5, payload["loaded_bytes"])

    def test_missing_context_fails_check_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = (Path(raw) / "repo").resolve()
            root.mkdir()
            (root / ".git").mkdir()
            (root / "CODEX_CONTEXT.md").write_text("not a default Codex document\n", encoding="utf-8")
            config = Path(raw) / "config.toml"
            config.write_text("", encoding="utf-8")

            code, payload = self.run_probe(root, config, "--check")

        self.assertEqual(1, code)
        self.assertEqual("MISSING", payload["status"])
        self.assertFalse((root / "AGENTS.md").exists())


if __name__ == "__main__":
    unittest.main()
