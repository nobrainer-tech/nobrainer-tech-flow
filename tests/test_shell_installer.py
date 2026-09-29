"""The no-Python installer, scripts/install.sh, against the real scripts and a private home.

It must behave like scripts/install.py: same locations and variables, same conflict
rule, the same setup record (either one undoes the other), no authorization granted,
and the instruction block byte for byte what the Python helper writes.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.support import find_bash


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "install.sh"
INSTALL_PY = ROOT / "scripts" / "install.py"
PERSONALIZATION = ROOT / "scripts" / "install_personalization.py"
START = "<!-- NOBRAINER-TECH-FLOW:START -->"
CONFIG_VARIABLES = ("CLAUDE_CONFIG_DIR", "CODEX_HOME", "XDG_CONFIG_HOME")
SHELL = find_bash() if os.name == "nt" else shutil.which("sh")


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


SKILLS_MODULE = load("install_skills_for_shell_tests", ROOT / "scripts" / "install_skills.py")
PERSONALIZATION_MODULE = load("personalization_for_shell_tests", PERSONALIZATION)
SKILLS = sorted(SKILLS_MODULE.CURATED_SKILLS)


def symlinks_work() -> bool:
    # CI sets this so that a runner without link rights fails instead of skipping.
    if os.environ.get("NOBRAINER_REQUIRE_SYMLINKS") == "1":
        return True
    try:
        with tempfile.TemporaryDirectory() as scratch:
            (Path(scratch) / "target").mkdir()
            os.symlink(Path(scratch) / "target", Path(scratch) / "link", target_is_directory=True)
    except (OSError, NotImplementedError):
        return False
    return True


def environment(home: Path | None, variables: dict[str, str] | None = None) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key not in CONFIG_VARIABLES}
    if home is not None:
        env.update({"HOME": str(home), "USERPROFILE": str(home)})
    env.update(variables or {})
    return env


def run_sh(
    *args: str,
    home: Path | None = None,
    variables: dict[str, str] | None = None,
    cwd: Path = ROOT,
    shell: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*(shell or [SHELL]), SCRIPT.as_posix(), *args],
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
        stdin=subprocess.DEVNULL,
        env=environment(home, variables),
    )


def run_py(*args: str, home: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
        stdin=subprocess.DEVNULL,
        env=environment(home),
    )


def entries(root: Path) -> list[str]:
    return sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))


def other_shells() -> list[list[str]]:
    """POSIX shells besides the default one that can run the script here."""

    shells = []
    if os.name != "nt":
        for name, command in (
            ("dash", ["dash"]),
            ("bash", ["bash", "--posix"]),
            ("busybox", ["busybox", "sh"]),
            # zsh runs a script as sh would when it emulates sh, as it does when named sh.
            ("zsh", ["zsh", "--emulate", "sh"]),
        ):
            if shutil.which(name):
                shells.append(command)
    return shells


@unittest.skipIf(SHELL is None, "no POSIX shell here")
class ShellInstallerTests(unittest.TestCase):
    def test_the_script_parses_in_every_available_posix_shell(self) -> None:
        for shell in ([SHELL], *other_shells()):
            with self.subTest(shell=shell):
                result = subprocess.run([*shell, "-n", SCRIPT.as_posix()], capture_output=True, text=True, check=False)
                self.assertEqual(0, result.returncode, result.stderr)

    def test_the_script_keeps_lf_line_endings(self) -> None:
        self.assertNotIn(b"\r", SCRIPT.read_bytes())
        attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
        self.assertRegex(attributes, r"(?m)^scripts/install\.sh\s+.*eol=lf")

    def test_help_and_usage_errors(self) -> None:
        helped = run_sh("--help")
        self.assertEqual(0, helped.returncode, helped.stderr)
        for expected in ("--client", "--apply", "--undo", "--home", "docs/INSTALL.md"):
            self.assertIn(expected, helped.stdout)
        for arguments in ((), ("--client", "notepad"), ("--client", "claude", "--bogus")):
            with self.subTest(arguments=arguments):
                result = run_sh(*arguments)
                self.assertEqual(2, result.returncode)
                self.assertIn("usage:", result.stderr)

    def test_its_skill_and_legacy_lists_are_the_python_installers(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")

        def names(variable: str) -> set[str]:
            match = re.search(rf"^{variable}='([^']*)'", text, re.MULTILINE)
            self.assertIsNotNone(match, variable)
            return set(match.group(1).split())

        legacy = {old for old, new in SKILLS_MODULE.LEGACY_TO_CANONICAL.items() if old != new}
        self.assertEqual(set(SKILLS), names("SKILLS"))
        self.assertEqual(legacy | set(SKILLS_MODULE.UNMAPPED_LEGACY), names("LEGACY"))

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_the_block_it_writes_is_byte_for_byte_the_python_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            home.mkdir()

            result = run_sh("--client", "codex", "--home", str(home), "--apply", home=home)

            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            expected = PERSONALIZATION_MODULE.build_block(None, False, False, None).encode("utf-8")
            self.assertEqual(expected, (home / ".codex" / "AGENTS.md").read_bytes())
            again = run_py(str(PERSONALIZATION), "--client", "codex", "--home", str(home), home=home)
            self.assertIn("UNCHANGED: managed block is current", again.stdout)

    def test_the_preview_changes_nothing_shows_the_text_and_names_the_next_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            home.mkdir()

            result = run_sh("--client", "claude", "--home", str(home), home=home)

            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertEqual([], entries(home))
            self.assertIn(f"SKILLS: {len(SKILLS)} to link into", result.stdout)
            self.assertIn(f"+{START}", result.stdout)
            self.assertIn("AUTO_UPDATE: CHECK_AND_NOTIFY", result.stdout)
            self.assertIn("NO_CHANGES:", result.stdout)
            self.assertRegex(result.stdout, r"install with: sh \S*install\.sh --client claude --apply --home ")

    def test_each_client_previews_its_own_documented_locations(self) -> None:
        expectations = {
            "claude": (".claude/skills", ".claude/CLAUDE.md"),
            "codex": (".agents/skills", ".codex/AGENTS.md"),
            "opencode": (".config/opencode/skills", ".config/opencode/AGENTS.md"),
            "copilot": (".copilot/skills", ".copilot/copilot-instructions.md"),
        }
        for client, (skills, target) in expectations.items():
            with self.subTest(client=client), tempfile.TemporaryDirectory() as temp:
                home = Path(temp) / "home"
                home.mkdir()

                result = run_sh("--client", client, "--home", str(home), home=home)

                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                self.assertRegex(result.stdout, rf"SKILLS: \d+ to link into \S*/home/{re.escape(skills)} ")
                self.assertRegex(result.stdout, rf"TARGET: \S*/home/{re.escape(target)}\n")
                self.assertEqual([], entries(home))

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_apply_repeat_and_undo_round_trip_in_every_available_shell(self) -> None:
        for shell in ([SHELL], *other_shells()):
            with self.subTest(shell=shell), tempfile.TemporaryDirectory() as temp:
                home = Path(temp) / "home"
                instructions = home / ".claude" / "CLAUDE.md"
                instructions.parent.mkdir(parents=True)
                original = b"# My rules\r\n\r\nAlways answer in Polish.\r\n"
                instructions.write_bytes(original)
                skills = home / ".claude" / "skills"
                flags = ("--client", "claude", "--home", str(home))

                applied = run_sh(*flags, "--apply", home=home, shell=shell)

                self.assertEqual(0, applied.returncode, applied.stdout + applied.stderr)
                self.assertIn(f"SKILLS: {len(SKILLS)} linked in", applied.stdout)
                self.assertIn(f"({len(SKILLS)} new)", applied.stdout)
                for name in SKILLS:
                    self.assertTrue((skills / name).is_symlink(), name)
                    self.assertEqual((ROOT / "skills" / name).resolve(), (skills / name).resolve())
                written = instructions.read_bytes()
                self.assertTrue(written.startswith(original))
                self.assertIn(START.encode(), written)
                self.assertNotIn(b"grants standing authorization", written)
                backups = [path for path in instructions.parent.iterdir() if ".bak." in path.name]
                self.assertEqual(1, len(backups))
                self.assertEqual(original, backups[0].read_bytes())
                record = json.loads((home / ".nobrainer-flow-onboarding-claude.json").read_text(encoding="utf-8"))
                self.assertEqual(SKILLS, record["created_skills"])
                self.assertEqual(Path(record["profile"]["target"]), instructions)

                again = run_sh(*flags, "--apply", home=home, shell=shell)
                self.assertEqual(0, again.returncode, again.stdout + again.stderr)
                self.assertIn("(0 new)", again.stdout)
                self.assertEqual(written, instructions.read_bytes())

                preview = run_sh(*flags, "--undo", home=home, shell=shell)
                self.assertEqual(0, preview.returncode, preview.stdout + preview.stderr)
                self.assertIn(f"UNDO_PLAN: unlink {len(SKILLS)} skills", preview.stdout)
                self.assertEqual(written, instructions.read_bytes())

                undone = run_sh(*flags, "--undo", "--apply", home=home, shell=shell)
                self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
                self.assertIn(f"SKILLS: {len(SKILLS)} unlinked", undone.stdout)
                self.assertIn("is back as it was before the setup", undone.stdout)
                self.assertFalse(skills.exists())
                self.assertEqual(original, instructions.read_bytes())
                self.assertFalse((home / ".nobrainer-flow-onboarding-claude.json").exists())

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_either_installer_undoes_what_the_other_did(self) -> None:
        for installer, undoer in (("sh", "py"), ("py", "sh")):
            with self.subTest(installed_by=installer), tempfile.TemporaryDirectory() as temp:
                home = Path(temp) / "home"
                instructions = home / ".claude" / "CLAUDE.md"
                instructions.parent.mkdir(parents=True)
                original = b"# Mine, with no line break at the end"
                instructions.write_bytes(original)
                flags = ("--client", "claude", "--home", str(home))

                def step(tool: str, *more: str) -> subprocess.CompletedProcess[str]:
                    if tool == "sh":
                        return run_sh(*flags, *more, home=home)
                    return run_py(str(INSTALL_PY), *flags, *more, home=home)

                applied = step(installer, "--apply")
                self.assertEqual(0, applied.returncode, applied.stdout + applied.stderr)
                repeated = step(undoer, "--apply")
                self.assertEqual(0, repeated.returncode, repeated.stdout + repeated.stderr)
                undone = step(undoer, "--undo", "--apply")

                self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
                self.assertEqual(original, instructions.read_bytes())
                self.assertFalse((home / ".claude" / "skills").exists())

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_edits_outside_the_block_survive_the_undo(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            instructions = home / ".claude" / "CLAUDE.md"
            instructions.parent.mkdir(parents=True)
            instructions.write_bytes(b"# Mine\n")
            flags = ("--client", "claude", "--home", str(home))
            self.assertEqual(0, run_sh(*flags, "--apply", home=home).returncode)
            with instructions.open("ab") as handle:
                handle.write(b"\n# Added later\n")

            self.assertEqual(0, run_sh(*flags, "--apply", home=home).returncode)
            undone = run_sh(*flags, "--undo", "--apply", home=home)

            self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
            content = instructions.read_text(encoding="utf-8")
            self.assertTrue(content.startswith("# Mine\n"))
            self.assertIn("# Added later", content)
            self.assertNotIn(START, content)

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_undo_refuses_a_file_or_link_that_changed_since(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            instructions = home / ".claude" / "CLAUDE.md"
            flags = ("--client", "claude", "--home", str(home))
            self.assertEqual(0, run_sh(*flags, "--apply", home=home).returncode)
            with instructions.open("a", encoding="utf-8") as handle:
                handle.write("\nedited after the setup\n")

            refused = run_sh(*flags, "--undo", "--apply", home=home)

            self.assertEqual(3, refused.returncode)
            self.assertIn("PRESERVED: personalization changed since setup", refused.stdout)
            self.assertTrue((home / ".claude" / "skills" / "nobrainer-build").is_symlink())
            self.assertIn("edited after the setup", instructions.read_text(encoding="utf-8"))

    def test_a_foreign_skill_or_an_earlier_layout_is_refused_before_anything_is_written(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            skills = home / ".claude" / "skills"
            (skills / "nobrainer-build").mkdir(parents=True)
            (skills / "nobrainer-build" / "SKILL.md").write_text("hand-made\n", encoding="utf-8")
            before = entries(home)

            for flags in ((), ("--apply",)):
                with self.subTest(flags=flags):
                    result = run_sh("--client", "claude", "--home", str(home), *flags, home=home)
                    self.assertEqual(3, result.returncode, result.stdout + result.stderr)
                    self.assertIn("CONFLICT: nobrainer-build", result.stderr)
                    self.assertIn("HINT:", result.stderr)
                    self.assertEqual(before, entries(home))

            shutil.rmtree(skills / "nobrainer-build")
            (skills / "nobrainer-ultra").mkdir()
            legacy = run_sh("--client", "claude", "--home", str(home), home=home)
            self.assertEqual(3, legacy.returncode)
            self.assertIn("LEGACY: nobrainer-ultra", legacy.stderr)
            self.assertIn("docs/MIGRATION_TO_FLOW.md", legacy.stderr)

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_the_variable_a_client_reads_is_followed_and_others_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            home = root / "home"
            profile = root / "claude-profile"
            home.mkdir()
            profile.mkdir()
            variables = {"CLAUDE_CONFIG_DIR": str(profile), "XDG_CONFIG_HOME": "~/.config", "CODEX_HOME": "relative"}

            applied = run_sh("--client", "claude", "--apply", home=home, variables=variables)

            self.assertEqual(0, applied.returncode, applied.stdout + applied.stderr)
            self.assertTrue((profile / "skills" / "nobrainer-tech-flow").is_symlink())
            self.assertIn(START, (profile / "CLAUDE.md").read_text(encoding="utf-8"))
            self.assertIn("NOTE: this setup follows CLAUDE_CONFIG_DIR=", applied.stdout)
            self.assertFalse((home / ".claude").exists())
            undone = run_sh("--client", "claude", "--undo", "--apply", home=home, variables=variables)
            self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
            self.assertFalse((profile / "skills").exists())

    def test_empty_and_relative_variables(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            home.mkdir()
            for client, name, value in (
                ("claude", "CLAUDE_CONFIG_DIR", "relative"),
                ("claude", "CLAUDE_CONFIG_DIR", ""),
                ("codex", "CODEX_HOME", "  "),
                ("opencode", "XDG_CONFIG_HOME", "~/.config"),
            ):
                with self.subTest(variable=name, value=value):
                    result = run_sh("--client", client, home=home, variables={name: value})
                    self.assertEqual(2, result.returncode, result.stdout + result.stderr)
                    self.assertIn(f"{name} must be an absolute path", result.stderr)
            empty = run_sh("--client", "codex", home=home, variables={"CODEX_HOME": ""})
            self.assertEqual(0, empty.returncode, empty.stdout + empty.stderr)
            self.assertRegex(empty.stdout, r"TARGET: \S*/home/\.codex/AGENTS\.md")
            self.assertEqual([], entries(home))

    def test_instruction_files_it_must_not_touch(self) -> None:
        cases = {
            "codex override": ("codex", ".codex/AGENTS.override.md", "# overriding rules\n", "takes precedence over AGENTS.md"),
            "legacy instructions": ("claude", ".claude/CLAUDE.md", "# NoBrainer Flow\nold rules\n", "explicit migration is required"),
            "malformed markers": ("claude", ".claude/CLAUDE.md", f"{START}\nno end\n", "malformed or duplicated"),
        }
        for label, (client, relative, content, message) in cases.items():
            with self.subTest(case=label), tempfile.TemporaryDirectory() as temp:
                home = Path(temp) / "home"
                path = home / relative
                path.parent.mkdir(parents=True)
                path.write_text(content, encoding="utf-8")
                before = entries(home)

                result = run_sh("--client", client, "--home", str(home), "--apply", home=home)

                self.assertEqual(3, result.returncode, result.stdout + result.stderr)
                self.assertIn(message, result.stderr)
                self.assertEqual(before, entries(home))
                self.assertEqual(content, path.read_text(encoding="utf-8"))

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_a_symlinked_instruction_file_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            (home / ".claude").mkdir(parents=True)
            real = Path(temp) / "real.md"
            real.write_text("# real\n", encoding="utf-8")
            (home / ".claude" / "CLAUDE.md").symlink_to(real)

            result = run_sh("--client", "claude", "--home", str(home), "--apply", home=home)

            self.assertEqual(3, result.returncode)
            self.assertIn("regular non-symlink file", result.stderr)
            self.assertEqual("# real\n", real.read_text(encoding="utf-8"))

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_an_existing_block_with_options_is_left_exactly_as_it_is(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            earlier = run_py(
                str(PERSONALIZATION), "--client", "claude", "--home", str(home),
                "--auto-update", "--preferences", "Answer in Polish.", "--apply", home=home,
            )
            self.assertEqual(0, earlier.returncode, earlier.stderr)
            instructions = home / ".claude" / "CLAUDE.md"
            before = instructions.read_bytes()

            preview = run_sh("--client", "claude", "--home", str(home), home=home)
            self.assertIn("PRESENT: the managed block is already there", preview.stdout)
            self.assertIn("NOTE: it differs from this version's default block", preview.stdout)
            applied = run_sh("--client", "claude", "--home", str(home), "--apply", home=home)
            self.assertEqual(0, applied.returncode, applied.stdout + applied.stderr)
            self.assertEqual(before, instructions.read_bytes())
            undone = run_sh("--client", "claude", "--home", str(home), "--undo", "--apply", home=home)

            self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
            self.assertEqual(before, instructions.read_bytes())
            self.assertFalse((home / ".claude" / "skills").exists())

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_a_claude_file_that_is_only_the_codex_import_keeps_a_single_block(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            self.assertEqual(0, run_py(str(PERSONALIZATION), "--client", "codex", "--home", str(home), "--apply", home=home).returncode)
            instructions = home / ".claude" / "CLAUDE.md"
            instructions.parent.mkdir(parents=True)
            only_import = "\n@~/.codex/AGENTS.md\n\n"
            instructions.write_text(only_import, encoding="utf-8")

            applied = run_sh("--client", "claude", "--home", str(home), "--apply", home=home)
            self.assertEqual(0, applied.returncode, applied.stdout + applied.stderr)
            self.assertIn("inherited from the Codex global instructions", applied.stdout)
            self.assertEqual(only_import, instructions.read_text(encoding="utf-8"))

            instructions.write_text("@~/.codex/AGENTS.md\nClaude-only rules.\n", encoding="utf-8")
            own = run_sh("--client", "claude", "--home", str(home), "--apply", home=home)
            self.assertEqual(0, own.returncode, own.stdout + own.stderr)
            self.assertEqual(1, instructions.read_text(encoding="utf-8").count(START))

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_an_import_of_a_codex_file_without_the_block_still_gets_the_block(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            (home / ".codex").mkdir(parents=True)
            (home / ".codex" / "AGENTS.md").write_text("# Codex rules only\n", encoding="utf-8")
            instructions = home / ".claude" / "CLAUDE.md"
            instructions.parent.mkdir(parents=True)
            instructions.write_text("@~/.codex/AGENTS.md\n", encoding="utf-8")

            applied = run_sh("--client", "claude", "--home", str(home), "--apply", home=home)

            self.assertEqual(0, applied.returncode, applied.stdout + applied.stderr)
            self.assertNotIn("inherited", applied.stdout)
            self.assertEqual(1, instructions.read_text(encoding="utf-8").count(START))

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_a_later_run_keeps_the_first_backup_and_every_link_in_the_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            granted = run_py(
                str(PERSONALIZATION), "--client", "claude", "--home", str(home), "--auto-update", "--apply", home=home,
            )
            self.assertEqual(0, granted.returncode, granted.stderr)
            instructions = home / ".claude" / "CLAUDE.md"
            original = instructions.read_bytes()
            flags = ("--client", "claude", "--home", str(home))
            self.assertEqual(0, run_py(str(INSTALL_PY), *flags, "--apply", home=home).returncode)
            # The owner deletes the block by hand and two links go missing.
            instructions.write_text("# Mine now\n", encoding="utf-8")
            skills = home / ".claude" / "skills"
            for name in SKILLS[:2]:
                (skills / name).unlink()

            again = run_sh(*flags, "--apply", home=home)
            self.assertEqual(0, again.returncode, again.stdout + again.stderr)
            self.assertIn("(2 new)", again.stdout)
            record = json.loads((home / ".nobrainer-flow-onboarding-claude.json").read_text(encoding="utf-8"))
            self.assertEqual(SKILLS, record["created_skills"])
            undone = run_sh(*flags, "--undo", "--apply", home=home)

            self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
            self.assertFalse(skills.exists())
            content = instructions.read_text(encoding="utf-8")
            # The block the file held before the first setup comes back, grant and all.
            self.assertIn("grants standing authorization to apply", content)
            self.assertIn("# Mine now", content)
            self.assertEqual(1, content.count(START))
            self.assertNotEqual(original, instructions.read_bytes())

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_a_link_that_points_elsewhere_is_never_taken_for_ours(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            skills = home / ".claude" / "skills"
            skills.mkdir(parents=True)
            elsewhere = Path(temp) / "elsewhere"
            elsewhere.mkdir()
            (skills / "nobrainer-build").symlink_to(elsewhere)

            planned = run_sh("--client", "claude", "--home", str(home), home=home)
            self.assertEqual(3, planned.returncode, planned.stdout + planned.stderr)
            self.assertIn("CONFLICT: nobrainer-build", planned.stderr)

            (skills / "nobrainer-build").unlink()
            flags = ("--client", "claude", "--home", str(home))
            self.assertEqual(0, run_sh(*flags, "--apply", home=home).returncode)
            (skills / "nobrainer-review").unlink()
            (skills / "nobrainer-review").symlink_to(elsewhere)
            refused = run_sh(*flags, "--undo", "--apply", home=home)
            self.assertEqual(3, refused.returncode)
            self.assertIn("PRESERVED: changed target", refused.stdout)
            self.assertTrue((skills / "nobrainer-build").is_symlink())

    def test_undo_without_a_recorded_setup_says_so(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            home.mkdir()

            result = run_sh("--client", "claude", "--home", str(home), "--undo", "--apply", home=home)

            self.assertEqual(3, result.returncode)
            self.assertIn("rollback state not found", result.stderr)
            self.assertIn("none is recorded for Claude Code", result.stderr)
            self.assertEqual([], entries(home))

    def test_a_relative_home_is_resolved_against_the_callers_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            here = Path(temp).resolve()

            result = run_sh("--client", "codex", "--home", "relative-home", cwd=here)

            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertRegex(result.stdout, r"TARGET: \S*/relative-home/\.codex/AGENTS\.md")
            self.assertFalse((ROOT / "relative-home").exists())
            self.assertEqual([], entries(here))

    @unittest.skipIf(os.name == "nt", "a fake ln on PATH is a POSIX check")
    def test_a_machine_that_cannot_link_is_told_so_before_anything_is_written(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            home.mkdir()
            fake = Path(temp) / "bin"
            fake.mkdir()
            (fake / "ln").write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            (fake / "ln").chmod(0o755)

            result = run_sh(
                "--client", "claude", "--home", str(home), "--apply", home=home,
                variables={"PATH": f"{fake}{os.pathsep}{os.environ['PATH']}"},
            )

            self.assertEqual(2, result.returncode)
            self.assertIn("cannot create symbolic links", result.stderr)
            self.assertEqual([], entries(home))

    @unittest.skipIf(os.name == "nt", "the tool sandbox is built from POSIX paths")
    def test_it_runs_with_no_python_on_the_path(self) -> None:
        tools = (
            "sh uname mktemp rm mkdir ln rmdir cat sed tr grep cut awk cmp tail od date cp mv sort chmod git"
        ).split()
        with tempfile.TemporaryDirectory() as temp:
            sandbox = Path(temp) / "bin"
            sandbox.mkdir()
            for tool in tools + ["sha256sum", "shasum", "iconv"]:
                found = shutil.which(tool)
                if found:
                    (sandbox / tool).symlink_to(found)
                elif tool in tools:
                    self.skipTest(f"{tool} is not installed here")
            home = Path(temp) / "home"
            instructions = home / ".claude" / "CLAUDE.md"
            instructions.parent.mkdir(parents=True)
            instructions.write_bytes(b"# Mine\n")
            variables = {"PATH": str(sandbox)}
            self.assertIsNone(shutil.which("python3", path=str(sandbox)))
            self.assertIsNone(shutil.which("python", path=str(sandbox)))
            flags = ("--client", "claude", "--home", str(home))
            shell = [str(sandbox / "sh")]

            applied = run_sh(*flags, "--apply", home=home, variables=variables, shell=shell)
            undone = run_sh(*flags, "--undo", "--apply", home=home, variables=variables, shell=shell)

            self.assertEqual(0, applied.returncode, applied.stdout + applied.stderr)
            self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
            self.assertEqual(b"# Mine\n", instructions.read_bytes())

    @unittest.skipIf(os.name == "nt", "the record holds Windows paths there")
    def test_a_record_it_cannot_read_points_to_the_python_undo(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "høme"
            home.mkdir()
            record = home / ".nobrainer-flow-onboarding-claude.json"
            record.write_text(
                json.dumps({"destination": str(home / ".claude" / "skills"), "created_skills": [], "profile": {}}, indent=2) + "\n",
                encoding="utf-8",
            )
            self.assertIn("\\u00f8", record.read_text(encoding="utf-8"))

            result = run_sh("--client", "claude", "--home", str(home), "--undo", home=home)

            self.assertEqual(3, result.returncode)
            self.assertIn("cannot read the setup record", result.stderr)
            self.assertIn("scripts/install.py --client claude --undo --apply", result.stderr)


if __name__ == "__main__":
    unittest.main()
