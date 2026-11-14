import io, unittest
from contextlib import redirect_stdout
from shop.importer import import_file

class T2(unittest.TestCase):
    def load(self, path):
        with redirect_stdout(io.StringIO()):
            return import_file(path)

    def test_supplier_b_decimal_comma(self):
        rows = self.load("data/supplier-b.csv")
        self.assertEqual(len(rows), 200)
        row = next(r for r in rows if r["sku"] == "B-0037")
        self.assertAlmostEqual(row["price"], 12.5)
        self.assertTrue(all(isinstance(r["price"], float) for r in rows))

    def test_supplier_a_unchanged(self):
        rows = self.load("data/supplier-a.csv")
        self.assertEqual(len(rows), 2000)
        self.assertEqual(round(sum(r["price"] for r in rows), 2), EXPECTED_A)

EXPECTED_A = 985431.55
