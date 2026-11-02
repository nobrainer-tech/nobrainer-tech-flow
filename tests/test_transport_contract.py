"""Source-contract checks for session transport; these do not prove client runtime."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SESSIONS = ROOT / "skills" / "nobrainer-sessions"


def read(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


class TransportContractTests(unittest.TestCase):
    def test_sessions_links_transport_contract(self) -> None:
        self.assertIn("(references/transport.md)", read(SESSIONS / "SKILL.md"))

    def test_transport_requires_receipt_and_readback(self) -> None:
        text = read(SESSIONS / "references" / "transport.md")
        for phrase in (
            "`PREVIEW` by default",
            "A title or name is a hint, never identity",
            "never through a shell",
            "A zero exit code proves neither",
            "Completion needs `result` readback from the target",
            "its absence means remain in MAIN",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_cli_workers_are_owner_gated_scoped_and_verified(self) -> None:
        text = read(SESSIONS / "references" / "transport.md")
        for phrase in (
            "Use it only when the owner allows that backend",
            "`workspace-write` only for an implementer with an exclusive write scope",
            "`read-only` for review and diagnosis",
            "A timeout returns the unit to MAIN",
            "the report is a claim",
            "run.terminal.completed",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_portfolio_stays_at_eighteen(self) -> None:
        skills = [p for p in (ROOT / "skills").iterdir() if (p / "SKILL.md").exists()]
        self.assertEqual(len(skills), 18)


if __name__ == "__main__":
    unittest.main()
