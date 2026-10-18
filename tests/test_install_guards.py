from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "install_guards.py"
INSTALL = ROOT / "scripts" / "install.py"
SKILL = ROOT / "skills" / "nobrainer-tech-flow"
OTHER_HOOKS = {
    "permissions": {"allow": ["Bash(ls:*)"]},
    "hooks": {
        "PreToolUse": [{"matcher": "Write", "hooks": [{"type": "command", "command": "my-lint"}]}],
        "PostToolUse": [{"matcher": "Edit", "hooks": [{"type": "command", "command": "my-format"}]}],
    },
}


@unittest.skipIf(os.name == "nt", "the Flow guards are POSIX-only")
class InstallGuardsTests(unittest.TestCase):
    def setUp(self) -> None:
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.home = Path(scratch.name) / "home"
        self.config = self.home / ".claude"
        self.settings = self.config / "settings.json"
        (self.config / "skills").mkdir(parents=True)
        (self.config / "skills" / "nobrainer-tech-flow").symlink_to(SKILL, target_is_directory=True)
        self.guard = self.config / "skills" / "nobrainer-tech-flow" / "scripts" / "flow_guard.py"

    def run_script(self, *args: str, script: Path = SCRIPT, home: bool = True, env: dict | None = None):
        environment = {key: value for key, value in os.environ.items() if key != "CLAUDE_CONFIG_DIR"}
        environment["HOME"] = str(self.home)
        environment.update(env or {})
        extra = ("--home", str(self.home)) if home else ()
        return subprocess.run(
            [sys.executable, str(script), *args, *extra],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            stdin=subprocess.DEVNULL,
            env=environment,
        )

    def write_settings(self, value: object) -> bytes:
        self.settings.write_text(json.dumps(value, indent=4), encoding="utf-8")
        return self.settings.read_bytes()

    def backups(self) -> list[Path]:
        return sorted(self.config.glob("settings.json.flow-guards-*.bak"))

    def ours(self, settings: dict) -> dict[str, list[str]]:
        return {
            event: [hook["command"] for group in groups for hook in group["hooks"] if str(self.guard) in hook["command"]]
            for event, groups in settings.get("hooks", {}).items()
        }

    def test_preview_prints_the_diff_and_disclaimer_and_writes_nothing(self) -> None:
        for existing in (None, OTHER_HOOKS):
            with self.subTest(existing=bool(existing)):
                before = self.write_settings(existing) if existing else None
                preview = self.run_script()
                self.assertEqual(0, preview.returncode, preview.stderr)
                self.assertIn("+++ ", preview.stdout)
                self.assertIn('"PreToolUse"', preview.stdout)
                self.assertIn(f"{self.guard} pre-tool", preview.stdout)
                self.assertIn("not a security boundary", preview.stdout)
                self.assertIn("sh -c or variables bypass it", preview.stdout)
                self.assertIn("NO_CHANGES", preview.stdout)
                if before is None:
                    self.assertFalse(self.settings.exists())
                else:
                    self.assertEqual(before, self.settings.read_bytes())
                self.assertEqual([], self.backups())

    def test_apply_merges_keeps_other_hooks_and_backs_up(self) -> None:
        before = self.write_settings(OTHER_HOOKS)
        applied = self.run_script("--apply")
        self.assertEqual(0, applied.returncode, applied.stderr)
        self.assertIn("INSTALLED", applied.stdout)
        settings = json.loads(self.settings.read_text(encoding="utf-8"))
        self.assertEqual(OTHER_HOOKS["permissions"], settings["permissions"])
        self.assertEqual(OTHER_HOOKS["hooks"]["PostToolUse"], settings["hooks"]["PostToolUse"])
        self.assertEqual(OTHER_HOOKS["hooks"]["PreToolUse"][0], settings["hooks"]["PreToolUse"][0])
        self.assertEqual("Bash", settings["hooks"]["PreToolUse"][1]["matcher"])
        mine = self.ours(settings)
        self.assertEqual(1, len(mine["PreToolUse"]))
        self.assertTrue(mine["PreToolUse"][0].endswith("pre-tool || true; fi"))
        self.assertEqual(1, len(mine["Stop"]))
        self.assertEqual(1, len(mine["SubagentStop"]))
        [backup] = self.backups()
        self.assertEqual(before, backup.read_bytes())
        self.assertIn(f"BACKUP: {backup}", applied.stdout)

    def test_a_second_apply_changes_nothing(self) -> None:
        self.write_settings(OTHER_HOOKS)
        self.run_script("--apply")
        first = self.settings.read_bytes()
        again = self.run_script("--apply")
        self.assertEqual(0, again.returncode, again.stderr)
        self.assertIn("UP TO DATE", again.stdout)
        self.assertEqual(first, self.settings.read_bytes())
        self.assertEqual(1, len(self.backups()))

    def test_undo_removes_exactly_our_entries(self) -> None:
        self.write_settings(OTHER_HOOKS)
        self.run_script("--apply")
        preview = self.run_script("--undo")
        self.assertIn("NO_CHANGES", preview.stdout)
        self.assertRegex(preview.stdout, r'\n-\s+"command": "if \[ -f ' + re.escape(str(self.guard)))
        undone = self.run_script("--undo", "--apply")
        self.assertEqual(0, undone.returncode, undone.stderr)
        self.assertIn("REMOVED", undone.stdout)
        self.assertEqual(OTHER_HOOKS, json.loads(self.settings.read_text(encoding="utf-8")))
        again = self.run_script("--undo", "--apply")
        self.assertIn("NOTHING TO UNDO", again.stdout)

    def test_undo_of_a_fresh_install_leaves_no_hooks_key(self) -> None:
        self.run_script("--apply")
        self.assertEqual([], self.backups())
        self.run_script("--undo", "--apply")
        self.assertEqual({}, json.loads(self.settings.read_text(encoding="utf-8")))

    def test_malformed_settings_are_refused_untouched(self) -> None:
        for content in ("{not json", "[]", json.dumps({"hooks": []}), json.dumps({"hooks": {"Stop": {}}})):
            with self.subTest(content=content):
                self.settings.write_text(content, encoding="utf-8")
                for flags in (("--apply",), ("--undo", "--apply"), ()):
                    refused = self.run_script(*flags)
                    self.assertEqual(3, refused.returncode, refused.stdout)
                    self.assertIn("REFUSED", refused.stderr)
                    self.assertEqual(content, self.settings.read_text(encoding="utf-8"))
                self.assertEqual([], self.backups())

    def test_without_the_skill_link_it_is_unsupported(self) -> None:
        (self.config / "skills" / "nobrainer-tech-flow").unlink()
        result = self.run_script("--apply")
        self.assertEqual(3, result.returncode)
        self.assertIn("UNSUPPORTED", result.stdout)
        self.assertIn("plugin-only", result.stdout)
        self.assertFalse(self.settings.exists())

    def test_claude_config_dir_selects_the_settings_file(self) -> None:
        config = self.home / "profile"
        (config / "skills").mkdir(parents=True)
        (config / "skills" / "nobrainer-tech-flow").symlink_to(SKILL, target_is_directory=True)
        applied = self.run_script("--apply", home=False, env={"CLAUDE_CONFIG_DIR": str(config)})
        self.assertEqual(0, applied.returncode, applied.stderr)
        settings = json.loads((config / "settings.json").read_text(encoding="utf-8"))
        self.assertIn(str(config / "skills" / "nobrainer-tech-flow" / "scripts" / "flow_guard.py"), json.dumps(settings))
        self.assertFalse(self.settings.exists())

    def test_installed_hook_commands_run_and_fail_open(self) -> None:
        self.run_script("--apply")
        settings = json.loads(self.settings.read_text(encoding="utf-8"))
        command = settings["hooks"]["PreToolUse"][-1]["hooks"][0]["command"]
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "git push --force"}, "cwd": "/"})
        asked = subprocess.run(["sh", "-c", command], input=payload, text=True, capture_output=True, check=False)
        self.assertEqual(0, asked.returncode)
        self.assertEqual("ask", json.loads(asked.stdout)["hookSpecificOutput"]["permissionDecision"])
        (self.config / "skills" / "nobrainer-tech-flow").unlink()
        silent = subprocess.run(["sh", "-c", command], input=payload, text=True, capture_output=True, check=False)
        self.assertEqual((0, ""), (silent.returncode, silent.stdout))

    def test_install_py_delegates_for_claude_only(self) -> None:
        preview = self.run_script("--client", "claude", "--guards", script=INSTALL)
        self.assertEqual(0, preview.returncode, preview.stderr)
        self.assertIn("scripts/install.py --client claude --guards --apply --home", preview.stdout)
        applied = self.run_script("--client", "claude", "--guards", "--apply", script=INSTALL)
        self.assertEqual(0, applied.returncode, applied.stderr)
        self.assertIn("INSTALLED", applied.stdout)
        for client in ("codex", "opencode", "copilot"):
            with self.subTest(client=client):
                other = self.run_script("--client", client, "--guards", "--apply", script=INSTALL)
                self.assertEqual(3, other.returncode)
                self.assertIn("UNSUPPORTED", other.stdout)

    def test_install_py_undo_mentions_guards_left_behind(self) -> None:
        spec = importlib.util.spec_from_file_location("_guards_install_py", INSTALL)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        self.addCleanup(sys.modules.pop, spec.name, None)
        spec.loader.exec_module(module)
        ctx = module.Context("claude", True, self.home, ("--home", str(self.home)), self.config / "skills", None)
        self.assertIsNone(module.guards_note(ctx))
        self.run_script("--apply")
        note = module.guards_note(ctx)
        self.assertIn(f"stay in {self.settings}", note)
        self.assertIn("--client claude --guards --undo --apply --home", note)
        codex = module.Context("codex", True, self.home, ("--home", str(self.home)), self.home / ".agents" / "skills", None)
        self.assertIsNone(module.guards_note(codex))


if __name__ == "__main__":
    unittest.main()
