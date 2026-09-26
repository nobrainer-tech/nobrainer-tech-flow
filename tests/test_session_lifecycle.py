from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
EVENTS = (
    "START",
    "AFTER_COMPACTION",
    "MATERIAL_TRANSITION",
    "BEFORE_CLOSEOUT",
)
SIGNALS = ("turn_age", "history_size", "compactions", "cost_or_tokens")


@dataclass(frozen=True)
class HealthSnapshot:
    policy: dict[str, int]
    signals: dict[str, int]
    warning_policy: dict[str, int] | None = None
    unsupported: bool = False


def session_health_gate(snapshot: HealthSnapshot) -> str:
    """Small test-only reference for the portable gate, not a host adapter."""
    if snapshot.unsupported:
        return "UNSUPPORTED"
    expected = set(snapshot.policy)
    if snapshot.warning_policy:
        expected.update(snapshot.warning_policy)
    if any(name not in snapshot.signals for name in expected):
        return "UNKNOWN"
    if any(
        snapshot.signals[name] > limit
        for name, limit in snapshot.policy.items()
    ):
        return "ROTATE_REQUIRED"
    if snapshot.warning_policy and any(
        snapshot.signals.get(name, 0) > limit
        for name, limit in snapshot.warning_policy.items()
    ):
        return "WARNING"
    return "HEALTHY"


def rotation_action(
    health: str, *, owner_approved: bool, hard_budget_required: bool = False
) -> tuple[str, bool]:
    if health == "WARNING":
        return "CHECKPOINT_AND_RESTRICT_DISPATCH", False
    if health in {"UNKNOWN", "UNSUPPORTED"}:
        return (
            "BLOCKED_REQUIRED_BUDGET" if hard_budget_required else "CONTINUE_BOUNDED",
            False,
        )
    if health != "ROTATE_REQUIRED":
        return "CONTINUE", False
    if not owner_approved:
        return "CHECKPOINT_AND_END_TURN", False
    return "ROTATE_WITH_OWNER_APPROVAL", True


def runtime_release(owned_workers: int | None, *, supported: bool = True) -> str:
    if not supported:
        return "UNSUPPORTED"
    if owned_workers is None:
        return "UNKNOWN"
    return "VERIFIED" if owned_workers == 0 else "NOT_RELEASED"


def live_worker_count(workers: list[subprocess.Popen[bytes]]) -> int:
    return sum(worker.poll() is None for worker in workers)


def clean_closeout(health: str, task_complete: bool, release: str) -> bool:
    return health == "HEALTHY" and task_complete and release == "VERIFIED"


def no_ready_action(
    ready_rows: list[str], owner_gated: bool, *, running: bool = False,
    reported: bool = False, complete: bool = False,
) -> str:
    if not ready_rows and reported:
        return "AUDIT"
    if not ready_rows and running:
        return "WAIT"
    if not ready_rows and complete:
        return "COMPLETE"
    if not ready_rows and owner_gated:
        return "OWNER_DECISION_REQUIRED"
    return "CONTINUE"


