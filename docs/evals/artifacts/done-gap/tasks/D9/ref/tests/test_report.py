import unittest
from decimal import Decimal

from shop.report import render_text, summarize


class ReportTest(unittest.TestCase):
    def test_small_orders(self):
        text = render_text(summarize([Decimal("100.00"), Decimal("250.50")]))
        self.assertIn("gross: 350.50", text)
        self.assertIn("discount: 0.00", text)


if __name__ == "__main__":
    unittest.main()
