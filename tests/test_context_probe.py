from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "nobrainer-context" / "scripts"
SCRIPT = SCRIPTS / "codex_context.py"
INVENTORY = SCRIPTS / "context_inventory.py"


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


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


SHARED = "- Run the full unit suite with python3 -m unittest before every commit.\n"


class ContextInventoryTests(unittest.TestCase):
    def inventory(self, cwd: Path, *extra: str) -> tuple[int, dict]:
        config = cwd / "missing-codex-config.toml"
        result = subprocess.run(
            [sys.executable, str(INVENTORY), "--cwd", str(cwd), "--codex-config", str(config), "--json", *extra],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual("", result.stderr)
        return result.returncode, json.loads(result.stdout)

    def repo(self, raw: str) -> Path:
        root = (Path(raw) / "repo").resolve()
        (root / ".git").mkdir(parents=True)
        return root

    def paths(self, payload: dict, client: str) -> dict[str, str]:
        return {item["path"]: item["mode"] for item in payload["clients"][client]["files"]}

    def test_pointer_layout_is_current_and_each_client_reads_the_source(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = self.repo(raw)
            write(root / "AGENTS.md", "# Rules\n" + SHARED)
            write(root / "CLAUDE.md", "@AGENTS.md\n\nUse the Claude review command.\n")
            write(root / "GEMINI.md", "@./AGENTS.md\n")
            write(root / ".claude/rules/api.md", "---\npaths:\n  - src/api/**\n---\nAPI rule\n")
            before = sorted(p.relative_to(root) for p in root.rglob("*"))
            code, payload = self.inventory(root, "--check")
            after = sorted(p.relative_to(root) for p in root.rglob("*"))

        self.assertEqual(0, code, payload["findings"])
        self.assertEqual("CURRENT", payload["status"])
        self.assertEqual(before, after)
        self.assertEqual({"CLAUDE.md": "launch", "AGENTS.md": "import", ".claude/rules/api.md": "on_demand"},
                         self.paths(payload, "claude"))
        self.assertEqual({"GEMINI.md": "launch", "AGENTS.md": "import"}, self.paths(payload, "gemini"))
        self.assertEqual({"AGENTS.md": "launch"}, self.paths(payload, "codex"))
        self.assertEqual({"AGENTS.md": "launch"}, self.paths(payload, "opencode"))
        self.assertEqual("AGENTS.md", payload["source_of_truth_candidate"])
        self.assertEqual([], payload["duplicates"])

    def test_claude_reads_agents_only_without_claude_files(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = self.repo(raw)
            write(root / "AGENTS.md", SHARED)
            _, alone = self.inventory(root, "--client", "claude")
            write(root / "CLAUDE.local.md", "personal note\n")
            _, local = self.inventory(root, "--client", "claude")

        self.assertEqual({"AGENTS.md": "launch"}, self.paths(alone, "claude"))
        self.assertEqual({"CLAUDE.local.md": "launch"}, self.paths(local, "claude"))
        self.assertEqual(["claude"], list(local["clients"]))

    def test_copies_duplicates_and_line_guidance_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = self.repo(raw)
            body = "# Rules\n" + SHARED + "".join(f"line {n}\n" for n in range(210))
            write(root / "AGENTS.md", body)
            write(root / "CLAUDE.md", body)
            write(root / ".github/copilot-instructions.md", "Intro\n" + SHARED)
            code, payload = self.inventory(root, "--check")

        self.assertEqual(1, code)
        self.assertEqual("ATTENTION", payload["status"])
        self.assertIn(["AGENTS.md", "CLAUDE.md"], payload["identical_copies"])
        locations = payload["duplicates"][0]["locations"]
        self.assertEqual({"AGENTS.md:2", "CLAUDE.md:2", ".github/copilot-instructions.md:2"}, set(locations))
        self.assertTrue(any("CLAUDE.md has 212 lines" in item for item in payload["findings"]))
        self.assertGreater(payload["clients"]["copilot"]["repeated_lines"], 0)

    def test_cursor_rules_and_copilot_scopes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = self.repo(raw)
            write(root / ".cursor/rules/always.mdc", "---\nalwaysApply: true\n---\nAlways\n")
            write(root / ".cursor/rules/ts.mdc", "---\nglobs: src/**/*.ts\nalwaysApply: false\n---\nTS\n")
            write(root / ".cursor/rules/ignored.md", "plain markdown is ignored\n")
            write(root / ".cursorrules", "legacy\n")
            write(root / ".github/instructions/py.instructions.md", "---\napplyTo: '**/*.py'\n---\nPy\n")
            _, payload = self.inventory(root, "--client", "cursor", "--client", "copilot")

        self.assertEqual({".cursor/rules/always.mdc": "launch", ".cursor/rules/ts.mdc": "conditional",
                          ".cursorrules": "legacy"}, self.paths(payload, "cursor"))
        self.assertEqual({".github/instructions/py.instructions.md": "conditional"}, self.paths(payload, "copilot"))

    def test_gemini_file_name_setting_and_opencode_instructions(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = self.repo(raw)
            write(root / "AGENTS.md", "shared\n")
            write(root / "CONVENTIONS.md", "conventions\n")
            write(root / ".gemini/settings.json", json.dumps({"context": {"fileName": ["AGENTS.md", "GEMINI.md"]}}))
            write(root / "opencode.json", json.dumps({"instructions": ["CONVENTIONS.md", "https://example.com/x.md"]}))
            _, payload = self.inventory(root, "--client", "gemini", "--client", "opencode")

        self.assertEqual({"AGENTS.md": "launch"}, self.paths(payload, "gemini"))
        self.assertEqual({"AGENTS.md": "launch", "CONVENTIONS.md": "launch"}, self.paths(payload, "opencode"))

    def test_imports_inside_code_are_ignored_and_loops_stop(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = self.repo(raw)
            write(root / "CLAUDE.md", "Mention `@SECRET.md` literally.\n```\n@OTHER.md\n```\n@a.md\n")
            write(root / "a.md", "@b.md\n")
            write(root / "b.md", "@a.md\n")
            write(root / "SECRET.md", "x\n")
            write(root / "OTHER.md", "y\n")
            _, payload = self.inventory(root, "--client", "claude")

        self.assertEqual({"CLAUDE.md": "launch", "a.md": "import", "b.md": "import"}, self.paths(payload, "claude"))

    def test_goal_pointer_states(self) -> None:
        goal = "GOAL_ID: g-1\nOUTCOME: ship\nSTATUS: ACTIVE\n"
        with tempfile.TemporaryDirectory() as raw:
            root = self.repo(raw)
            write(root / "AGENTS.md", SHARED)
            write(root / "tasks/GOAL.md", goal)
            _, missing = self.inventory(root)
            write(root / "AGENTS.md", SHARED + "Current goal: tasks/GOAL.md\n")
            _, pointed = self.inventory(root)
            write(root / "AGENTS.md", SHARED + "Current goal: tasks/old-goal.md\n")
            _, stale = self.inventory(root)

        self.assertEqual("NOT_POINTED", missing["goal"]["status"])
        self.assertEqual("POINTED", pointed["goal"]["status"])
        self.assertEqual("STALE_POINTER", stale["goal"]["status"])
        self.assertEqual(["tasks/old-goal.md"], stale["goal"]["missing_paths"])

    def test_codex_truncation_is_a_finding(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = self.repo(raw)
            write(root / "AGENTS.md", "x" * 64)
            config = Path(raw) / "config.toml"
            config.write_text("project_doc_max_bytes = 10\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(INVENTORY), "--cwd", str(root), "--codex-config", str(config),
                 "--client", "codex", "--check"],
                cwd=ROOT, capture_output=True, text=True, check=False,
            )

        self.assertEqual(1, result.returncode)
        self.assertIn("CONTEXT: ATTENTION", result.stdout)
        self.assertIn("truncated", result.stdout)

    def test_empty_project_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            code, payload = self.inventory(self.repo(raw), "--check")

        self.assertEqual(1, code)
        self.assertEqual("MISSING", payload["status"])


if __name__ == "__main__":
    unittest.main()
