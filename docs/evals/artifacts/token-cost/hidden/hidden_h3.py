import csv, subprocess, sys, unittest
from datetime import datetime, timezone
from shop import pricing, report

def utc(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00"))

def cli(path):
    out = subprocess.run([sys.executable, "-m", "shop", "report", path], capture_output=True, text=True, check=True).stdout
    return dict(line.split(": ") for line in out.strip().splitlines())

class H3(unittest.TestCase):
    def test_saturday_just_after_midnight_in_warsaw(self):
        self.assertAlmostEqual(pricing.discount_at(100.0, utc("2026-03-27T23:30:00Z")), 2.0)

    def test_sunday_evening_utc_is_monday_in_summer(self):
        self.assertAlmostEqual(pricing.discount_at(100.0, utc("2026-03-29T22:30:00Z")), 0.0)

    def test_sunday_in_winter_at_threshold(self):
        self.assertAlmostEqual(pricing.discount_at(1000.0, utc("2026-01-25T22:30:00Z")), 120.0)

    def test_weekday(self):
        self.assertAlmostEqual(pricing.discount_at(600.0, utc("2026-03-25T10:00:00Z")), 30.0)

    def test_dated_report_matches_invoices(self):
        with open("data/orders-dated.csv", newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        expected = round(sum(pricing.discount_at(float(r["total"]), utc(r["placed_at"])) for r in rows), 2)
        self.assertAlmostEqual(float(cli("data/orders-dated.csv")["discount"]), expected, places=2)

    def test_undated_report_matches_invoices(self):
        totals = report.load_totals("data/orders.csv")
        expected = round(sum(pricing.discount(t) for t in totals), 2)
        self.assertAlmostEqual(float(cli("data/orders.csv")["discount"]), expected, places=2)
