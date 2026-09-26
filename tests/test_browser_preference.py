from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "nobrainer-browser" / "SKILL.md"


class BrowserPreferenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = " ".join(SKILL.read_text(encoding="utf-8").split())

    def test_codex_native_browser_is_nonblocking_default(self) -> None:
        for required in (
            "Codex desktop",
            "Codex built-in browser",
            "@Browser",
            "Continue with the built-in browser without waiting for a reply",
            "clicks, typing, screenshots and result verification",
        ):
            self.assertIn(required, self.text)

    def test_browser_panel_display_is_not_automation(self) -> None:
        self.assertIn("open_in_codex", self.text)
        self.assertIn("does not provide browser automation", self.text)
        self.assertIn("Do not treat it as an `@Browser` interaction capability", self.text)

    def test_existing_authenticated_session_requires_preference_or_need(self) -> None:
        for required in (
            "already approved regular Chrome session",
            "owner chooses their regular browser session",
            "Use CDP attach only under the existing-session rules below",
            "Never copy cookies or profile data between browsers",
        ):
            self.assertIn(required, self.text)

    def test_persisted_preference_is_reused_only_when_supported_and_authorized(self) -> None:
        for required in (
            "Do not ask again in the same task/session after a preference is known",
            "only when authorized",
            "instead of claiming it was saved",
            "For clients other than Codex",
        ):
            self.assertIn(required, self.text)


if __name__ == "__main__":
    unittest.main()
