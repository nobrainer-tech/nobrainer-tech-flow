from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
RESTART_GATE_PATH = ROOT / "skills/nobrainer-sessions/scripts/restart_gate.py"
RESTART_GATE_SPEC = importlib.util.spec_from_file_location(
    "doctor_delivery_restart_gate", RESTART_GATE_PATH
)
assert RESTART_GATE_SPEC is not None and RESTART_GATE_SPEC.loader is not None
RESTART_GATE = importlib.util.module_from_spec(RESTART_GATE_SPEC)
RESTART_GATE_SPEC.loader.exec_module(RESTART_GATE)


class RestartGateDeliveryFixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = dict(
            schema=1,
            mode="adaptive",
            policy_authorized=True,
            remaining_work=True,
            source_id="old",
            goal_id="goal",
            creation_status="not_sent",
            compactions=2,
            current_input_tokens=80_000,
            fresh_input_tokens=15_000,
            restart_overhead_tokens=10_000,
            remaining_calls=3,
            progress_since_restart=True,
            safe_boundary=True,
            active_writers=0,
            pending_operations=0,
            checkpoint_readback=True,
            checkpoint_current=True,
            fresh_create_supported=True,
            target_read_supported=True,
            transfer_supported=True,
        )

    def action(self, **updates: object) -> str:
        return RESTART_GATE.decide(dict(self.state, **updates))["action"]

    def test_uncertain_creation_is_reconciled_before_terminal_policy_branches(self) -> None:
        cases = (
            {"remaining_work": False},
            {"mode": "off"},
            {"policy_authorized": False},
            {"required_budget_unmeasurable": True},
        )
        for updates in cases:
            with self.subTest(updates=updates):
                self.assertEqual(
                    self.action(creation_status="unknown", **updates),
                    "RECONCILE_TARGET",
                )

    def test_unexpected_target_is_reconciled_before_no_remaining_work_closes(self) -> None:
        self.assertEqual(
            self.action(target_id="possibly-created", remaining_work=False),
            "RECONCILE_TARGET",
        )


class SddTemplateDeliveryFixTests(unittest.TestCase):
    def test_template_represents_lifecycle_and_contract_change_stop_states(self) -> None:
        template_path = ROOT / "skills/nobrainer-spec-driven-development/references/spec-template.md"
        template = template_path.read_text(encoding="utf-8")
        status_line = next(
            line for line in template.splitlines() if line.startswith("STATUS:")
        )
        states = set(re.findall(r"\b[A-Z][A-Z_]+\b", status_line))
        expected_states = {
            "DISCOVERY",
            "DRAFT",
            "REVIEW",
            "APPROVED",
            "IMPLEMENTING",
            "SPEC_CHANGE_PROPOSED",
            "VERIFYING",
            "ACCEPTED",
            "BLOCKED",
            "SUPERSEDED",
        }
        self.assertTrue(expected_states.issubset(states))
        normalized_template = " ".join(template.split())
        self.assertIn("`SPEC_CHANGE_PROPOSED` blocks implementation", normalized_template)
        self.assertIn("revised spec is reviewed and approved", normalized_template)


if __name__ == "__main__":
    unittest.main()
