from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
REFERENCES = SKILLS / "nobrainer-tech-flow" / "references"


def normalized(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


class ProofContractTests(unittest.TestCase):
    def test_build_proves_tests_would_notice_a_preserving_rewrite(self) -> None:
        text = normalized(SKILLS / "nobrainer-build" / "SKILL.md")
        for term in (
            "behavior-preserving rewrite",
            "seed one deliberate fault per changed behavior class",
            "disposable copy",
            "confirm a test fails, revert, and confirm a clean diff",
            "`TEST_SENSITIVITY: PROVEN | PARTLY_PROVEN | NOT_PROVEN`",
            "`NOT_PROVEN` leaves the preservation claim `UNVERIFIED`",
            "TEST_SENSITIVITY: PROVEN | PARTLY_PROVEN | NOT_PROVEN | NOT_APPLICABLE",
        ):
            with self.subTest(term=term):
                self.assertIn(term, text)

    def test_review_keeps_unproven_or_stale_evidence_open(self) -> None:
        text = normalized(SKILLS / "nobrainer-review" / "SKILL.md")
        for term in (
            'missing or `NOT_PROVEN` `TEST_SENSITIVITY` keeps a "no behavior change" claim open',
            "`STALE` or `CHANGED_DURING_RUN` evidence does not prove the current artifact",
        ):
            with self.subTest(term=term):
                self.assertIn(term, text)

    def test_model_routing_limits_worker_cost(self) -> None:
        text = normalized(REFERENCES / "model-routing.md")
        for term in (
            "same shared assignment prefix with the unit-specific part last",
            "plausible but unmeasured",
            "routine units get the lowest effort that still meets acceptance",
            "reaches its `BUDGET` stops and reports partial results",
        ):
            with self.subTest(term=term):
                self.assertIn(term, text)

    def test_security_treats_readable_credential_files_as_exposure(self) -> None:
        text = normalized(SKILLS / "nobrainer-security" / "SKILL.md")
        for term in (
            "plaintext `.env` or credential file in a workspace an agent can read counts as secret exposure",
            "secret manager at launch, scoped to the process",
            "Never print a secret value",
        ):
            with self.subTest(term=term):
                self.assertIn(term, text)


if __name__ == "__main__":
    unittest.main()
