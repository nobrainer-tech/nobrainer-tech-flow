import unittest

from shop.invoice import render_invoice
from shop.orders import Order, describe
from shop.report import summarize_orders


class InvoiceTest(unittest.TestCase):
    def test_invoice_lines(self):
        text = render_invoice(Order("I1", 600.0))
        self.assertIn("total: 600.00", text)
        self.assertIn("discount: 30.00", text)
        self.assertIn("to pay: 570.00", text)

    def test_describe(self):
        self.assertEqual(describe(Order("I2", 12.5, "paid")), "I2: 12.50 (paid)")

    def test_summarize_orders(self):
        self.assertEqual(summarize_orders([Order("I3", 100.0), Order("I4", 50.5)])["gross"], 150.5)


if __name__ == "__main__":
    unittest.main()
