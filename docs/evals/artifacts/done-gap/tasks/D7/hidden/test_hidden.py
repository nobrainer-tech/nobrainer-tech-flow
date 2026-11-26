import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from shop import pricing, report

ROOT = Path(__file__).resolve().parent.parent


def expected(rows):
    totals = [float(r["total"]) for r in rows if r["status"] != "cancelled"]
    gross = round(sum(totals), 2)
    disc = round(sum(pricing.discount(t) for t in totals), 2)
    return len(totals), gross, disc, round(gross - disc, 2)


def cli_report(path):
    result = subprocess.run([sys.executable, "-m", "shop", "report", str(path)], cwd=ROOT,
                            capture_output=True, text=True, timeout=120)
    values = {}
    for line in result.stdout.splitlines():
        key, _, value = line.partition(":")
        values[key.strip()] = float(value)
    return values


class CancelledTest(unittest.TestCase):
    def assertSummary(self, values, rows):
        orders, gross, disc, net = expected(rows)
        self.assertEqual(int(values["orders"]), orders)
        self.assertAlmostEqual(values["gross"], gross, places=2)
        self.assertAlmostEqual(values["discount"], disc, places=2)
        self.assertAlmostEqual(values["net"], net, places=2)

    def test_summarize_rows_excludes_cancelled(self):
        rows = [{"total": "600.00", "status": "paid"}, {"total": "1200.00", "status": "cancelled"},
                {"total": "40.25", "status": "shipped"}, {"total": "700.00", "status": "cancelled"}]
        self.assertSummary(report.summarize_rows(rows), rows)

    def test_cli_on_repo_data_excludes_cancelled(self):
        with open(ROOT / "data" / "orders.csv", newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertTrue(any(r["status"] == "cancelled" for r in rows))
        self.assertSummary(cli_report(ROOT / "data" / "orders.csv"), rows)

    def test_cli_on_temp_file_excludes_cancelled(self):
        rows = [{"total": "1000.00", "status": "cancelled"}, {"total": "520.40", "status": "paid"},
                {"total": "99.99", "status": "shipped"}, {"total": "2500.00", "status": "cancelled"}]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "orders.csv"
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["order_id", "customer", "total", "status"])
                for i, r in enumerate(rows):
                    writer.writerow([f"T-{i}", "C-1", r["total"], r["status"]])
            self.assertSummary(cli_report(path), rows)


if __name__ == "__main__":
    unittest.main()
