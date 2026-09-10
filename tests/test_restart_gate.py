from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

PATH = Path(__file__).resolve().parents[1] / 'skills/nobrainer-sessions/scripts/restart_gate.py'
spec = importlib.util.spec_from_file_location('restart_gate', PATH)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class RestartGateTests(unittest.TestCase):
    def setUp(self):
        self.state = dict(schema=1, mode='adaptive', policy_authorized=True,
            remaining_work=True, source_id='old', goal_id='goal', creation_status='not_sent',
            compactions=2, current_input_tokens=80000, fresh_input_tokens=15000,
            restart_overhead_tokens=10000, remaining_calls=3,
            progress_since_restart=True, safe_boundary=True, active_writers=0,
            pending_operations=0, checkpoint_readback=True, checkpoint_current=True,
            fresh_create_supported=True, target_read_supported=True, transfer_supported=True)

    def action(self, **updates):
        return gate.decide(dict(self.state, **updates))['action']

    def test_beneficial_forecast_is_bounded_and_explicitly_not_billing(self):
        d = gate.decide(dict(self.state, remaining_calls=999))
        self.assertEqual(d['action'], 'CREATE_FRESH')
        self.assertEqual(d['assessment']['horizon_calls'], 3)
        self.assertEqual(d['assessment']['estimated_net_tokens_saved'], 185000)
        self.assertEqual(d['assessment']['basis'], 'estimated_token_proxy_not_billing')

    def test_small_post_compaction_context_does_not_restart(self):
        self.assertEqual(self.action(current_input_tokens=16000), 'CONTINUE')

    def test_daily_age_and_compactions_do_not_override_unknown_economics(self):
        for value in (None, True, -1, float('nan'), float('inf')):
            with self.subTest(value=value):
                self.assertEqual(self.action(mode='daily', session_age_seconds=100000,
                    current_input_tokens=value), 'CHECKPOINT_ONLY')

    def test_no_progress_no_repeat_and_no_remaining_task_no_successor(self):
        self.assertEqual(self.action(progress_since_restart=False), 'CONTINUE')
        self.assertEqual(self.action(remaining_work=False), 'FINISH')

    def test_explicit_request_skips_economics_but_not_safety(self):
        self.assertEqual(self.action(explicit_restart=True, current_input_tokens=None), 'CREATE_FRESH')
        self.assertEqual(self.action(explicit_restart=True, active_writers=1), 'WAIT_SAFE_BOUNDARY')

    def test_no_standing_consent_and_unknown_required_budget(self):
        self.assertEqual(self.action(policy_authorized=False), 'CHECKPOINT_ONLY')
        self.assertEqual(self.action(required_budget_unmeasurable=True), 'BLOCKED')

    def test_unsafe_or_unknown_writers_and_pending_operations(self):
        for updates in ({'active_writers': 1}, {'active_writers': None},
                        {'active_writers': False}, {'pending_operations': 1}, {'safe_boundary': False}):
            self.assertEqual(self.action(**updates), 'WAIT_SAFE_BOUNDARY')

    def test_missing_checkpoint_and_stale_working_state(self):
        self.assertEqual(self.action(checkpoint_readback=False), 'CHECKPOINT')
        self.assertEqual(self.action(checkpoint_current=False), 'CHECKPOINT')

    def test_uncertain_transport_never_recreates(self):
        self.assertEqual(self.action(creation_status='unknown'), 'RECONCILE_TARGET')
        self.assertEqual(self.action(target_id='possibly-created'), 'RECONCILE_TARGET')
        self.assertEqual(self.action(fresh_create_supported=False), 'MANUAL_HANDOFF')

    def test_stale_ack_invalid_identity_and_no_authoritative_transfer(self):
        self.state.update(creation_status='confirmed', target_id='new')
        self.assertEqual(self.action(ack_matches=False), 'VERIFY_TARGET')
        self.assertEqual(self.action(target_id='old', ack_matches=True), 'BLOCKED')
        self.assertEqual(self.action(ack_matches=True, transfer_supported=False), 'MANUAL_HANDOFF')
        self.assertEqual(self.action(ack_matches=True, transfer_supported=True), 'COMMIT_TRANSFER')

    def test_archive_waits_for_takeover_and_retired_source(self):
        self.state.update(creation_status='confirmed', target_id='new', ack_matches=True,
            ownership_committed=True, archive_authorized=True, archive_supported=True)
        self.assertEqual(self.action(), 'VERIFY_TAKEOVER')
        self.state.update(target_takeover_readback=True)
        self.assertEqual(self.action(), 'VERIFY_SOURCE_RELEASE')
        self.state.update(source_retired_readback=True)
        self.assertEqual(self.action(), 'ARCHIVE_SOURCE')
        self.assertEqual(self.action(archive_supported=False), 'ARCHIVE_PENDING')
        self.assertEqual(self.action(archive_status='unknown'), 'RECONCILE_ARCHIVE')
        self.assertEqual(self.action(source_archived_readback=True), 'COMPLETE')
        self.assertEqual(self.action(target_id=None), 'BLOCKED')
        self.assertEqual(self.action(ack_matches=False), 'VERIFY_TAKEOVER')

    def test_pressure_can_rotate_without_billing_forecast(self):
        self.assertEqual(self.action(context_pressure=True,
            restart_overhead_tokens=None), 'CREATE_FRESH')
        self.assertEqual(self.action(context_capacity_tokens=100000,
            restart_overhead_tokens=None), 'CREATE_FRESH')

    def test_pressure_needs_smaller_start_and_progress(self):
        self.assertEqual(self.action(context_pressure=True, fresh_input_tokens=79000,
            restart_overhead_tokens=None), 'CHECKPOINT_ONLY')
        self.assertEqual(self.action(context_pressure=True, current_input_tokens=None,
            restart_overhead_tokens=None), 'CHECKPOINT_ONLY')
        self.assertEqual(self.action(context_pressure=True, progress_since_restart=False),
            'CONTINUE')
        self.assertEqual(self.action(context_pressure=True, active_writers=1),
            'WAIT_SAFE_BOUNDARY')

    def test_committed_transfer_cannot_return_source_to_work(self):
        for updates in ({'remaining_work': False}, {'mode': 'off'},
                        {'policy_authorized': False}, {'required_budget_unmeasurable': True}):
            self.assertEqual(self.action(ownership_committed=True, target_id='new',
                **updates), 'VERIFY_TAKEOVER')

    def test_real_cli_rejects_malformed_and_oversized_observations(self):
        for payload in ('[]', '{', 'x'*65537):
            p = subprocess.run([sys.executable, str(PATH)], input=payload, text=True, capture_output=True)
            self.assertEqual(p.returncode, 2)
            self.assertEqual(json.loads(p.stdout)['action'], 'BLOCKED')
        p = subprocess.run([sys.executable, str(PATH)], input=json.dumps(self.state), text=True, capture_output=True)
        self.assertEqual(p.returncode, 0)
        self.assertEqual(json.loads(p.stdout)['action'], 'CREATE_FRESH')


if __name__ == '__main__':
    unittest.main()
