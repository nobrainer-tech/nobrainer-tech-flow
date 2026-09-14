from __future__ import annotations

import re
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WRITING = ROOT / "skills" / "nobrainer-writing" / "SKILL.md"
BROWSER = ROOT / "skills" / "nobrainer-browser" / "SKILL.md"


def read_skill(path: Path) -> str:
    if not path.is_file():
        raise AssertionError(f"missing skill under test: {path}")
    return path.read_text(encoding="utf-8")


def description(text: str) -> str:
    match = re.search(r'^description:\s*"(.*)"$', text, re.MULTILINE)
    if match is None:
        raise AssertionError("skill description is missing")
    return match.group(1)


class DoctorContextFixTests(unittest.TestCase):
    def test_writing_trigger_names_prose_as_the_object_of_review(self) -> None:
        trigger = description(read_skill(WRITING))

        self.assertIn("prose quality", trigger)
        self.assertNotIn("user-facing prose such as", trigger)

    def test_writing_audit_metadata_is_scoped_to_prose(self) -> None:
        text = read_skill(WRITING)

        self.assertRegex(
            text,
            r"When the owner asks for an audit, comparison or measured\s+"
            r"compression of the prose itself",
        )

    def test_browser_checks_local_capability_before_registry_access(self) -> None:
        text = read_skill(BROWSER)
        capability_start = text.index("## Capability and install gate")
        first_probe_start = text.index("```bash", capability_start)
        first_probe_end = text.index("```", first_probe_start + len("```bash"))
        first_probe = text[first_probe_start:first_probe_end]

        self.assertIn("command -v playwright-cli", first_probe)
        self.assertIn("node_modules/.bin/playwright", first_probe)
        self.assertNotIn("npm exec", first_probe)
        self.assertNotIn("npm view", first_probe)

        setup_gate = text.index("When setup is explicitly in scope")
        registry_probe = text.index("npm view @playwright/cli version")
        self.assertLess(setup_gate, registry_probe)

    def test_browser_has_a_no_setup_no_registry_path(self) -> None:
        text = read_skill(BROWSER)

        self.assertIn("setup is not in scope", text)
        self.assertIn("do not query npm or install", text)

    def browser_probe(self) -> str:
        text = read_skill(BROWSER)
        capability_start = text.index("## Capability and install gate")
        first_probe_start = text.index("```bash", capability_start)
        first_probe_end = text.index("```", first_probe_start + len("```bash"))
        return text[first_probe_start + len("```bash") : first_probe_end]

    def run_browser_probe(
        self, *, global_cli: bool = False, local_test_cli: bool = False
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory(prefix="browser-b01-") as raw:
            fixture = Path(raw)
            bin_dir = fixture / "bin"
            bin_dir.mkdir()
            (fixture / "package.json").write_text("{}\n", encoding="utf-8")

            if global_cli:
                global_path = bin_dir / "playwright-cli"
                global_path.write_text(
                    "#!/bin/sh\nprintf '%s\\n' 'playwright-cli 0.fixture'\n",
                    encoding="utf-8",
                )
                global_path.chmod(0o755)

            if local_test_cli:
                local_path = fixture / "node_modules" / ".bin" / "playwright"
                local_path.parent.mkdir(parents=True)
                local_path.write_text(
                    "#!/bin/sh\nprintf '%s\\n' 'playwright test-cli 0.fixture'\n",
                    encoding="utf-8",
                )
                local_path.chmod(0o755)

            environment = os.environ.copy()
            environment["PATH"] = str(bin_dir)
            return subprocess.run(
                ["/bin/bash", "-c", self.browser_probe()],
                cwd=fixture,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )

    def test_browser_probe_global_only_is_available(self) -> None:
        result = self.run_browser_probe(global_cli=True)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("global_cli=usable", result.stdout)
        self.assertIn("local_test_cli=none", result.stdout)
        self.assertIn("some_playwright_capability=available", result.stdout)

    def test_browser_probe_local_test_cli_is_distinct_and_available(self) -> None:
        result = self.run_browser_probe(local_test_cli=True)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("global_cli=none", result.stdout)
        self.assertIn("local_test_cli=usable", result.stdout)
        self.assertIn("some_playwright_capability=available", result.stdout)

    def test_browser_probe_none_is_unavailable_without_registry_access(self) -> None:
        result = self.run_browser_probe()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("global_cli=none", result.stdout)
        self.assertIn("local_test_cli=none", result.stdout)
        self.assertIn("some_playwright_capability=none", result.stderr)


if __name__ == "__main__":
    unittest.main()
