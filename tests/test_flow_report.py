"""Contract checks for scripts/flow_report.py: honest claims, verified quotes, no clock."""

from __future__ import annotations

import io
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

from scripts import flow_report


def render_without_validators(tests=None):
    """Render the report with the two validator subprocesses stubbed out; only the text under test matters."""
    with mock.patch.object(flow_report, "validators", return_value={"skills": True, "suite": True}):
        return flow_report.render(tests)


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

    def test_files_outside_git_skip_bytecode_caches(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "skills" / "demo"
            (skill / "scripts" / "__pycache__").mkdir(parents=True)
            (skill / "SKILL.md").write_text("---\nname: demo\n---\n", encoding="utf-8")
            (skill / "scripts" / "helper.py").write_text("x = 1\n", encoding="utf-8")
            (skill / "scripts" / "__pycache__" / "helper.cpython-313.pyc").write_bytes(b"0" * 500)
            with mock.patch.object(flow_report, "ROOT", Path(tmp)):
                names = sorted(p.name for p in flow_report.files_under("skills/demo"))
            self.assertEqual(names, ["SKILL.md", "helper.py"])

    @unittest.skipUnless(shutil.which("git"), "git is needed to build a tracked-files fixture")
    def test_inventories_count_tracked_files_not_untracked_ones(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tests").mkdir()
            for name in ("test_a.py", "test_b.py"):
                (root / "tests" / name).write_text("import unittest\nclass T(unittest.TestCase):\n    def test_x(self): pass\n",
                                                   encoding="utf-8")
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(["git", "-C", str(root), "add", "tests/test_a.py"], check=True)
            with mock.patch.object(flow_report, "ROOT", root):
                self.assertEqual(flow_report.test_inventory(), {"files": 1, "defined_cases": 1})

    @unittest.skipUnless(shutil.which("git"), "git is needed to build a checkout fixture")
    def test_a_checkout_with_no_tracked_files_under_a_path_counts_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs" / "evals").mkdir(parents=True)
            (root / "docs" / "evals" / "scratch.md").write_text("untracked\n", encoding="utf-8")
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            with mock.patch.object(flow_report, "ROOT", root):
                self.assertEqual(flow_report.files_under("docs/evals"), [])

    @unittest.skipUnless(shutil.which("git"), "git is needed to build a checkout fixture")
    def test_a_tree_inside_someone_elses_repository_is_walked_not_listed(self):
        with tempfile.TemporaryDirectory() as tmp:
            outer = Path(tmp)
            subprocess.run(["git", "init", "-q", str(outer)], check=True)
            inner = outer / "extracted"
            (inner / "skills" / "demo").mkdir(parents=True)
            (inner / "skills" / "demo" / "SKILL.md").write_text("x\n", encoding="utf-8")
            with mock.patch.object(flow_report, "ROOT", inner):
                self.assertFalse(flow_report.own_checkout())
                self.assertEqual([p.name for p in flow_report.files_under("skills")], ["SKILL.md"])

    def test_release_cadence_counts_records_by_the_month_they_were_first_added(self):
        log = "\n".join(["@@2026-10-02", "docs/releases/v2.0.0.md", "", "@@2026-09-30", "docs/releases/v1.9.0.md",
                          "docs/releases/v1.9.1.md", "docs/releases/v1.9.1-readback.md", "",
                          "@@2026-08-31", "docs/releases/v1.9.0.md"])
        with mock.patch.object(flow_report, "history", return_value=True), mock.patch.object(flow_report, "git", return_value=log):
            cadence = flow_report.release_cadence()
        self.assertEqual(cadence, {"records": 3, "months": {"2026-08": 1, "2026-09": 1, "2026-10": 1}})

    def test_a_failing_fresh_suite_fails_the_command(self):
        failed = {"schema": "s", "exit_code": 1, "tests": 3, "seconds": 1.0, "failures": 1, "errors": 0, "skipped": 0,
                  "failed_tests": ["t.C.test_x"], "summary": "FAILED (failures=1)", "python": "3", "system": "Linux",
                  "cpus": 1, "commit": "0123456789abcdef", "dirty": False, "note": "n"}
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(flow_report, "DATA", Path(tmp) / "data"), \
                mock.patch.object(flow_report, "run_suite", return_value=failed), \
                mock.patch.object(flow_report, "validators", return_value={"skills": True, "suite": True}), \
                mock.patch.object(sys, "argv", ["flow_report.py", "--run-tests"]), \
                mock.patch.object(sys, "stdout", io.StringIO()), redirect_stderr(io.StringIO()) as err:
            self.assertEqual(flow_report.main(), 1)
            self.assertTrue((Path(tmp) / "data" / "test-run.json").exists())
        self.assertIn("suite failed", err.getvalue())

    def test_run_suite_records_a_dirty_tree_and_the_commit(self):
        done = mock.Mock(returncode=0, stderr="Ran 3 tests in 1.5s\n\nOK (skipped=1)\n")

        def fake_git(*args):
            return {"rev-parse": "0123456789abcdef", "status": " M scripts/flow_report.py"}[args[0]]

        with mock.patch.object(flow_report.subprocess, "run", return_value=done), mock.patch.object(flow_report, "git", side_effect=fake_git), \
                mock.patch.object(flow_report, "own_checkout", return_value=True):
            run = flow_report.run_suite()
        self.assertEqual((run["tests"], run["skipped"], run["exit_code"], run["dirty"], run["commit"]),
                         (3, 1, 0, True, "0123456789abcdef"))
        with mock.patch.object(flow_report.subprocess, "run", return_value=done), mock.patch.object(flow_report, "own_checkout", return_value=True), \
                mock.patch.object(flow_report, "git", side_effect=lambda *a: "" if a[0] == "status" else "0123456789abcdef"):
            self.assertFalse(flow_report.run_suite()["dirty"])

    def test_a_suite_run_outside_its_own_checkout_records_no_commit(self):
        done = mock.Mock(returncode=0, stderr="Ran 3 tests in 1.5s\n\nOK\n")
        with mock.patch.object(flow_report.subprocess, "run", return_value=done), mock.patch.object(flow_report, "own_checkout", return_value=False), \
                mock.patch.object(flow_report, "git", return_value="the-commit-of-some-other-repository"):
            run = flow_report.run_suite()
        self.assertEqual((run["commit"], run["dirty"]), (None, None))
        self.assertIn("not a git checkout", render_without_validators(run)[0])

    def test_size_counts_crlf_as_lf(self):
        with tempfile.TemporaryDirectory() as tmp:
            lf, crlf = Path(tmp) / "lf.md", Path(tmp) / "crlf.md"
            lf.write_bytes(b"one\ntwo\n")
            crlf.write_bytes(b"one\r\ntwo\r\n")
            self.assertEqual(flow_report.shipped_size(lf), flow_report.shipped_size(crlf))

    def test_percentile_is_nearest_rank(self):
        self.assertEqual(flow_report.percentile([1, 2, 3, 4, 5, 6], 0.9), 6)
        self.assertEqual(flow_report.percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 0.9), 9)
        self.assertEqual(flow_report.percentile([7], 0.9), 7)
        self.assertEqual(flow_report.percentile([6, 1, 5, 2, 4, 3], 0.9), 6)

    def test_failed_test_ids_are_not_doubled(self):
        err = ("FAIL: test_a (test_mod.Case.test_a)\nERROR: test_b (tests.test_mod.Case.test_b)\n"
               "FAIL: test_c (test_mod.Case)\n")
        self.assertEqual(flow_report.failed_ids(err),
                         ["test_mod.Case.test_a", "test_mod.Case.test_c", "tests.test_mod.Case.test_b"])

    def test_recorded_run_states_whether_the_tree_was_clean(self):
        run = {"system": "Linux", "python": "3.13", "cpus": 2, "tests": 1, "exit_code": 0, "failures": 0, "errors": 0,
               "skipped": 0, "seconds": 60.0, "commit": "0123456789abcdef", "note": "n"}
        self.assertIn("(clean tree)", render_without_validators({**run, "dirty": False})[0])
        self.assertIn("(uncommitted changes in the tree)", render_without_validators({**run, "dirty": True})[0])
        self.assertIn("(tree state not recorded)", render_without_validators(run)[0])

    def test_without_full_history_the_report_says_not_run_and_will_not_be_written(self):
        with mock.patch.object(flow_report, "history", return_value=False):
            text, _ = render_without_validators()
            self.assertIn("Release records by month: `NOT_RUN` here", text)
            self.assertIn("release records per month `NOT_RUN` here", text)
            err = io.StringIO()
            with mock.patch.object(sys, "argv", ["flow_report.py", "--write"]), redirect_stderr(err):
                self.assertEqual(flow_report.main(), 2)
            self.assertIn("full history", err.getvalue())

    def test_report_is_deterministic_and_states_what_is_not_measured(self):
        first, _ = flow_report.render(None)
        second, _ = flow_report.render(None)
        self.assertEqual(first, second)
        self.assertEqual(first.count("**Not measured:**"), 4)
        self.assertNotIn("/home/", first)

    def test_cost_section_does_not_claim_a_host_shows_what_flow_ships(self):
        text, _ = render_without_validators()
        self.assertIn("not a measure of what any host shows", text)
        self.assertNotIn("always visible", text.lower())

    def test_missing_ci_snapshot_is_not_run_not_a_number(self):
        self.assertIsNone(flow_report.ci_stats(None))


if __name__ == "__main__":
    unittest.main()
