"""The no-Python installer, scripts/install.sh, against the real scripts and a private home.

It must behave like scripts/install.py: same locations and variables, same conflict
rule, the same setup record (either one undoes the other), no authorization granted,
and the instruction block byte for byte what the Python helper writes.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import itertools
import json
import os
import re
import shutil
import stat
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

DEFAULT_BLOCK = PERSONALIZATION_MODULE.build_block(None, False, False, None)
# The block an earlier version wrote: the same, with one sentence worded differently.
STALE_BLOCK = DEFAULT_BLOCK.replace(" Keep coordination in MAIN.", " Keep coordination in MAIN, always.")
# The default block 2.3.1 wrote, which also named the private nobrainer-ak skill.
BLOCK_2_3_1 = DEFAULT_BLOCK.replace(
    "- Use `nobrainer-writing` for material writing when available;",
    "- Use `nobrainer-ak` (`nbak`) for relevant marketing and sales content creation when available. "
    "For general writing use `nobrainer-writing` when available;",
)


def stale_layouts() -> dict[str, tuple[bytes, bytes, bytes]]:
    """Bytes before a block of an earlier version, the block, and the bytes after it."""

    stale = STALE_BLOCK.encode()
    return {
        "plain text around the block": (b"# Mine\n\n", stale, b"\n\nAfter\n"),
        "Windows line breaks": (b"# Mine\r\n\r\n", STALE_BLOCK.replace("\n", "\r\n").encode(), b"\r\nAfter\r\n"),
        "a block that starts the file": (b"", stale, b"\nAfter\n"),
        "a block that ends the file without a line break": (b"# Mine\n", stale, b""),
        "a byte order mark, a NUL byte and a lone CR": (b"\xef\xbb\xbf# Mine\x00\r after\r\n", stale, b"\nend"),
    }


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


def install_step(installer: str, *args: str, home: Path) -> subprocess.CompletedProcess[str]:
    """One run of the shell installer ("sh") or of the Python one ("py")."""

    if installer == "sh":
        return run_sh(*args, home=home)
    return run_py(str(INSTALL_PY), *args, home=home)


def chain(path: str) -> list[str]:
    """A relative path and each folder above it, outermost first."""

    parts = Path(path).parts
    return [Path(*parts[: count + 1]).as_posix() for count in range(len(parts))]


# Where a client keeps its skills and its instruction file, under a home that never ran it.
LAYOUTS = {
    "codex": (".agents/skills", ".codex/AGENTS.md"),
    "opencode": (".config/opencode/skills", ".config/opencode/AGENTS.md"),
}


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
        self.assertEqual(set(SKILLS_MODULE.RETIRED_LEGACY), names("RETIRED"))

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_foreign_retired_symlink_survives_preview_apply_repeat_and_undo(self) -> None:
        for shell in ([SHELL], *other_shells()):
            with self.subTest(shell=shell), tempfile.TemporaryDirectory() as temp:
                home = Path(temp) / "home"
                skills = home / ".claude" / "skills"
                skills.mkdir(parents=True)
                foreign = Path(temp) / "private-reddit"
                foreign.mkdir()
                marker = foreign / "SKILL.md"
                marker.write_bytes(b"private Reddit skill\x00\r\n")
                target = skills / "nobrainer-reddit"
                target.symlink_to(foreign, target_is_directory=True)
                original = target.lstat()
                original_link = target.readlink()
                before = entries(home)
                flags = ("--client", "claude", "--home", str(home))
                message = (
                    "PRESERVED_FOREIGN: nobrainer-reddit: retired from nobrainer-tech-flow; "
                    "left unchanged: "
                )

                for step in ((), ("--apply",), ("--apply",), ("--undo", "--apply")):
                    result = run_sh(*flags, *step, home=home, shell=shell)
                    self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                    if "--undo" not in step:
                        lines = [line for line in result.stderr.splitlines() if line.startswith(message)]
                        self.assertTrue(lines, result.stderr)
                        for line in lines:
                            if os.name == "nt":
                                # Git Bash prints its POSIX view of the Windows path.
                                self.assertTrue(line.endswith("/.claude/skills/nobrainer-reddit"), line)
                            else:
                                self.assertEqual(message + str(target), line)
                        self.assertNotIn("LEGACY: nobrainer-reddit", result.stderr)
                    if not step:
                        self.assertEqual(before, entries(home))
                    self.assertEqual(original_link, target.readlink())
                    self.assertEqual(original.st_ino, target.lstat().st_ino)
                    self.assertEqual(b"private Reddit skill\x00\r\n", marker.read_bytes())
                self.assertEqual([target], list(skills.iterdir()))
                self.assertFalse((home / ".nobrainer-flow-onboarding-claude.json").exists())

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_foreign_retired_directory_survives_preview_apply_repeat_and_undo(self) -> None:
        for shell in ([SHELL], *other_shells()):
            with self.subTest(shell=shell), tempfile.TemporaryDirectory() as temp:
                home = Path(temp) / "home"
                target = home / ".claude" / "skills" / "nobrainer-reddit"
                target.mkdir(parents=True)
                marker = target / "SKILL.md"
                marker.write_bytes(b"private Reddit skill\x00\r\n")
                original = target.lstat()
                before = entries(home)
                flags = ("--client", "claude", "--home", str(home))

                for step in ((), ("--apply",), ("--apply",), ("--undo", "--apply")):
                    result = run_sh(*flags, *step, home=home, shell=shell)
                    self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                    if "--undo" not in step:
                        self.assertIn("PRESERVED_FOREIGN: nobrainer-reddit:", result.stderr)
                    if not step:
                        self.assertEqual(before, entries(home))
                    self.assertEqual(original.st_ino, target.lstat().st_ino)
                    self.assertEqual([marker], list(target.iterdir()))
                    self.assertEqual(b"private Reddit skill\x00\r\n", marker.read_bytes())
                self.assertEqual([target], list(target.parent.iterdir()))

    def test_foreign_renamed_and_unmapped_names_still_block_in_every_shell(self) -> None:
        for shell in ([SHELL], *other_shells()):
            for name in ("nb-flow", "nobrainer-fast-audit"):
                with self.subTest(shell=shell, name=name), tempfile.TemporaryDirectory() as temp:
                    home = Path(temp) / "home"
                    target = home / ".claude" / "skills" / name
                    target.mkdir(parents=True)
                    marker = target / "SKILL.md"
                    marker.write_bytes(b"private skill\n")
                    before = entries(home)
                    for step in ((), ("--apply",)):
                        result = run_sh("--client", "claude", "--home", str(home), *step, home=home, shell=shell)
                        self.assertEqual(3, result.returncode, result.stdout + result.stderr)
                        self.assertIn(f"LEGACY: {name}:", result.stderr)
                        self.assertNotIn(f"PRESERVED_FOREIGN: {name}", result.stderr)
                        self.assertEqual(before, entries(home))
                        self.assertEqual(b"private skill\n", marker.read_bytes())

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_retired_exact_link_classification_matches_python_in_every_shell(self) -> None:
        for shell in ([SHELL], *other_shells()):
            for case in (
                "root", "skills", "relative-root", "relative-skills", "chain",
                "parent-link", "link-before-dotdot", "foreign", "canonical", "loop",
                "trailing-newline", "chained-trailing-newline",
            ):
                with self.subTest(shell=shell, case=case), tempfile.TemporaryDirectory() as temp:
                    home = Path(temp) / "home"
                    skills = home / ".claude" / "skills"
                    skills.mkdir(parents=True)
                    target = skills / "nobrainer-reddit"
                    bridge = Path(temp) / "bridge"
                    old_source = ROOT / "nobrainer-reddit"
                    linked = old_source
                    exact = case in {"root", "skills", "relative-root", "relative-skills", "chain", "parent-link", "link-before-dotdot"}
                    if case in {"skills", "relative-skills"}:
                        linked = ROOT / "skills" / "nobrainer-reddit"
                    if case.startswith("relative-"):
                        start = skills.resolve()
                        if os.path.splitdrive(linked)[0].lower() != os.path.splitdrive(start)[0].lower():
                            continue  # A relative link cannot cross Windows drives.
                        linked = Path(os.path.relpath(linked, start))
                    elif case == "chain":
                        bridge.symlink_to(old_source, target_is_directory=True)
                        linked = bridge
                    elif case in {"parent-link", "link-before-dotdot"}:
                        if case == "link-before-dotdot" and os.name == "nt":
                            continue  # Windows collapses ".." before it follows a link.
                        bridge.symlink_to(ROOT if case == "parent-link" else ROOT / "skills", target_is_directory=True)
                        linked = bridge / "nobrainer-reddit" if case == "parent-link" else bridge / ".." / "nobrainer-reddit"
                    elif case == "foreign":
                        linked = Path(temp) / "private-reddit"
                    elif case == "canonical":
                        linked = ROOT / "skills" / "nobrainer-build"
                    elif case == "loop":
                        bridge.symlink_to(bridge, target_is_directory=True)
                        linked = bridge
                    elif case in {"trailing-newline", "chained-trailing-newline"}:
                        if os.name == "nt":
                            continue  # Windows path syntax excludes this Unix filename.
                        linked = ROOT / "nobrainer-reddit\n"
                        if case == "chained-trailing-newline":
                            bridge.symlink_to(linked, target_is_directory=True)
                            linked = bridge
                    target.symlink_to(linked, target_is_directory=True)
                    self.assertEqual(exact, SKILLS_MODULE.is_exact_legacy_link(target, "nobrainer-reddit"))
                    original = target.lstat()
                    original_link = target.readlink()
                    for step in (((), ("--apply",)) if exact else ((),)):
                        result = run_sh("--client", "claude", "--home", str(home), *step, home=home, shell=shell)
                        self.assertEqual(3 if exact else 0, result.returncode, result.stdout + result.stderr)
                        self.assertIn("LEGACY: nobrainer-reddit:" if exact else "PRESERVED_FOREIGN: nobrainer-reddit:", result.stderr)
                        if exact:
                            self.assertIn("docs/MIGRATION_TO_FLOW.md", result.stderr)
                        self.assertEqual(original_link, target.readlink())
                        self.assertEqual(original.st_ino, target.lstat().st_ino)
                        self.assertEqual([target], list(skills.iterdir()))

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
                self.assertIn("INSTALLED:", applied.stdout)
                self.assertIn("NEXT: restart Claude Code", applied.stdout)
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
                record_path = home / ".nobrainer-flow-onboarding-claude.json"
                record = json.loads(record_path.read_text(encoding="utf-8"))
                self.assertEqual(SKILLS, record["created_skills"])
                self.assertEqual(Path(record["profile"]["target"]), instructions)
                if os.name != "nt":
                    self.assertEqual(0o600, stat.S_IMODE(record_path.stat().st_mode))

                again = run_sh(*flags, "--apply", home=home, shell=shell)
                self.assertEqual(0, again.returncode, again.stdout + again.stderr)
                self.assertIn("(0 new)", again.stdout)
                self.assertIn("UP TO DATE:", again.stdout)
                self.assertNotIn("INSTALLED:", again.stdout)
                self.assertNotIn("NEXT: restart", again.stdout)
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
    def test_a_repeat_apply_says_nothing_changed_and_asks_for_a_restart_only_after_a_change(self) -> None:
        for installer in ("sh", "py"):
            with self.subTest(installer=installer), tempfile.TemporaryDirectory() as temp:
                home = Path(temp) / "home"
                instructions = home / ".claude" / "CLAUDE.md"
                instructions.parent.mkdir(parents=True)
                instructions.write_bytes(b"# Mine\n")
                skills = home / ".claude" / "skills"
                flags = ("--client", "claude", "--home", str(home), "--apply")

                def apply() -> subprocess.CompletedProcess[str]:
                    if installer == "sh":
                        return run_sh(*flags, home=home)
                    return run_py(str(INSTALL_PY), *flags, home=home)

                def check(result: subprocess.CompletedProcess[str], changed: bool) -> None:
                    self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                    self.assertEqual(changed, "INSTALLED:" in result.stdout, result.stdout)
                    self.assertEqual(changed, "NEXT: restart Claude Code" in result.stdout, result.stdout)
                    self.assertEqual(not changed, "UP TO DATE:" in result.stdout, result.stdout)

                check(apply(), True)
                nothing = apply()
                check(nothing, False)
                self.assertIn("is already installed for Claude Code; nothing changed", nothing.stdout)
                self.assertIn("(0 new)", nothing.stdout)
                self.assertIn("left as it is", nothing.stdout)
                self.assertIn("UNDO:", nothing.stdout)
                self.assertNotIn("RECORD:", nothing.stdout)
                # Text added outside the block only updates the record, so undo accepts it.
                with instructions.open("ab") as handle:
                    handle.write(b"\n# Added later\n")
                edited = apply()
                check(edited, False)
                self.assertIn("RECORD: updated", edited.stdout)
                # A link that went missing and a block deleted by hand are written again.
                (skills / SKILLS[0]).unlink()
                written = instructions.read_bytes()
                instructions.write_bytes(written[: written.index(START.encode())])
                repaired = apply()
                check(repaired, True)
                self.assertIn("(1 new)", repaired.stdout)
                self.assertIn(START.encode(), instructions.read_bytes())

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
    def test_windows_line_breaks_in_the_record_and_the_file_are_undone_byte_for_byte(self) -> None:
        for undoer in ("sh", "py"):
            with self.subTest(undone_by=undoer), tempfile.TemporaryDirectory() as temp:
                home = Path(temp) / "home"
                earlier = run_py(str(PERSONALIZATION), "--client", "claude", "--home", str(home), "--apply", home=home)
                self.assertEqual(0, earlier.returncode, earlier.stderr)
                instructions = home / ".claude" / "CLAUDE.md"
                # A Windows editor saved the file, its block included, with CRLF line breaks.
                block = instructions.read_bytes().replace(b"\n", b"\r\n")
                original = b"# Mine\r\n\r\n" + block + b"\r\n# After\r\n"
                instructions.write_bytes(original)
                flags = ("--client", "claude", "--home", str(home))
                applied = run_py(str(INSTALL_PY), *flags, "--apply", home=home)
                self.assertEqual(0, applied.returncode, applied.stdout + applied.stderr)
                self.assertNotEqual(original, instructions.read_bytes())
                # Python writes the record with CRLF line breaks on Windows.
                record = home / ".nobrainer-flow-onboarding-claude.json"
                record.write_bytes(record.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))

                if undoer == "sh":
                    undone = run_sh(*flags, "--undo", "--apply", home=home)
                else:
                    undone = run_py(str(INSTALL_PY), *flags, "--undo", "--apply", home=home)

                self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
                self.assertIn("is back as it was before the setup", undone.stdout)
                self.assertEqual(original, instructions.read_bytes())
                self.assertFalse((home / ".claude" / "skills").exists())
                self.assertFalse(record.exists())

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_unusual_files_come_back_byte_for_byte_from_either_undo(self) -> None:
        originals = {
            "old Mac line breaks": b"a\rb\r",
            "a NUL byte": b"# Mine\x00x\n",
            "a byte order mark": b"\xef\xbb\xbf# Mine\r\n",
            "no final line break": b"# Mine",
        }
        for label, original in originals.items():
            for undoer in ("sh", "py"):
                with self.subTest(case=label, undone_by=undoer), tempfile.TemporaryDirectory() as temp:
                    home = Path(temp) / "home"
                    instructions = home / ".claude" / "CLAUDE.md"
                    instructions.parent.mkdir(parents=True)
                    instructions.write_bytes(original)
                    flags = ("--client", "claude", "--home", str(home))
                    applied = run_sh(*flags, "--apply", home=home)
                    self.assertEqual(0, applied.returncode, applied.stdout + applied.stderr)

                    if undoer == "sh":
                        undone = run_sh(*flags, "--undo", "--apply", home=home)
                    else:
                        undone = run_py(str(INSTALL_PY), *flags, "--undo", "--apply", home=home)

                    self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
                    self.assertEqual(original, instructions.read_bytes())

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_both_undos_give_the_same_bytes_after_edits_around_the_block(self) -> None:
        cases = {
            "text added after the block": (b"abc\n", b"\nlater\n", b"abc\nlater\n"),
            "a line break added at the end": (b"abc", b"\n", b"abc"),
            "text added to a file the setup created": (None, b"\nmine", b"mine"),
            "a blank file": (b"\n\n", b"", b"\n\n"),
        }
        for label, (original, added, expected) in cases.items():
            for undoer in ("sh", "py"):
                with self.subTest(case=label, undone_by=undoer), tempfile.TemporaryDirectory() as temp:
                    home = Path(temp) / "home"
                    instructions = home / ".claude" / "CLAUDE.md"
                    instructions.parent.mkdir(parents=True)
                    if original is not None:
                        instructions.write_bytes(original)
                    flags = ("--client", "claude", "--home", str(home))
                    self.assertEqual(0, run_sh(*flags, "--apply", home=home).returncode)
                    with instructions.open("ab") as handle:
                        handle.write(added)
                    # A repeat run records the edited file, so the undo accepts it.
                    self.assertEqual(0, run_sh(*flags, "--apply", home=home).returncode)

                    if undoer == "sh":
                        undone = run_sh(*flags, "--undo", "--apply", home=home)
                    else:
                        undone = run_py(str(INSTALL_PY), *flags, "--undo", "--apply", home=home)

                    self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
                    self.assertEqual(expected, instructions.read_bytes())

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_text_added_after_a_block_that_ended_the_file_keeps_its_own_line(self) -> None:
        for undoer in ("sh", "py"):
            with self.subTest(undone_by=undoer), tempfile.TemporaryDirectory() as temp:
                home = Path(temp) / "home"
                earlier = run_py(
                    str(PERSONALIZATION), "--client", "claude", "--home", str(home), "--auto-update", "--apply", home=home,
                )
                self.assertEqual(0, earlier.returncode, earlier.stderr)
                instructions = home / ".claude" / "CLAUDE.md"
                original = instructions.read_bytes()
                self.assertTrue(original.endswith(b"-->"))
                flags = ("--client", "claude", "--home", str(home))
                self.assertEqual(0, run_py(str(INSTALL_PY), *flags, "--apply", home=home).returncode)
                with instructions.open("ab") as handle:
                    handle.write(b"\nlater\n")
                self.assertEqual(0, run_py(str(INSTALL_PY), *flags, "--apply", home=home).returncode)

                if undoer == "sh":
                    undone = run_sh(*flags, "--undo", "--apply", home=home)
                else:
                    undone = run_py(str(INSTALL_PY), *flags, "--undo", "--apply", home=home)

                self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
                self.assertEqual(original + b"\nlater\n", instructions.read_bytes())

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_a_tampered_record_is_refused_and_nothing_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            instructions = home / ".claude" / "CLAUDE.md"
            instructions.parent.mkdir(parents=True)
            instructions.write_bytes(b"# Mine\n")
            flags = ("--client", "claude", "--home", str(home))
            self.assertEqual(0, run_sh(*flags, "--apply", home=home).returncode)
            record_path = home / ".nobrainer-flow-onboarding-claude.json"
            genuine = json.loads(record_path.read_text(encoding="utf-8"))
            written = instructions.read_bytes()
            elsewhere = home / "elsewhere.md"
            elsewhere.write_bytes(written)
            stray = instructions.parent / "stray.md"
            stray.write_bytes(b"# Mine\n")
            linked = instructions.parent / f"{instructions.name}.bak.link"
            linked.symlink_to(Path(genuine["profile"]["backup"]))
            off_lines = written.replace(b"\n" + START.encode(), b" " + START.encode())
            end_marker = b"<!-- NOBRAINER-TECH-FLOW:END -->"
            swapped = written.replace(START.encode(), b"\0").replace(end_marker, START.encode()).replace(b"\0", end_marker)

            def profile(**changes: str):
                return lambda record: record["profile"].update(changes)

            cases = {
                "a target outside the documented places": (profile(target=str(elsewhere)), written, "refusing unexpected personalization target"),
                "a backup not named after the target": (profile(backup=str(stray)), written, "refusing unexpected personalization backup"),
                "a backup that is a link": (profile(backup=str(linked)), written, "personalization backup must be a regular file"),
                "a hash of the wrong length": (profile(written_sha256=genuine["profile"]["written_sha256"][1:]), written, "invalid personalization readback hash"),
                "a skill that is not one of the eighteen": (lambda record: record["created_skills"].append("not-a-skill"), written, "cannot read the setup record"),
                "a block that does not stand on lines of its own": (
                    profile(written_sha256=hashlib.sha256(off_lines).hexdigest()), off_lines, "does not stand on lines of its own",
                ),
                "markers in the wrong order": (
                    profile(written_sha256=hashlib.sha256(swapped).hexdigest()), swapped, "does not stand on lines of its own",
                ),
            }
            for label, (tamper, content, message) in cases.items():
                with self.subTest(case=label):
                    record = copy.deepcopy(genuine)
                    tamper(record)
                    record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
                    instructions.write_bytes(content)
                    before = (instructions.read_bytes(), record_path.read_bytes(), entries(home))

                    refused = run_sh(*flags, "--undo", "--apply", home=home)

                    self.assertEqual(3, refused.returncode, refused.stdout + refused.stderr)
                    self.assertIn(message, refused.stdout + refused.stderr)
                    self.assertEqual(before, (instructions.read_bytes(), record_path.read_bytes(), entries(home)))

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_a_setup_recorded_elsewhere_stops_the_next_run_and_its_hint_undoes_it(self) -> None:
        for client, name, message, via_home in (
            ("claude", "CLAUDE_CONFIG_DIR", "different skills destination", False),
            ("codex", "CODEX_HOME", "different personalization target", False),
            # With --home the variables do not count, so the printed undo sets the home
            # and the variable instead of passing --home.
            ("claude", "CLAUDE_CONFIG_DIR", "different skills destination", True),
        ):
            with self.subTest(client=client, via_home=via_home), tempfile.TemporaryDirectory() as temp:
                root = Path(temp).resolve()
                home, first, second = root / "home", root / "first", root / "second"
                for folder in (home, first, second):
                    folder.mkdir()
                applied = run_sh("--client", client, "--apply", home=home, variables={name: str(first)})
                self.assertEqual(0, applied.returncode, applied.stdout + applied.stderr)

                if via_home:
                    refused = run_sh("--client", client, "--home", str(home), home=home)
                    later_home, later = second, {}
                else:
                    refused = run_sh("--client", client, home=home, variables={name: str(second)})
                    later_home, later = home, {name: str(second)}

                self.assertEqual(3, refused.returncode, refused.stdout + refused.stderr)
                self.assertIn(message, refused.stderr)
                self.assertEqual([], list(second.iterdir()))
                hint = re.search(r"^HINT: undo that setup with (.*), then run this again$", refused.stderr, re.MULTILINE)
                self.assertIsNotNone(hint, refused.stderr)
                self.assertIn(f"{name}=", hint.group(1))
                # The hint works as printed, from an environment that names other places.
                path = f"{Path(SHELL).parent}{os.pathsep}{os.environ.get('PATH', '')}"
                undone = subprocess.run(
                    [SHELL, "-c", hint.group(1)],
                    cwd=root, env=environment(later_home, {**later, "PATH": path}),
                    text=True, encoding="utf-8", errors="replace", capture_output=True, check=False, stdin=subprocess.DEVNULL,
                )
                self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
                self.assertFalse((home / f".nobrainer-flow-onboarding-{client}.json").exists())

    def test_paths_the_python_scripts_would_refuse_are_refused_before_anything_is_written(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cases = {"a tab": "h\tme", "U+2028": "h me", "U+0085": "h\u0085me"}
            if os.name != "nt" and shutil.which("iconv"):
                # Passed as the bytes h, 0xE9, m, e.
                cases["bytes that are not UTF-8"] = "h\udce9me"
            for label, name in cases.items():
                with self.subTest(case=label):
                    result = run_sh("--client", "claude", "--home", str(root / name), home=root)
                    self.assertEqual(2, result.returncode, result.stdout + result.stderr)
                    self.assertIn("ERROR: --home ", result.stderr)
                    self.assertEqual([], entries(root))
            fine = run_sh("--client", "claude", "--home", str(root / "zażółć"), home=root)
            self.assertEqual(0, fine.returncode, fine.stdout + fine.stderr)

            if shutil.which("iconv"):
                home = root / "home"
                instructions = home / ".claude" / "CLAUDE.md"
                instructions.parent.mkdir(parents=True)
                instructions.write_bytes(b"# Latin-1: \xe9\n")
                refused = run_sh("--client", "claude", "--home", str(home), "--apply", home=home)
                self.assertEqual(3, refused.returncode, refused.stdout + refused.stderr)
                self.assertIn("target is not UTF-8 text", refused.stderr)
                self.assertEqual(b"# Latin-1: \xe9\n", instructions.read_bytes())
                self.assertFalse((home / ".claude" / "skills").exists())

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_a_claude_file_that_becomes_only_the_codex_import_can_still_be_undone(self) -> None:
        for undoer in ("sh", "py"):
            with self.subTest(undone_by=undoer), tempfile.TemporaryDirectory() as temp:
                home = Path(temp) / "home"
                codex = run_py(str(PERSONALIZATION), "--client", "codex", "--home", str(home), "--apply", home=home)
                self.assertEqual(0, codex.returncode, codex.stderr)
                instructions = home / ".claude" / "CLAUDE.md"
                instructions.parent.mkdir(parents=True)
                instructions.write_bytes(b"# Mine\n")
                flags = ("--client", "claude", "--home", str(home))
                self.assertEqual(0, run_sh(*flags, "--apply", home=home).returncode)
                instructions.write_bytes(b"@~/.codex/AGENTS.md\n")
                again = run_sh(*flags, "--apply", home=home)
                self.assertIn("inherited from the Codex global instructions", again.stdout)

                if undoer == "sh":
                    undone = run_sh(*flags, "--undo", "--apply", home=home)
                else:
                    undone = run_py(str(INSTALL_PY), *flags, "--undo", "--apply", home=home)

                self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
                self.assertFalse((home / ".claude" / "skills").exists())
                self.assertEqual(b"@~/.codex/AGENTS.md\n", instructions.read_bytes())

    def test_it_runs_by_relative_path_from_the_checkout_with_cdpath_set(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            home.mkdir()

            result = subprocess.run(
                [SHELL, "scripts/install.sh", "--client", "claude", "--home", str(home)],
                cwd=ROOT, env=environment(home, {"CDPATH": "."}),
                text=True, encoding="utf-8", errors="replace", capture_output=True, check=False, stdin=subprocess.DEVNULL,
            )

            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn("SKILLS:", result.stdout)

    def test_a_tilde_the_shell_left_alone_in_home_is_the_home_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            here = Path(temp) / "here"
            home.mkdir()
            here.mkdir()

            result = run_sh("--client", "claude", "--home=~/profile", home=home, cwd=here)

            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertRegex(result.stdout, r"SKILLS: \d+ to link into \S*/home/profile/\.claude/skills ")
            self.assertEqual([], entries(here))
            other = run_sh("--client", "claude", "--home=~someone/profile", home=home, cwd=here)
            self.assertEqual(2, other.returncode, other.stdout + other.stderr)
            self.assertIn("write the full path", other.stderr)

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
    def test_undo_after_the_file_was_edited_unlinks_the_skills_and_leaves_the_file(self) -> None:
        for installer in ("sh", "py"):
            with self.subTest(installer=installer), tempfile.TemporaryDirectory() as temp:
                home = Path(temp) / "home"
                instructions = home / ".claude" / "CLAUDE.md"
                skills = home / ".claude" / "skills"
                flags = ("--client", "claude", "--home", str(home))
                self.assertEqual(0, install_step(installer, *flags, "--apply", home=home).returncode)
                with instructions.open("a", encoding="utf-8") as handle:
                    handle.write("\nedited after the setup\n")
                edited = instructions.read_bytes()

                preview = install_step(installer, *flags, "--undo", home=home)

                self.assertEqual(0, preview.returncode, preview.stdout + preview.stderr)
                self.assertIn("PRESERVED: personalization changed since setup", preview.stdout)
                self.assertNotIn("remove the managed block", preview.stdout)
                self.assertTrue((skills / "nobrainer-build").is_symlink())
                partly = install_step(installer, *flags, "--undo", "--apply", home=home)

                self.assertEqual(3, partly.returncode, partly.stdout + partly.stderr)
                self.assertIn("PARTLY UNDONE:", partly.stdout)
                self.assertIn(f"SKILLS: {len(SKILLS)} unlinked", partly.stdout)
                self.assertIn("PRESERVED: personalization changed since setup", partly.stdout)
                self.assertIn("HINT: ", partly.stdout)
                self.assertEqual([], list(skills.iterdir()))
                self.assertEqual(edited, instructions.read_bytes())
                record = json.loads((home / ".nobrainer-flow-onboarding-claude.json").read_text(encoding="utf-8"))
                self.assertEqual([], record["created_skills"])

                # As the hint says: the setup again records the file as it is, then the undo
                # takes the block out and keeps the edit.
                self.assertEqual(0, install_step(installer, *flags, "--apply", home=home).returncode)
                undone = install_step(installer, *flags, "--undo", "--apply", home=home)

                self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
                content = instructions.read_text(encoding="utf-8") if instructions.exists() else ""
                self.assertNotIn(START, content)
                self.assertIn("edited after the setup", content)
                self.assertFalse(skills.exists())
                self.assertFalse((home / ".nobrainer-flow-onboarding-claude.json").exists())

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_undo_completes_once_the_block_was_taken_out_by_hand(self) -> None:
        # The hint of a partial undo offers to delete the block by hand; the next undo then
        # finishes instead of stopping at the changed file again.
        for installer in ("sh", "py"):
            for partly_first in (True, False):
                with self.subTest(installer=installer, partly_first=partly_first), tempfile.TemporaryDirectory() as temp:
                    home = Path(temp) / "home"
                    instructions = home / ".codex" / "AGENTS.md"
                    flags = ("--client", "codex", "--home", str(home))
                    self.assertEqual(0, install_step(installer, *flags, "--apply", home=home).returncode)
                    instructions.write_bytes(instructions.read_bytes() + b"\nedited after the setup\n")
                    if partly_first:
                        partly = install_step(installer, *flags, "--undo", "--apply", home=home)
                        self.assertEqual(3, partly.returncode, partly.stdout + partly.stderr)
                        self.assertIn("undo again", partly.stdout)
                    text = instructions.read_text(encoding="utf-8")
                    edited = (text[: text.index(START)] + text[text.index("<!-- NOBRAINER-TECH-FLOW:END -->") + 32 :]).encode()
                    instructions.write_bytes(edited)

                    preview = install_step(installer, *flags, "--undo", home=home)

                    self.assertEqual(0, preview.returncode, preview.stdout + preview.stderr)
                    self.assertIn("no longer holds the managed block, so it is left as it is", preview.stdout)
                    undone = install_step(installer, *flags, "--undo", "--apply", home=home)

                    self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
                    self.assertIn("UNDONE:", undone.stdout)
                    self.assertNotIn("PARTLY", undone.stdout)
                    self.assertNotIn("managed block included", undone.stdout)
                    self.assertIn("no longer holds the managed block, so it is left as it is", undone.stdout)
                    self.assertEqual(edited, instructions.read_bytes())
                    self.assertEqual([".codex", ".codex/AGENTS.md"], entries(home))

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_undo_after_an_edit_does_not_need_the_backup(self) -> None:
        # The backup only serves to put the block back, which an edited file does not get.
        for installer in ("sh", "py"):
            with self.subTest(installer=installer), tempfile.TemporaryDirectory() as temp:
                home = Path(temp) / "home"
                instructions = home / ".codex" / "AGENTS.md"
                instructions.parent.mkdir(parents=True)
                instructions.write_bytes(b"# Mine\n")
                flags = ("--client", "codex", "--home", str(home))
                self.assertEqual(0, install_step(installer, *flags, "--apply", home=home).returncode)
                instructions.write_bytes(instructions.read_bytes() + b"\nedited after the setup\n")
                edited = instructions.read_bytes()
                for backup in instructions.parent.glob("AGENTS.md.bak.*"):
                    backup.unlink()

                partly = install_step(installer, *flags, "--undo", "--apply", home=home)

                self.assertEqual(3, partly.returncode, partly.stdout + partly.stderr)
                self.assertIn("PARTLY UNDONE:", partly.stdout)
                self.assertEqual([], list((home / ".agents" / "skills").iterdir()))
                self.assertEqual(edited, instructions.read_bytes())

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_the_hint_after_an_edit_never_leads_to_an_undo_that_cannot_run(self) -> None:
        # The hint offers to record the file as it is now and undo again. That record keeps the
        # backup it names, so with the backup gone the next undo would stop on it, and the hint
        # must ask for the block to be taken out by hand instead.
        for installer in ("sh", "py"):
            for backup_kept in (True, False):
                with self.subTest(installer=installer, backup_kept=backup_kept), tempfile.TemporaryDirectory() as temp:
                    home = Path(temp) / "home"
                    instructions = home / ".codex" / "AGENTS.md"
                    instructions.parent.mkdir(parents=True)
                    instructions.write_bytes(b"# Mine\n")
                    flags = ("--client", "codex", "--home", str(home))
                    self.assertEqual(0, install_step(installer, *flags, "--apply", home=home).returncode)
                    instructions.write_bytes(instructions.read_bytes() + b"\nedited after the setup\n")
                    if not backup_kept:
                        for backup in instructions.parent.glob("AGENTS.md.bak.*"):
                            backup.unlink()

                    partly = install_step(installer, *flags, "--undo", "--apply", home=home)

                    self.assertEqual(3, partly.returncode, partly.stdout + partly.stderr)
                    hint = "\n".join(line for line in partly.stdout.splitlines() if line.startswith("HINT: "))
                    self.assertIn("delete the lines from", hint.lower())
                    if backup_kept:
                        self.assertIn("records the file as it is now", hint)
                        self.assertEqual(0, install_step(installer, *flags, "--apply", home=home).returncode)
                    else:
                        self.assertNotIn("records the file as it is now", hint)
                        text = instructions.read_bytes()
                        start, end = text.index(START.encode()), text.index(b"<!-- NOBRAINER-TECH-FLOW:END -->")
                        instructions.write_bytes(text[:start] + text[end + len(b"<!-- NOBRAINER-TECH-FLOW:END -->"):])
                    undone = install_step(installer, *flags, "--undo", "--apply", home=home)

                    self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
                    self.assertNotIn(START.encode(), instructions.read_bytes())
                    self.assertIn(b"edited after the setup", instructions.read_bytes())
                    self.assertFalse((home / ".nobrainer-flow-onboarding-codex.json").exists())

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    @unittest.skipIf(os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0), "needs a folder this account cannot search")
    def test_a_record_in_a_home_that_cannot_be_searched_stops_the_undo(self) -> None:
        # The record sits in a home this account can no longer search, while CLAUDE_CONFIG_DIR
        # keeps the skills and the instructions reachable. The record cannot be checked, which
        # is not the same as no record, so the undo stops instead of reporting nothing to undo.
        for installer in ("sh", "py"):
            for mode in (0o000, 0o600):
                with self.subTest(installer=installer, mode=oct(mode)), tempfile.TemporaryDirectory() as temp:
                    home = Path(temp) / "home"
                    home.mkdir()
                    config = Path(temp) / "profile"
                    config.mkdir()
                    variables = {"CLAUDE_CONFIG_DIR": str(config)}

                    def step(*more: str) -> subprocess.CompletedProcess[str]:
                        if installer == "sh":
                            return run_sh("--client", "claude", *more, home=home, variables=variables)
                        return subprocess.run(
                            [sys.executable, str(INSTALL_PY), "--client", "claude", *more],
                            cwd=ROOT, text=True, encoding="utf-8", errors="replace", capture_output=True,
                            check=False, stdin=subprocess.DEVNULL, env=environment(home, variables),
                        )

                    self.assertEqual(0, step("--apply").returncode)
                    record = home / ".nobrainer-flow-onboarding-claude.json"
                    before = (entries(config), (config / "CLAUDE.md").read_bytes(), record.read_bytes())
                    home.chmod(mode)
                    try:
                        refused = step("--undo", "--apply")
                    finally:
                        home.chmod(0o755)

                    self.assertEqual(3, refused.returncode, refused.stdout + refused.stderr)
                    self.assertNotIn("NOTHING TO UNDO", refused.stdout)
                    self.assertIn(f"ERROR: cannot check {record}", refused.stderr)
                    self.assertNotIn("Traceback", refused.stderr)
                    self.assertEqual(before, (entries(config), (config / "CLAUDE.md").read_bytes(), record.read_bytes()))
                    self.assertTrue((config / "skills" / SKILLS[0]).is_symlink())

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_undo_refuses_a_link_that_changed_since(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            instructions = home / ".claude" / "CLAUDE.md"
            skills = home / ".claude" / "skills"
            flags = ("--client", "claude", "--home", str(home))
            self.assertEqual(0, run_sh(*flags, "--apply", home=home).returncode)
            before = instructions.read_bytes()
            (skills / "nobrainer-review").unlink()
            (skills / "nobrainer-review").symlink_to(Path(temp), target_is_directory=True)

            refused = run_sh(*flags, "--undo", "--apply", home=home)

            self.assertEqual(3, refused.returncode)
            self.assertIn("PRESERVED: changed target", refused.stdout)
            self.assertTrue((skills / "nobrainer-build").is_symlink())
            self.assertEqual(before, instructions.read_bytes())

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
            variables = {"CLAUDE_CONFIG_DIR": str(profile), "XDG_CONFIG_HOME": "~/.config", "CODEX_HOME": "/with\ta tab"}

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
    def test_a_block_of_an_earlier_version_is_replaced_and_every_byte_around_it_stays(self) -> None:
        self.assertNotEqual(DEFAULT_BLOCK, STALE_BLOCK)
        every_shell = ("Windows line breaks", "a byte order mark, a NUL byte and a lone CR")
        for label, (before, stale, after) in stale_layouts().items():
            original = before + stale + after
            expected = before + DEFAULT_BLOCK.encode() + after
            for shell in [[SHELL], *other_shells()] if label in every_shell else [[SHELL]]:
                with self.subTest(layout=label, shell=shell), tempfile.TemporaryDirectory() as temp:
                    home = Path(temp) / "home"
                    target = home / ".codex" / "AGENTS.md"
                    target.parent.mkdir(parents=True)
                    target.write_bytes(original)
                    flags = ("--client", "codex", "--home", str(home))

                    applied = run_sh(*flags, "--apply", home=home, shell=shell)

                    self.assertEqual(0, applied.returncode, applied.stdout + applied.stderr)
                    self.assertEqual(expected, target.read_bytes())
                    self.assertIn("INSTALLED:", applied.stdout)
                    self.assertIn("managed block updated to this version's text", applied.stdout)
                    self.assertIn("NEXT: restart Codex", applied.stdout)
                    backups = [path for path in target.parent.iterdir() if ".bak." in path.name]
                    self.assertEqual([original], [path.read_bytes() for path in backups])
                    again = run_sh(*flags, "--apply", home=home, shell=shell)
                    self.assertEqual(0, again.returncode, again.stdout + again.stderr)
                    self.assertIn("UP TO DATE:", again.stdout)
                    self.assertEqual(expected, target.read_bytes())
            with self.subTest(layout=label, installer="py"), tempfile.TemporaryDirectory() as temp:
                home = Path(temp) / "home"
                target = home / ".codex" / "AGENTS.md"
                target.parent.mkdir(parents=True)
                target.write_bytes(original)

                applied = run_py(str(INSTALL_PY), "--client", "codex", "--home", str(home), "--apply", home=home)

                self.assertEqual(0, applied.returncode, applied.stdout + applied.stderr)
                self.assertEqual(expected, target.read_bytes())
                self.assertIn("managed block updated to this version's text", applied.stdout)

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_the_block_2_3_1_wrote_is_replaced_by_either_installer_and_undone_byte_for_byte(self) -> None:
        self.assertNotEqual(DEFAULT_BLOCK, BLOCK_2_3_1)
        for installer in ("sh", "py"):
            with self.subTest(installer=installer), tempfile.TemporaryDirectory() as temp:
                home = Path(temp) / "home"
                instructions = home / ".claude" / "CLAUDE.md"
                instructions.parent.mkdir(parents=True)
                original = b"# Mine\n\n" + BLOCK_2_3_1.encode() + b"\n\nAfter\n"
                instructions.write_bytes(original)
                flags = ("--client", "claude", "--home", str(home))

                applied = install_step(installer, *flags, "--apply", home=home)

                self.assertEqual(0, applied.returncode, applied.stdout + applied.stderr)
                self.assertIn("managed block updated to this version's text", applied.stdout)
                self.assertEqual(b"# Mine\n\n" + DEFAULT_BLOCK.encode() + b"\n\nAfter\n", instructions.read_bytes())
                self.assertNotIn(b"nobrainer-ak", instructions.read_bytes())
                undone = install_step(installer, *flags, "--undo", "--apply", home=home)

                self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
                self.assertEqual(original, instructions.read_bytes())

    def test_the_preview_of_a_replaced_block_shows_what_changes_and_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            target = home / ".codex" / "AGENTS.md"
            target.parent.mkdir(parents=True)
            original = b"# Mine\n\n" + STALE_BLOCK.encode() + b"\n\nAfter\n"
            target.write_bytes(original)
            before = entries(home)

            preview = run_sh("--client", "codex", "--home", str(home), home=home)

            self.assertEqual(0, preview.returncode, preview.stdout + preview.stderr)
            lines = preview.stdout.splitlines()
            self.assertIn("UPDATE: nobrainer-tech-flow personalization block", lines)
            self.assertIn("PRESERVED: content outside the managed block", lines)
            self.assertIn("-" + next(line for line in STALE_BLOCK.splitlines() if "always" in line), lines)
            self.assertIn("+" + next(line for line in DEFAULT_BLOCK.splitlines() if "MAIN. Never" in line), lines)
            self.assertIn("NO_CHANGES:", preview.stdout)
            self.assertEqual(original, target.read_bytes())
            self.assertEqual(before, entries(home))

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_undo_after_a_replaced_block_puts_the_profile_back_as_it_was_before_the_setup(self) -> None:
        for installer in ("sh", "py"):
            with self.subTest(installer=installer), tempfile.TemporaryDirectory() as temp:
                home = Path(temp) / "home"
                target = home / ".codex" / "AGENTS.md"
                target.parent.mkdir(parents=True)
                original = b"# Mine\r\n\r\nAlways answer in Polish.\r\n"
                target.write_bytes(original)
                flags = ("--client", "codex", "--home", str(home))
                self.assertEqual(0, install_step(installer, *flags, "--apply", home=home).returncode)
                # The setup of an earlier version: the same file, its block worded as it was then.
                installed = target.read_bytes()
                aged = installed.replace(DEFAULT_BLOCK.encode(), STALE_BLOCK.encode())
                self.assertNotEqual(installed, aged)
                target.write_bytes(aged)
                record_path = home / ".nobrainer-flow-onboarding-codex.json"
                record = json.loads(record_path.read_text(encoding="utf-8"))
                record["profile"]["written_sha256"] = hashlib.sha256(aged).hexdigest()
                record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

                refreshed = install_step(installer, *flags, "--apply", home=home)

                self.assertEqual(0, refreshed.returncode, refreshed.stdout + refreshed.stderr)
                self.assertEqual(installed, target.read_bytes())
                undone = install_step(installer, *flags, "--undo", "--apply", home=home)

                self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
                self.assertEqual(original, target.read_bytes())
                self.assertFalse(record_path.exists())

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_a_replaced_block_with_no_record_is_undone_to_the_block_it_replaced(self) -> None:
        for installer in ("sh", "py"):
            with self.subTest(installer=installer), tempfile.TemporaryDirectory() as temp:
                home = Path(temp) / "home"
                target = home / ".codex" / "AGENTS.md"
                target.parent.mkdir(parents=True)
                original = b"# Mine\n\n" + STALE_BLOCK.encode() + b"\n\nAfter\n"
                target.write_bytes(original)
                flags = ("--client", "codex", "--home", str(home))

                applied = install_step(installer, *flags, "--apply", home=home)

                self.assertEqual(0, applied.returncode, applied.stdout + applied.stderr)
                self.assertEqual(b"# Mine\n\n" + DEFAULT_BLOCK.encode() + b"\n\nAfter\n", target.read_bytes())
                undone = install_step(installer, *flags, "--undo", "--apply", home=home)

                self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
                self.assertEqual(original, target.read_bytes())

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_a_block_that_cannot_be_replaced_without_losing_something_is_left_as_it_is(self) -> None:
        preference = "- Owner-approved setup preference: Answer in Polish.\n"
        stale_with_grant = PERSONALIZATION_MODULE.build_block(None, True, False, None).replace(
            " Keep coordination in MAIN.", " Keep coordination in MAIN, always."
        )
        cases = {
            "a preference": STALE_BLOCK.replace("- Use `nobrainer-writing`", preference + "- Use `nobrainer-writing`").encode(),
            "a standing authorization": stale_with_grant.encode(),
            "a saved wiki root": PERSONALIZATION_MODULE.build_block(Path("/wiki"), False, False, None).replace(
                " Keep coordination in MAIN.", " Keep coordination in MAIN, always."
            ).encode(),
            "a start marker in the middle of a line": b"# Mine\ntext " + START.encode() + b"\nbody\n<!-- NOBRAINER-TECH-FLOW:END -->\n",
        }
        for label, original in cases.items():
            with self.subTest(case=label), tempfile.TemporaryDirectory() as temp:
                home = Path(temp) / "home"
                target = home / ".codex" / "AGENTS.md"
                target.parent.mkdir(parents=True)
                target.write_bytes(original)
                flags = ("--client", "codex", "--home", str(home))

                preview = run_sh(*flags, home=home)
                applied = run_sh(*flags, "--apply", home=home)

                self.assertIn("PRESENT: the managed block is already there and is left as it is", preview.stdout)
                self.assertIn("NOTE: it differs from this version's default block", preview.stdout)
                self.assertEqual(0, applied.returncode, applied.stdout + applied.stderr)
                self.assertIn("already has the managed block; left as it is", applied.stdout)
                self.assertEqual(original, target.read_bytes())
                self.assertEqual([], [path for path in target.parent.iterdir() if ".bak." in path.name])

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

    def test_undo_without_a_recorded_setup_is_a_clean_no_op_in_every_shell(self) -> None:
        for shell in ([SHELL], *other_shells()):
            for step in (("--undo",), ("--undo", "--apply")):
                with self.subTest(shell=shell, step=step), tempfile.TemporaryDirectory() as temp:
                    home = Path(temp) / "home"
                    home.mkdir()

                    result = run_sh("--client", "claude", "--home", str(home), *step, home=home, shell=shell)

                    self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                    self.assertIn("NOTHING TO UNDO: no setup is recorded for Claude Code", result.stdout)
                    # Git Bash names the path its own way (/tmp/...), so only its end is compared.
                    self.assertIn(f"{Path(temp).name}/home/.nobrainer-flow-onboarding-claude.json", result.stdout)
                    self.assertEqual("", result.stderr)
                    self.assertEqual([], entries(home))

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_a_second_undo_changes_nothing_and_succeeds_for_either_installer(self) -> None:
        for installer in ("sh", "py"):
            with self.subTest(installer=installer), tempfile.TemporaryDirectory() as temp:
                home = Path(temp) / "home"
                instructions = home / ".claude" / "CLAUDE.md"
                instructions.parent.mkdir(parents=True)
                original = b"# Mine\n"
                instructions.write_bytes(original)
                flags = ("--client", "claude", "--home", str(home))

                def step(*more: str) -> subprocess.CompletedProcess[str]:
                    if installer == "sh":
                        return run_sh(*flags, *more, home=home)
                    return run_py(str(INSTALL_PY), *flags, *more, home=home)

                self.assertEqual(0, step("--apply").returncode)
                first = step("--undo", "--apply")
                self.assertEqual(0, first.returncode, first.stdout + first.stderr)
                self.assertIn("UNDONE:", first.stdout)
                after_first = (entries(home), instructions.read_bytes())

                for more in (("--undo",), ("--undo", "--apply")):
                    second = step(*more)

                    self.assertEqual(0, second.returncode, second.stdout + second.stderr)
                    self.assertIn("NOTHING TO UNDO", second.stdout)
                    self.assertNotIn("UNDONE:", second.stdout)
                    self.assertEqual("", second.stderr)
                    self.assertEqual(after_first, (entries(home), instructions.read_bytes()))
                self.assertEqual(original, instructions.read_bytes())

    @unittest.skipIf(os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0), "needs a mode this account cannot write through")
    def test_a_failed_record_save_puts_a_read_only_instruction_file_back(self) -> None:
        # The client folders can be written, the home that holds the record cannot. The run
        # must undo its own changes, the read-only instruction file included.
        for installer in ("sh", "py"):
            with self.subTest(installer=installer), tempfile.TemporaryDirectory() as temp:
                home = Path(temp) / "home"
                instructions = home / ".codex" / "AGENTS.md"
                instructions.parent.mkdir(parents=True)
                (home / ".agents" / "skills").mkdir(parents=True)
                instructions.write_bytes(b"# Mine\n")
                instructions.chmod(0o444)
                home.chmod(0o555)
                try:
                    result = install_step(installer, "--client", "codex", "--home", str(home), "--apply", home=home)
                finally:
                    home.chmod(0o755)

                self.assertNotEqual(0, result.returncode, result.stdout + result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual(b"# Mine\n", instructions.read_bytes())
                self.assertEqual(0o444, instructions.stat().st_mode & 0o777)
                self.assertEqual([], entries(home / ".agents" / "skills"))
                self.assertFalse((home / ".nobrainer-flow-onboarding-codex.json").exists())

    def test_a_record_with_a_relative_destination_is_refused_and_does_not_hang(self) -> None:
        # A hand-edited record names its skills folder without a leading slash and lists a
        # folder no setup could have made. Both installers must refuse it, not loop on it.
        # "skills" exists in the folder the installers run from; "missing-skills" does not.
        for installer, relative in itertools.product(("sh", "py"), ("skills", "missing-skills")):
            with self.subTest(installer=installer, destination=relative), tempfile.TemporaryDirectory() as temp:
                home = Path(temp) / "home"
                home.mkdir()
                flags = ("--client", "codex", "--home", str(home))
                self.assertEqual(0, install_step(installer, *flags, "--apply", home=home).returncode)
                record_path = home / ".nobrainer-flow-onboarding-codex.json"
                # Edited in place: the shell installer reads only the layout it writes.
                text = record_path.read_text(encoding="utf-8")
                record = json.loads(text)
                text = text.replace(json.dumps(record["destination"]), json.dumps(relative), 1)
                text = text.replace(json.dumps(record["created_dirs"][0]), json.dumps(str(Path(temp) / "elsewhere")), 1)
                record_path.write_text(text, encoding="utf-8")
                self.assertEqual(relative, json.loads(text)["destination"])
                command = [SHELL, SCRIPT.as_posix()] if installer == "sh" else [sys.executable, str(INSTALL_PY)]
                try:
                    result = subprocess.run(
                        [*command, *flags, "--undo", "--apply"], cwd=ROOT, text=True, encoding="utf-8",
                        errors="replace", capture_output=True, check=False, stdin=subprocess.DEVNULL,
                        env=environment(home), timeout=120,
                    )
                except subprocess.TimeoutExpired:
                    self.fail("the undo did not finish")

                self.assertEqual(3, result.returncode, result.stdout + result.stderr)
                self.assertTrue(record_path.exists())

    def test_undo_still_fails_when_a_record_is_there_but_cannot_be_used(self) -> None:
        def garbage(path: Path) -> None:
            path.write_text("{ this is not a setup record", encoding="utf-8")

        def folder(path: Path) -> None:
            path.mkdir()

        def dangling_link(path: Path) -> None:
            path.symlink_to(path.parent / "nowhere")

        cases = {
            "text that is not JSON": (".nobrainer-flow-onboarding-claude.json", garbage),
            "a folder in its place": (".nobrainer-flow-onboarding-claude.json", folder),
            "a dangling link in its place": (".nobrainer-flow-onboarding-claude.json", dangling_link),
            "an unreadable older record": (".nobrainer-flow-onboarding.json", garbage),
            "a dangling link as the older record": (".nobrainer-flow-onboarding.json", dangling_link),
        }
        for label, (name, make) in cases.items():
            if "dangling" in label and not symlinks_work():
                continue
            for installer in ("sh", "py"):
                with self.subTest(case=label, installer=installer), tempfile.TemporaryDirectory() as temp:
                    home = Path(temp) / "home"
                    home.mkdir()
                    make(home / name)
                    before = entries(home)
                    flags = ("--client", "claude", "--home", str(home), "--undo", "--apply")

                    if installer == "sh":
                        result = run_sh(*flags, home=home)
                    else:
                        result = run_py(str(INSTALL_PY), *flags, home=home)

                    self.assertNotEqual(0, result.returncode, result.stdout + result.stderr)
                    self.assertNotIn("NOTHING TO UNDO", result.stdout)
                    self.assertIn("ERROR", result.stdout + result.stderr)
                    self.assertEqual(before, entries(home))

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_undo_takes_away_the_folders_the_setup_made_in_every_available_shell(self) -> None:
        # Codex keeps its skills in ~/.agents and its instructions in ~/.codex. Neither is
        # there when the client never ran, and after the undo neither is left behind.
        folders = [".agents", ".agents/skills", ".codex"]
        for shell in ([SHELL], *other_shells()):
            with self.subTest(shell=shell), tempfile.TemporaryDirectory() as temp:
                home = Path(temp) / "home"
                home.mkdir()
                flags = ("--client", "codex", "--home", str(home))

                applied = run_sh(*flags, "--apply", home=home, shell=shell)

                self.assertEqual(0, applied.returncode, applied.stdout + applied.stderr)
                record_path = home / ".nobrainer-flow-onboarding-codex.json"
                record = json.loads(record_path.read_text(encoding="utf-8"))
                # Each folder is written the way it really is, with the links on the way resolved.
                self.assertEqual(sorted(str((home / folder).resolve()) for folder in folders), sorted(record["created_dirs"]))
                tree = entries(home)

                preview = run_sh(*flags, "--undo", home=home, shell=shell)

                self.assertEqual(0, preview.returncode, preview.stdout + preview.stderr)
                # Git Bash names a folder its own way (a drive or /tmp spelling), so only the part
                # below the temporary folder is compared; the record above checks the full path.
                for folder in folders:
                    self.assertIn(f"{Path(temp).name}/home/{folder}: removed if it is still empty", preview.stdout)
                self.assertEqual(tree, entries(home))

                undone = run_sh(*flags, "--undo", "--apply", home=home, shell=shell)

                self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
                for folder in folders:
                    self.assertRegex(undone.stdout, f"FOLDER: removed the empty folder .*{Path(temp).name}/home/{re.escape(folder)}\n")
                self.assertEqual([], entries(home))

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_undo_leaves_the_profile_as_it_was_whatever_was_there_before(self) -> None:
        for installer in ("sh", "py"):
            for client, (skills, instructions) in LAYOUTS.items():
                folder = Path(instructions).parent.as_posix()
                starts = {
                    "an empty profile": [],
                    "only the outer skills folder": [chain(skills)[0]],
                    "the folder of the instruction file": [folder],
                    "an empty skills folder": [skills],
                }
                for start, existing in starts.items():
                    with self.subTest(installer=installer, client=client, start=start), tempfile.TemporaryDirectory() as temp:
                        home = Path(temp) / "home"
                        home.mkdir()
                        for name in existing:
                            (home / name).mkdir(parents=True, exist_ok=True)
                        before = entries(home)
                        flags = ("--client", client, "--home", str(home))

                        applied = install_step(installer, *flags, "--apply", home=home)

                        self.assertEqual(0, applied.returncode, applied.stdout + applied.stderr)
                        self.assertTrue((home / skills / SKILLS[0]).is_symlink())
                        undone = install_step(installer, *flags, "--undo", "--apply", home=home)

                        self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
                        self.assertEqual(before, entries(home))

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_a_folder_that_holds_something_now_stays_when_the_setup_is_undone(self) -> None:
        for installer in ("sh", "py"):
            for client, (skills, instructions) in LAYOUTS.items():
                with self.subTest(installer=installer, client=client), tempfile.TemporaryDirectory() as temp:
                    home = Path(temp) / "home"
                    home.mkdir()
                    flags = ("--client", client, "--home", str(home))
                    folder = Path(instructions).parent.as_posix()
                    self.assertEqual(0, install_step(installer, *flags, "--apply", home=home).returncode)
                    notes = home / folder / "notes.md"
                    notes.write_bytes(b"mine\n")

                    undone = install_step(installer, *flags, "--undo", "--apply", home=home)

                    self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
                    self.assertEqual("", undone.stderr)
                    self.assertEqual([*chain(folder), f"{folder}/notes.md"], entries(home))
                    self.assertEqual(b"mine\n", notes.read_bytes())

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_a_record_from_before_the_folder_list_is_undone_as_it_was_then(self) -> None:
        # Such a record cannot say which folders the setup made, so it claims none and only the
        # skills folder goes, when it is empty. Running the setup again keeps it that way.
        # "skills" exists in the folder the installers run from; "missing-skills" does not.
        for installer, relative in itertools.product(("sh", "py"), ("skills", "missing-skills")):
            with self.subTest(installer=installer, destination=relative), tempfile.TemporaryDirectory() as temp:
                home = Path(temp) / "home"
                home.mkdir()
                flags = ("--client", "codex", "--home", str(home))
                self.assertEqual(0, install_step(installer, *flags, "--apply", home=home).returncode)
                record_path = home / ".nobrainer-flow-onboarding-codex.json"
                record = json.loads(record_path.read_text(encoding="utf-8"))
                self.assertIn("created_dirs", record)
                del record["created_dirs"]
                record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
                (home / LAYOUTS["codex"][0] / SKILLS[0]).unlink()

                again = install_step(installer, *flags, "--apply", home=home)

                self.assertEqual(0, again.returncode, again.stdout + again.stderr)
                self.assertIn("(1 new)", again.stdout)
                self.assertNotIn("created_dirs", json.loads(record_path.read_text(encoding="utf-8")))
                undone = install_step(installer, *flags, "--undo", "--apply", home=home)

                self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
                self.assertNotIn("FOLDER:", undone.stdout)
                self.assertEqual([".agents", ".codex"], entries(home))

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_a_record_that_lists_a_folder_the_setup_cannot_have_made_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            home.mkdir()
            flags = ("--client", "codex", "--home", str(home))
            self.assertEqual(0, run_sh(*flags, "--apply", home=home).returncode)
            record_path = home / ".nobrainer-flow-onboarding-codex.json"
            genuine = json.loads(record_path.read_text(encoding="utf-8"))
            elsewhere = home / "elsewhere"
            elsewhere.mkdir()
            listed = genuine["created_dirs"]
            cases = {
                "a relative path": ["relative/place"],
                "a path with ..": [f"{home}/.agents/../.codex"],
                "the root": ["/"],
                "a folder beside the setup's own": [str(elsewhere)],
                "a folder listed twice": [*listed, listed[0]],
                "text instead of a list": str(home / ".codex"),
                "an entry that is not text": [7],
            }
            for label, value in cases.items():
                for installer in ("sh", "py"):
                    for step in (("--undo", "--apply"), ("--apply",)):
                        with self.subTest(case=label, installer=installer, step=step):
                            record = copy.deepcopy(genuine)
                            record["created_dirs"] = value
                            record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
                            before = (entries(home), record_path.read_bytes())

                            refused = install_step(installer, *flags, *step, home=home)

                            # The shell script and the undo refuse with 3; a Python apply reports its own code.
                            if step == ("--undo", "--apply") or installer == "sh":
                                self.assertEqual(3, refused.returncode, refused.stdout + refused.stderr)
                            else:
                                self.assertNotEqual(0, refused.returncode, refused.stdout + refused.stderr)
                            self.assertNotIn("Traceback", refused.stderr)
                            self.assertEqual(before, (entries(home), record_path.read_bytes()))

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_a_folder_that_now_lies_under_a_link_is_left_where_the_link_points(self) -> None:
        # After the setup, ~/.config is swapped for a link to another tree that has folders of
        # the same names. The undo must not follow the link and remove them.
        for installer in ("sh", "py"):
            with self.subTest(installer=installer), tempfile.TemporaryDirectory() as temp:
                home = Path(temp) / "home"
                home.mkdir()
                flags = ("--client", "opencode", "--home", str(home))
                self.assertEqual(0, install_step(installer, *flags, "--apply", home=home).returncode)
                (home / ".config").rename(Path(temp) / "moved")
                elsewhere = Path(temp) / "elsewhere"
                (elsewhere / "opencode" / "skills").mkdir(parents=True)
                (home / ".config").symlink_to(elsewhere, target_is_directory=True)

                undone = install_step(installer, *flags, "--undo", "--apply", home=home)

                self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
                self.assertIn("a folder above it is a link now, so it is left as it is", undone.stdout)
                self.assertNotIn("FOLDER: removed", undone.stdout)
                self.assertEqual(["opencode", "opencode/skills"], entries(elsewhere))
                self.assertTrue((home / ".config").is_symlink())

    @unittest.skipIf(os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0), "needs a mode this account cannot write through")
    def test_a_read_only_instruction_file_is_appended_to_and_refreshed_and_stays_read_only(self) -> None:
        for installer in ("sh", "py"):
            with self.subTest(installer=installer), tempfile.TemporaryDirectory() as temp:
                home = Path(temp) / "home"
                instructions = home / ".codex" / "AGENTS.md"
                instructions.parent.mkdir(parents=True)
                instructions.write_bytes(b"# Mine\n")
                instructions.chmod(0o444)
                flags = ("--client", "codex", "--home", str(home), "--apply")

                appended = install_step(installer, *flags, home=home)

                self.assertEqual(0, appended.returncode, appended.stdout + appended.stderr)
                self.assertIn(b"NOBRAINER-TECH-FLOW:START", instructions.read_bytes())
                self.assertEqual(0o444, instructions.stat().st_mode & 0o777)
                text = instructions.read_bytes()
                start = text.index(b"NOBRAINER-TECH-FLOW:START")
                instructions.chmod(0o644)
                instructions.write_bytes(text[:start] + text[start:].replace(b"task entrypoint", b"entry", 1))
                instructions.chmod(0o444)

                refreshed = install_step(installer, *flags, home=home)

                self.assertEqual(0, refreshed.returncode, refreshed.stdout + refreshed.stderr)
                self.assertEqual(text, instructions.read_bytes())
                self.assertEqual(0o444, instructions.stat().st_mode & 0o777)
                # The undo writes the file the same way: the block goes and the mode stays.
                undone = install_step(installer, "--client", "codex", "--home", str(home), "--undo", "--apply", home=home)

                self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
                self.assertEqual(b"# Mine\n", instructions.read_bytes())
                self.assertEqual(0o444, instructions.stat().st_mode & 0o777)
                self.assertEqual([".codex", ".codex/AGENTS.md"], [name for name in entries(home) if ".bak." not in name])

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    @unittest.skipIf(os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0), "needs a file this account cannot read")
    def test_an_instruction_file_or_backup_the_undo_cannot_read_stops_it_before_anything_changes(self) -> None:
        # A file that cannot be read cannot be told apart from one without the block. Taking it
        # for one would remove the links and the record while the block stays in the file.
        for installer in ("sh", "py"):
            for unreadable in ("instruction file", "backup"):
                with self.subTest(installer=installer, unreadable=unreadable), tempfile.TemporaryDirectory() as temp:
                    home = Path(temp) / "home"
                    instructions = home / ".codex" / "AGENTS.md"
                    instructions.parent.mkdir(parents=True)
                    instructions.write_bytes(b"# Mine\n")
                    flags = ("--client", "codex", "--home", str(home))
                    self.assertEqual(0, install_step(installer, *flags, "--apply", home=home).returncode)
                    record_path = home / ".nobrainer-flow-onboarding-codex.json"
                    (backup,) = instructions.parent.glob("AGENTS.md.bak.*")
                    locked = instructions if unreadable == "instruction file" else backup
                    before = (entries(home), record_path.read_bytes(), instructions.read_bytes())
                    locked.chmod(0o000)
                    try:
                        refused = install_step(installer, *flags, "--undo", "--apply", home=home)
                    finally:
                        locked.chmod(0o644)

                    self.assertEqual(3, refused.returncode, refused.stdout + refused.stderr)
                    self.assertIn(f"ERROR: cannot read {locked}", refused.stderr)
                    self.assertNotIn("Traceback", refused.stderr)
                    self.assertEqual(before, (entries(home), record_path.read_bytes(), instructions.read_bytes()))
                    self.assertTrue((home / ".agents" / "skills" / SKILLS[0]).is_symlink())

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_a_folder_named_through_dot_dot_that_was_there_before_survives_the_undo(self) -> None:
        # CLAUDE_CONFIG_DIR reaches an existing folder through a folder that does not exist
        # yet. Before the setup, "missing/.." does not exist either, but once "missing" is made
        # it is the existing folder, and the undo must not take that one away.
        for installer in ("sh", "py"):
            for alias in ("missing/../config", "missing/../../profile/config"):
                with self.subTest(installer=installer, alias=alias), tempfile.TemporaryDirectory() as temp:
                    home = Path(temp) / "home"
                    home.mkdir()
                    profile = Path(temp) / "profile"
                    profile.mkdir()
                    variables = {"CLAUDE_CONFIG_DIR": f"{profile}/{alias}"}

                    def step(*more: str) -> subprocess.CompletedProcess[str]:
                        if installer == "sh":
                            return run_sh("--client", "claude", *more, home=home, variables=variables)
                        return subprocess.run(
                            [sys.executable, str(INSTALL_PY), "--client", "claude", *more],
                            cwd=ROOT, text=True, encoding="utf-8", errors="replace", capture_output=True,
                            check=False, stdin=subprocess.DEVNULL, env=environment(home, variables),
                        )

                    applied = step("--apply")

                    self.assertEqual(0, applied.returncode, applied.stdout + applied.stderr)
                    # Windows drops "missing/.." from the path before any folder is made.
                    folders = ["config", "config/skills"] + ([] if os.name == "nt" else ["missing"])
                    made = [name for name in entries(profile) if not name.startswith("config/skills/")]
                    self.assertEqual(sorted([*folders, "config/CLAUDE.md"]), made)
                    record = json.loads((home / ".nobrainer-flow-onboarding-claude.json").read_text(encoding="utf-8"))
                    real = profile.resolve()
                    self.assertEqual(sorted(str(real / name) for name in folders), sorted(record["created_dirs"]))
                    undone = step("--undo", "--apply")

                    self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
                    self.assertTrue(profile.is_dir())
                    self.assertEqual([], entries(profile))
                    self.assertEqual([], entries(home))

    @unittest.skipUnless(os.name == "nt", "directory junctions exist only on Windows")
    def test_the_undo_leaves_a_junction_put_in_place_of_a_folder_it_made(self) -> None:
        # After the setup, ~/.agents is replaced by a junction to a folder that holds an empty
        # skills folder. Removing the junction would disconnect that folder from whatever uses it.
        for installer in ("sh", "py"):
            with self.subTest(installer=installer), tempfile.TemporaryDirectory() as temp:
                home = Path(temp) / "home"
                home.mkdir()
                flags = ("--client", "codex", "--home", str(home))
                self.assertEqual(0, install_step(installer, *flags, "--apply", home=home).returncode)
                theirs = Path(temp) / "theirs"
                (theirs / "skills").mkdir(parents=True)
                shutil.rmtree(home / ".agents")
                junction = subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(home / ".agents"), str(theirs)],
                    text=True, capture_output=True, check=False,
                )
                self.assertEqual(0, junction.returncode, junction.stdout + junction.stderr)

                undone = install_step(installer, *flags, "--undo", "--apply", home=home)

                self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
                self.assertTrue((home / ".agents").exists())
                self.assertEqual(["skills"], entries(theirs))

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_a_repeat_apply_never_hands_a_folder_behind_a_new_link_to_the_undo(self) -> None:
        # After the setup, ~/.agents is swapped for a link to a folder that was there before
        # and holds an empty skills folder. Applying again and undoing must leave that folder.
        # "skills" exists in the folder the installers run from; "missing-skills" does not.
        for installer, relative in itertools.product(("sh", "py"), ("skills", "missing-skills")):
            with self.subTest(installer=installer, destination=relative), tempfile.TemporaryDirectory() as temp:
                home = Path(temp) / "home"
                home.mkdir()
                flags = ("--client", "codex", "--home", str(home))
                self.assertEqual(0, install_step(installer, *flags, "--apply", home=home).returncode)
                record_path = home / ".nobrainer-flow-onboarding-codex.json"
                first = json.loads(record_path.read_text(encoding="utf-8"))["created_dirs"]
                theirs = Path(temp) / "theirs"
                (theirs / "skills").mkdir(parents=True)
                shutil.rmtree(home / ".agents")
                (home / ".agents").symlink_to(theirs, target_is_directory=True)

                again = install_step(installer, *flags, "--apply", home=home)

                self.assertEqual(0, again.returncode, again.stdout + again.stderr)
                self.assertEqual(first, json.loads(record_path.read_text(encoding="utf-8"))["created_dirs"])
                undone = install_step(installer, *flags, "--undo", "--apply", home=home)

                self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
                self.assertEqual(["skills"], entries(theirs))
                self.assertTrue((home / ".agents").is_symlink())

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_folders_the_setup_made_that_a_link_joined_since_are_still_undone(self) -> None:
        # After a Codex setup, ~/.agents/skills is moved to ~/.codex/skills and ~/.agents is
        # replaced by a link to ~/.codex. Two untouched folders of the record now lead to one.
        # The undo still takes the links away, and leaves the moved tree and the link alone.
        runs = [("sh", shell) for shell in ([SHELL], *other_shells())] + [("py", None)]
        for installer, shell in runs:
            with self.subTest(installer=installer, shell=shell), tempfile.TemporaryDirectory() as temp:
                home = Path(temp) / "home"
                home.mkdir()
                flags = ("--client", "codex", "--home", str(home))

                def step(*more: str) -> subprocess.CompletedProcess[str]:
                    if shell:
                        return run_sh(*flags, *more, home=home, shell=shell)
                    return install_step(installer, *flags, *more, home=home)

                self.assertEqual(0, step("--apply").returncode)
                (home / ".agents" / "skills").rename(home / ".codex" / "skills")
                (home / ".agents").rmdir()
                (home / ".agents").symlink_to(home / ".codex", target_is_directory=True)
                (home / ".codex" / "config.toml").write_text("mine\n", encoding="utf-8")

                undone = step("--undo", "--apply")

                self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
                self.assertIn(f"SKILLS: {len(SKILLS)} unlinked", undone.stdout)
                self.assertEqual([".agents", ".codex", ".codex/config.toml", ".codex/skills"], entries(home))
                # The link still leads to ~/.codex. readlink on Windows adds a \\?\ prefix, so the
                # resolved paths are compared.
                self.assertTrue((home / ".agents").is_symlink())
                self.assertEqual((home / ".codex").resolve(), (home / ".agents").resolve())
                self.assertEqual("mine\n", (home / ".codex" / "config.toml").read_text(encoding="utf-8"))

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_two_entries_that_lead_to_one_folder_keep_that_folder(self) -> None:
        # A record that lists a home that was there before under two spellings, its real path
        # and a link to it, is accepted, but neither spelling can be trusted as made by the
        # setup. The undo removes the links and the folders it did make, and keeps the home.
        runs = [("sh", shell) for shell in ([SHELL], *other_shells())] + [("py", None)]
        for installer, shell in runs:
            with self.subTest(installer=installer, shell=shell), tempfile.TemporaryDirectory() as temp:
                home = Path(temp) / "home"
                home.mkdir()
                alias = Path(temp) / "alias"
                alias.symlink_to(home, target_is_directory=True)
                flags = ("--client", "codex", "--home", str(home))

                def step(*more: str) -> subprocess.CompletedProcess[str]:
                    if shell:
                        return run_sh(*flags, *more, home=home, shell=shell)
                    return install_step(installer, *flags, *more, home=home)

                self.assertEqual(0, step("--apply").returncode)
                record_path = home / ".nobrainer-flow-onboarding-codex.json"
                record = json.loads(record_path.read_text(encoding="utf-8"))
                record["created_dirs"] = [*record["created_dirs"], str(alias), str(home.resolve())]
                record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

                undone = step("--undo", "--apply")

                self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
                self.assertIn(f"SKILLS: {len(SKILLS)} unlinked", undone.stdout)
                self.assertTrue(home.is_dir())
                self.assertEqual([], entries(home))
                self.assertTrue(alias.is_symlink())
                # Both spellings are kept and named. Git Bash prints its POSIX view of the
                # Windows path (/tmp/... or /c/...), so each line is matched by its end.
                kept = [line for line in undone.stdout.splitlines() if "another folder in the record leads to the same folder" in line]
                self.assertEqual(2, len(kept), undone.stdout)
                for name in ("alias", "home"):
                    self.assertTrue(
                        any(re.match(rf"PRESERVED: .*{re.escape(Path(temp).name)}[\\/]{name}: ", line) for line in kept),
                        undone.stdout,
                    )

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    @unittest.skipIf(os.name == "nt", "Windows does not allow a line break in a file name")
    def test_a_folder_whose_real_path_holds_a_line_break_stops_the_setup_before_anything_is_written(self) -> None:
        # The path as written is plain, but a link on the way leads to a folder whose name holds
        # a line break. The record lists the folders the setup makes as they really are, so the
        # setup must refuse before it writes anything, not record a path no undo can read.
        layouts = {
            # ~/.claude is a link, and the skills folder would be made behind it.
            "claude": ("skills", {}, True),
            # CODEX_HOME names a folder still to be made behind a link.
            "codex": ("sub", {"CODEX_HOME": "{link}/sub"}, False),
        }
        runs = [("sh", shell) for shell in ([SHELL], *other_shells())] + [("py", None)]
        for (client, (made, variables, at_home)), name, (installer, shell) in itertools.product(
            layouts.items(), ("real\nname", "real\n"), runs
        ):
            with self.subTest(client=client, name=name, installer=installer, shell=shell), tempfile.TemporaryDirectory() as temp:
                home = Path(temp) / "home"
                home.mkdir()
                real = Path(temp) / name
                real.mkdir()
                link = home / ".claude" if at_home else Path(temp) / "link"
                link.symlink_to(real, target_is_directory=True)
                env = {key: value.format(link=link) for key, value in variables.items()}
                before = entries(Path(temp))
                if shell:
                    result = run_sh("--client", client, "--apply", home=home, variables=env, shell=shell)
                else:
                    result = subprocess.run(
                        [sys.executable, str(INSTALL_PY), "--client", client, "--apply"],
                        cwd=ROOT, text=True, encoding="utf-8", errors="replace", capture_output=True,
                        check=False, stdin=subprocess.DEVNULL, env=environment(home, env),
                    )

                self.assertEqual(2, result.returncode, result.stdout + result.stderr)
                self.assertIn("control character", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual(before, entries(Path(temp)))
                self.assertFalse((real / made).exists())

    @unittest.skipIf(os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0), "needs a folder this account cannot write")
    def test_a_home_that_cannot_be_made_stops_the_setup_before_anything_is_written(self) -> None:
        # CLAUDE_CONFIG_DIR is writable, but the home for the record lies under a folder that
        # is not. Nothing may be written that no record describes.
        for installer in ("sh", "py"):
            with self.subTest(installer=installer), tempfile.TemporaryDirectory() as temp:
                locked = Path(temp) / "locked"
                locked.mkdir()
                home = locked / "home"
                config = Path(temp) / "claude-config"
                config.mkdir()
                variables = {"CLAUDE_CONFIG_DIR": str(config)}
                locked.chmod(0o555)
                try:
                    if installer == "sh":
                        result = run_sh("--client", "claude", "--apply", home=home, variables=variables)
                    else:
                        result = subprocess.run(
                            [sys.executable, str(INSTALL_PY), "--client", "claude", "--apply"],
                            cwd=ROOT, text=True, encoding="utf-8", errors="replace", capture_output=True,
                            check=False, stdin=subprocess.DEVNULL, env=environment(home, variables),
                        )
                finally:
                    locked.chmod(0o755)

                self.assertNotEqual(0, result.returncode, result.stdout + result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual([], entries(config))
                self.assertFalse(home.exists())

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_a_home_made_only_for_the_record_is_taken_away_again(self) -> None:
        # CLAUDE_CONFIG_DIR puts the skills and the instructions in a folder that exists, and
        # the home is made only to hold the setup record. The undo takes the home away too.
        for installer in ("sh", "py"):
            with self.subTest(installer=installer), tempfile.TemporaryDirectory() as temp:
                home = Path(temp) / "missing-home"
                config = Path(temp) / "claude-config"
                config.mkdir()
                variables = {"CLAUDE_CONFIG_DIR": str(config)}

                def step(*more: str) -> subprocess.CompletedProcess[str]:
                    if installer == "sh":
                        return run_sh("--client", "claude", *more, home=home, variables=variables)
                    return subprocess.run(
                        [sys.executable, str(INSTALL_PY), "--client", "claude", *more],
                        cwd=ROOT, text=True, encoding="utf-8", errors="replace", capture_output=True,
                        check=False, stdin=subprocess.DEVNULL, env=environment(home, variables),
                    )

                applied = step("--apply")

                self.assertEqual(0, applied.returncode, applied.stdout + applied.stderr)
                self.assertEqual([".nobrainer-flow-onboarding-claude.json"], entries(home))
                record = json.loads((home / ".nobrainer-flow-onboarding-claude.json").read_text(encoding="utf-8"))
                self.assertIn(str(home.resolve()), record["created_dirs"])
                undone = step("--undo", "--apply")

                self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
                self.assertFalse(home.exists())
                self.assertEqual([], entries(config))

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_a_home_the_setup_had_to_create_is_taken_away_again(self) -> None:
        for installer in ("sh", "py"):
            with self.subTest(installer=installer), tempfile.TemporaryDirectory() as temp:
                home = Path(temp) / "fresh" / "profile"
                flags = ("--client", "codex", "--home", str(home))

                applied = install_step(installer, *flags, "--apply", home=home)

                self.assertEqual(0, applied.returncode, applied.stdout + applied.stderr)
                self.assertTrue((home / ".agents" / "skills" / SKILLS[0]).is_symlink())
                undone = install_step(installer, *flags, "--undo", "--apply", home=home)

                self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
                self.assertEqual([], entries(Path(temp)))

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_either_installer_takes_away_the_folders_the_other_one_recorded(self) -> None:
        for installer, undoer in (("sh", "py"), ("py", "sh")):
            with self.subTest(installed_by=installer), tempfile.TemporaryDirectory() as temp:
                home = Path(temp) / "home"
                home.mkdir()
                flags = ("--client", "opencode", "--home", str(home))
                self.assertEqual(0, install_step(installer, *flags, "--apply", home=home).returncode)
                # A link that went missing makes the next run rewrite the record, folder list included.
                (home / LAYOUTS["opencode"][0] / SKILLS[0]).unlink()
                repeated = install_step(undoer, *flags, "--apply", home=home)
                self.assertEqual(0, repeated.returncode, repeated.stdout + repeated.stderr)
                self.assertIn("(1 new)", repeated.stdout)

                undone = install_step(undoer, *flags, "--undo", "--apply", home=home)

                self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
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
            "sh uname mktemp rm mkdir ln rmdir cat sed tr grep cut head tail cmp od date cp mv sort chmod git ls readlink"
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
            retired = home / ".claude" / "skills" / "nobrainer-reddit"
            retired.parent.mkdir()
            retired.symlink_to(Path(temp) / "private-reddit", target_is_directory=True)
            original_link = retired.readlink()
            original_inode = retired.lstat().st_ino
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
            self.assertIn("PRESERVED_FOREIGN: nobrainer-reddit:", applied.stderr)
            self.assertEqual(original_link, retired.readlink())
            self.assertEqual(original_inode, retired.lstat().st_ino)

    @unittest.skipUnless(symlinks_work(), "this account cannot create symbolic links")
    def test_a_setup_from_before_the_context_rename_updates_and_undoes(self) -> None:
        # Until 2.4.1 the module was called nobrainer-codex-context. A setup made then
        # records that name and links it into this checkout, where it no longer exists.
        old, new = "nobrainer-codex-context", "nobrainer-context"
        runs = [("sh", shell) for shell in ([SHELL], *other_shells())] + [("py", None)]
        for installer, shell in runs:
            with self.subTest(installer=installer, shell=shell), tempfile.TemporaryDirectory() as temp:
                home = Path(temp) / "home"
                flags = ("--client", "claude", "--home", str(home))

                def run(*extra: str) -> subprocess.CompletedProcess[str]:
                    if installer == "sh":
                        return run_sh(*flags, *extra, home=home, shell=shell)
                    return run_py(str(INSTALL_PY), *flags, *extra, home=home)

                self.assertEqual(0, run("--apply").returncode)
                skills = home / ".claude" / "skills"
                record = home / ".nobrainer-flow-onboarding-claude.json"
                (skills / new).unlink()
                (skills / old).symlink_to(ROOT / "skills" / old, target_is_directory=True)
                record.write_text(record.read_text(encoding="utf-8").replace(f'"{new}"', f'"{old}"'), encoding="utf-8")
                pristine = record.read_bytes()

                preview = run("--undo")
                self.assertEqual(0, preview.returncode, preview.stdout + preview.stderr)
                self.assertIn("unlink 18 skills", preview.stdout)
                undone = run("--undo", "--apply")
                self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
                self.assertFalse(skills.exists())

                # Updating instead: the setup removes the link its record lists, links the
                # new name and records it, and undo then removes everything.
                self.assertEqual(0, run("--apply").returncode)
                (skills / new).unlink()
                (skills / old).symlink_to(ROOT / "skills" / old, target_is_directory=True)
                record.write_bytes(pristine)
                shown = run()
                self.assertEqual(0, shown.returncode, shown.stdout + shown.stderr)
                self.assertTrue((skills / old).is_symlink())
                self.assertIn(f"REMOVE_RETIRED: {old}", shown.stdout)

                # A run that fails after the old link was due to go keeps it: the record
                # cannot be written here, and the previous installation stays usable.
                if os.name != "nt" and os.geteuid() != 0:
                    home.chmod(0o555)
                    try:
                        failed = run("--apply")
                    finally:
                        home.chmod(0o755)
                    self.assertNotEqual(0, failed.returncode, failed.stdout + failed.stderr)
                    self.assertTrue((skills / old).is_symlink(), failed.stdout + failed.stderr)
                    self.assertEqual(ROOT / "skills" / old, (skills / old).readlink())
                    self.assertEqual(pristine, record.read_bytes())
                    self.assertEqual([], [p.name for p in skills.iterdir() if p.name.startswith(".")])
                    if (skills / new).is_symlink():
                        (skills / new).unlink()
                again = run("--apply")
                self.assertEqual(0, again.returncode, again.stdout + again.stderr)
                self.assertFalse((skills / old).is_symlink())
                self.assertEqual(ROOT / "skills" / new, (skills / new).resolve())
                saved = json.loads(record.read_text(encoding="utf-8"))["created_skills"]
                self.assertEqual(SKILLS, saved)

                # A link at the old name that the record does not list is not this setup's.
                (skills / old).symlink_to(ROOT / "skills" / old, target_is_directory=True)
                blocked = run("--apply")
                self.assertEqual(3, blocked.returncode, blocked.stdout + blocked.stderr)
                self.assertTrue((skills / old).is_symlink())

                # A run that only retires the old link still rewrites the record.
                data = json.loads(record.read_text(encoding="utf-8"))
                data["created_skills"] = sorted(data["created_skills"] + [old])
                record.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
                only = run("--apply")
                self.assertEqual(0, only.returncode, only.stdout + only.stderr)
                self.assertFalse((skills / old).is_symlink())
                self.assertEqual(SKILLS, json.loads(record.read_text(encoding="utf-8"))["created_skills"])
                self.assertEqual(0, run("--undo", "--apply").returncode)

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
            self.assertIn(f"--undo --apply --home '{home}'", result.stderr)


if __name__ == "__main__":
    unittest.main()
