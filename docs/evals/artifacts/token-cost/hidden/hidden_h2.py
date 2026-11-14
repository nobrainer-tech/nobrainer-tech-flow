import io, os, tempfile, unittest
from contextlib import redirect_stdout
from shop.importer import import_file

def load(path):
    with redirect_stdout(io.StringIO()):
        return import_file(path)

def load_text(text):
    handle, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(handle, "w", encoding="utf-8") as out:
        out.write(text)
    try:
        return load(path)
    finally:
        os.unlink(path)

class H2(unittest.TestCase):
    def test_supplier_c(self):
        rows = {r["sku"]: r for r in load("data/supplier-c.csv")}
        self.assertEqual(len(rows), 40)
        self.assertEqual(rows["C-0007"]["name"], "bolt; zinc")
        self.assertAlmostEqual(rows["C-0007"]["price"], 1234.5)
        self.assertAlmostEqual(rows["C-0008"]["price"], 12.5)
        self.assertAlmostEqual(rows["C-0009"]["price"], 7.0)
        self.assertAlmostEqual(rows["C-0010"]["price"], 30010.1)
        self.assertTrue(all(isinstance(r["price"], float) for r in rows.values()))

    def test_existing_files(self):
        self.assertEqual(len(load("data/supplier-a.csv")), 2000)
        rows = {r["sku"]: r for r in load("data/supplier-b.csv")}
        self.assertEqual(len(rows), 200)
        self.assertAlmostEqual(rows["B-0037"]["price"], 12.5)

    def test_comma_file_with_thousands(self):
        rows = load_text('sku,name,qty,price\nX-1,a,1,"1,234.50"\nX-2,b,1,2.5\n')
        self.assertAlmostEqual(rows[0]["price"], 1234.5)
        self.assertAlmostEqual(rows[1]["price"], 2.5)
