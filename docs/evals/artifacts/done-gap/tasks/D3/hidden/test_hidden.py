import csv
import glob
import os
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal, ROUND_HALF_UP

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CENT = Decimal("0.01")


def discount(total):
    rate = Decimal("0.10") if total >= 1000 else Decimal("0.05") if total >= 500 else Decimal("0")
    return (total * rate).quantize(CENT, rounding=ROUND_HALF_UP)


def expected_blocks(path):
    """Independent computation: {code: (orders, gross, discount, net)} as strings, in print order."""
    with open(path, newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    groups = {}
    for row in rows:
        code = (row.get("currency") or "").strip().upper() or "PLN"
        groups.setdefault(code, []).append(Decimal(row["total"]))
    result = []
    for code in sorted(groups, key=lambda c: (c != "PLN", c)):
        totals = groups[code]
        gross = sum(totals)
        disc = sum(discount(t) for t in totals)
        result.append((code, [str(len(totals)), f"{gross:.2f}", f"{disc:.2f}", f"{gross - disc:.2f}"]))
    return result


def run_report(path):
    return subprocess.run([sys.executable, "-m", "shop", "report", path], cwd=ROOT, capture_output=True, text=True)


def parse_blocks(stdout):
    blocks = []
    for chunk in stdout.strip().replace("\r\n", "\n").split("\n\n"):
        fields = [line.split(": ", 1) for line in chunk.splitlines()]
        keys = [k for k, _ in fields]
        assert keys == ["currency", "orders", "gross", "discount", "net"], chunk
        blocks.append((fields[0][1], [v for _, v in fields[1:]]))
    return blocks


def all_orders_files():
    files = sorted(glob.glob(os.path.join(ROOT, "data", "orders*.csv")))
    files += sorted(glob.glob(os.path.join(ROOT, "data", "archive", "*.csv")))
    return files


class HiddenTest(unittest.TestCase):
    def test_files_exist(self):
        names = [os.path.relpath(p, ROOT) for p in all_orders_files()]
        self.assertGreaterEqual(len(names), 6, names)

    def test_every_orders_file_reports_per_currency(self):
        for path in all_orders_files():
            with self.subTest(file=os.path.relpath(path, ROOT)):
                run = run_report(path)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(parse_blocks(run.stdout), expected_blocks(path))

    def test_pln_first_then_alphabetical(self):
        path = os.path.join(ROOT, "data", "orders-eur.csv")
        codes = [code for code, _ in parse_blocks(run_report(path).stdout)]
        self.assertEqual(codes, ["PLN", "EUR", "USD"])

    def test_no_column_is_one_pln_block(self):
        path = os.path.join(ROOT, "data", "archive", "2025-12.csv")
        blocks = parse_blocks(run_report(path).stdout)
        self.assertEqual([code for code, _ in blocks], ["PLN"])

    def test_case_folding_and_empty_cells(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "mixed.csv")
            with open(path, "w", newline="", encoding="utf-8") as handle:
                handle.write(
                    "order_id,customer,currency,total\r\n"
                    "M-1,C-1,eur,100.00\r\n"
                    "M-2,C-2,Eur,600.00\r\n"
                    "M-3,C-3,,1000.00\r\n"
                    "M-4,C-4,pln,50.00\r\n"
                    "M-5,C-5,EUR,20.00\r\n"
                    "M-6,C-6,usd,700.00\r\n"
                )
            blocks = parse_blocks(run_report(path).stdout)
        self.assertEqual(blocks, [
            ("PLN", ["2", "1050.00", "100.00", "950.00"]),
            ("EUR", ["3", "720.00", "30.00", "690.00"]),
            ("USD", ["1", "700.00", "35.00", "665.00"]),
        ])

    def test_discount_is_per_order_not_per_currency_total(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "split.csv")
            with open(path, "w", newline="", encoding="utf-8") as handle:
                handle.write("order_id,customer,currency,total\nS-1,C-1,EUR,400.00\nS-2,C-2,EUR,400.00\n")
            blocks = parse_blocks(run_report(path).stdout)
        self.assertEqual(blocks, [("EUR", ["2", "800.00", "0.00", "800.00"])])


if __name__ == "__main__":
    unittest.main()
