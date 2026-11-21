import ast
import contextlib
import csv
import io
import subprocess
import sys
import tempfile
import unittest
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from shop import importer, pricing, report

ROOT = Path(__file__).resolve().parent.parent
CENT = Decimal("0.01")


def half_up(value):
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def expected_discount(total):
    rate = Decimal("0.10") if total >= 1000 else Decimal("0.05") if total >= 500 else Decimal("0")
    return half_up(total * rate)


class PricingTest(unittest.TestCase):
    def test_discount_is_decimal_half_up(self):
        for text, want in (("502.50", "25.13"), ("512.50", "25.63"), ("1000.05", "100.01"),
                           ("1000.50", "100.05"), ("1234.55", "123.46"), ("499.99", "0.00"),
                           ("500.00", "25.00"), ("999.99", "50.00"), ("1000.00", "100.00")):
            got = pricing.discount(Decimal(text))
            self.assertIsInstance(got, Decimal, text)
            self.assertEqual(got, Decimal(want), text)
            self.assertEqual(got.as_tuple().exponent, -2, text)

    def test_discount_rate_is_decimal(self):
        for text, want in (("100", "0.00"), ("500", "0.05"), ("1000", "0.10")):
            rate = pricing.discount_rate(Decimal(text))
            self.assertIsInstance(rate, Decimal)
            self.assertEqual(rate, Decimal(want))


class ReportTest(unittest.TestCase):
    def write_csv(self, tmp, totals):
        path = Path(tmp) / "orders.csv"
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["order_id", "customer", "total"])
            for i, total in enumerate(totals):
                writer.writerow([f"T-{i}", "C-1", total])
        return path

    def test_load_totals_and_summarize_are_decimal(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_csv(tmp, ["502.50", "19.90", "1000.50"])
            totals = report.load_totals(path)
        self.assertEqual(totals, [Decimal("502.50"), Decimal("19.90"), Decimal("1000.50")])
        for value in totals:
            self.assertIsInstance(value, Decimal)
        summary = report.summarize(totals)
        self.assertEqual(summary["orders"], 3)
        for key in ("gross", "discount", "net"):
            self.assertIsInstance(summary[key], Decimal, key)
        self.assertEqual(summary["gross"], Decimal("1522.90"))
        self.assertEqual(summary["discount"], Decimal("25.13") + Decimal("100.05"))
        self.assertEqual(summary["net"], Decimal("1522.90") - Decimal("125.18"))

    def test_cli_prints_half_up_cents(self):
        totals = ["502.50", "512.50", "1000.50", "1000.05", "501.90", "19.90", "2000.10"]
        want_gross = sum(Decimal(t) for t in totals)
        want_disc = sum(expected_discount(Decimal(t)) for t in totals)
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_csv(tmp, totals)
            out = subprocess.run([sys.executable, "-m", "shop", "report", str(path)], cwd=ROOT,
                                 capture_output=True, text=True, timeout=120).stdout
        self.assertEqual(out.splitlines(), [
            "orders: 7", f"gross: {want_gross:.2f}", f"discount: {want_disc:.2f}",
            f"net: {want_gross - want_disc:.2f}"])

    def test_cli_on_repo_data(self):
        with open(ROOT / "data" / "orders.csv", newline="", encoding="utf-8") as handle:
            totals = [Decimal(r["total"]) for r in csv.DictReader(handle)]
        want_gross = sum(totals)
        want_disc = sum(expected_discount(t) for t in totals)
        out = subprocess.run([sys.executable, "-m", "shop", "report", "data/orders.csv"], cwd=ROOT,
                             capture_output=True, text=True, timeout=120).stdout
        self.assertIn(f"gross: {want_gross:.2f}", out)
        self.assertIn(f"discount: {want_disc:.2f}", out)
        self.assertIn(f"net: {want_gross - want_disc:.2f}", out)


class ImporterTest(unittest.TestCase):
    def test_parse_price(self):
        for text, want in (("12,50", "12.50"), (" 3.5 ", "3.50"), ("0,99", "0.99")):
            got = importer.parse_price(text)
            self.assertIsInstance(got, Decimal)
            self.assertEqual(got, Decimal(want))

    def test_import_files_give_decimal_prices(self):
        with contextlib.redirect_stdout(io.StringIO()):
            a = importer.import_file(str(ROOT / "data" / "supplier-a.csv"))
            b = importer.import_file(str(ROOT / "data" / "supplier-b.csv"))
        with open(ROOT / "data" / "supplier-a.csv", newline="", encoding="utf-8") as handle:
            raw_a = [r["price"] for r in csv.DictReader(handle)]
        self.assertEqual([r["price"] for r in a], [Decimal(p) for p in raw_a])
        for row in a + b:
            self.assertIsInstance(row["price"], Decimal)
        by_sku = {r["sku"]: r["price"] for r in b}
        self.assertEqual(by_sku["B-0037"], Decimal("12.50"))
        self.assertEqual(by_sku["B-0001"], Decimal("26.64"))


class NoFloatTest(unittest.TestCase):
    def test_no_float_in_shop(self):
        problems = []
        for path in sorted((ROOT / "shop").glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "float":
                    problems.append(f"{path.name}:{node.lineno} float()")
                elif isinstance(node, ast.Constant) and isinstance(node.value, float):
                    problems.append(f"{path.name}:{node.lineno} literal {node.value!r}")
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