def read_goal(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if ": " in line:
            key, value = line.split(": ", 1)
            fields[key] = value
    return fields


def clear_mode(
    *,
    clear_supported: bool,
    clear_readback: bool,
    goal_persisted: bool,
    goal_readback: bool,
    handoff_persisted: bool,
    writers: int,
) -> str:
    if writers:
        return "MANUAL_REQUIRED"
    if not goal_persisted or not goal_readback or not handoff_persisted:
        return "MANUAL_REQUIRED"
    if not clear_supported:
        return "END_TURN"
    if clear_readback:
        return "HOST_CLEAR"
    return "MANUAL_REQUIRED"


class SessionLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = {
            "turn_age": 100,
            "history_size": 1000,
            "compactions": 3,
            "cost_or_tokens": 10_000,
        }
        self.signals = {
            "turn_age": 20,
            "history_size": 400,
            "compactions": 1,
            "cost_or_tokens": 2_000,
        }

    def test_clean_session_trace_is_healthy_and_released(self) -> None:
        snapshot = HealthSnapshot(self.policy, self.signals)
        for event in EVENTS:
            with self.subTest(event=event):
                self.assertEqual(session_health_gate(snapshot), "HEALTHY")
        self.assertEqual(runtime_release(0), "VERIFIED")
        self.assertTrue(clean_closeout("HEALTHY", True, "VERIFIED"))

    def test_limit_checkpoints_and_ends_turn_without_rotation(self) -> None:
        signals = dict(self.signals, history_size=1_001)
        health = session_health_gate(HealthSnapshot(self.policy, signals))
        self.assertEqual(health, "ROTATE_REQUIRED")
        action, created_session = rotation_action(health, owner_approved=False)
        self.assertEqual(action, "CHECKPOINT_AND_END_TURN")
        self.assertFalse(created_session)

    def test_unknown_and_unsupported_signals_never_look_healthy(self) -> None:
        incomplete = dict(self.signals)
        incomplete.pop("history_size")
        self.assertEqual(
            session_health_gate(HealthSnapshot(self.policy, incomplete)), "UNKNOWN"
        )
        self.assertEqual(
            session_health_gate(
                HealthSnapshot(self.policy, self.signals, unsupported=True)
            ),
            "UNSUPPORTED",
        )
        self.assertFalse(clean_closeout("UNKNOWN", True, "VERIFIED"))
        self.assertFalse(clean_closeout("HEALTHY", True, "UNSUPPORTED"))
        self.assertEqual(
            rotation_action("UNKNOWN", owner_approved=False),
            ("CONTINUE_BOUNDED", False),
        )
        self.assertEqual(
            rotation_action("UNSUPPORTED", owner_approved=False),
            ("CONTINUE_BOUNDED", False),
        )

    def test_unmeasurable_required_budget_still_blocks_dependent_work(self) -> None:
        for health in ("UNKNOWN", "UNSUPPORTED"):
            self.assertEqual(
                rotation_action(health, owner_approved=False, hard_budget_required=True),
                ("BLOCKED_REQUIRED_BUDGET", False),
            )

    def test_empty_ready_set_distinguishes_wait_audit_and_completion(self) -> None:
        self.assertEqual(no_ready_action([], False, running=True), "WAIT")
        self.assertEqual(no_ready_action([], False, reported=True), "AUDIT")
        self.assertEqual(no_ready_action([], False, complete=True), "COMPLETE")
        self.assertEqual(no_ready_action([], True, running=True), "WAIT")

    def test_task_complete_does_not_release_live_workers(self) -> None:
        self.assertEqual(runtime_release(1), "NOT_RELEASED")
        self.assertFalse(clean_closeout("HEALTHY", True, "NOT_RELEASED"))

    def test_warning_checkpoints_before_hard_limit(self) -> None:
        warning_policy = dict(self.policy, history_size=700)
        signals = dict(self.signals, history_size=800)
        health = session_health_gate(
            HealthSnapshot(self.policy, signals, warning_policy=warning_policy)
        )
        self.assertEqual(health, "WARNING")
        action, created_session = rotation_action(health, owner_approved=False)
        self.assertEqual(action, "CHECKPOINT_AND_RESTRICT_DISPATCH")
        self.assertFalse(created_session)

    def test_missing_warning_signal_is_unknown(self) -> None:
        self.assertEqual(
            session_health_gate(
                HealthSnapshot(
                    {"turn_age": 100},
                    {"turn_age": 20},
                    warning_policy={"history_size": 700},
                )
            ),
            "UNKNOWN",
        )

    def test_clean_session_releases_a_controlled_live_worker(self) -> None:
        worker = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(30)"]
        )
        try:
            self.assertEqual(runtime_release(live_worker_count([worker])), "NOT_RELEASED")
            self.assertFalse(clean_closeout("HEALTHY", True, "NOT_RELEASED"))
        finally:
            worker.terminate()
            worker.wait(timeout=5)
        self.assertEqual(runtime_release(live_worker_count([worker])), "VERIFIED")

    def test_no_ready_work_returns_owner_decision_required(self) -> None:
        action = no_ready_action([], owner_gated=True)
        self.assertEqual(action, "OWNER_DECISION_REQUIRED")

    def test_resume_reads_durable_goal_instead_of_stale_summary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            goal_path = Path(directory) / "goal.md"
            goal_path.write_text(
                "GOAL_ID: runtime-guard\n"
                "OUTCOME: Resume safely\n"
                "STATUS: ACTIVE\n"
                "CHECKPOINT: tests passed\n"
                "NEXT_SAFE_ACTION: review current diff\n",
                encoding="utf-8",
            )
            stale_summary = {"NEXT_SAFE_ACTION": "repeat implementation"}
            goal = read_goal(goal_path)
            self.assertEqual(goal["GOAL_ID"], "runtime-guard")
            self.assertEqual(goal["NEXT_SAFE_ACTION"], "review current diff")
            self.assertNotEqual(
                goal["NEXT_SAFE_ACTION"], stale_summary["NEXT_SAFE_ACTION"]
            )

    def test_clear_requires_no_writer_and_positive_readback(self) -> None:
        self.assertEqual(
            clear_mode(
                clear_supported=True,
                clear_readback=True,
                goal_persisted=True,
                goal_readback=True,
                handoff_persisted=True,
                writers=0,
            ),
            "HOST_CLEAR",
        )
        self.assertEqual(
            clear_mode(
                clear_supported=True,
                clear_readback=False,
                goal_persisted=True,
                goal_readback=True,
                handoff_persisted=True,
                writers=0,
            ),
            "MANUAL_REQUIRED",
        )
        self.assertEqual(
            clear_mode(
                clear_supported=True,
                clear_readback=True,
                goal_persisted=True,
                goal_readback=True,
                handoff_persisted=True,
                writers=1,
            ),
            "MANUAL_REQUIRED",
        )
        self.assertEqual(
            clear_mode(
                clear_supported=False,
                clear_readback=False,
                goal_persisted=True,
                goal_readback=True,
                handoff_persisted=True,
                writers=0,
            ),
            "END_TURN",
        )
        for goal_persisted, goal_readback, handoff_persisted in (
            (False, True, True),
            (True, False, True),
            (True, True, False),
        ):
            with self.subTest(
                goal_persisted=goal_persisted,
                goal_readback=goal_readback,
                handoff_persisted=handoff_persisted,
            ):
                self.assertEqual(
                    clear_mode(
                        clear_supported=True,
                        clear_readback=True,
                        goal_persisted=goal_persisted,
                        goal_readback=goal_readback,
                        handoff_persisted=handoff_persisted,
                        writers=0,
                    ),
                    "MANUAL_REQUIRED",
                )

    def test_portable_contract_names_health_and_release_boundaries(self) -> None:
        paths = (
            ROOT / "skills" / "nobrainer-tech-flow" / "SKILL.md",
            ROOT / "skills" / "nobrainer-tech-flow" / "references" / "long-run-state.md",
            ROOT / "skills" / "nobrainer-sessions" / "SKILL.md",
            ROOT / "skills" / "nobrainer-sessions" / "references" / "protocol.md",
            ROOT / "docs" / "TESTING.md",
            ROOT / "docs" / "COMPATIBILITY.md",
            ROOT / "README.md",
            ROOT / "assets" / "nobrainer-workflow.svg",
        )
        combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        for term in (
            "SESSION_HEALTH_GATE",
            "RUNTIME_RELEASE",
            "AFTER_COMPACTION",
            "MATERIAL_TRANSITION",
            "BEFORE_CLOSEOUT",
            "ROTATE_REQUIRED",
            "CHECKPOINT_AND_END_TURN",
            "OWNER_DECISION_REQUIRED",
            "task_complete",
            "UNKNOWN",
            "UNSUPPORTED",
            "RUNTIME_RELEASE readback",
            "GOAL_FILE",
            "CLEAR_MODE",
            "HOST_CLEAR",
            "MANUAL_REQUIRED",
            "WARNING",
        ):
            self.assertIn(term, combined)
        self.assertNotRegex(combined, re.compile(r"\bPID\b"))
        self.assertNotIn("JSONL", combined)
        self.assertNotIn("/" + "Users" + "/", combined)
        self.assertNotIn("/" + "Volumes" + "/", combined)


if __name__ == "__main__":
    unittest.main()
