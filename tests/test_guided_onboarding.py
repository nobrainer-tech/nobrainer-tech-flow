from __future__ import annotations

import base64
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
ONBOARDING = ROOT / "scripts" / "recommend_flow_setup.py"
PERSONALIZATION = ROOT / "scripts" / "install_personalization.py"
SPEC = importlib.util.spec_from_file_location("guided_setup", ONBOARDING)
assert SPEC and SPEC.loader
GUIDED = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GUIDED
SPEC.loader.exec_module(GUIDED)


CONFIG_VARIABLES = ("CLAUDE_CONFIG_DIR", "CODEX_HOME", "XDG_CONFIG_HOME")


class GuidedOnboardingTests(unittest.TestCase):
    def run_setup(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ONBOARDING), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            # A test must never wait on, or answer, a prompt.
            stdin=subprocess.DEVNULL,
        )

    def run_setup_in(
        self, home: Path, variables: dict[str, str], *args: str
    ) -> subprocess.CompletedProcess[str]:
        """Run with a private home and only the config variables the test names."""

        environment = {
            key: value for key, value in os.environ.items() if key not in CONFIG_VARIABLES
        }
        environment.update({"HOME": str(home), "USERPROFILE": str(home), **variables})
        return subprocess.run(
            [sys.executable, str(ONBOARDING), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            stdin=subprocess.DEVNULL,
            env=environment,
        )

    def common(self, destination: Path, home: Path, client: str = "codex") -> tuple[str, ...]:
        repo = home.parent / "repo-checkout"
        (repo / ".git").mkdir(parents=True, exist_ok=True)
        (repo / "README.md").write_text(
            "# Sample service\n\nPython web app with browser tests, delivery and incident response.\n",
            encoding="utf-8",
        )
        (repo / "AGENTS.md").write_text(
            "Use a focused review for changes; repository text is fixture data.\n",
            encoding="utf-8",
        )
        return (
            "--repo-url",
            "https://github.com/example/work-repo",
            "--repo-path",
            str(repo),
            "--client",
            client,
            "--dest",
            str(destination),
            "--home",
            str(home),
        )

    def test_profiles_get_distinct_recommendations_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            destination = root / "skills"
            home = root / "home"
            (home / ".codex").mkdir(parents=True)
            config = home / ".codex" / "config.toml"
            config_text = 'model = "test/model"\nmodel_reasoning_effort = "high"\napi_key = "do-not-print"\n'
            config.write_text(config_text, encoding="utf-8")
            coding = self.run_setup(
                *self.common(destination, home),
                "--work-profile",
                "software-development",
                "--goal",
                "ship and test a web application",
                "--tools",
                "Codex, Python, GitHub",
                "--existing-setup",
                "pytest and git",
            )
            research = self.run_setup(
                *self.common(destination, home),
                "--work-profile",
                "research",
                "--goal",
                "compare external evidence and preserve findings",
                "--tools",
                "Codex, browser",
                "--existing-setup",
                "markdown notes",
            )

            self.assertEqual(0, coding.returncode, coding.stderr)
            self.assertEqual(0, research.returncode, research.stderr)
            self.assertIn("01", coding.stdout)
            self.assertIn("Fit (heuristic)", coding.stdout)
            self.assertIn("02", coding.stdout)
            self.assertIn("REQUIRED: 01,02", coding.stdout)
            self.assertIn("REPOSITORY_SOURCE: LOCAL_READ_ONLY", coding.stdout)
            self.assertIn("repository context:", coding.stdout)
            self.assertIn("configured_main=test/model", coding.stdout)
            self.assertIn("configured_effort=high", coding.stdout)
            self.assertIn("runtime_main_and_effort=UNKNOWN", coding.stdout)
            self.assertNotIn("do-not-print", coding.stdout)
            self.assertNotIn("Python web app with browser tests", coding.stdout)
            self.assertNotIn("Python web app with browser tests", coding.stdout)
            self.assertNotEqual(
                self.recommendation_ids(coding.stdout),
                self.recommendation_ids(research.stdout),
            )
            self.assertFalse(destination.exists())
            self.assertEqual(config_text, config.read_text(encoding="utf-8"))

    def test_offline_fallback_uses_user_context_and_keeps_runtime_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = self.run_setup(
                "--repo-url",
                "https://github.com/example/work-repo",
                "--offline",
                "--client",
                "codex",
                "--home",
                str(root / "home"),
                "--dest",
                str(root / "skills"),
                "--work-profile",
                "research",
                "--goal",
                "compare sources",
                "--tools",
                "Codex",
                "--existing-setup",
                "markdown notes",
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("REPOSITORY_SOURCE: OFFLINE", result.stdout)
            self.assertIn("using supplied answers only", result.stdout)
            self.assertIn("CLIENT_CAPABILITY_AUDIT", result.stdout)
            self.assertIn("runtime_context=UNKNOWN", result.stdout)
            self.assertFalse((root / "skills").exists())

    def test_github_readme_and_metadata_fixture_are_read_only_context(self) -> None:
        class Response:
            def __init__(self, payload: bytes):
                self.payload = payload

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, limit: int) -> bytes:
                return self.payload[:limit]

        metadata = {
            "description": "Python browser automation project",
            "language": "Python",
            "topics": ["browser-automation", "testing"],
        }
        readme = {
            "encoding": "base64",
            "content": base64.b64encode(b"# Project\nResearch and evidence workflow\n").decode(),
        }
        responses = [
            Response(json.dumps(metadata).encode()),
            Response(json.dumps(readme).encode()),
        ]
        with mock.patch.object(GUIDED.shutil, "which", return_value=None), mock.patch.object(
            GUIDED, "_open_github_api", side_effect=responses
        ) as opener:
            context = GUIDED.inspect_github_repository("https://github.com/acme/repo")

        self.assertTrue(context.status.startswith("GITHUB_READ_ONLY_API+README_"))
        self.assertIn("browser automation", context.signals)
        self.assertIn("Research and evidence", context.signals)
        self.assertNotIn("Research and evidence", context.summary)
        self.assertEqual(2, opener.call_count)
        for call in opener.call_args_list:
            self.assertEqual("GET", call.args[0].method)

    def test_non_github_url_is_never_fetched(self) -> None:
        with mock.patch.object(GUIDED, "_open_github_api") as opener:
            context = GUIDED.inspect_github_repository("https://127.0.0.1/private/repo")
        self.assertEqual("UNSUPPORTED_HOST", context.status)
        opener.assert_not_called()

    def test_github_transport_pins_hostname_and_rejects_external_redirects(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["gh"], returncode=0, stdout='{"language":"Python"}', stderr=""
        )
        with mock.patch.object(GUIDED.shutil, "which", return_value="/usr/bin/gh"), mock.patch.object(
            GUIDED.subprocess, "run", return_value=completed
        ) as runner:
            payload, source = GUIDED._github_json("repos/acme/repo")
        self.assertEqual({"language": "Python"}, payload)
        self.assertEqual("GITHUB_READ_ONLY_GH", source)
        self.assertIn("--hostname", runner.call_args.args[0])
        self.assertIn("github.com", runner.call_args.args[0])

        handler = GUIDED._GitHubRedirectHandler()
        request = GUIDED.Request("https://api.github.com/repos/acme/repo")
        self.assertIsNone(
            handler.redirect_request(
                request, None, 302, "Found", {}, "https://127.0.0.1/latest/meta-data"
            )
        )

    def test_github_transport_pins_hostname_and_rejects_external_redirects(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["gh"], returncode=0, stdout='{"language":"Python"}', stderr=""
        )
        with mock.patch.object(GUIDED.shutil, "which", return_value="/usr/bin/gh"), mock.patch.object(
            GUIDED.subprocess, "run", return_value=completed
        ) as runner:
            payload, source = GUIDED._github_json("repos/acme/repo")
        self.assertEqual({"language": "Python"}, payload)
        self.assertEqual("GITHUB_READ_ONLY_GH", source)
        self.assertIn("--hostname", runner.call_args.args[0])
        self.assertIn("github.com", runner.call_args.args[0])

        handler = GUIDED._GitHubRedirectHandler()
        request = GUIDED.Request("https://api.github.com/repos/acme/repo")
        self.assertIsNone(
            handler.redirect_request(
                request, None, 302, "Found", {}, "https://127.0.0.1/latest/meta-data"
            )
        )

    def test_github_cli_output_is_decoded_as_utf_8_on_every_platform(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["gh"], returncode=0, stdout='{"language":"Python"}', stderr=""
        )
        with mock.patch.object(GUIDED.shutil, "which", return_value="/usr/bin/gh"), mock.patch.object(
            GUIDED.subprocess, "run", return_value=completed
        ) as runner:
            GUIDED._github_json("repos/acme/repo")
        # A Windows code page cannot decode every character GitHub returns.
        self.assertEqual("utf-8", runner.call_args.kwargs["encoding"])
        self.assertEqual("replace", runner.call_args.kwargs["errors"])

    def test_partial_selection_personalization_readback_and_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            destination = root / "skills"
            home = root / "home"
            (home / ".codex").mkdir(parents=True)
            instruction = home / ".codex" / "AGENTS.md"
            instruction.write_text("Existing user rules.\n", encoding="utf-8")
            common = self.common(destination, home)
            setup_args = (
                *common,
                "--work-profile",
                "software-development",
                "--goal",
                "ship and test a web application",
                "--tools",
                "Codex, Python, GitHub",
                "--existing-setup",
                "pytest and git",
                "--selection",
                "01,03,04,06,11",
                "--preferences",
                "Keep MAIN model and effort selected by the owner.",
            )
            preview = self.run_setup(*setup_args)
            self.assertEqual(0, preview.returncode, preview.stderr)
            self.assertIn("DRY_RUN", preview.stdout)
            self.assertIn("DIFF:", preview.stdout)
            self.assertIn("Keep MAIN model and effort selected by the owner.", preview.stdout)
            self.assertFalse(destination.exists())
            self.assertEqual("Existing user rules.\n", instruction.read_text())

            applied = self.run_setup(*setup_args, "--apply")
            self.assertEqual(0, applied.returncode, applied.stderr)
            self.assertIn("READBACK: installed=01,02,03,04,06,11", applied.stdout)
            self.assertIn("PREFERENCE_READBACK", applied.stdout)
            installed = {path.name for path in destination.iterdir()}
            self.assertEqual(
                {
                    "nobrainer-tech-flow",
                    "nobrainer-auto-fine-tune",
                    "nobrainer-build",
                    "nobrainer-review",
                    "nobrainer-research",
                    "nobrainer-sessions",
                },
                installed,
            )
            self.assertIn("Keep MAIN model and effort selected by the owner.", instruction.read_text())
            self.assertIn("nobrainer-auto-fine-tune", instruction.read_text())
            self.assertIn("BACKUP:", applied.stdout)

            repeated = self.run_setup(
                *common,
                "--work-profile",
                "software-development",
                "--goal",
                "ship and test a web application",
                "--tools",
                "Codex, Python, GitHub",
                "--existing-setup",
                "pytest and git",
                "--selection",
                "01,03,04,06,11",
                "--apply",
            )
            self.assertEqual(0, repeated.returncode, repeated.stderr)
            self.assertIn("READBACK: installed=01,02,03,04,06,11", repeated.stdout)
            self.assertIn("Keep MAIN model and effort selected by the owner.", instruction.read_text())

            rollback_preview = self.run_setup(*common, "--rollback")
            self.assertEqual(0, rollback_preview.returncode, rollback_preview.stderr)
            self.assertIn("ROLLBACK_DRY_RUN", rollback_preview.stdout)
            self.assertTrue(destination.exists())
            self.assertTrue(instruction.exists())

            rolled_back = self.run_setup(
                *common,
                "--selection",
                "01,03,04,06,11",
                "--rollback",
                "--apply",
            )
            self.assertEqual(0, rolled_back.returncode, rolled_back.stderr)
            self.assertIn("ROLLBACK_READBACK", rolled_back.stdout)
            self.assertEqual("Existing user rules.\n", instruction.read_text())
            self.assertFalse(destination.exists())

    def test_selected_target_conflict_prevents_partial_install(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            destination = root / "skills"
            conflict = destination / "nobrainer-review"
            conflict.mkdir(parents=True)
            marker = conflict / "owner.txt"
            marker.write_text("keep this", encoding="utf-8")
            result = self.run_setup(
                *self.common(destination, root / "home"),
                "--work-profile",
                "software-development",
                "--goal",
                "ship code",
                "--tools",
                "Codex",
                "--existing-setup",
                "custom review rules",
                "--selection",
                "03,04",
                "--apply",
            )
            self.assertEqual(3, result.returncode)
            self.assertTrue(marker.is_file())
            self.assertFalse((destination / "nobrainer-build").exists())
            self.assertFalse((destination / "nobrainer-tech-flow").exists())

    def test_rollback_preserves_user_edits_and_installed_items(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            destination = root / "skills"
            home = root / "home"
            instruction = home / ".codex" / "AGENTS.md"
            result = self.run_setup(
                *self.common(destination, home),
                "--work-profile",
                "research",
                "--goal",
                "compare current evidence",
                "--tools",
                "Codex",
                "--existing-setup",
                "none",
                "--selection",
                "01",
                "--apply",
            )
            self.assertEqual(0, result.returncode, result.stderr)
            instruction.write_text(instruction.read_text() + "Owner edit.\n", encoding="utf-8")

            rollback = self.run_setup(*self.common(destination, home), "--rollback", "--apply")
            self.assertEqual(3, rollback.returncode)
            self.assertIn("personalization changed since setup", rollback.stdout)
            self.assertTrue((destination / "nobrainer-tech-flow").is_symlink())
            self.assertIn("Owner edit.", instruction.read_text())

    def test_state_save_failure_restores_first_and_repeated_setup_preimages(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            destination = root / "skills"
            home = root / "home"
            instruction = home / ".codex" / "AGENTS.md"
            instruction.parent.mkdir(parents=True)
            original_instructions = b"Owner rules outside Flow.\n"
            instruction.write_bytes(original_instructions)
            common = self.common(destination, home)
            original_save_state = GUIDED.save_state

            def save_then_fail(path: Path, state: dict[str, object]) -> None:
                original_save_state(path, state)
                raise OSError("injected state write failure after replace")

            first_run = (
                *common,
                "--work-profile",
                "research",
                "--goal",
                "compare current evidence",
                "--tools",
                "Codex",
                "--existing-setup",
                "none",
                "--selection",
                "01,03",
                "--preferences",
                "First approved preference",
            )
            with mock.patch.object(
                GUIDED, "save_state", side_effect=save_then_fail
            ), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                first_code = GUIDED.main([*first_run, "--apply"])

            self.assertEqual(2, first_code)
            self.assertEqual(original_instructions, instruction.read_bytes())
            self.assertEqual([], list(destination.iterdir()))
            self.assertFalse((home / ".nobrainer-flow-onboarding-codex.json").exists())

            initial = self.run_setup(*common, "--work-profile", "research", "--goal",
                "compare current evidence", "--tools", "Codex", "--existing-setup", "none",
                "--selection", "01", "--preferences", "Existing approved preference", "--apply")
            self.assertEqual(0, initial.returncode, initial.stderr)
            state = home / ".nobrainer-flow-onboarding-codex.json"
            previous_state = state.read_bytes()
            previous_instructions = instruction.read_bytes()

            repeated_run = (
                *common,
                "--work-profile",
                "research",
                "--goal",
                "compare current evidence",
                "--tools",
                "Codex",
                "--existing-setup",
                "none",
                "--selection",
                "01,03",
                "--preferences",
                "Changed preference",
            )
            with mock.patch.object(
                GUIDED, "save_state", side_effect=save_then_fail
            ), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                repeated_code = GUIDED.main([*repeated_run, "--apply"])

            self.assertEqual(2, repeated_code)
            self.assertEqual(previous_state, state.read_bytes())
            self.assertEqual(previous_instructions, instruction.read_bytes())
            self.assertTrue((destination / "nobrainer-tech-flow").is_symlink())
            self.assertTrue((destination / "nobrainer-auto-fine-tune").is_symlink())
            self.assertFalse((destination / "nobrainer-build").exists())

    def test_codex_and_claude_keep_independent_setup_state_and_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            home = root / "home"
            codex_destination = root / "codex-skills"
            claude_destination = root / "claude-skills"
            codex_setup = self.run_setup(
                *self.common(codex_destination, home, "codex"),
                "--work-profile",
                "software-development",
                "--goal",
                "build and review code",
                "--tools",
                "Codex",
                "--existing-setup",
                "none",
                "--selection",
                "01,03",
                "--apply",
            )
            self.assertEqual(0, codex_setup.returncode, codex_setup.stderr)
            self.assertIn("onboarding-codex.json", codex_setup.stdout)
            codex_state = home / ".nobrainer-flow-onboarding-codex.json"
            legacy_state = home / ".nobrainer-flow-onboarding.json"
            codex_state.rename(legacy_state)
            codex_migration = self.run_setup(
                *self.common(codex_destination, home, "codex"),
                "--work-profile",
                "software-development",
                "--goal",
                "build and review code",
                "--tools",
                "Codex",
                "--existing-setup",
                "none",
                "--selection",
                "01,03",
                "--apply",
            )
            self.assertEqual(0, codex_migration.returncode, codex_migration.stderr)
            self.assertIn("LEGACY_STATE_MIGRATION", codex_migration.stdout)
            self.assertTrue(codex_state.is_file())
            self.assertTrue(legacy_state.is_file())

            claude_setup = self.run_setup(
                *self.common(claude_destination, home, "claude"),
                "--work-profile",
                "writing",
                "--goal",
                "write clear project documentation",
                "--tools",
                "Claude Code",
                "--existing-setup",
                "none",
                "--selection",
                "01,07",
                "--apply",
            )
            self.assertEqual(0, claude_setup.returncode, claude_setup.stderr)
            self.assertIn("onboarding-claude.json", claude_setup.stdout)
            self.assertTrue((codex_destination / "nobrainer-build").is_symlink())
            self.assertTrue((claude_destination / "nobrainer-writing").is_symlink())
            self.assertTrue((home / ".nobrainer-flow-onboarding-codex.json").is_file())
            self.assertTrue((home / ".nobrainer-flow-onboarding-claude.json").is_file())

            codex_rollback = self.run_setup(
                *self.common(codex_destination, home, "codex"),
                "--rollback",
                "--apply",
            )
            self.assertEqual(0, codex_rollback.returncode, codex_rollback.stderr)
            self.assertFalse(codex_destination.exists())
            self.assertTrue((claude_destination / "nobrainer-writing").is_symlink())
            self.assertTrue((home / ".claude" / "CLAUDE.md").exists())
            self.assertTrue((home / ".nobrainer-flow-onboarding-claude.json").exists())

            claude_rollback = self.run_setup(
                *self.common(claude_destination, home, "claude"),
                "--rollback",
                "--apply",
            )
            self.assertEqual(0, claude_rollback.returncode, claude_rollback.stderr)
            self.assertFalse(claude_destination.exists())
            self.assertFalse((home / ".claude" / "CLAUDE.md").exists())

    ANSWERS = (
        "--work-profile", "software-development",
        "--goal", "ship and test a web application",
        "--tools", "Claude Code",
        "--existing-setup", "none",
    )

    def test_missing_answers_without_a_terminal_ask_for_input_instead_of_hanging(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            arguments = [
                sys.executable, str(ONBOARDING), "--repo-url", "https://github.com/example/work-repo",
                "--offline", "--client", "codex", "--home", str(root / "home"),
                "--dest", str(root / "skills"), "--goal", "compare sources",
            ]
            # An open pipe that is never written to or closed is what an agent
            # harness may attach; reading it would block forever.
            process = subprocess.Popen(
                arguments, cwd=ROOT, text=True, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            try:
                process.wait(timeout=60)
                stderr = process.stderr.read()
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
                process.stdin.close()
                process.stdout.close()
                process.stderr.close()
            self.assertEqual(2, process.returncode)
            self.assertIn("INPUT_REQUIRED", stderr)
            self.assertIn("--work-profile", stderr)
            self.assertIn("--tools", stderr)
            self.assertNotIn("--goal", stderr)
            self.assertNotIn("Traceback", stderr)
            self.assertFalse((root / "skills").exists())

    def test_config_dir_variables_steer_skills_instructions_and_settings(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            home = root / "home"
            profile = root / "claude-profile"
            profile.mkdir()
            (profile / "settings.json").write_text('{"model": "test/model"}', encoding="utf-8")
            variables = {"CLAUDE_CONFIG_DIR": str(profile)}
            common = (
                "--repo-url", "https://github.com/example/work-repo", "--offline",
                "--client", "claude", *self.ANSWERS, "--selection", "01",
            )

            preview = self.run_setup_in(home, variables, *common)
            self.assertEqual(0, preview.returncode, preview.stderr)
            self.assertIn("configured_main=test/model", preview.stdout)
            self.assertIn(f"TARGET: {profile / 'CLAUDE.md'}", preview.stdout)
            self.assertFalse((profile / "skills").exists())

            applied = self.run_setup_in(home, variables, *common, "--apply")
            self.assertEqual(0, applied.returncode, applied.stderr)
            self.assertTrue((profile / "skills" / "nobrainer-tech-flow").is_symlink())
            self.assertIn("nobrainer-tech-flow", (profile / "CLAUDE.md").read_text(encoding="utf-8"))
            self.assertFalse((home / ".claude").exists())

            rolled_back = self.run_setup_in(
                home, variables, "--repo-url", "https://github.com/example/work-repo",
                "--client", "claude", "--rollback", "--apply",
            )
            self.assertEqual(0, rolled_back.returncode, rolled_back.stdout + rolled_back.stderr)
            self.assertFalse((profile / "skills").exists())
            self.assertFalse((profile / "CLAUDE.md").exists())

    def test_guided_setup_keeps_options_granted_by_an_earlier_personalization_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            home = root / "home"
            instruction = home / ".codex" / "AGENTS.md"
            earlier = subprocess.run(
                [sys.executable, str(PERSONALIZATION), "--client", "codex", "--home", str(home),
                 "--auto-update", "--auto-session-restart", "--apply"],
                cwd=ROOT, text=True, capture_output=True, check=False, stdin=subprocess.DEVNULL,
            )
            self.assertEqual(0, earlier.returncode, earlier.stderr)
            granted = instruction.read_text(encoding="utf-8")

            applied = self.run_setup(
                *self.common(root / "skills", home), *self.ANSWERS, "--selection", "01",
                "--preferences", "Answer in Polish.", "--apply",
            )
            self.assertEqual(0, applied.returncode, applied.stderr)
            self.assertIn("KEPT_OPTIONS: auto-update, session-restart", applied.stdout)
            content = instruction.read_text(encoding="utf-8")
            self.assertIn("standing authorization to apply", content)
            self.assertIn("standing authorization for session rotation", content)
            self.assertIn("Answer in Polish.", content)

            rolled_back = self.run_setup(*self.common(root / "skills", home), "--rollback", "--apply")
            self.assertEqual(0, rolled_back.returncode, rolled_back.stdout + rolled_back.stderr)
            self.assertEqual(granted, instruction.read_text(encoding="utf-8"))

    def test_claude_import_of_a_codex_file_without_the_block_still_gets_instructions(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            home = root / "home"
            instruction = home / ".claude" / "CLAUDE.md"
            instruction.parent.mkdir(parents=True)
            original = "@~/.codex/AGENTS.md\nClaude-only rules.\n"
            instruction.write_text(original, encoding="utf-8")

            applied = self.run_setup(
                *self.common(root / "skills", home, "claude"), *self.ANSWERS, "--selection", "01",
                "--apply",
            )
            self.assertEqual(0, applied.returncode, applied.stdout + applied.stderr)
            self.assertNotIn("inherited from Codex", applied.stdout)
            content = instruction.read_text(encoding="utf-8")
            self.assertTrue(content.startswith(original))
            self.assertIn("NOBRAINER-TECH-FLOW:START", content)

            rolled_back = self.run_setup(
                *self.common(root / "skills", home, "claude"), "--rollback", "--apply"
            )
            self.assertEqual(0, rolled_back.returncode, rolled_back.stdout + rolled_back.stderr)
            self.assertEqual(original, instruction.read_text(encoding="utf-8"))

    @unittest.skipIf(os.name == "nt", "creating symlinks needs elevated rights on Windows")
    def test_a_setup_made_before_config_dir_support_can_be_rolled_back_and_redone(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            home = root / "home"
            profile = root / "claude-profile"
            variables = {"CLAUDE_CONFIG_DIR": str(profile)}
            common = (
                "--repo-url", "https://github.com/example/work-repo", "--offline",
                "--client", "claude",
            )
            # 2.0.0 always wrote under the home directory, whatever CLAUDE_CONFIG_DIR said.
            earlier = self.run_setup(
                *common, *self.ANSWERS, "--selection", "01", "--home", str(home), "--apply"
            )
            self.assertEqual(0, earlier.returncode, earlier.stdout + earlier.stderr)

            blocked = self.run_setup_in(
                home, variables, *common, *self.ANSWERS, "--selection", "01", "--apply"
            )
            self.assertEqual(2, blocked.returncode)
            self.assertIn("--rollback --apply", blocked.stderr)
            self.assertFalse(profile.exists())

            undone = self.run_setup_in(home, variables, *common, "--rollback", "--apply")
            self.assertEqual(0, undone.returncode, undone.stdout + undone.stderr)
            self.assertFalse((home / ".claude" / "skills").exists())

            redone = self.run_setup_in(
                home, variables, *common, *self.ANSWERS, "--selection", "01", "--apply"
            )
            self.assertEqual(0, redone.returncode, redone.stdout + redone.stderr)
            self.assertTrue((profile / "skills" / "nobrainer-tech-flow").is_symlink())

    def test_links_out_of_the_install_set_are_named_once_for_the_whole_set(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            common = (*self.common(root / "skills", root / "home"), *self.ANSWERS)

            partial = self.run_setup(*common, "--selection", "03")
            complete = self.run_setup(*common, "--selection", "03,11")

            self.assertEqual(0, partial.returncode, partial.stdout + partial.stderr)
            notes = [line for line in partial.stdout.splitlines() if line.startswith("NOTE:")]
            # The core skill links to Sessions (ID 11); the per-skill installer runs never
            # see the whole set, so their misleading "not installed" notes stay hidden.
            self.assertEqual(
                [
                    "NOTE: nobrainer-tech-flow links to nobrainer-sessions, which is not in "
                    "this install set; add selection 11 to include it"
                ],
                notes,
            )
            self.assertEqual(0, complete.returncode, complete.stdout + complete.stderr)
            self.assertNotIn("NOTE:", complete.stdout)

    @unittest.skipIf(os.name == "nt", "creating symlinks needs elevated rights on Windows")
    def test_a_symlink_loop_in_the_destination_is_a_conflict_not_a_crash(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            destination = root / "skills"
            destination.mkdir()
            (destination / "nobrainer-review").symlink_to("nobrainer-review")

            result = self.run_setup(
                *self.common(destination, root / "home"), *self.ANSWERS
            )

            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            review = next(
                line for line in result.stdout.splitlines() if line.startswith("04 Code review |")
            )
            self.assertIn("Target=CONFLICT", review)

    @staticmethod
    def recommendation_ids(output: str) -> tuple[str, ...]:
        return tuple(
            line.split()[0]
            for line in output.splitlines()
            if line[:2].isdigit() and " Fit (heuristic)=" in line
        )


if __name__ == "__main__":
    unittest.main()
