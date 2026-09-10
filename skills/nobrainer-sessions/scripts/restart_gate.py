#!/usr/bin/env python3
"""Evaluate normalized session observations; never create, send, archive or lock.

Optional hook adapters supply verified observations. Missing safety observations
fail closed. This helper is not a session backend or proof of host capability.
"""
from __future__ import annotations
import json
import sys


def decide(state: dict) -> dict[str, object]:
    assessment = {}
    def result(action: str, reason: str) -> dict[str, object]:
        return {"action": action, "reason": reason, **({"assessment": assessment} if assessment else {})}

    def yes(name: str) -> bool:
        return state.get(name) is True

    def number(name: str) -> float | None:
        value = state.get(name)
        return value if type(value) in (int, float) and 0 <= value < float("inf") else None

    if type(state.get("schema")) is not int or state["schema"] != 1:
        return result("BLOCKED", "unsupported_schema")
    if not isinstance(state.get("source_id"), str) or not state["source_id"].strip():
        return result("BLOCKED", "source_identity")
    if not isinstance(state.get("goal_id"), str) or not state["goal_id"].strip():
        return result("BLOCKED", "goal_identity")
    target = state.get("target_id")
    if yes("ownership_committed") and (
        not isinstance(target, str) or not target.strip() or target == state["source_id"]
    ):
        return result("BLOCKED", "committed_target_identity")
    # After a committed transfer the source must never resume implementation.
    if yes("ownership_committed"):
        if not yes("target_takeover_readback") or not yes("ack_matches"):
            return result("VERIFY_TAKEOVER", "source_remains_readonly")
        if not yes("source_retired_readback"):
            return result("VERIFY_SOURCE_RELEASE", "do_not_archive_an_unreleased_source")
        if state.get("archive_status") == "unknown":
            return result("RECONCILE_ARCHIVE", "target_owns_work_never_recreate")
        if yes("source_archived_readback"):
            return result("COMPLETE", "takeover_and_archive_verified")
        if not yes("archive_authorized") or not yes("archive_supported"):
            return result("ARCHIVE_PENDING", "target_owns_work_source_remains_readonly")
        return result("ARCHIVE_SOURCE", "archive_exact_source_only")
    if not yes("remaining_work"):
        return result("FINISH" if state.get("remaining_work") is False else "BLOCKED", "remaining_work")
    if yes("required_budget_unmeasurable"):
        return result("BLOCKED", "required_budget_unmeasurable")
    if state.get("mode") not in ("off", "adaptive", "daily"):
        return result("BLOCKED", "invalid_mode")
    if state["mode"] == "off" or not yes("policy_authorized"):
        return result("CHECKPOINT_ONLY", "restart_not_authorized")
    if state.get("creation_status") == "unknown":
        return result("RECONCILE_TARGET", "never_retry_uncertain_create")
    if state.get("creation_status") not in ("not_sent", "confirmed"):
        return result("BLOCKED", "creation_status")
    target = state.get("target_id")
    if state["creation_status"] == "confirmed":
        if not isinstance(target, str) or not target.strip() or target == state["source_id"]:
            return result("BLOCKED", "target_identity")
    elif target:
        return result("RECONCILE_TARGET", "unexpected_target")
    # A short forecast limits optimistic claims about days of future work.
    current, fresh, overhead, calls = (number(name) for name in (
        "current_input_tokens", "fresh_input_tokens", "restart_overhead_tokens", "remaining_calls"
    ))
    measured = all(value is not None for value in (current, fresh, overhead, calls))
    pays_back = False
    if measured:
        horizon = min(calls, 3)
        avoided = (current - fresh) * horizon
        pays_back = horizon >= 1 and avoided > 2 * overhead
        assessment = {
            "basis": "estimated_token_proxy_not_billing",
            "horizon_calls": horizon,
            "estimated_net_tokens_saved": avoided - overhead,
            "pays_back_with_margin": pays_back,
        }
    # Pressure and a materially smaller startup justify health rotation even
    # without a price/overhead forecast. Capacity is host-observed, never guessed.
    capacity = number("context_capacity_tokens")
    occupancy = current / capacity if current is not None and capacity else None
    pressure = yes("context_pressure") or (occupancy is not None and occupancy >= 0.70)
    smaller_start = current is not None and current > 0 and fresh is not None and fresh <= 0.80 * current
    health_benefit = pressure and smaller_start
    assessment.update({
        "context_occupancy": occupancy,
        "context_pressure": pressure,
        "materially_smaller_start": smaller_start,
        "health_rotation_qualified": health_benefit,
    })
    triggered = yes("explicit_restart") or pressure or pays_back
    compactions = number("compactions")
    triggered = triggered or (compactions is not None and compactions >= 2)
    age = number("session_age_seconds")
    triggered = triggered or (state["mode"] == "daily" and age is not None and age >= 86400)
    if state["creation_status"] == "not_sent" and not triggered:
        return result("CONTINUE", "no_observed_trigger")
    if not yes("safe_boundary") or number("active_writers") != 0 or number("pending_operations") != 0:
        return result("WAIT_SAFE_BOUNDARY", "writes_or_operations_not_released")
    if not yes("checkpoint_readback") or not yes("checkpoint_current"):
        return result("CHECKPOINT", "persist_and_verify_current_state")
    if state["creation_status"] == "not_sent":
        if not yes("explicit_restart") and not pays_back and not health_benefit:
            return result("CHECKPOINT_ONLY" if not measured else "CONTINUE", "benefit_unmeasured" if not measured else "restart_does_not_pay_back")
        if not yes("explicit_restart") and not yes("progress_since_restart"):
            return result("CONTINUE", "prevent_restart_without_progress")
        if not yes("transfer_supported"):
            return result("MANUAL_HANDOFF", "no_authoritative_ownership_transfer")
        if not yes("fresh_create_supported") or not yes("target_read_supported"):
            return result("MANUAL_HANDOFF", "native_transport_unavailable")
        return result("CREATE_FRESH", "record_identity_and_receipt_before_retry")
    if not yes("ack_matches"):
        return result("VERIFY_TARGET", "exact_goal_checkpoint_and_target_ack_required")
    if not yes("transfer_supported"):
        return result("MANUAL_HANDOFF", "no_authoritative_ownership_transfer")
    return result("COMMIT_TRANSFER", "conditional_transfer_required_target_stays_readonly")


def main() -> int:
    try:
        raw = sys.stdin.buffer.read(65537)
        if len(raw) > 65536:
            raise ValueError("input_too_large")
        state = json.loads(raw)
        if not isinstance(state, dict):
            raise ValueError("expected_object")
        output = decide(state)
    except (ValueError, UnicodeDecodeError):
        output = {"action": "BLOCKED", "reason": "invalid_input"}
    print(json.dumps(output, sort_keys=True))
    return 2 if output["action"] == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
