"""Contract checks for scripts/flow_report.py: honest claims, verified quotes, no clock."""

from __future__ import annotations

import unittest
from unittest import mock

from scripts import flow_report


class FlowReportTests(unittest.TestCase):
    def test_every_ledger_quote_is_still_in_its_source(self):
        stale = [e["id"] for e in flow_report.check_ledger() if not e["verified"]]
        self.assertEqual(stale, [])

    def test_a_drifted_quote_is_detected(self):
        entry = {"id": "x", "metric": "cost", "claim": "c", "source": "docs/TESTING.md", "quote": "text that is not in the file"}
        with mock.patch.object(flow_report, "read_json", return_value={"entries": [entry]}):
            self.assertFalse(flow_report.check_ledger()[0]["verified"])

    def test_ci_pass_rate_excludes_cancelled_and_splits_main(self):
        def run(event, branch, conclusion):
            return {"event": event, "branch": branch, "conclusion": conclusion,
                    "started_at": "2026-10-01T10:00:00Z", "updated_at": "2026-10-01T10:10:00Z"}
        snap = {"captured_at": "2026-10-23T00:00:00Z", "runs": [
            run("push", "main", "success"), run("push", "main", "failure"), run("push", "main", "cancelled"),
            run("pull_request", "other", "success"), run("pull_request", "other", "success")]}
        stats = flow_report.ci_stats(snap)
        self.assertEqual(stats["all"]["pass_rate"], "75.0%")
        self.assertEqual(stats["main_push"]["pass_rate"], "50.0%")
        self.assertEqual(stats["main_push"]["cancelled"], 1)
        self.assertEqual(stats["all"]["median_s"], 600)

    def test_report_is_deterministic_and_states_what_is_not_measured(self):
        first, _ = flow_report.render(None)
        second, _ = flow_report.render(None)
        self.assertEqual(first, second)
        self.assertEqual(first.count("**Not measured:**"), 4)
        self.assertNotIn("/home/", first)

    def test_missing_ci_snapshot_is_not_run_not_a_number(self):
        self.assertIsNone(flow_report.ci_stats(None))


if __name__ == "__main__":
    unittest.main()
