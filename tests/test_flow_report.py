"""Contract checks for scripts/flow_report.py: honest claims, verified quotes, no clock."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
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

    def test_every_quote_of_a_multi_quote_entry_must_be_present(self):
        entry = {"id": "x", "metric": "cost", "claim": "c", "source": "docs/TESTING.md",
                 "quote": ["## Measurement report", "text that is not in the file"]}
        with mock.patch.object(flow_report, "read_json", return_value={"entries": [entry]}):
            self.assertFalse(flow_report.check_ledger()[0]["verified"])
        entry["quote"] = ["## Measurement report", "paid-run-plan.md"]
        with mock.patch.object(flow_report, "read_json", return_value={"entries": [entry]}):
            self.assertTrue(flow_report.check_ledger()[0]["verified"])

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

    def test_runs_outside_main_and_pull_requests_get_their_own_row(self):
        def run(event, branch, conclusion):
            return {"event": event, "branch": branch, "conclusion": conclusion,
                    "started_at": "2026-10-01T10:00:00Z", "updated_at": "2026-10-01T10:10:00Z"}
        snap = {"captured_at": "2026-10-23T00:00:00Z", "runs": [
            run("push", "main", "success"), run("pull_request", "other", "success"),
            run("workflow_dispatch", "other", "failure"), run("push", "other", "success")]}
        stats = flow_report.ci_stats(snap)
        self.assertEqual(stats["other"]["runs"], 2)
        self.assertEqual(stats["other_events"], ["push", "workflow_dispatch"])
        self.assertEqual(stats["all"]["runs"], sum(stats[k]["runs"] for k in ("main_push", "pull_request", "other")))

    def test_test_inventory_counts_a_shadowed_method_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "tests").mkdir()
            (Path(tmp) / "tests" / "test_x.py").write_text(
                "import unittest\n"
                "class A(unittest.TestCase):\n"
                "    def test_one(self): pass\n"
                "    def test_one(self): pass\n"
                "    def test_two(self): pass\n"
                "    def helper(self): pass\n"
                "class B(unittest.TestCase):\n"
                "    def test_one(self): pass\n", encoding="utf-8")
            with mock.patch.object(flow_report, "ROOT", Path(tmp)):
                self.assertEqual(flow_report.test_inventory(), {"files": 1, "defined_cases": 3})

    def test_skill_size_ignores_bytecode_caches_outside_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "skills" / "demo"
            (skill / "scripts" / "__pycache__").mkdir(parents=True)
            (skill / "SKILL.md").write_text("---\nname: demo\n---\n", encoding="utf-8")
            (skill / "scripts" / "helper.py").write_text("x = 1\n", encoding="utf-8")
            (skill / "scripts" / "__pycache__" / "helper.cpython-313.pyc").write_bytes(b"0" * 500)
            with mock.patch.object(flow_report, "ROOT", Path(tmp)):
                names = sorted(p.name for p in flow_report.skill_files(skill))
            self.assertEqual(names, ["SKILL.md", "helper.py"])

    def test_report_is_deterministic_and_states_what_is_not_measured(self):
        first, _ = flow_report.render(None)
        second, _ = flow_report.render(None)
        self.assertEqual(first, second)
        self.assertEqual(first.count("**Not measured:**"), 4)
        self.assertNotIn("/home/", first)

    def test_cost_section_does_not_claim_a_host_shows_what_flow_ships(self):
        text, _ = flow_report.render(None)
        self.assertIn("not a measure of what any host shows", text)
        self.assertNotIn("always visible", text.lower())

    def test_missing_ci_snapshot_is_not_run_not_a_number(self):
        self.assertIsNone(flow_report.ci_stats(None))


if __name__ == "__main__":
    unittest.main()
