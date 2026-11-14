import subprocess, sys, unittest
from shop import pricing, report

class T5(unittest.TestCase):
    def test_report_matches_pricing(self):
        totals = [999.99, 1000.0, 1500.0, 499.99, 500.0, 20.0]
        summary = report.summarize(totals)
        self.assertAlmostEqual(summary["discount"], round(sum(pricing.discount(t) for t in totals), 2), places=2)
        self.assertAlmostEqual(summary["net"], round(summary["gross"] - summary["discount"], 2), places=2)

    def test_cli_report(self):
        totals = report.load_totals("data/orders.csv")
        expected = round(sum(pricing.discount(t) for t in totals), 2)
        out = subprocess.run([sys.executable, "-m", "shop", "report", "data/orders.csv"],
                             capture_output=True, text=True, check=True).stdout
        self.assertIn(f"discount: {expected:.2f}", out)
