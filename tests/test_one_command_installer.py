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
    # CI sets this so that a runner without link rights fails instead of skipping.
    return os.environ.get("NOBRAINER_REQUIRE_SYMLINKS") == "1" or INSTALL.symlinks_available()


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
            self.assertIn("put the managed block back as it was before the setup", preview.stdout)
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

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_a_claude_profile_that_imports_the_codex_file_keeps_its_single_copy_of_the_block(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            codex = subprocess.run(
                [sys.executable, str(PERSONALIZATION), "--client", "codex", "--home", str(home), "--apply"],
                cwd=ROOT, text=True, capture_output=True, check=False, stdin=subprocess.DEVNULL,
            )
            self.assertEqual(0, codex.returncode, codex.stderr)
            instructions = home / ".claude" / "CLAUDE.md"
            instructions.parent.mkdir(parents=True)
            original = "@~/.codex/AGENTS.md\n"
            instructions.write_text(original, encoding="utf-8")

            preview = self.run_install("--client", "claude", "--home", str(home))
            self.assertEqual(0, preview.returncode, preview.stdout + preview.stderr)
            self.assertIn("INHERITS_CODEX", preview.stdout)

            applied = self.run_install("--client", "claude", "--home", str(home), "--apply")
            self.assertEqual(0, applied.returncode, applied.stdout + applied.stderr)
            self.assertIn("inherited from the Codex global instructions", applied.stdout)
            self.assertEqual(original, instructions.read_text(encoding="utf-8"))
            self.assertTrue((home / ".claude" / "skills" / "nobrainer-tech-flow").is_symlink())

            undone = self.run_install("--client", "claude", "--home", str(home), "--undo", "--apply")
            self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
            self.assertIn(f"SKILLS: {SKILL_COUNT} unlinked", undone.stdout)
            self.assertNotIn("INSTRUCTIONS:", undone.stdout)
            self.assertEqual(original, instructions.read_text(encoding="utf-8"))
            self.assertFalse((home / ".claude" / "skills").exists())

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

    def install(self, home: Path, *flags: str, variables: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        arguments = ["--client", "claude", *flags]
        if variables is None:
            arguments += ["--home", str(home)]
        result = self.run_install(*arguments, home=home, variables=variables)
        return result

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_undo_after_a_second_apply_puts_back_the_file_from_before_the_first(self) -> None:
        # A later release changes the block, and --apply runs again: the undo must not
        # restore the file as it was just before that second run, block included.
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            instructions = home / ".claude" / "CLAUDE.md"
            instructions.parent.mkdir(parents=True)
            original = b"# Mine\n"
            instructions.write_bytes(original)
            self.assertEqual(0, self.install(home, "--apply").returncode)
            older = instructions.read_bytes().replace(
                b"Split substantial work into bounded tasks", b"Split work into bounded tasks"
            )
            instructions.write_bytes(older)

            again = self.install(home, "--apply")
            self.assertEqual(0, again.returncode, again.stdout + again.stderr)
            undone = self.install(home, "--undo", "--apply")

            self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
            self.assertEqual(original, instructions.read_bytes())

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_edits_outside_the_block_between_two_installs_survive_the_undo(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            instructions = home / ".claude" / "CLAUDE.md"
            instructions.parent.mkdir(parents=True)
            instructions.write_bytes(b"# Mine\n")
            self.assertEqual(0, self.install(home, "--apply").returncode)
            with instructions.open("ab") as handle:
                handle.write(b"\n# Added later\n")

            self.assertEqual(0, self.install(home, "--apply").returncode)
            undone = self.install(home, "--undo", "--apply")

            self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
            content = instructions.read_text(encoding="utf-8")
            self.assertTrue(content.startswith("# Mine\n"))
            self.assertIn("# Added later", content)
            self.assertNotIn(START, content)
            self.assertIn("the rest of the file is kept as it is now", undone.stdout)

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_a_block_that_was_there_before_the_install_is_still_there_after_the_undo(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            earlier = subprocess.run(
                [sys.executable, str(PERSONALIZATION), "--client", "claude", "--home", str(home),
                 "--auto-update", "--preferences", "Answer in Polish.", "--apply"],
                cwd=ROOT, text=True, capture_output=True, check=False, stdin=subprocess.DEVNULL,
            )
            self.assertEqual(0, earlier.returncode, earlier.stderr)
            instructions = home / ".claude" / "CLAUDE.md"
            before = instructions.read_bytes()

            self.assertEqual(0, self.install(home, "--apply").returncode)
            self.assertEqual(before, instructions.read_bytes())
            undone = self.install(home, "--undo", "--apply")

            self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
            self.assertEqual(before, instructions.read_bytes())
            self.assertFalse((home / ".claude" / "skills").exists())

    def test_the_preview_shows_an_authorization_that_apply_would_keep(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            earlier = subprocess.run(
                [sys.executable, str(PERSONALIZATION), "--client", "claude", "--home", str(home),
                 "--auto-update", "--apply"],
                cwd=ROOT, text=True, capture_output=True, check=False, stdin=subprocess.DEVNULL,
            )
            self.assertEqual(0, earlier.returncode, earlier.stderr)

            preview = self.install(home)

            self.assertEqual(0, preview.returncode, preview.stdout + preview.stderr)
            self.assertIn("KEPT_OPTIONS: auto-update", preview.stdout)
            self.assertIn("UNCHANGED: managed block is current", preview.stdout)
            self.assertNotIn("CHECK_AND_NOTIFY", preview.stdout)

    def test_an_explicit_home_wins_over_the_client_variable_in_the_preview(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            home = root / "home"
            home.mkdir()

            preview = self.run_install(
                "--client", "claude", "--home", str(home),
                home=root, variables={"CLAUDE_CONFIG_DIR": str(root / "other")},
            )

            self.assertEqual(0, preview.returncode, preview.stdout + preview.stderr)
            skills_line = next(line for line in preview.stdout.splitlines() if line.startswith("SKILLS:"))
            self.assertIn(str(home / ".claude" / "skills"), skills_line)
            self.assertNotIn(str(root / "other"), preview.stdout)

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_the_preview_refuses_what_apply_would_refuse_and_names_this_commands_flags(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            home = root / "home"
            (root / "A").mkdir()
            (root / "B").mkdir()
            home.mkdir()
            first = self.run_install("--client", "claude", "--apply", home=home, variables={"CLAUDE_CONFIG_DIR": str(root / "A")})
            self.assertEqual(0, first.returncode, first.stdout + first.stderr)
            self.assertIn(f"NOTE: this setup follows CLAUDE_CONFIG_DIR={root / 'A'}", first.stdout)

            preview = self.run_install("--client", "claude", home=home, variables={"CLAUDE_CONFIG_DIR": str(root / "B")})

            self.assertEqual(2, preview.returncode, preview.stdout + preview.stderr)
            self.assertIn("different skills destination", preview.stderr)
            self.assertIn("--undo --apply", preview.stderr)
            self.assertNotIn("--rollback", preview.stderr)
            self.assertEqual([], list((root / "B").iterdir()))

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_an_undo_counts_the_links_it_removed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            self.assertEqual(0, self.install(home, "--apply").returncode)
            skills = home / ".claude" / "skills"
            for item in GUIDED.ITEMS[:5]:
                (skills / item.skill).unlink()

            undone = self.install(home, "--undo", "--apply")

            self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
            self.assertIn(f"SKILLS: {SKILL_COUNT - 5} unlinked", undone.stdout)

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_a_link_from_an_earlier_layout_gets_the_migration_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            skills = home / ".claude" / "skills"
            skills.mkdir(parents=True)
            (skills / "nobrainer-ultra").symlink_to(ROOT / "nobrainer-ultra")

            result = self.install(home)

            self.assertEqual(3, result.returncode, result.stdout + result.stderr)
            self.assertIn("scripts/install_skills.py --client claude --dest", result.stderr)
            self.assertIn("--migrate-legacy --apply", result.stderr)
            self.assertNotIn("rerun with --migrate-legacy", result.stderr)

    @unittest.skipIf(os.name == "nt", "HOME does not choose the home directory on Windows")
    def test_an_empty_home_variable_is_refused(self) -> None:
        result = self.run_install("--client", "claude", home=None, variables={"HOME": ""})

        self.assertEqual(2, result.returncode)
        self.assertIn("HOME is set but empty", result.stderr)

    @unittest.skipIf(os.name == "nt", "Windows paths cannot hold a line break")
    def test_a_home_with_a_line_break_is_refused_before_anything_is_written(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "new\nline"
            home.mkdir()

            for flags in ((), ("--apply",)):
                with self.subTest(flags=flags):
                    result = self.install(home, *flags)
                    self.assertEqual(2, result.returncode, result.stdout + result.stderr)
                    self.assertIn("line break or control character", result.stderr)
                    self.assertEqual([], self.entries(home))


if __name__ == "__main__":
    unittest.main()
