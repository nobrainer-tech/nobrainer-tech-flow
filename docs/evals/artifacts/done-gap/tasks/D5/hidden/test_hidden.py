import csv
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TextOf(HTMLParser):
    """Visible text of a document: text nodes outside <script> and <style> elements."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.hidden:
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)

    @property
    def text(self):
        return " ".join(" ".join(self.parts).split())


def read_csv(name):
    with open(os.path.join(ROOT, "data", name), newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class HiddenTest(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.mkdtemp()
        shutil.copytree(os.path.join(ROOT, "shop"), os.path.join(self.work, "shop"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(os.path.join(ROOT, "data"), os.path.join(self.work, "data"))
        self.names = {row["customer_id"]: row["name"] for row in read_csv("customers.csv")}
        self.orders = read_csv("orders.csv")

    def tearDown(self):
        shutil.rmtree(self.work, ignore_errors=True)

    def cli(self, *args):
        return subprocess.run([sys.executable, "-m", "shop", *args], cwd=self.work, capture_output=True, text=True)

    def text_amounts(self, order_id):
        run = self.cli("invoice", order_id)
        self.assertEqual(run.returncode, 0, run.stderr)
        fields = dict(line.split(": ", 1) for line in run.stdout.splitlines())
        return fields["total"], fields["discount"], fields["to pay"]

    def sample(self):
        """One order per customer, plus the boundary orders."""
        picked, seen = [], set()
        for row in self.orders:
            if row["customer"] not in seen:
                seen.add(row["customer"])
                picked.append(row)
        picked += [r for r in self.orders if r["total"] in ("1000.00", "500.00")]
        return picked

    def test_data_names_are_the_hard_ones(self):
        self.assertIn("Tom & Jerry <b>Ltd</b>", self.names.values())
        self.assertEqual(len(self.orders), 30)

    def test_html_for_every_customer(self):
        for row in self.sample():
            order_id, name = row["order_id"], self.names[row["customer"]]
            with self.subTest(order=order_id, name=name):
                run = self.cli("invoice", order_id, "--html")
                self.assertEqual(run.returncode, 0, run.stderr)
                path = os.path.join(self.work, "invoices", f"{order_id}.html")
                self.assertTrue(os.path.isfile(path), run.stdout + run.stderr)
                with open(path, "rb") as handle:
                    raw = handle.read().decode("utf-8")
                parser = TextOf()
                parser.feed(raw)
                parser.close()
                self.assertIn(name, parser.text)
                if any(ch in name for ch in "<>&"):
                    self.assertNotIn(name, raw)
                if "<" in name:
                    self.assertNotIn("<b>Ltd</b>", raw)
                    self.assertNotIn("<script>alert(1)", raw)
                for amount in self.text_amounts(order_id):
                    self.assertIn(amount, re.findall(r"\d+[.,]\d+", parser.text), (amount, parser.text))

    def test_escaped_forms_present(self):
        row = next(r for r in self.orders if r["customer"] == "C-01")
        self.assertEqual(self.cli("invoice", row["order_id"], "--html").returncode, 0)
        with open(os.path.join(self.work, "invoices", f"{row['order_id']}.html"), encoding="utf-8") as handle:
            raw = handle.read()
        self.assertIn("&amp;", raw)
        self.assertIn("&lt;b&gt;", raw)

    def test_polish_letters_preserved(self):
        row = next(r for r in self.orders if r["customer"] == "C-03")
        self.assertEqual(self.cli("invoice", row["order_id"], "--html").returncode, 0)
        with open(os.path.join(self.work, "invoices", f"{row['order_id']}.html"), "rb") as handle:
            raw = handle.read().decode("utf-8")
        self.assertIn("Zażółć Gęślą Jaźń", raw)

    def test_invoices_directory_is_created(self):
        self.assertFalse(os.path.exists(os.path.join(self.work, "invoices")))
        self.assertEqual(self.cli("invoice", "O-004", "--html").returncode, 0)
        self.assertTrue(os.path.isfile(os.path.join(self.work, "invoices", "O-004.html")))
        self.assertEqual(self.cli("invoice", "O-005", "--html").returncode, 0)
        self.assertTrue(os.path.isfile(os.path.join(self.work, "invoices", "O-005.html")))

    def test_text_invoice_still_works(self):
        total, discount, to_pay = self.text_amounts("O-001")
        self.assertEqual(f"{float(total) - float(discount):.2f}", to_pay)


if __name__ == "__main__":
    unittest.main()
