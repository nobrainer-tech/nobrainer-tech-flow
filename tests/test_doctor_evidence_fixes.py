from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SECURITY = ROOT / "skills" / "nobrainer-security" / "SKILL.md"
AUTOIMPROVE = ROOT / "skills" / "nobrainer-autoimprove" / "SKILL.md"


class DoctorEvidenceFixTests(unittest.TestCase):
    def test_f03_generic_security_trigger_freezes_or_clarifies_mode(self) -> None:
        text = SECURITY.read_text(encoding="utf-8")
        normalized = " ".join(text.split()).lower()

        self.assertIn("if the owner does not name a mode", normalized)
        for phrase in (
            "exact diff, component, endpoint or data flow",
            "pre-freeze design",
            "dependency, installer, plugin or workflow",
            "pre-release acceptance",
            "ask one focused clarification",
            "only if unresolved ambiguity materially changes",
            "continue independent read-only inspection",
        ):
            self.assertIn(phrase, normalized)

    def test_f04_strict_cap_guards_reserved_offsets(self) -> None:
        text = AUTOIMPROVE.read_text(encoding="utf-8")
        normalized = " ".join(text.split()).lower()

        self.assertIn("limit <= 40", normalized)
        self.assertIn("limit <= 50", normalized)
        self.assertIn("before applying either formula", normalized)
        self.assertIn("return `blocked` within the cap", normalized)
        self.assertIn("small limits alone are not a blocker", normalized)
        self.assertIn("otherwise apply the existing formula", normalized)
        self.assertLess(
            normalized.index("if `limit <= 40`"),
            normalized.index("budget the draft to `min(limit - 40, 140)`"),
        )


if __name__ == "__main__":
    unittest.main()
