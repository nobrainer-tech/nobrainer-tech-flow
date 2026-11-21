import unittest

from shop.report import render_text, summarize, summarize_rows


class ReportTest(unittest.TestCase):
    def test_small_orders(self):
        text = render_text(summarize([100.0, 250.5]))
        self.assertIn("gross: 350.50", text)
        self.assertIn("discount: 0.00", text)

    def test_rows(self):
        rows = [{"total": "100.00", "status": "paid"}, {"total": "250.50", "status": "shipped"}]
        summary = summarize_rows(rows)
        self.assertEqual(summary["orders"], 2)
        self.assertEqual(summary["gross"], 350.5)

    def test_discount_tiers(self):
        rows = [{"total": "600.00", "status": "paid"}, {"total": "1000.00", "status": "paid"}]
        self.assertEqual(summarize_rows(rows)["discount"], 130.0)


if __name__ == "__main__":
    unittest.main()
