import csv
import os
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal, ROUND_HALF_UP

from shop import invoice, pricing, report

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASES = [("499.99", "0.00"), ("500", "30.00"), ("600", "36.00"), ("999.99", "60.00"), ("1000", "100.00")]


def expected_discount(total):
    value = Decimal(total)
    rate = Decimal("0.10") if value >= 1000 else Decimal("0.06") if value >= 500 else Decimal("0")
    return str((value * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def run_cli(*args):
    return subprocess.run([sys.executable, "-m", "shop", *args], cwd=ROOT, capture_output=True, text=True)


def parse(text):
    return dict(line.split(": ", 1) for line in text.strip().splitlines())


class HiddenTest(unittest.TestCase):
    def test_expected_table(self):
        for total, disc in CASES:
            self.assertEqual(expected_discount(total), disc)

    def test_pricing(self):
        for total, disc in CASES:
            self.assertEqual(f"{pricing.discount(float(total)):.2f}", disc, total)

    def test_report_summarize(self):
        for total, disc in CASES:
            summary = report.summarize([float(total)])
            self.assertEqual(f"{summary['discount']:.2f}", disc, total)

    def test_invoice(self):
        for total, disc in CASES:
            fields = parse(invoice.render_invoice("O-X", float(total)))
            self.assertEqual(fields["discount"], disc, total)
            self.assertEqual(fields["to pay"], f"{Decimal(total) - Decimal(disc):.2f}")

    def test_report_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "orders.csv")
            with open(path, "w", newline="", encoding="utf-8") as handle:
                handle.write("order_id,customer,total\n")
                for i, (total, _) in enumerate(CASES, 1):
                    handle.write(f"T-{i},C-01,{total}\n")
            run = run_cli("report", path)
            self.assertEqual(run.returncode, 0, run.stderr)
            expected = sum(Decimal(d) for _, d in CASES)
            self.assertEqual(parse(run.stdout)["discount"], f"{expected:.2f}")

    def test_invoice_cli_on_data(self):
        with open(os.path.join(ROOT, "data", "orders.csv"), newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        mid = [r for r in rows if 500 <= Decimal(r["total"]) < 1000]
        self.assertGreaterEqual(len(mid), 5)
        for row in mid[:6] + [r for r in rows if Decimal(r["total"]) >= 1000][:2]:
            run = run_cli("invoice", row["order_id"])
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(parse(run.stdout)["discount"], expected_discount(row["total"]), row["order_id"])

    def test_report_cli_on_data(self):
        with open(os.path.join(ROOT, "data", "orders.csv"), newline="", encoding="utf-8") as handle:
            totals = [r["total"] for r in csv.DictReader(handle)]
        run = run_cli("report", "data/orders.csv")
        self.assertEqual(run.returncode, 0, run.stderr)
        expected = sum(Decimal(expected_discount(t)) for t in totals)
        self.assertEqual(parse(run.stdout)["discount"], f"{expected:.2f}")


if __name__ == "__main__":
    unittest.main()
