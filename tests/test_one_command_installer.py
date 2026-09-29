from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "install.py"
PERSONALIZATION = ROOT / "scripts" / "install_personalization.py"
SPEC = importlib.util.spec_from_file_location("one_command_installer", SCRIPT)
assert SPEC and SPEC.loader
INSTALL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = INSTALL
SPEC.loader.exec_module(INSTALL)
GUIDED = INSTALL.load_guided()
SKILL_COUNT = len(GUIDED.ITEMS)
START = "<!-- NOBRAINER-TECH-FLOW:START -->"
CONFIG_VARIABLES = ("CLAUDE_CONFIG_DIR", "CODEX_HOME", "XDG_CONFIG_HOME")


def symlinks_work() -> bool:
    return INSTALL.symlinks_available()


class OneCommandInstallerTests(unittest.TestCase):
    def run_install(
        self,
        *args: str,
        home: Path | None = None,
        variables: dict[str, str] | None = None,
        cwd: Path = ROOT,
    ) -> subprocess.CompletedProcess[str]:
        """Run with a private home and only the config variables the test names."""

        environment = {key: value for key, value in os.environ.items() if key not in CONFIG_VARIABLES}
        if home is not None:
            environment.update({"HOME": str(home), "USERPROFILE": str(home)})
        environment.update(variables or {})
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
            stdin=subprocess.DEVNULL,
            env=environment,
        )

    def entries(self, root: Path) -> list[str]:
        return sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

    def test_help_names_what_a_person_needs_and_where_the_rest_lives(self) -> None:
        result = self.run_install("--help")

        self.assertEqual(0, result.returncode, result.stderr)
        for expected in ("--client", "--apply", "--undo", "--home", "docs/INSTALL.md"):
            self.assertIn(expected, result.stdout)

    def test_it_offers_exactly_the_clients_the_guided_setup_can_undo(self) -> None:
        self.assertEqual(set(GUIDED.CLIENTS), set(INSTALL.LABELS))

    def test_a_missing_or_unknown_client_is_a_usage_error(self) -> None:
        for arguments in ((), ("--client", "notepad")):
            with self.subTest(arguments=arguments):
                result = self.run_install(*arguments)
                self.assertEqual(2, result.returncode)
                self.assertIn("--client", result.stderr)

    def test_the_preview_changes_nothing_shows_the_text_and_names_the_next_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            home.mkdir()

            result = self.run_install("--client", "claude", "--home", str(home))

            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertEqual([], self.entries(home))
            self.assertIn(f"SKILLS: {SKILL_COUNT} to link into", result.stdout)
            self.assertIn("0 already linked", result.stdout)
            # The person consents to the exact text that will be written.
            self.assertIn("DIFF:", result.stdout)
            self.assertIn(f"+{START}", result.stdout)
            self.assertIn("AUTO_UPDATE: CHECK_AND_NOTIFY", result.stdout)
            self.assertIn("AUTO_SESSION_RESTART: ASSESS_CHECKPOINT_RECOMMEND", result.stdout)
            self.assertIn("NO_CHANGES:", result.stdout)
            self.assertIn(f"scripts/install.py --client claude --apply --home {home}", result.stdout)

    def test_each_client_previews_its_own_documented_locations(self) -> None:
        expectations = {
            "claude": (Path(".claude", "skills"), Path(".claude", "CLAUDE.md")),
            "codex": (Path(".agents", "skills"), Path(".codex", "AGENTS.md")),
            "opencode": (Path(".config", "opencode", "skills"), Path(".config", "opencode", "AGENTS.md")),
            "copilot": (Path(".copilot", "skills"), Path(".copilot", "copilot-instructions.md")),
        }
        for client, (skills, instructions) in expectations.items():
            with self.subTest(client=client), tempfile.TemporaryDirectory() as temp:
                home = Path(temp) / "home"
                home.mkdir()

                result = self.run_install("--client", client, "--home", str(home))

                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                lines = result.stdout.splitlines()
                skills_line = next(line for line in lines if line.startswith("SKILLS:"))
                target_line = next(line for line in lines if line.startswith("TARGET:"))
                self.assertTrue(skills_line.split(" to link into ")[1].split(" (")[0].endswith(str(skills)), skills_line)
                self.assertTrue(target_line.endswith(str(instructions)), target_line)
                self.assertIn(INSTALL.LABELS[client], lines[0])
                self.assertEqual([], self.entries(home))

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_apply_repeat_and_undo_round_trip_leaves_the_profile_as_it_was(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            instructions = home / ".claude" / "CLAUDE.md"
            instructions.parent.mkdir(parents=True)
            original = b"# My rules\r\n\r\nAlways answer in Polish.\r\n"
            instructions.write_bytes(original)
            skills = home / ".claude" / "skills"

            applied = self.run_install("--client", "claude", "--home", str(home), "--apply")

            self.assertEqual(0, applied.returncode, applied.stdout + applied.stderr)
            self.assertIn("INSTALLED:", applied.stdout)
            self.assertIn(f"SKILLS: {SKILL_COUNT} linked in", applied.stdout)
            self.assertIn(f"({SKILL_COUNT} new)", applied.stdout)
            self.assertIn(f"scripts/install.py --client claude --undo --apply --home {home}", applied.stdout)
            for item in GUIDED.ITEMS:
                link = skills / item.skill
                self.assertTrue(link.is_symlink(), item.skill)
                self.assertEqual((ROOT / "skills" / item.skill).resolve(), link.resolve())
            written = instructions.read_bytes()
            self.assertTrue(written.startswith(original))
            self.assertIn(START.encode(), written)
            # Nothing standing was granted: the defaults only check, assess and recommend.
            self.assertNotIn(b"grants standing authorization", written)
            backups = [path for path in instructions.parent.iterdir() if ".bak." in path.name]
            self.assertEqual(1, len(backups))
            self.assertEqual(original, backups[0].read_bytes())

            again = self.run_install("--client", "claude", "--home", str(home), "--apply")

            self.assertEqual(0, again.returncode, again.stdout + again.stderr)
            self.assertIn("(0 new)", again.stdout)
            self.assertEqual(written, instructions.read_bytes())

            preview = self.run_install("--client", "claude", "--home", str(home), "--undo")

            self.assertEqual(0, preview.returncode, preview.stdout + preview.stderr)
            self.assertIn(f"UNDO_PLAN: unlink {SKILL_COUNT} skills", preview.stdout)
            self.assertIn("restore it from", preview.stdout)
            self.assertIn("NO_CHANGES:", preview.stdout)
            self.assertEqual(SKILL_COUNT, len(list(skills.iterdir())))
            self.assertEqual(written, instructions.read_bytes())

            undone = self.run_install("--client", "claude", "--home", str(home), "--undo", "--apply")

            self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
            self.assertIn("UNDONE:", undone.stdout)
            self.assertIn(f"SKILLS: {SKILL_COUNT} unlinked", undone.stdout)
            self.assertFalse(skills.exists())
            self.assertEqual(original, instructions.read_bytes())
            self.assertFalse((home / ".nobrainer-flow-onboarding-claude.json").exists())

    def test_a_foreign_skill_is_refused_before_anything_is_written(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            foreign = home / ".claude" / "skills" / "nobrainer-build"
            foreign.mkdir(parents=True)
            (foreign / "SKILL.md").write_text("hand-made\n", encoding="utf-8")
            before = self.entries(home)

            for arguments in ((), ("--apply",)):
                with self.subTest(arguments=arguments):
                    result = self.run_install("--client", "claude", "--home", str(home), *arguments)

                    self.assertEqual(3, result.returncode, result.stdout + result.stderr)
                    self.assertIn("CONFLICT: nobrainer-build", result.stderr)
                    self.assertIn("HINT:", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertEqual(before, self.entries(home))

    def test_undo_without_a_recorded_setup_says_so(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            home.mkdir()

            result = self.run_install("--client", "claude", "--home", str(home), "--undo", "--apply")

            self.assertEqual(3, result.returncode)
            self.assertIn("rollback state not found", result.stderr)
            self.assertIn("none is recorded for Claude Code", result.stderr)
            self.assertEqual([], self.entries(home))

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_the_variable_a_client_reads_selects_where_it_installs_when_home_is_not_given(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            home = root / "home"
            profile = root / "claude-profile"
            home.mkdir()
            profile.mkdir()
            # A variable the client never reads must not matter, even when it is unusable.
            variables = {"CLAUDE_CONFIG_DIR": str(profile), "XDG_CONFIG_HOME": "~/.config"}

            preview = self.run_install("--client", "claude", home=home, variables=variables)
            self.assertEqual(0, preview.returncode, preview.stdout + preview.stderr)
            self.assertIn(str(profile / "skills"), preview.stdout)
            self.assertIn(str(profile / "CLAUDE.md"), preview.stdout)

            applied = self.run_install("--client", "claude", "--apply", home=home, variables=variables)

            self.assertEqual(0, applied.returncode, applied.stdout + applied.stderr)
            self.assertTrue((profile / "skills" / "nobrainer-tech-flow").is_symlink())
            self.assertIn(START, (profile / "CLAUDE.md").read_text(encoding="utf-8"))
            self.assertFalse((home / ".claude").exists())

            undone = self.run_install("--client", "claude", "--undo", "--apply", home=home, variables=variables)
            self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
            self.assertFalse((profile / "skills").exists())

    def test_a_broken_variable_of_the_selected_client_is_an_error_not_a_guess(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            home.mkdir()

            result = self.run_install("--client", "claude", home=home, variables={"CLAUDE_CONFIG_DIR": "relative"})

            self.assertEqual(2, result.returncode)
            self.assertIn("CLAUDE_CONFIG_DIR must be an absolute path", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual([], self.entries(home))

    def test_a_relative_home_directory_variable_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            here = Path(temp).resolve()

            result = self.run_install("--client", "codex", home=Path("relative-home"), cwd=here)

            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            self.assertIn("absolute path", result.stderr)
            self.assertFalse((ROOT / "relative-home").exists())
            self.assertEqual([], self.entries(here))

    def test_a_relative_home_is_resolved_against_the_callers_directory_not_the_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            here = Path(temp).resolve()

            result = self.run_install("--client", "codex", "--home", "relative-home", cwd=here)

            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            target = next(line for line in result.stdout.splitlines() if line.startswith("TARGET: "))
            # The helpers run from the checkout, so they must be handed an absolute path.
            self.assertEqual(str(here / "relative-home" / ".codex" / "AGENTS.md"), target.removeprefix("TARGET: "))
            self.assertIn(str(here / "relative-home"), result.stdout)
            self.assertFalse((ROOT / "relative-home").exists())
            self.assertEqual([], self.entries(here))

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_an_authorization_granted_earlier_is_kept_and_none_is_ever_added(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            granted = subprocess.run(
                [sys.executable, str(PERSONALIZATION), "--client", "claude", "--home", str(home),
                 "--auto-update", "--apply"],
                cwd=ROOT, text=True, capture_output=True, check=False, stdin=subprocess.DEVNULL,
            )
            self.assertEqual(0, granted.returncode, granted.stderr)

            result = self.run_install("--client", "claude", "--home", str(home), "--apply")

            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn("KEPT_OPTIONS: auto-update", result.stdout)
            content = (home / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")
            self.assertIn("grants standing authorization to apply", content)
            self.assertNotIn("grants standing authorization for session rotation", content)

    def test_it_never_asks_the_helpers_for_a_standing_authorization_or_a_preference(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            ctx = INSTALL.Context("claude", True, Path(temp), ("--home", temp), Path(temp) / "skills", GUIDED)

            command = INSTALL.guided_command(ctx, "--selection", "01")

        for forbidden in ("--auto-update", "--auto-session-restart", "--preferences", "--wiki-root"):
            self.assertNotIn(forbidden, command)
        self.assertIn("--offline", command)

    def test_a_machine_that_cannot_link_is_told_what_to_do_and_nothing_is_written(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            home.mkdir()
            captured = io.StringIO()

            with mock.patch.object(INSTALL, "symlinks_available", return_value=False), \
                    contextlib.redirect_stderr(captured), contextlib.redirect_stdout(io.StringIO()):
                code = INSTALL.main(["--client", "claude", "--home", str(home), "--apply"])

            self.assertEqual(2, code)
            self.assertIn("cannot create symbolic links", captured.getvalue())
            self.assertIn("Developer Mode", captured.getvalue())
            self.assertIn("docs/INSTALL.md", captured.getvalue())
            self.assertEqual([], self.entries(home))

    def test_the_link_probe_reports_a_refused_symlink_as_unavailable(self) -> None:
        with mock.patch.object(os, "symlink", side_effect=OSError(1314, "A required privilege is not held")):
            self.assertFalse(INSTALL.symlinks_available())
        self.assertIsInstance(INSTALL.symlinks_available(), bool)


if __name__ == "__main__":
    unittest.main()
