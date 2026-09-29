"""Behaviours that broke, or could break, on Windows.

The module runs on every platform; the Windows-only checks skip elsewhere. CI runs it
on a Windows runner, which is the only place the hook wrapper and the copy-mode
publish are exercised for real.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.support import find_bash


ROOT = Path(__file__).resolve().parents[1]
MARKER = "NOBRAINER_BOOTSTRAP_V1"
CONFIG_VARIABLES = ("CLAUDE_CONFIG_DIR", "CODEX_HOME", "XDG_CONFIG_HOME")


def run(command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=kwargs.pop("cwd", ROOT),
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
        stdin=subprocess.DEVNULL,
        **kwargs,
    )


def clean_environment(**extra: str) -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if key not in CONFIG_VARIABLES + ("CLAUDE_PLUGIN_ROOT", "CURSOR_PLUGIN_ROOT")
    }
    environment.update(extra)
    return environment


class HookScriptTests(unittest.TestCase):
    @unittest.skipIf(find_bash() is None, "bash is not available")
    def test_session_start_emits_the_bootstrap_for_each_host(self) -> None:
        bash = find_bash()
        # str(Path) is what a Windows host passes: backslashes on Windows.
        script = str(ROOT / "hooks" / "session-start")
        for variable, expected in (
            ("CLAUDE_PLUGIN_ROOT", ("hookSpecificOutput", "additionalContext")),
            ("CURSOR_PLUGIN_ROOT", ("additional_context",)),
        ):
            with self.subTest(host=variable):
                result = run(
                    [bash, script], env=clean_environment(**{variable: str(ROOT)})
                )
                self.assertEqual(0, result.returncode, result.stderr)
                payload = json.loads(result.stdout)
                for key in expected:
                    payload = payload[key]
                self.assertIn(MARKER, payload)

    @unittest.skipIf(find_bash() is None, "bash is not available")
    def test_session_start_finds_the_bootstrap_from_a_foreign_directory(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            result = run(
                [find_bash(), str(ROOT / "hooks" / "session-start")],
                cwd=raw,
                env=clean_environment(CLAUDE_PLUGIN_ROOT=str(ROOT)),
            )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn(MARKER, result.stdout)

    @unittest.skipIf(os.name == "nt", "a backslash cannot be part of a Windows directory name")
    @unittest.skipIf(find_bash() is None, "bash is not available")
    def test_session_start_still_works_in_a_directory_with_a_backslash_in_its_name(self) -> None:
        # Only Windows hosts pass backslash paths; on POSIX a backslash is an ordinary
        # character and must not be rewritten.
        with tempfile.TemporaryDirectory() as raw:
            plugin = Path(raw) / "back\\slash"
            (plugin / "hooks").mkdir(parents=True)
            (plugin / "adapters").mkdir()
            shutil.copy(ROOT / "hooks" / "session-start", plugin / "hooks" / "session-start")
            shutil.copy(ROOT / "adapters" / "bootstrap.md", plugin / "adapters" / "bootstrap.md")

            result = run(
                [find_bash(), str(plugin / "hooks" / "session-start")],
                env=clean_environment(CLAUDE_PLUGIN_ROOT=str(plugin)),
            )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn(MARKER, result.stdout)

    @unittest.skipIf(shutil.which("sh") is None, "sh is not available")
    def test_wrapper_shell_half_runs_under_a_plain_posix_sh(self) -> None:
        # A host may start the wrapper through /bin/sh (dash on Debian and Ubuntu), so
        # its shell half must not use bash-only syntax; session-start, which the
        # wrapper hands to bash, may. Forward slashes: how hosts build the command.
        environment = clean_environment(CLAUDE_PLUGIN_ROOT=str(ROOT))
        bash = find_bash()
        if os.name == "nt" and bash is not None:
            # The wrapper's inner `exec bash` must find Git Bash, not the WSL launcher.
            environment["PATH"] = str(Path(bash).parent) + os.pathsep + environment.get("PATH", "")
        result = run(
            ["sh", (ROOT / "hooks" / "run-hook.cmd").as_posix(), "session-start"],
            env=environment,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn(MARKER, result.stdout)

    @unittest.skipUnless(os.name == "nt", "the batch half of the wrapper only runs on Windows")
    @unittest.skipIf(find_bash() is None, "Git Bash is not available")
    def test_batch_wrapper_reaches_the_bootstrap_through_git_bash(self) -> None:
        result = run(
            ["cmd", "/c", str(ROOT / "hooks" / "run-hook.cmd"), "session-start"],
            env=clean_environment(CURSOR_PLUGIN_ROOT=str(ROOT)),
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn(MARKER, json.loads(result.stdout)["additional_context"])


class InstallerTests(unittest.TestCase):
    def test_copy_install_is_idempotent(self) -> None:
        # Symlinks need privileges on Windows, so copy mode is the supported route
        # there; it used to die on ctypes.CDLL(None) before publishing anything.
        with tempfile.TemporaryDirectory() as raw:
            destination = Path(raw) / "skills"
            command = [
                sys.executable,
                str(ROOT / "scripts" / "install_skills.py"),
                "--client", "agents",
                "--dest", str(destination),
                "--mode", "copy",
                "--skill", "nobrainer-tech-flow",
                "--skill", "nobrainer-auto-fine-tune",
                "--apply",
            ]
            first = run(command)
            second = run(command)

            self.assertEqual(0, first.returncode, first.stdout + first.stderr)
            self.assertTrue((destination / "nobrainer-tech-flow" / "SKILL.md").is_file())
            self.assertEqual(0, second.returncode, second.stdout + second.stderr)
            self.assertIn("KEEP: nobrainer-tech-flow", second.stdout)


class PersonalizationTests(unittest.TestCase):
    def test_block_is_written_once_and_follows_codex_home(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            codex_home = root / "codex-profile"
            command = [
                sys.executable,
                str(ROOT / "scripts" / "install_personalization.py"),
                "--client", "codex",
                "--apply",
            ]
            environment = clean_environment(
                HOME=str(root / "home"),
                USERPROFILE=str(root / "home"),
                CODEX_HOME=str(codex_home),
            )
            first = run(command, env=environment)
            second = run(command, env=environment)

            self.assertEqual(0, first.returncode, first.stdout + first.stderr)
            content = (codex_home / "AGENTS.md").read_text(encoding="utf-8")
            self.assertEqual(1, content.count("NOBRAINER-TECH-FLOW:START"))
            self.assertEqual(0, second.returncode, second.stdout + second.stderr)
            self.assertIn("UNCHANGED", second.stdout)
            self.assertFalse((root / "home" / ".codex").exists())


class SessionTitleTests(unittest.TestCase):
    def test_default_utc_title_needs_no_time_zone_database(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "skills" / "nobrainer-sessions" / "scripts" / "session_title.py")],
            input=json.dumps({"title": "Task", "started_at": "2026-09-05T23:30:00Z"}),
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual("Task | started 05-09", json.loads(result.stdout)["display_title"])


if __name__ == "__main__":
    unittest.main()
