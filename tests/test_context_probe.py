from __future__ import annotations

import json
import os
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
    def inventory(self, cwd: Path, *extra: str, home: Path | None = None) -> tuple[int, dict]:
        config = cwd / "missing-codex-config.toml"
        env = dict(os.environ)
        if home is not None:
            env.update(HOME=str(home), USERPROFILE=str(home))
            for name in ("CODEX_HOME", "CLAUDE_CONFIG_DIR", "XDG_CONFIG_HOME"):
                env.pop(name, None)
        result = subprocess.run(
            [sys.executable, str(INVENTORY), "--cwd", str(cwd), "--codex-config", str(config), "--json", *extra],
            cwd=ROOT, capture_output=True, text=True, check=False, env=env,
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

    def test_home_imports_global_files_and_odd_opencode_entries(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = self.repo(raw)
            home = (Path(raw) / "home").resolve()
            write(home / "shared.md", "shared notes\n")
            write(home / ".claude/CLAUDE.md", "user rules\n")
            write(root / "CLAUDE.md", "@~/shared.md\n")
            write(root / "AGENTS.md", "agents\n")
            outside = Path(raw) / "outside.md"
            write(outside, "absolute entry\n")
            entries = [str(outside), "", "~/shared.md", "docs/**/*.md", 7]
            write(root / "opencode.json", json.dumps({"instructions": entries}))
            write(root / "docs/a/b.md", "nested\n")
            code, payload = self.inventory(root, "--client", "claude", "--client", "opencode",
                                           "--include-global", home=home)

        self.assertIn(code, (0, 1))
        claude = self.paths(payload, "claude")
        self.assertEqual("import", claude["~/shared.md"])
        self.assertEqual("global", claude["~/.claude/CLAUDE.md"])
        opencode = self.paths(payload, "opencode")
        for name in ("AGENTS.md", str(outside.resolve()), "~/shared.md", "docs/a/b.md"):
            self.assertIn(name, opencode)

    @unittest.skipIf(os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0), "needs POSIX permissions")
    def test_unreadable_file_is_a_finding_not_a_crash(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = self.repo(raw)
            write(root / "AGENTS.md", SHARED)
            (root / "AGENTS.md").chmod(0)
            try:
                code, payload = self.inventory(root, "--client", "opencode")
            finally:
                (root / "AGENTS.md").chmod(0o600)

        self.assertEqual(0, code)
        self.assertEqual("ATTENTION", payload["status"])
        self.assertIn("opencode: AGENTS.md cannot be read", payload["findings"])

    def test_dot_claude_pointer_resolves_relative_to_its_file(self) -> None:
        guide = (SCRIPTS.parent / "references" / "consolidate.md").read_text(encoding="utf-8")
        self.assertIn("`@../AGENTS.md`", guide)
        with tempfile.TemporaryDirectory() as raw:
            root = self.repo(raw)
            write(root / "AGENTS.md", SHARED)
            write(root / ".claude/CLAUDE.md", "@../AGENTS.md\n")
            code, payload = self.inventory(root, "--client", "claude", "--check")

        self.assertEqual(0, code, payload["findings"])
        self.assertEqual({".claude/CLAUDE.md": "launch", "AGENTS.md": "import"}, self.paths(payload, "claude"))

    def test_unresolved_import_is_a_finding(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = self.repo(raw)
            write(root / "CLAUDE.md", "# Rules\n\n@missing-security.md\n")
            code, payload = self.inventory(root, "--client", "claude", "--check")

        self.assertEqual(1, code)
        self.assertEqual("ATTENTION", payload["status"])
        self.assertIn("claude: CLAUDE.md:3 imports missing-security.md, which does not exist", payload["findings"])

    def test_claude_reads_ancestors_above_the_git_root(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = (Path(raw) / "workspace").resolve()
            root = workspace / "repo"
            (root / ".git").mkdir(parents=True)
            write(workspace / "CLAUDE.md", "workspace rules\n")
            write(root / "AGENTS.md", SHARED)
            _, payload = self.inventory(root, "--client", "claude", "--client", "codex")

        self.assertEqual({str(workspace / "CLAUDE.md"): "launch"}, self.paths(payload, "claude"))
        self.assertEqual({"AGENTS.md": "launch"}, self.paths(payload, "codex"))

    def test_descendant_instructions_are_on_demand_and_not_counted_at_launch(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = self.repo(raw)
            write(root / "AGENTS.md", SHARED)
            write(root / "CLAUDE.md", "@AGENTS.md\n")
            write(root / "src/CLAUDE.md", "src claude\n")
            write(root / "src/GEMINI.md", "src gemini\n")
            write(root / "src/AGENTS.md", "src agents\n")
            write(root / "node_modules/pkg/AGENTS.md", "vendored\n")
            _, payload = self.inventory(root)

        self.assertEqual("on_demand", self.paths(payload, "claude")["src/CLAUDE.md"])
        self.assertEqual("on_demand", self.paths(payload, "gemini")["src/GEMINI.md"])
        self.assertEqual("conditional", self.paths(payload, "cursor")["src/AGENTS.md"])
        self.assertEqual("conditional", self.paths(payload, "copilot")["src/AGENTS.md"])
        self.assertNotIn("src/AGENTS.md", self.paths(payload, "codex"))
        for client in payload["clients"]:
            self.assertNotIn("node_modules/pkg/AGENTS.md", self.paths(payload, client))
        claude = payload["clients"]["claude"]
        self.assertEqual(sum(e["bytes"] for e in claude["files"] if e["path"] in ("CLAUDE.md", "AGENTS.md")),
                         claude["launch_bytes"])

    def test_imports_keep_conditional_scope_and_startup_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = self.repo(raw)
            write(root / "CLAUDE.md", "root instructions\n")
            write(root / "shared.md", "@nested.md\nshared instruction text\n")
            write(root / "nested.md", "nested instruction text\n")
            write(root / ".claude/rules/a-scoped.md", "---\npaths: src/**\n---\n@../../shared.md\n")
            _, conditional = self.inventory(root, "--client", "claude")
            self.assertEqual("on_demand", self.paths(conditional, "claude")["shared.md"])
            self.assertEqual("on_demand", self.paths(conditional, "claude")["nested.md"])
            self.assertEqual((root / "CLAUDE.md").stat().st_size,
                             conditional["clients"]["claude"]["launch_bytes"])
            # This startup import follows the conditional one in discovery order.
            write(root / ".claude/rules/z-always.md", "@../../shared.md\n")
            _, startup = self.inventory(root, "--client", "claude")
            self.assertEqual("import", self.paths(startup, "claude")["shared.md"])
            self.assertEqual("import", self.paths(startup, "claude")["nested.md"])
            self.assertEqual(sum((root / name).stat().st_size for name in
                                 ("CLAUDE.md", "shared.md", "nested.md", ".claude/rules/z-always.md")),
                             startup["clients"]["claude"]["launch_bytes"])

    def test_opencode_jsonc_and_parse_errors(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = self.repo(raw)
            write(root / "AGENTS.md", "shared\n")
            write(root / "SECURITY.md", "security\n")
            write(root / "opencode.jsonc", '{\n  // team rules\n  "instructions": ["SECURITY.md",], /* end */\n}\n')
            _, jsonc = self.inventory(root, "--client", "opencode")
            # String contents that resemble a trailing comma are literal path bytes.
            write(root / "notes,].md", "literal filename\n")
            write(root / "opencode.jsonc", '{"instructions": ["notes,].md"]}')
            _, literal = self.inventory(root, "--client", "opencode")
            self.assertIn("notes,].md", self.paths(literal, "opencode"))
            for invalid in ('{"instructions": []} /* unclosed', '{"instructions": [], "x": tr/* gap */ue}'):
                write(root / "opencode.jsonc", invalid)
                code, problem = self.inventory(root, "--client", "opencode", "--check")
                self.assertEqual(1, code)
                self.assertTrue(any("cannot be parsed" in item for item in problem["findings"]))
            (root / "opencode.jsonc").unlink()
            write(root / "opencode.json", '{"instructions": ["SECURITY.md"')
            code, broken = self.inventory(root, "--client", "opencode", "--check")

        self.assertIn("SECURITY.md", self.paths(jsonc, "opencode"))
        self.assertEqual(1, code)
        self.assertTrue(any(item.startswith("opencode: opencode.json cannot be parsed") for item in broken["findings"]))

    def test_invalid_codex_config_fails_the_check(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = self.repo(raw)
            write(root / "AGENTS.md", SHARED)
            config = Path(raw) / "config.toml"
            config.write_text("project_doc_max_bytes = [\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(INVENTORY), "--cwd", str(root), "--codex-config", str(config),
                 "--client", "codex", "--json", "--check"],
                cwd=ROOT, capture_output=True, text=True, check=False,
            )
            payload = json.loads(result.stdout)

        self.assertEqual(1, result.returncode)
        self.assertEqual("ATTENTION", payload["status"])
        self.assertTrue(any(item.startswith("codex: config unreadable") for item in payload["findings"]))

    def test_duplicate_locations_count_lines_inside_code_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = self.repo(raw)
            write(root / "AGENTS.md", "# A\n```sh\nmake\n```\n" + SHARED)
            write(root / "CLAUDE.md", SHARED)
            _, payload = self.inventory(root)

        self.assertEqual({"AGENTS.md:5", "CLAUDE.md:1"}, set(payload["duplicates"][0]["locations"]))

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

    def test_completed_goals_need_no_pointer_but_dangling_paths_still_fail(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = self.repo(raw)
            write(root / "tasks/GOAL.md", "GOAL_ID: historical\nSTATUS: COMPLETE\n")
            for pointer in ("", "Current goal: tasks/GOAL.md\n"):
                with self.subTest(pointer=pointer):
                    write(root / "AGENTS.md", SHARED + pointer)
                    code, payload = self.inventory(root, "--client", "codex", "--check")
                    self.assertEqual(0, code, payload["findings"])
                    self.assertEqual("NONE", payload["goal"]["status"])
                    self.assertEqual([{"path": "tasks/GOAL.md", "status": "COMPLETE"}],
                                     payload["goal"]["goal_files"])
            write(root / "AGENTS.md", SHARED + "Current goal: tasks/missing-goal.md\n")
            code, dangling = self.inventory(root, "--client", "codex", "--check")

        self.assertEqual(1, code)
        self.assertEqual("STALE_POINTER", dangling["goal"]["status"])

    def test_included_globals_expand_imports_for_totals_duplicates_and_goals(self) -> None:
        for client, filename in (("claude", ".claude/CLAUDE.md"), ("gemini", ".gemini/GEMINI.md")):
            with self.subTest(client=client), tempfile.TemporaryDirectory() as raw:
                root = self.repo(raw)
                home = (Path(raw) / "home").resolve()
                project = "CLAUDE.md" if client == "claude" else "GEMINI.md"
                write(root / project, SHARED)
                write(root / "tasks/GOAL.md", "GOAL_ID: current\nSTATUS: ACTIVE\n")
                write(home / filename, "@../shared.md\n")
                write(home / "shared.md", SHARED + "Current goal: tasks/GOAL.md\n@nested.md\n")
                write(home / "nested.md", "nested global instructions\n")
                _, excluded = self.inventory(root, "--client", client, home=home)
                _, payload = self.inventory(root, "--client", client, "--include-global", home=home)

                self.assertNotIn("~/shared.md", self.paths(excluded, client))
                self.assertEqual({project: "launch", "~/" + filename: "global",
                                  "~/shared.md": "import", "~/nested.md": "import"}, self.paths(payload, client))
                self.assertEqual(sum(p.stat().st_size for p in
                                     (root / project, home / filename, home / "shared.md", home / "nested.md")),
                                 payload["clients"][client]["launch_bytes"])
                self.assertEqual(1, payload["clients"][client]["repeated_lines"])
                self.assertEqual("POINTED", payload["goal"]["status"])

    def test_included_global_missing_import_fails_check(self) -> None:
        for client, filename in (("claude", ".claude/CLAUDE.md"), ("gemini", ".gemini/GEMINI.md")):
            with self.subTest(client=client), tempfile.TemporaryDirectory() as raw:
                root = self.repo(raw)
                home = (Path(raw) / "home").resolve()
                write(home / filename, "@missing.md\n")
                code, payload = self.inventory(root, "--client", client, "--include-global", "--check", home=home)

                self.assertEqual(1, code)
                self.assertIn(f"{client}: ~/{filename}:1 imports missing.md, which does not exist", payload["findings"])

    def test_claude_line_guidance_excludes_agents_fallback_and_rules(self) -> None:
        for filename in ("AGENTS.md", ".claude/rules/long.md"):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as raw:
                root = self.repo(raw)
                write(root / filename, "".join(f"instruction {n}\n" for n in range(201)))
                code, payload = self.inventory(root, "--client", "claude", "--check")

                self.assertEqual(0, code, payload["findings"])
                self.assertFalse(payload["clients"]["claude"]["files"][0]["over_guidance"])

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
