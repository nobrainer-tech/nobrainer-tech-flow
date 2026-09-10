from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "nobrainer-decide" / "SKILL.md"
README = ROOT / "README.md"


class DecideContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.skill = SKILL.read_text(encoding="utf-8")
        self.readme = README.read_text(encoding="utf-8")

    def test_three_depths_and_public_triggers_are_explicit(self) -> None:
        for text in ("just decide", "just-decide", "decide", "nb-decide",
                     "nobrainer-decide", "deep decide", "deep-decide"):
            self.assertIn(text, self.skill)
        self.assertIn("| `just decide`, `just-decide` | LIGHT |", self.skill)
        self.assertIn("| `decide`, `nb-decide`, `nobrainer-decide` | STANDARD |", self.skill)
        self.assertIn("| `deep decide`, `deep-decide` | HIGH |", self.skill)
        for text in ("`just decide`", "`just-decide`", "`nobrainer-decide`", "`deep-decide`"):
            self.assertIn(text, self.readme)

    def test_decision_gates_do_not_force_panels_or_false_precision(self) -> None:
        for text in (
            "FEASIBLE, INFEASIBLE or UNVERIFIED",
            "delivery deadline",
            "budget and minimum reliability",
            "total cost",
            "time to first useful result",
            "current demand, plausible growth and an adverse scenario",
            "Accept ties",
            "Do not re-score to force a gap",
            "do not require a fixed panel",
            "Depth never changes the selected model, permissions or budget",
            "recommend one bounded experiment",
        ):
            self.assertIn(text, self.skill)


if __name__ == "__main__":
    unittest.main()
