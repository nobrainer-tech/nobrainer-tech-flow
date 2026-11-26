import subprocess
import sys
import unittest

from shop.invoice import render_invoice


class InvoiceTest(unittest.TestCase):
    def test_small_order_has_no_discount(self):
        text = render_invoice("O-900", 120.0)
        self.assertIn("discount: 0.00", text)
        self.assertIn("to pay: 120.00", text)

    def test_top_tier(self):
        text = render_invoice("O-901", 1200.0)
        self.assertIn("discount: 120.00", text)
        self.assertIn("to pay: 1080.00", text)

    def test_cli_invoice(self):
        run = subprocess.run([sys.executable, "-m", "shop", "invoice", "O-029"], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("discount: 100.00", run.stdout)


if __name__ == "__main__":
    unittest.main()
