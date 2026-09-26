from __future__ import annotations

import datetime as dt
import json
import contextlib
import importlib.util
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import check_flow_update as checker


class UpdateVersionTests(unittest.TestCase):
    def test_semver_comparison_handles_v_prefix_and_prereleases(self) -> None:
        self.assertTrue(checker.is_newer("v1.2.0", "1.1.9"))
        self.assertTrue(checker.is_newer("1.2.0", "1.2.0-rc.1"))
        self.assertTrue(checker.is_newer("1.2.0-rc.2", "1.2.0-rc.1"))
        self.assertFalse(checker.is_newer("1.2.0-alpha", "1.2.0"))
        self.assertFalse(checker.is_newer("1.2.0+build.2", "v1.2.0+build.1"))

    def test_unknown_or_invalid_versions_fail_closed(self) -> None:
        with self.assertRaises(checker.UpdateCheckError):
            checker.is_newer("latest", "1.0.0")
        with self.assertRaises(checker.UpdateCheckError):
            checker.parse_version("1.0.0-01")


class UpdateCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.now = dt.datetime(2026, 9, 26, 10, 30, tzinfo=dt.timezone(dt.timedelta(hours=2)))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_checks_once_per_client_day_and_installed_ref(self) -> None:
        calls: list[int] = []

        def fetcher() -> tuple[str, str]:
            calls.append(1)
            return "v1.2.0", "https://github.com/nobrainer-tech/nobrainer-tech-flow/releases/tag/v1.2.0"

        first = checker.check_update("codex", "1.1.0", root=self.root, now=self.now, fetcher=fetcher)
        second = checker.check_update("codex", "1.1.0", root=self.root, now=self.now, fetcher=fetcher)
        other_client = checker.check_update("claude", "1.1.0", root=self.root, now=self.now, fetcher=fetcher)
        other_ref = checker.check_update("codex", "1.0.0", root=self.root, now=self.now, fetcher=fetcher)

        self.assertEqual("UPDATE_AVAILABLE", first["status"])
        self.assertFalse(first["cached"])
        self.assertTrue(second["cached"])
        self.assertEqual(3, len(calls))
        self.assertFalse(other_client["cached"])
        self.assertFalse(other_ref["cached"])
        saved = json.loads((self.root / "codex" / "state.json").read_text(encoding="utf-8"))
        self.assertIn("2026-09-26|1.1.0", saved["checks"])
        self.assertEqual("v1.2.0", saved["latest_verified"]["latest_ref"])

    def test_force_refetches_same_day_and_next_day_refetches(self) -> None:
        calls: list[int] = []

        def fetcher() -> tuple[str, str]:
            calls.append(1)
            return "1.1.0", "https://github.com/nobrainer-tech/nobrainer-tech-flow/releases/tag/1.1.0"

        checker.check_update("codex", "1.1.0", root=self.root, now=self.now, fetcher=fetcher)
        forced = checker.check_update("codex", "1.1.0", root=self.root, now=self.now, force=True, fetcher=fetcher)
        tomorrow = checker.check_update(
            "codex", "1.1.0", root=self.root, now=self.now + dt.timedelta(days=1), fetcher=fetcher
        )
        self.assertFalse(forced["cached"])
        self.assertFalse(tomorrow["cached"])
        self.assertEqual(3, len(calls))

    def test_offline_result_is_explicitly_stale_and_attempt_is_cached(self) -> None:
        good = lambda: (
            "1.2.0",
            "https://github.com/nobrainer-tech/nobrainer-tech-flow/releases/tag/1.2.0",
        )
        checker.check_update("codex", "1.1.0", root=self.root, now=self.now - dt.timedelta(days=1), fetcher=good)
        calls: list[int] = []

        def offline() -> tuple[str, str]:
            calls.append(1)
            raise checker.UpdateCheckError("offline")

        failed = checker.check_update("codex", "1.1.0", root=self.root, now=self.now, fetcher=offline)
        cached = checker.check_update("codex", "1.1.0", root=self.root, now=self.now, fetcher=offline)
        self.assertEqual("CHECK_FAILED", failed["status"])
        self.assertTrue(failed["stale"])
        self.assertEqual("1.2.0", failed["latest_ref"])
        self.assertTrue(cached["cached"])
        self.assertEqual(1, len(calls))

    def test_offline_without_prior_release_has_no_fabricated_version(self) -> None:
        def offline() -> tuple[str, str]:
            raise checker.UpdateCheckError("offline")

        result = checker.check_update("codex", "1.1.0", root=self.root, now=self.now, fetcher=offline)
        self.assertEqual("CHECK_FAILED", result["status"])
        self.assertIsNone(result["latest_ref"])
        self.assertFalse(result["stale"])

    def test_skill_version_read(self) -> None:
        version_file = self.root / "VERSION"
        version_file.write_text("1.2.3\n", encoding="utf-8")
        self.assertEqual("1.2.3", checker.read_installed_version(version_file))

    def test_skills_only_install_runs_checker_from_skill_local_version(self) -> None:
        installed_skill = self.root / "skills" / "nobrainer-tech-flow"
        installed_skill.mkdir(parents=True)
        source_skill = Path(__file__).resolve().parents[1] / "skills" / "nobrainer-tech-flow"
        shutil.copy2(
            source_skill / "VERSION",
            installed_skill / "VERSION",
        )
        installed_scripts = installed_skill / "scripts"
        installed_scripts.mkdir()
        helper_source = source_skill / "scripts" / "check_flow_update.py"
        helper = installed_scripts / "check_flow_update.py"
        shutil.copy2(helper_source, helper)
        spec = importlib.util.spec_from_file_location("installed_flow_update_checker", helper)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        installed_checker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(installed_checker)

        self.assertEqual("2.0.0", installed_checker.read_installed_version())
        result = installed_checker.check_update(
            "codex",
            installed_checker.read_installed_version(),
            root=self.root / "state",
            now=self.now,
            fetcher=lambda: (
                "2.0.0",
                "https://github.com/nobrainer-tech/nobrainer-tech-flow/releases/tag/2.0.0",
            ),
        )
        self.assertEqual("CURRENT", result["status"])

    def test_github_response_is_bounded_and_validated(self) -> None:
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, size: int) -> bytes:
                self.size = size
                return json.dumps(
                    {
                        "tag_name": "v1.2.0",
                        "html_url": "https://github.com/nobrainer-tech/nobrainer-tech-flow/releases/tag/v1.2.0",
                        "draft": False,
                        "prerelease": False,
                    }
                ).encode()

        response = Response()
        with patch.object(checker.urllib.request, "urlopen", return_value=response) as open_url:
            self.assertEqual(("v1.2.0", "https://github.com/nobrainer-tech/nobrainer-tech-flow/releases/tag/v1.2.0"), checker.fetch_latest_release())
        self.assertEqual(checker.MAX_RESPONSE_BYTES + 1, response.size)
        self.assertEqual(checker.TIMEOUT_SECONDS, open_url.call_args.kwargs["timeout"])

    def test_github_release_url_must_match_official_tag(self) -> None:
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, size: int) -> bytes:
                return json.dumps(
                    {
                        "tag_name": "v1.2.0",
                        "html_url": "https://github.com/nobrainer-tech/nobrainer-tech-flow/releases/tag/v1.1.0",
                        "draft": False,
                        "prerelease": False,
                    }
                ).encode()

        with patch.object(checker.urllib.request, "urlopen", return_value=Response()):
            with self.assertRaisesRegex(checker.UpdateCheckError, "does not match"):
                checker.fetch_latest_release()

    def test_update_notice_describes_reviewed_release_and_never_old_checkout_command(self) -> None:
        result = {
            "status": "UPDATE_AVAILABLE",
            "client": "codex",
            "installed_ref": "1.1.0",
            "latest_ref": "v1.2.0",
            "release_url": "https://github.com/nobrainer-tech/nobrainer-tech-flow/releases/tag/v1.2.0",
            "cached": False,
            "stale": False,
        }
        with patch.object(sys.modules["check_flow_update"], "check_update", return_value=result):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = checker.main(["--client", "codex", "--installed-version", "1.1.0"])

        text = output.getvalue()
        self.assertEqual(0, code)
        self.assertIn("obtain and review release tag v1.2.0", text)
        self.assertIn("installer dry-run", text)
        self.assertIn("read back the installed files and version", text)
        self.assertNotIn("Next command:", text)
        self.assertNotIn("--apply", text)


if __name__ == "__main__":
    unittest.main()
