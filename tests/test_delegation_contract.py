"""Source-contract checks; these do not prove native scheduling or client runtime."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / "skills" / "nobrainer-tech-flow" / "references"


def read_contract(name: str) -> str:
    return " ".join((REFERENCES / name).read_text(encoding="utf-8").split())


class DelegationContractTests(unittest.TestCase):
    def test_ready_units_dispatch_before_execution_or_blocking_wait(self) -> None:
        text = read_contract("delivery.md")
        for phrase in (
            "Before executing non-trivial work or entering a blocking wait",
            "dispatch every useful eligible unit promptly",
            "authorized usage limits",
            "eligible ready unit stays in MAIN",
            "record the concrete reason in the current plan",
            "shared mutable state",
            "missing accepted dependency",
            "unavailable capability/route",
            "authority gate",
            "usage limit",
            "tiny or tightly coupled step",
            "A missing measured speedup is not by itself a reason",
            "One visible MAIN coordinator is compatible with many native workers",
        ):
            with self.subTest(phrase=phrase):
                self.assertTrue(phrase in text, f"Missing contract phrase: {phrase!r}")

    def test_single_native_delegate_needs_no_dispatcher_queue(self) -> None:
        text = read_contract("delivery.md")
        self.assertIn("A single bounded native delegate needs no Dispatcher queue", text)
        self.assertIn("MAIN keeps coordination and acceptance", text)
        self.assertIn("explicit owner request or authorized MAIN restart", text)

    def test_native_packet_preserves_context_method_authority_and_proof(self) -> None:
        raw = (REFERENCES / "communication.md").read_text(encoding="utf-8")
        for field in (
            "TASK", "INPUTS", "WRITE_SCOPE", "DEPENDENCIES", "METHOD",
            "MODEL_AND_EFFORT", "AUTHORITY", "ACCEPTANCE", "BUDGET_AND_STOP", "RETURN",
        ):
            with self.subTest(field=field):
                self.assertRegex(raw, rf"(?m)^{field}:")
        text = " ".join(raw.split())
        for phrase in (
            "fresh context by default",
            "AGENTS and owning-method obligations",
            "literal error text",
            "material exclusions",
            "full Sessions/Dispatcher contract",
            "Do not delegate further or start a successor",
        ):
            with self.subTest(phrase=phrase):
                self.assertTrue(phrase in text, f"Missing contract phrase: {phrase!r}")
        self.assertIn("communication.md#small-native-worker-packet", read_contract("delivery.md"))

    def test_completion_refills_without_unrelated_waits_or_duplicate_takeover(self) -> None:
        text = read_contract("delivery.md")
        for phrase in (
            "On each worker completion",
            "exact returned ID",
            "release only that unit's proven ownership",
            "recompute readiness",
            "without waiting for unrelated slow workers",
            "waiting, suspended or uncertain worker",
            "bounded next observation",
            "Do not duplicate a unit after an uncertain send or timeout",
            "reserve its possible capacity and write scope",
            "host proves no worker is executing",
        ):
            with self.subTest(phrase=phrase):
                self.assertTrue(phrase in text, f"Missing contract phrase: {phrase!r}")

    def test_shared_resources_and_authority_stay_bounded(self) -> None:
        text = read_contract("delivery.md")
        for phrase in (
            "one owner for every shared mutable resource",
            "browser/profile", "test database", "port", "migration", "generated artifact",
            "flat MAIN-owned delegation",
            "express assignment authority",
            "reserved capacity slot",
            "host or owner prohibition",
            "never spawn dummy probes",
            "No duplicate investigations of the same question",
            "Keep quota/cost ceilings",
            "No filler units",
        ):
            with self.subTest(phrase=phrase):
                self.assertTrue(phrase in text, f"Missing contract phrase: {phrase!r}")

    def test_ordinary_fan_out_reaches_builder_readiness(self) -> None:
        text = read_contract("delivery.md")
        self.assertIn("idea-to-delivery.md#builder-readiness-check", text)
        self.assertIn(
            "Before a large or risky multi-writer fan-out that is not already executable",
            text,
        )
        self.assertIn("skip it for already-executable plans and mechanical changes", text)

    def test_builder_readiness_is_one_bounded_conditional_pass(self) -> None:
        text = read_contract("idea-to-delivery.md")
        for phrase in (
            "large or risky multi-writer fan-out",
            "one bounded read-only pass",
            "first assigned unit",
            "missing interface or caller",
            "unavailable tool", "conflicting scope", "unresolved product decision", "impossible proof",
            "MAIN resolves routine choices",
            "existing single clarification round",
            "Skip this check for already-executable plans and mechanical changes",
            "does not authorize new scope or consequential effects",
        ):
            with self.subTest(phrase=phrase):
                self.assertTrue(phrase in text, f"Missing contract phrase: {phrase!r}")


if __name__ == "__main__":
    unittest.main()
